"""
Search endpoints - advanced search and map search.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from pydantic import BaseModel

from app.db.database import get_db
from app.models.project import Project, Developer
from app.models.unit import Unit, UnitStatus
from app.models.location import District, City
from app.models.user import User
from app.api.v1.endpoints.auth import get_current_user
from app.api.v1.endpoints.projects import get_visibility_filter

router = APIRouter()


# Schemas
class SearchResult(BaseModel):
    type: str  # project, developer, district
    id: int
    slug: str
    name_en: Optional[str]
    name_ru: Optional[str]
    subtitle: Optional[str]
    image_url: Optional[str]


class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: int


class AdvancedSearchFilters(BaseModel):
    # Location
    country_id: Optional[int] = None
    city_ids: Optional[List[int]] = None
    district_ids: Optional[List[int]] = None
    
    # Price
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    first_payment_min: Optional[float] = None
    first_payment_max: Optional[float] = None
    
    # Property
    property_types: Optional[List[str]] = None
    bedrooms: Optional[List[int]] = None
    
    # Area
    area_min: Optional[float] = None
    area_max: Optional[float] = None
    
    # Completion
    completion_year_min: Optional[int] = None
    completion_year_max: Optional[int] = None
    completion_quarter: Optional[str] = None
    years_after_completion: Optional[int] = None  # 0 = ready, 1+ = years completed
    
    # Developer
    developer_ids: Optional[List[int]] = None
    
    # Infrastructure nearby
    poi_types: Optional[List[str]] = None
    max_distance_to_beach: Optional[int] = None  # meters
    
    # Status
    status: Optional[List[str]] = None
    
    # Ownership
    ownership_type: Optional[str] = None


class AdvancedSearchResult(BaseModel):
    id: int
    slug: str
    name_en: Optional[str]
    name_ru: Optional[str]
    cover_image_url: Optional[str]
    
    lat: Optional[float]
    lng: Optional[float]
    district_name: Optional[str]
    developer_name: Optional[str]
    
    property_types: List[str]
    status: str
    completion_quarter: Optional[str]
    
    min_price_usd: Optional[float]
    max_price_usd: Optional[float]
    available_units: int
    
    # Matching criteria
    match_score: float


class AdvancedSearchResponse(BaseModel):
    results: List[AdvancedSearchResult]
    total: int
    page: int
    page_size: int
    filters_applied: dict


# Endpoints
@router.get("/quick", response_model=SearchResponse)
async def quick_search(
    q: str = Query(..., min_length=2, max_length=100),
    limit: int = Query(10, ge=1, le=50),
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Quick search across projects, developers, and districts."""
    visibility = get_visibility_filter(current_user)
    search_term = f"%{q}%"
    results = []
    
    # Search projects
    projects_result = await db.execute(
        select(Project)
        .where(
            or_(
                Project.name_en.ilike(search_term),
                Project.name_ru.ilike(search_term),
                Project.slug.ilike(search_term)
            ),
            Project.is_active == True,
            Project.visibility.in_(visibility)
        )
        .limit(limit)
    )
    for p in projects_result.scalars().all():
        results.append(SearchResult(
            type="project",
            id=p.id,
            slug=p.slug,
            name_en=p.name_en,
            name_ru=p.name_ru,
            subtitle=f"From ${p.min_price_usd:,.0f}" if p.min_price_usd else None,
            image_url=p.cover_image_url
        ))
    
    # Search developers
    developers_result = await db.execute(
        select(Developer)
        .where(
            or_(
                Developer.name_en.ilike(search_term),
                Developer.name_ru.ilike(search_term),
                Developer.slug.ilike(search_term)
            ),
            Developer.is_active == True
        )
        .limit(5)
    )
    for d in developers_result.scalars().all():
        results.append(SearchResult(
            type="developer",
            id=d.id,
            slug=d.slug,
            name_en=d.name_en,
            name_ru=d.name_ru,
            subtitle=f"{d.projects_count} projects",
            image_url=d.logo_url
        ))
    
    # Search districts
    districts_result = await db.execute(
        select(District)
        .where(
            or_(
                District.name_en.ilike(search_term),
                District.name_ru.ilike(search_term),
                District.slug.ilike(search_term)
            ),
            District.is_active == True,
            District.visibility.in_(visibility)
        )
        .limit(5)
    )
    for d in districts_result.scalars().all():
        results.append(SearchResult(
            type="district",
            id=d.id,
            slug=d.slug,
            name_en=d.name_en,
            name_ru=d.name_ru,
            subtitle=f"{d.projects_count} projects",
            image_url=d.cover_image_url
        ))
    
    return SearchResponse(results=results[:limit], total=len(results))


