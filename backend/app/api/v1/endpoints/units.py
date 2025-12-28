"""
Units endpoints with filtering.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from app.db.database import get_db
from app.models.unit import Unit, UnitStatus, UnitType, ViewType
from app.models.project import Project
from app.models.user import User, UserRole
from app.api.v1.endpoints.auth import get_current_user
from app.api.v1.endpoints.projects import get_visibility_filter

router = APIRouter()


# Schemas
class UnitListItem(BaseModel):
    id: int
    unit_number: str
    building: Optional[str]
    floor: Optional[int]
    
    unit_type: str
    bedrooms: int
    bathrooms: Optional[float]
    
    layout_name: Optional[str]
    layout_image_url: Optional[str]
    
    area_sqm: float
    area_sqft: Optional[float]
    
    view_type: Optional[str]
    view_description: Optional[str]
    
    price: Optional[float]
    currency: str
    price_usd: Optional[float]
    price_per_sqm: Optional[float]
    price_per_sqm_usd: Optional[float]
    
    # Price change
    previous_price_usd: Optional[float]
    price_change_percent: Optional[float]
    
    # Payment
    downpayment_percent: Optional[float]
    downpayment_amount_usd: Optional[float]
    
    status: str
    is_active: bool
    
    class Config:
        from_attributes = True


class UnitDetail(UnitListItem):
    project_id: int
    phase_id: Optional[int]
    
    indoor_area: Optional[float]
    outdoor_area: Optional[float]
    land_area: Optional[float]
    
    features: Optional[List[str]]
    furniture: Optional[str]
    images: Optional[List[str]]
    floor_plan_url: Optional[str]
    
    last_price_update: Optional[str]
    
    class Config:
        from_attributes = True


class UnitListResponse(BaseModel):
    items: List[UnitListItem]
    total: int
    page: int
    page_size: int
    
    # Aggregates
    price_range: dict
    area_range: dict
    floor_range: dict
    available_types: List[dict]
    status_counts: dict


class UnitFilters(BaseModel):
    # Price
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    
    # Area
    area_min: Optional[float] = None
    area_max: Optional[float] = None
    
    # Floor
    floor_min: Optional[int] = None
    floor_max: Optional[int] = None
    
    # Type
    unit_types: Optional[List[str]] = None
    bedrooms: Optional[List[int]] = None
    
    # View
    view_types: Optional[List[str]] = None
    
    # Status
    status: Optional[List[str]] = None
    
    # Phase
    phase_id: Optional[int] = None


def apply_unit_filters(query, filters: UnitFilters):
    """Apply filters to unit query."""
    
    # Price range
    if filters.price_min:
        query = query.where(Unit.price_usd >= filters.price_min)
    if filters.price_max:
        query = query.where(Unit.price_usd <= filters.price_max)
    
    # Area range
    if filters.area_min:
        query = query.where(Unit.area_sqm >= filters.area_min)
    if filters.area_max:
        query = query.where(Unit.area_sqm <= filters.area_max)
    
    # Floor range
    if filters.floor_min:
        query = query.where(Unit.floor >= filters.floor_min)
    if filters.floor_max:
        query = query.where(Unit.floor <= filters.floor_max)
    
    # Unit types
    if filters.unit_types:
        query = query.where(Unit.unit_type.in_(filters.unit_types))
    
    # Bedrooms
    if filters.bedrooms:
        query = query.where(Unit.bedrooms.in_(filters.bedrooms))
    
    # View types
    if filters.view_types:
        query = query.where(Unit.view_type.in_(filters.view_types))
    
    # Status
    if filters.status:
        query = query.where(Unit.status.in_(filters.status))
    else:
        # Default: only available and reserved
        query = query.where(Unit.status.in_([UnitStatus.AVAILABLE, UnitStatus.RESERVED]))
    
    # Phase
    if filters.phase_id:
        query = query.where(Unit.phase_id == filters.phase_id)
    
    return query


async def get_units_aggregates(db: AsyncSession, project_id: int) -> dict:
    """Get aggregate statistics for units in a project."""
    
    # Price range
    price_result = await db.execute(
        select(
            func.min(Unit.price_usd).label("min_price"),
            func.max(Unit.price_usd).label("max_price")
        ).where(
            Unit.project_id == project_id,
            Unit.is_active == True,
            Unit.status.in_([UnitStatus.AVAILABLE, UnitStatus.RESERVED])
        )
    )
    price_row = price_result.one()
    
    # Area range
    area_result = await db.execute(
        select(
            func.min(Unit.area_sqm).label("min_area"),
            func.max(Unit.area_sqm).label("max_area")
        ).where(
            Unit.project_id == project_id,
            Unit.is_active == True,
            Unit.status.in_([UnitStatus.AVAILABLE, UnitStatus.RESERVED])
        )
    )
    area_row = area_result.one()
    
    # Floor range
    floor_result = await db.execute(
        select(
            func.min(Unit.floor).label("min_floor"),
            func.max(Unit.floor).label("max_floor")
        ).where(
            Unit.project_id == project_id,
            Unit.is_active == True,
            Unit.floor.isnot(None)
        )
    )
    floor_row = floor_result.one()
    
    # Available types with counts
    types_result = await db.execute(
        select(
            Unit.unit_type,
            Unit.bedrooms,
            func.count(Unit.id).label("count"),
            func.min(Unit.price_usd).label("min_price")
        ).where(
            Unit.project_id == project_id,
            Unit.is_active == True,
            Unit.status.in_([UnitStatus.AVAILABLE, UnitStatus.RESERVED])
        ).group_by(Unit.unit_type, Unit.bedrooms)
        .order_by(Unit.bedrooms)
    )
    types = [
        {
            "unit_type": row.unit_type,
            "bedrooms": row.bedrooms,
            "count": row.count,
            "min_price": row.min_price
        }
        for row in types_result.all()
    ]
    
    # Status counts
    status_result = await db.execute(
        select(
            Unit.status,
            func.count(Unit.id).label("count")
        ).where(
            Unit.project_id == project_id,
            Unit.is_active == True
        ).group_by(Unit.status)
    )
    status_counts = {row.status.value: row.count for row in status_result.all()}
    
    return {
        "price_range": {
            "min": price_row.min_price,
            "max": price_row.max_price
        },
        "area_range": {
            "min": area_row.min_area,
            "max": area_row.max_area
        },
        "floor_range": {
            "min": floor_row.min_floor,
            "max": floor_row.max_floor
        },
        "available_types": types,
        "status_counts": status_counts
    }


# Endpoints
@router.get("/project/{project_id}", response_model=UnitListResponse)
async def list_project_units(
    project_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    sort_by: str = Query("price_asc", regex="^(price_asc|price_desc|area_asc|area_desc|floor_asc|floor_desc|bedrooms)$"),
    # Filters
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    area_min: Optional[float] = None,
    area_max: Optional[float] = None,
    floor_min: Optional[int] = None,
    floor_max: Optional[int] = None,
    unit_types: Optional[str] = None,  # comma-separated
    bedrooms: Optional[str] = None,  # comma-separated
    view_types: Optional[str] = None,  # comma-separated
    status: Optional[str] = None,  # comma-separated
    phase_id: Optional[int] = None,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List units for a project with filters."""
    
    # Check project exists and user has access
    visibility = get_visibility_filter(current_user)
    project_result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.is_active == True,
            Project.visibility.in_(visibility)
        )
    )
    project = project_result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Parse filters
    filters = UnitFilters(
        price_min=price_min,
        price_max=price_max,
        area_min=area_min,
        area_max=area_max,
        floor_min=floor_min,
        floor_max=floor_max,
        unit_types=unit_types.split(",") if unit_types else None,
        bedrooms=[int(x) for x in bedrooms.split(",")] if bedrooms else None,
        view_types=view_types.split(",") if view_types else None,
        status=status.split(",") if status else None,
        phase_id=phase_id
    )
    
    # Build query
    query = select(Unit).where(
        Unit.project_id == project_id,
        Unit.is_active == True,
        Unit.deleted_at.is_(None)
    )
    query = apply_unit_filters(query, filters)
    
    # Sorting
    if sort_by == "price_asc":
        query = query.order_by(Unit.price_usd.asc().nullslast())
    elif sort_by == "price_desc":
        query = query.order_by(Unit.price_usd.desc().nullslast())
    elif sort_by == "area_asc":
        query = query.order_by(Unit.area_sqm.asc())
    elif sort_by == "area_desc":
        query = query.order_by(Unit.area_sqm.desc())
    elif sort_by == "floor_asc":
        query = query.order_by(Unit.floor.asc().nullslast())
    elif sort_by == "floor_desc":
        query = query.order_by(Unit.floor.desc().nullslast())
    elif sort_by == "bedrooms":
        query = query.order_by(Unit.bedrooms.asc(), Unit.price_usd.asc())
    
    # Count total
    count_query = select(func.count(Unit.id)).where(
        Unit.project_id == project_id,
        Unit.is_active == True,
        Unit.deleted_at.is_(None)
    )
    count_query = apply_unit_filters(count_query, filters)
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    units = result.scalars().all()
    
    # Get aggregates
    aggregates = await get_units_aggregates(db, project_id)
    
    return UnitListResponse(
        items=units,
        total=total,
        page=page,
        page_size=page_size,
        **aggregates
    )


