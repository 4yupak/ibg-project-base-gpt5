"""
Analytics endpoints - dashboards, stats, exports.
"""
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case
from pydantic import BaseModel
import io
import csv

from app.db.database import get_db
from app.models.project import Project, ProjectStatus
from app.models.unit import Unit, UnitStatus, UnitType
from app.models.price import PriceVersion, PriceHistory, PriceVersionStatus
from app.models.collection import Collection, CollectionEvent
from app.models.audit import ParsingError
from app.models.user import User, UserRole
from app.api.v1.endpoints.auth import require_roles

router = APIRouter()


# Schemas
class ProjectStats(BaseModel):
    total_units: int
    available_units: int
    reserved_units: int
    sold_units: int
    sold_percent: float
    
    by_type: List[dict]
    by_bedrooms: List[dict]


class WeeklyData(BaseModel):
    week: str
    value: float


class ProjectAnalytics(BaseModel):
    project_id: int
    project_name: str
    stats: ProjectStats
    weekly_sales: List[WeeklyData]
    weekly_price_changes: List[WeeklyData]


class DashboardSummary(BaseModel):
    total_projects: int
    total_units: int
    available_units: int
    sold_units: int
    average_price_usd: Optional[float]
    
    projects_by_status: dict
    units_by_type: dict
    
    recent_price_updates: int
    pending_reviews: int
    parsing_errors: int


class ParsingErrorResponse(BaseModel):
    id: int
    project_id: Optional[int]
    project_name: Optional[str]
    error_type: str
    error_message: str
    source_file: Optional[str]
    is_resolved: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# Endpoints
@router.get("/dashboard", response_model=DashboardSummary)
async def get_dashboard(
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ANALYST)),
    db: AsyncSession = Depends(get_db)
):
    """Get dashboard summary statistics."""
    
    # Total projects
    projects_count = await db.execute(
        select(func.count(Project.id)).where(
            Project.is_active == True,
            Project.deleted_at.is_(None)
        )
    )
    total_projects = projects_count.scalar()
    
    # Total units
    units_result = await db.execute(
        select(
            func.count(Unit.id).label("total"),
            func.sum(case((Unit.status == UnitStatus.AVAILABLE, 1), else_=0)).label("available"),
            func.sum(case((Unit.status == UnitStatus.SOLD, 1), else_=0)).label("sold"),
            func.avg(Unit.price_usd).label("avg_price")
        ).where(
            Unit.is_active == True,
            Unit.deleted_at.is_(None)
        )
    )
    units_row = units_result.one()
    
    # Projects by status
    status_result = await db.execute(
        select(
            Project.status,
            func.count(Project.id)
        ).where(
            Project.is_active == True,
            Project.deleted_at.is_(None)
        ).group_by(Project.status)
    )
    projects_by_status = {row[0].value: row[1] for row in status_result.all()}
    
    # Units by type
    type_result = await db.execute(
        select(
            Unit.unit_type,
            func.count(Unit.id)
        ).where(
            Unit.is_active == True,
            Unit.status == UnitStatus.AVAILABLE
        ).group_by(Unit.unit_type)
    )
    units_by_type = {row[0].value: row[1] for row in type_result.all()}
    
    # Recent price updates (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_updates = await db.execute(
        select(func.count(PriceVersion.id)).where(
            PriceVersion.created_at >= week_ago,
            PriceVersion.status == PriceVersionStatus.COMPLETED
        )
    )
    
    # Pending reviews
    pending_reviews = await db.execute(
        select(func.count(PriceVersion.id)).where(
            PriceVersion.status == PriceVersionStatus.REQUIRES_REVIEW
        )
    )
    
    # Parsing errors
    parsing_errors = await db.execute(
        select(func.count(ParsingError.id)).where(
            ParsingError.is_resolved == False
        )
    )
    
    return DashboardSummary(
        total_projects=total_projects,
        total_units=units_row.total or 0,
        available_units=units_row.available or 0,
        sold_units=units_row.sold or 0,
        average_price_usd=float(units_row.avg_price) if units_row.avg_price else None,
        projects_by_status=projects_by_status,
        units_by_type=units_by_type,
        recent_price_updates=recent_updates.scalar(),
        pending_reviews=pending_reviews.scalar(),
        parsing_errors=parsing_errors.scalar()
    )