@router.post("/advanced", response_model=AdvancedSearchResponse)
async def advanced_search(
    filters: AdvancedSearchFilters,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("relevance", regex="^(relevance|price_asc|price_desc|newest)$"),
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Advanced search with multiple filters."""
    visibility = get_visibility_filter(current_user)
    
    query = select(Project).where(
        Project.is_active == True,
        Project.deleted_at.is_(None),
        Project.visibility.in_(visibility)
    )
    
    filters_applied = {}
    
    # Location filters
    if filters.district_ids:
        query = query.where(Project.district_id.in_(filters.district_ids))
        filters_applied["district_ids"] = filters.district_ids
    
    if filters.city_ids:
        query = query.join(District).where(District.city_id.in_(filters.city_ids))
        filters_applied["city_ids"] = filters.city_ids
    
    # Price filters
    if filters.price_min:
        query = query.where(Project.max_price_usd >= filters.price_min)
        filters_applied["price_min"] = filters.price_min
    
    if filters.price_max:
        query = query.where(Project.min_price_usd <= filters.price_max)
        filters_applied["price_max"] = filters.price_max
    
    # Property types
    if filters.property_types:
        for pt in filters.property_types:
            query = query.where(Project.property_types.contains([pt]))
        filters_applied["property_types"] = filters.property_types
    
    # Bedrooms
    if filters.bedrooms:
        query = query.where(
            and_(
                Project.min_bedrooms <= max(filters.bedrooms),
                Project.max_bedrooms >= min(filters.bedrooms)
            )
        )
        filters_applied["bedrooms"] = filters.bedrooms
    
    # Area
    if filters.area_min:
        query = query.where(Project.max_area >= filters.area_min)
        filters_applied["area_min"] = filters.area_min
    
    if filters.area_max:
        query = query.where(Project.min_area <= filters.area_max)
        filters_applied["area_max"] = filters.area_max
    
    # Completion
    if filters.completion_year_min:
        query = query.where(Project.completion_year >= filters.completion_year_min)
        filters_applied["completion_year_min"] = filters.completion_year_min
    
    if filters.completion_year_max:
        query = query.where(Project.completion_year <= filters.completion_year_max)
        filters_applied["completion_year_max"] = filters.completion_year_max
    
    # Developer
    if filters.developer_ids:
        query = query.where(Project.developer_id.in_(filters.developer_ids))
        filters_applied["developer_ids"] = filters.developer_ids
    
    # Status
    if filters.status:
        query = query.where(Project.status.in_(filters.status))
        filters_applied["status"] = filters.status
    
    # Ownership
    if filters.ownership_type:
        query = query.where(Project.ownership_type == filters.ownership_type)
        filters_applied["ownership_type"] = filters.ownership_type
    
    # Count total
    count_query = select(func.count(Project.id)).where(
        Project.is_active == True,
        Project.deleted_at.is_(None),
        Project.visibility.in_(visibility)
    )
    # Apply same filters to count query
    if filters.district_ids:
        count_query = count_query.where(Project.district_id.in_(filters.district_ids))
    if filters.price_min:
        count_query = count_query.where(Project.max_price_usd >= filters.price_min)
    if filters.price_max:
        count_query = count_query.where(Project.min_price_usd <= filters.price_max)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Sorting
    if sort_by == "price_asc":
        query = query.order_by(Project.min_price_usd.asc().nullslast())
    elif sort_by == "price_desc":
        query = query.order_by(Project.max_price_usd.desc().nullslast())
    elif sort_by == "newest":
        query = query.order_by(Project.created_at.desc())
    else:  # relevance
        query = query.order_by(Project.is_featured.desc(), Project.available_units.desc())
    
    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    projects = result.scalars().all()
    
    # Build response with additional data
    results = []
    for p in projects:
        # Get district and developer names
        district = await db.get(District, p.district_id)
        developer = await db.get(Developer, p.developer_id) if p.developer_id else None
        
        results.append(AdvancedSearchResult(
            id=p.id,
            slug=p.slug,
            name_en=p.name_en,
            name_ru=p.name_ru,
            cover_image_url=p.cover_image_url,
            lat=p.lat,
            lng=p.lng,
            district_name=district.name_en if district else None,
            developer_name=developer.name_en if developer else None,
            property_types=p.property_types or [],
            status=p.status.value,
            completion_quarter=p.completion_quarter,
            min_price_usd=p.min_price_usd,
            max_price_usd=p.max_price_usd,
            available_units=p.available_units,
            match_score=1.0  # TODO: Calculate actual match score
        ))
    
    return AdvancedSearchResponse(
        results=results,
        total=total,
        page=page,
        page_size=page_size,
        filters_applied=filters_applied
    )


@router.get("/suggestions")
async def get_search_suggestions(
    q: str = Query(..., min_length=1, max_length=50),
    db: AsyncSession = Depends(get_db)
):
    """Get search suggestions based on partial input."""
    search_term = f"{q}%"
    
    suggestions = []
    
    # Project name suggestions
    projects = await db.execute(
        select(Project.name_en)
        .where(
            Project.name_en.ilike(search_term),
            Project.is_active == True
        )
        .distinct()
        .limit(5)
    )
    suggestions.extend([{"text": p, "type": "project"} for p in projects.scalars().all() if p])
    
    # Developer suggestions
    developers = await db.execute(
        select(Developer.name_en)
        .where(
            Developer.name_en.ilike(search_term),
            Developer.is_active == True
        )
        .distinct()
        .limit(3)
    )
    suggestions.extend([{"text": d, "type": "developer"} for d in developers.scalars().all() if d])
    
    # District suggestions
    districts = await db.execute(
        select(District.name_en)
        .where(
            District.name_en.ilike(search_term),
            District.is_active == True
        )
        .distinct()
        .limit(3)
    )
    suggestions.extend([{"text": d, "type": "district"} for d in districts.scalars().all() if d])
    
    return {"suggestions": suggestions[:10]}
