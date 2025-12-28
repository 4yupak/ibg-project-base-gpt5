"""
Projects endpoints with filtering and map support.
"""
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field

from app.db.database import get_db
from app.models.project import Project, Developer, ProjectStatus, PropertyType, OwnershipType
from app.models.location import District, City, Country
from app.models.unit import Unit, UnitStatus
from app.models.user import User, UserRole
from app.api.v1.endpoints.auth import get_current_user, require_roles
from app.core.config import settings

router = APIRouter()


# Schemas
class DeveloperBrief(BaseModel):
    id: int
    name_en: Optional[str]
    name_ru: Optional[str]
    logo_url: Optional[str]
    
    class Config:
        from_attributes = True


class DistrictBrief(BaseModel):
    id: int
    name_en: Optional[str]
    name_ru: Optional[str]
    slug: str
    
    class Config:
        from_attributes = True


class ProjectListItem(BaseModel):
    id: int
    slug: str
    name_en: Optional[str]
    name_ru: Optional[str]
    cover_image_url: Optional[str]
    gallery: Optional[List[str]]
    
    # Location
    lat: Optional[float]
    lng: Optional[float]
    district: Optional[DistrictBrief]
    developer: Optional[DeveloperBrief]
    
    # Type & Status
    property_types: List[str]
    status: str
    construction_progress: Optional[int]
    
    # Completion
    completion_date: Optional[date]
    completion_quarter: Optional[str]
    completion_year: Optional[int]
    
    # Price
    min_price_usd: Optional[float]
    max_price_usd: Optional[float]
    min_price_per_sqm_usd: Optional[float]
    original_currency: str
    last_price_update: Optional[str]
    
    # Stats
    total_units: int
    available_units: int
    min_bedrooms: Optional[int]
    max_bedrooms: Optional[int]
    
    # Flags
    is_featured: bool
    requires_review: bool
    
    class Config:
        from_attributes = True


class ProjectDetail(ProjectListItem):
    description_en: Optional[str]
    description_ru: Optional[str]
    sales_points_en: Optional[str]
    sales_points_ru: Optional[str]
    
    address_en: Optional[str]
    address_ru: Optional[str]
    
    ownership_type: str
    leasehold_years: Optional[int]
    
    master_plan_url: Optional[str]
    video_url: Optional[str]
    virtual_tour_url: Optional[str]
    construction_photos: Optional[List[str]]
    
    amenities: Optional[List[str]]
    features: Optional[List[str]]
    internal_infrastructure_en: Optional[str]
    internal_infrastructure_ru: Optional[str]
    
    min_area: Optional[float]
    max_area: Optional[float]
    
    sold_units: int
    reserved_units: int
    
    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    items: List[ProjectListItem]
    total: int
    page: int
    page_size: int


class MapMarker(BaseModel):
    id: int
    slug: str
    name_en: Optional[str]
    name_ru: Optional[str]
    lat: float
    lng: float
    property_types: List[str]
    min_price_usd: Optional[float]
    available_units: int
    cover_image_url: Optional[str]


class MapResponse(BaseModel):
    markers: List[MapMarker]
    bounds: Optional[dict]


# Filters model
class ProjectFilters(BaseModel):
    # Location
    country_id: Optional[int] = None
    city_id: Optional[int] = None
    district_ids: Optional[List[int]] = None
    
    # Search
    search: Optional[str] = None
    developer_id: Optional[int] = None
    
    # Price
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    
    # Property
    property_types: Optional[List[str]] = None
    bedrooms_min: Optional[int] = None
    bedrooms_max: Optional[int] = None
    
    # Completion
    completion_year_min: Optional[int] = None
    completion_year_max: Optional[int] = None
    status: Optional[List[str]] = None
    
    # Ownership
    ownership_type: Optional[str] = None
    
    # Map bounds
    bounds_north: Optional[float] = None
    bounds_south: Optional[float] = None
    bounds_east: Optional[float] = None
    bounds_west: Optional[float] = None