@router.get("/project/{project_id}", response_model=ProjectAnalytics)
async def get_project_analytics(
    project_id: int,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ANALYST, UserRole.AGENT)),
    db: AsyncSession = Depends(get_db)
):
    """Get analytics for a specific project."""
    
    # Get project
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Unit stats
    stats_result = await db.execute(
        select(
            func.count(Unit.id).label("total"),
            func.sum(case((Unit.status == UnitStatus.AVAILABLE, 1), else_=0)).label("available"),
            func.sum(case((Unit.status == UnitStatus.RESERVED, 1), else_=0)).label("reserved"),
            func.sum(case((Unit.status == UnitStatus.SOLD, 1), else_=0)).label("sold")
        ).where(
            Unit.project_id == project_id,
            Unit.is_active == True
        )
    )
    stats_row = stats_result.one()
    
    total = stats_row.total or 0
    sold = stats_row.sold or 0
    sold_percent = (sold / total * 100) if total > 0 else 0
    
    # By type
    type_result = await db.execute(
        select(
            Unit.unit_type,
            func.count(Unit.id).label("total"),
            func.sum(case((Unit.status == UnitStatus.AVAILABLE, 1), else_=0)).label("available")
        ).where(
            Unit.project_id == project_id,
            Unit.is_active == True
        ).group_by(Unit.unit_type)
    )
    by_type = [
        {"type": row.unit_type.value, "total": row.total, "available": row.available}
        for row in type_result.all()
    ]
    
    # By bedrooms
    bedroom_result = await db.execute(
        select(
            Unit.bedrooms,
            func.count(Unit.id).label("total"),
            func.sum(case((Unit.status == UnitStatus.AVAILABLE, 1), else_=0)).label("available")
        ).where(
            Unit.project_id == project_id,
            Unit.is_active == True
        ).group_by(Unit.bedrooms)
        .order_by(Unit.bedrooms)
    )
    by_bedrooms = [
        {"bedrooms": row.bedrooms, "total": row.total, "available": row.available}
        for row in bedroom_result.all()
    ]
    
    # Weekly sales (last 12 weeks)
    weekly_sales = []
    for i in range(12):
        week_start = datetime.utcnow() - timedelta(weeks=i+1)
        week_end = datetime.utcnow() - timedelta(weeks=i)
        
        sold_count = await db.execute(
            select(func.count(PriceHistory.id)).where(
                PriceHistory.created_at >= week_start,
                PriceHistory.created_at < week_end,
                PriceHistory.new_status == "sold",
                PriceHistory.unit_id.in_(
                    select(Unit.id).where(Unit.project_id == project_id)
                )
            )
        )
        
        weekly_sales.append(WeeklyData(
            week=week_start.strftime("%Y-%W"),
            value=sold_count.scalar() or 0
        ))
    
    weekly_sales.reverse()
    
    # Weekly price changes
    weekly_price_changes = []
    for i in range(12):
        week_start = datetime.utcnow() - timedelta(weeks=i+1)
        week_end = datetime.utcnow() - timedelta(weeks=i)
        
        avg_change = await db.execute(
            select(func.avg(PriceHistory.price_change_percent)).where(
                PriceHistory.created_at >= week_start,
                PriceHistory.created_at < week_end,
                PriceHistory.price_change_percent.isnot(None),
                PriceHistory.unit_id.in_(
                    select(Unit.id).where(Unit.project_id == project_id)
                )
            )
        )
        
        weekly_price_changes.append(WeeklyData(
            week=week_start.strftime("%Y-%W"),
            value=float(avg_change.scalar() or 0)
        ))
    
    weekly_price_changes.reverse()
    
    return ProjectAnalytics(
        project_id=project_id,
        project_name=project.name_en or project.name_ru or str(project_id),
        stats=ProjectStats(
            total_units=total,
            available_units=stats_row.available or 0,
            reserved_units=stats_row.reserved or 0,
            sold_units=sold,
            sold_percent=sold_percent,
            by_type=by_type,
            by_bedrooms=by_bedrooms
        ),
        weekly_sales=weekly_sales,
        weekly_price_changes=weekly_price_changes
    )


@router.get("/parsing-errors", response_model=List[ParsingErrorResponse])
async def list_parsing_errors(
    resolved: Optional[bool] = None,
    error_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ANALYST)),
    db: AsyncSession = Depends(get_db)
):
    """List parsing errors."""
    query = select(ParsingError)
    
    if resolved is not None:
        query = query.where(ParsingError.is_resolved == resolved)
    
    if error_type:
        query = query.where(ParsingError.error_type == error_type)
    
    query = query.order_by(ParsingError.created_at.desc()).limit(limit)
    
    result = await db.execute(query)
    errors = result.scalars().all()
    
    # Add project names
    response = []
    for error in errors:
        project_name = None
        if error.project_id:
            project = await db.get(Project, error.project_id)
            project_name = project.name_en if project else None
        
        error_dict = {
            "id": error.id,
            "project_id": error.project_id,
            "project_name": project_name,
            "error_type": error.error_type,
            "error_message": error.error_message,
            "source_file": error.source_file,
            "is_resolved": error.is_resolved,
            "created_at": error.created_at
        }
        response.append(ParsingErrorResponse(**error_dict))
    
    return response


@router.get("/export/units")
async def export_units_csv(
    project_id: Optional[int] = None,
    district_id: Optional[int] = None,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ANALYST)),
    db: AsyncSession = Depends(get_db)
):
    """Export units to CSV."""
    query = select(Unit).where(
        Unit.is_active == True,
        Unit.deleted_at.is_(None)
    )
    
    if project_id:
        query = query.where(Unit.project_id == project_id)
    
    if district_id:
        query = query.join(Project).where(Project.district_id == district_id)
    
    result = await db.execute(query)
    units = result.scalars().all()
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "unit_id", "project_id", "unit_number", "unit_type", "bedrooms",
        "area_sqm", "floor", "view_type", "status",
        "price", "currency", "price_usd", "price_per_sqm_usd",
        "previous_price_usd", "price_change_percent"
    ])
    
    # Data
    for unit in units:
        writer.writerow([
            unit.id, unit.project_id, unit.unit_number, unit.unit_type.value, unit.bedrooms,
            unit.area_sqm, unit.floor, unit.view_type.value if unit.view_type else None, unit.status.value,
            unit.price, unit.currency, unit.price_usd, unit.price_per_sqm_usd,
            unit.previous_price_usd, unit.price_change_percent
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=units_export_{datetime.utcnow().strftime('%Y%m%d')}.csv"
        }
    )