@router.get("/{unit_id}", response_model=UnitDetail)
async def get_unit(
    unit_id: int,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get unit details by ID."""
    
    result = await db.execute(
        select(Unit)
        .options(selectinload(Unit.project))
        .where(
            Unit.id == unit_id,
            Unit.is_active == True,
            Unit.deleted_at.is_(None)
        )
    )
    unit = result.scalar_one_or_none()
    
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit not found"
        )
    
    # Check project visibility
    visibility = get_visibility_filter(current_user)
    if unit.project.visibility not in visibility:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit not found"
        )
    
    return unit


@router.get("/compare", response_model=List[UnitDetail])
async def compare_units(
    unit_ids: str = Query(..., description="Comma-separated unit IDs"),
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Compare multiple units side by side."""
    
    ids = [int(x) for x in unit_ids.split(",")]
    
    if len(ids) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 units for comparison"
        )
    
    result = await db.execute(
        select(Unit)
        .options(selectinload(Unit.project))
        .where(
            Unit.id.in_(ids),
            Unit.is_active == True,
            Unit.deleted_at.is_(None)
        )
    )
    units = result.scalars().all()
    
    # Filter by visibility
    visibility = get_visibility_filter(current_user)
    units = [u for u in units if u.project.visibility in visibility]
    
    return units