def apply_project_filters(query, filters: ProjectFilters, visibility_filter: str = None):
    """Apply filters to project query."""
    
    # Visibility filter based on user role
    if visibility_filter:
        query = query.where(Project.visibility.in_(visibility_filter))
    
    # Base filters
    query = query.where(
        Project.is_active == True,
        Project.deleted_at.is_(None)
    )
    
    # Location filters
    if filters.district_ids:
        query = query.where(Project.district_id.in_(filters.district_ids))
    
    # Search
    if filters.search:
        search_term = f"%{filters.search}%"
        query = query.where(
            or_(
                Project.name_en.ilike(search_term),
                Project.name_ru.ilike(search_term),
                Project.slug.ilike(search_term)
            )
        )
    
    # Developer
    if filters.developer_id:
        query = query.where(Project.developer_id == filters.developer_id)
    
    # Price range
    if filters.price_min:
        query = query.where(Project.max_price_usd >= filters.price_min)
    if filters.price_max:
        query = query.where(Project.min_price_usd <= filters.price_max)
    
    # Property types
    if filters.property_types:
        # JSON array contains check
        for pt in filters.property_types:
            query = query.where(Project.property_types.contains([pt]))
    
    # Bedrooms
    if filters.bedrooms_min:
        query = query.where(Project.max_bedrooms >= filters.bedrooms_min)
    if filters.bedrooms_max:
        query = query.where(Project.min_bedrooms <= filters.bedrooms_max)
    
    # Completion year
    if filters.completion_year_min:
        query = query.where(Project.completion_year >= filters.completion_year_min)
    if filters.completion_year_max:
        query = query.where(Project.completion_year <= filters.completion_year_max)
    
    # Status
    if filters.status:
        query = query.where(Project.status.in_(filters.status))
    
    # Ownership
    if filters.ownership_type:
        query = query.where(Project.ownership_type == filters.ownership_type)
    
    # Map bounds
    if all([filters.bounds_north, filters.bounds_south, filters.bounds_east, filters.bounds_west]):
        query = query.where(
            and_(
                Project.lat.isnot(None),
                Project.lng.isnot(None),
                Project.lat <= filters.bounds_north,
                Project.lat >= filters.bounds_south,
                Project.lng <= filters.bounds_east,
                Project.lng >= filters.bounds_west
            )
        )
    
    return query


def get_visibility_filter(user: Optional[User]) -> List[str]:
    """Get visibility filter based on user role."""
    if not user:
        return ["public"]
    
    if user.role in [UserRole.ADMIN, UserRole.AGENT, UserRole.CONTENT_MANAGER, UserRole.ANALYST]:
        return ["public", "internal", "partners_only"]
    elif user.role == UserRole.PARTNER:
        return ["public", "partners_only"]
    else:
        return ["public"]


