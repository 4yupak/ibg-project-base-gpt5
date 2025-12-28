"""
Prices endpoints - price versions, history, ingestion.
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from app.db.database import get_db
from app.models.price import PriceVersion, PriceHistory, PaymentPlan, PriceVersionStatus, PriceSourceType
from app.models.project import Project
from app.models.unit import Unit
from app.models.user import User, UserRole
from app.api.v1.endpoints.auth import get_current_user, require_roles

router = APIRouter()


# Schemas
class PriceVersionResponse(BaseModel):
    id: int
    project_id: int
    version_number: int
    source_type: str
    source_file_name: Optional[str]
    status: str
    
    processing_started_at: Optional[datetime]
    processing_completed_at: Optional[datetime]
    
    units_created: int
    units_updated: int
    units_unchanged: int
    units_errors: int
    
    original_currency: str
    exchange_rate_usd: Optional[float]
    
    errors: Optional[List[dict]]
    warnings: Optional[List[dict]]
    
    reviewed_at: Optional[datetime]
    review_notes: Optional[str]
    
    created_at: datetime
    
    class Config:
        from_attributes = True


class PriceVersionListResponse(BaseModel):
    items: List[PriceVersionResponse]
    total: int
    page: int
    page_size: int


class PriceHistoryResponse(BaseModel):
    id: int
    unit_id: int
    price_version_id: int
    
    old_price: Optional[float]
    old_price_usd: Optional[float]
    new_price: Optional[float]
    new_price_usd: Optional[float]
    
    price_change: Optional[float]
    price_change_percent: Optional[float]
    change_type: str
    
    currency: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class UnitPriceHistory(BaseModel):
    unit_number: str
    unit_type: str
    bedrooms: int
    history: List[PriceHistoryResponse]


class PaymentPlanResponse(BaseModel):
    id: int
    project_id: int
    name: str
    name_ru: Optional[str]
    description: Optional[str]
    description_ru: Optional[str]
    schedule: List[dict]
    installment_months: Optional[int]
    is_default: bool
    is_active: bool
    version: int
    
    class Config:
        from_attributes = True


class ReviewRequest(BaseModel):
    approve: bool
    notes: Optional[str] = None


# Endpoints
@router.get("/versions/project/{project_id}", response_model=PriceVersionListResponse)
async def list_price_versions(
    project_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ANALYST)),
    db: AsyncSession = Depends(get_db)
):
    """List price versions for a project."""
    query = select(PriceVersion).where(
        PriceVersion.project_id == project_id
    ).order_by(PriceVersion.created_at.desc())
    
    # Count
    count_query = select(func.count(PriceVersion.id)).where(
        PriceVersion.project_id == project_id
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    versions = result.scalars().all()
    
    return PriceVersionListResponse(
        items=versions,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/versions/{version_id}", response_model=PriceVersionResponse)
async def get_price_version(
    version_id: int,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ANALYST)),
    db: AsyncSession = Depends(get_db)
):
    """Get price version details."""
    result = await db.execute(
        select(PriceVersion).where(PriceVersion.id == version_id)
    )
    version = result.scalar_one_or_none()
    
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Price version not found"
        )
    
    return version


@router.post("/versions/{version_id}/review")
async def review_price_version(
    version_id: int,
    data: ReviewRequest,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Approve or reject a price version."""
    result = await db.execute(
        select(PriceVersion).where(PriceVersion.id == version_id)
    )
    version = result.scalar_one_or_none()
    
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Price version not found"
        )
    
    if version.status not in [PriceVersionStatus.REQUIRES_REVIEW, PriceVersionStatus.COMPLETED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Price version cannot be reviewed in current status"
        )
    
    version.reviewed_at = datetime.utcnow()
    version.reviewed_by_id = current_user.id
    version.review_notes = data.notes
    version.status = PriceVersionStatus.APPROVED if data.approve else PriceVersionStatus.REJECTED
    
    # If approved, update project's requires_review flag
    if data.approve:
        project = await db.get(Project, version.project_id)
        if project:
            project.requires_review = False
            project.verified_at = datetime.utcnow()
            project.verified_by_id = current_user.id
    
    await db.commit()
    
    return {"message": f"Price version {'approved' if data.approve else 'rejected'}"}


@router.get("/history/unit/{unit_id}", response_model=List[PriceHistoryResponse])
async def get_unit_price_history(
    unit_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get price history for a specific unit."""
    result = await db.execute(
        select(PriceHistory)
        .where(PriceHistory.unit_id == unit_id)
        .order_by(PriceHistory.created_at.desc())
        .limit(50)
    )
    
    return result.scalars().all()


@router.get("/history/project/{project_id}", response_model=List[UnitPriceHistory])
async def get_project_price_history(
    project_id: int,
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ANALYST)),
    db: AsyncSession = Depends(get_db)
):
    """Get price history for all units in a project (was/became)."""
    # Get units with price changes
    units_result = await db.execute(
        select(Unit)
        .where(
            Unit.project_id == project_id,
            Unit.previous_price.isnot(None)
        )
        .order_by(Unit.unit_number)
        .limit(limit)
    )
    units = units_result.scalars().all()
    
    result = []
    for unit in units:
        history_result = await db.execute(
            select(PriceHistory)
            .where(PriceHistory.unit_id == unit.id)
            .order_by(PriceHistory.created_at.desc())
            .limit(10)
        )
        history = history_result.scalars().all()
        
        result.append(UnitPriceHistory(
            unit_number=unit.unit_number,
            unit_type=unit.unit_type.value,
            bedrooms=unit.bedrooms,
            history=history
        ))
    
    return result


@router.get("/payment-plans/project/{project_id}", response_model=List[PaymentPlanResponse])
async def get_payment_plans(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get payment plans for a project."""
    result = await db.execute(
        select(PaymentPlan)
        .where(
            PaymentPlan.project_id == project_id,
            PaymentPlan.is_active == True
        )
        .order_by(PaymentPlan.is_default.desc())
    )
    
    return result.scalars().all()


@router.get("/requires-review", response_model=PriceVersionListResponse)
async def list_versions_requiring_review(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ANALYST)),
    db: AsyncSession = Depends(get_db)
):
    """List all price versions that require review."""
    query = select(PriceVersion).where(
        PriceVersion.status == PriceVersionStatus.REQUIRES_REVIEW
    ).order_by(PriceVersion.created_at.desc())
    
    # Count
    count_query = select(func.count(PriceVersion.id)).where(
        PriceVersion.status == PriceVersionStatus.REQUIRES_REVIEW
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    versions = result.scalars().all()
    
    return PriceVersionListResponse(
        items=versions,
        total=total,
        page=page,
        page_size=page_size
    )