# Endpoints
@router.get("/", response_model=ProjectListResponse)
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("featured", regex="^(featured|price_asc|price_desc|newest|completion)$"),
    # Filters as query params
    country_id: Optional[int] = None,
    city_id: Optional[int] = None,
    district_ids: Optional[str] = None,  # comma-separated
    search: Optional[str] = None,
    developer_id: Optional[int] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    property_types: Optional[str] = None,  # comma-separated
    bedrooms_min: Optional[int] = None,
    bedrooms_max: Optional[int] = None,
    completion_year_min: Optional[int] = None,
    completion_year_max: Optional[int] = None,
    status: Optional[str] = None,  # comma-separated
    ownership_type: Optional[str] = None,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List projects with filters."""
    # Parse comma-separated values
    filters = ProjectFilters(
        country_id=country_id,
        city_id=city_id,
        district_ids=[int(x) for x in district_ids.split(",")] if district_ids else None,
        search=search,
        developer_id=developer_id,
        price_min=price_min,
        price_max=price_max,
        property_types=property_types.split(",") if property_types else None,
        bedrooms_min=bedrooms_min,
        bedrooms_max=bedrooms_max,
        completion_year_min=completion_year_min,
        completion_year_max=completion_year_max,
        status=status.split(",") if status else None,
        ownership_type=ownership_type
    )
    
    visibility = get_visibility_filter(current_user)
    
    query = select(Project).options(
        selectinload(Project.developer),
        selectinload(Project.district)
    )
    query = apply_project_filters(query, filters, visibility)
    
    # Sorting
    if sort_by == "featured":
        query = query.order_by(Project.is_featured.desc(), Project.sort_order, Project.created_at.desc())
    elif sort_by == "price_asc":
        query = query.order_by(Project.min_price_usd.asc().nullslast())
    elif sort_by == "price_desc":
        query = query.order_by(Project.max_price_usd.desc().nullslast())
    elif sort_by == "newest":
        query = query.order_by(Project.created_at.desc())
    elif sort_by == "completion":
        query = query.order_by(Project.completion_year.asc().nullslast(), Project.completion_quarter.asc().nullslast())
    
    # Count total
    count_query = select(func.count(Project.id)).where(
        Project.is_active == True,
        Project.deleted_at.is_(None),
        Project.visibility.in_(visibility)
    )
    if filters.district_ids:
        count_query = count_query.where(Project.district_id.in_(filters.district_ids))
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    projects = result.scalars().all()
    
    return ProjectListResponse(
        items=projects,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/map", response_model=MapResponse)
async def get_map_markers(
    # Same filters as list
    district_ids: Optional[str] = None,
    search: Optional[str] = None,
    developer_id: Optional[int] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    property_types: Optional[str] = None,
    bedrooms_min: Optional[int] = None,
    bedrooms_max: Optional[int] = None,
    bounds_north: Optional[float] = None,
    bounds_south: Optional[float] = None,
    bounds_east: Optional[float] = None,
    bounds_west: Optional[float] = None,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get map markers for projects matching filters."""
    filters = ProjectFilters(
        district_ids=[int(x) for x in district_ids.split(",")] if district_ids else None,
        search=search,
        developer_id=developer_id,
        price_min=price_min,
        price_max=price_max,
        property_types=property_types.split(",") if property_types else None,
        bedrooms_min=bedrooms_min,
        bedrooms_max=bedrooms_max,
        bounds_north=bounds_north,
        bounds_south=bounds_south,
        bounds_east=bounds_east,
        bounds_west=bounds_west
    )
    
    visibility = get_visibility_filter(current_user)
    
    query = select(Project).where(
        Project.lat.isnot(None),
        Project.lng.isnot(None)
    )
    query = apply_project_filters(query, filters, visibility)
    
    result = await db.execute(query)
    projects = result.scalars().all()
    
    markers = [
        MapMarker(
            id=p.id,
            slug=p.slug,
            name_en=p.name_en,
            name_ru=p.name_ru,
            lat=p.lat,
            lng=p.lng,
            property_types=p.property_types or [],
            min_price_usd=p.min_price_usd,
            available_units=p.available_units,
            cover_image_url=p.cover_image_url
        )
        for p in projects
    ]
    
    # Calculate bounds if we have markers
    bounds = None
    if markers:
        lats = [m.lat for m in markers]
        lngs = [m.lng for m in markers]
        bounds = {
            "north": max(lats),
            "south": min(lats),
            "east": max(lngs),
            "west": min(lngs)
        }
    
    return MapResponse(markers=markers, bounds=bounds)


@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(
    project_id: int,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get project details by ID."""
    visibility = get_visibility_filter(current_user)
    
    result = await db.execute(
        select(Project)
        .options(
            selectinload(Project.developer),
            selectinload(Project.district)
        )
        .where(
            Project.id == project_id,
            Project.is_active == True,
            Project.deleted_at.is_(None),
            Project.visibility.in_(visibility)
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    return project


@router.get("/slug/{slug}", response_model=ProjectDetail)
async def get_project_by_slug(
    slug: str,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get project details by slug."""
    visibility = get_visibility_filter(current_user)
    
    result = await db.execute(
        select(Project)
        .options(
            selectinload(Project.developer),
            selectinload(Project.district)
        )
        .where(
            Project.slug == slug,
            Project.is_active == True,
            Project.deleted_at.is_(None),
            Project.visibility.in_(visibility)
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    return project
