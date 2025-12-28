"""
Locations endpoints - Countries, Cities, Districts, Infrastructure.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from app.db.database import get_db
from app.models.location import Country, City, District, Infrastructure
from app.models.user import User
from app.api.v1.endpoints.auth import get_current_user
from app.api.v1.endpoints.projects import get_visibility_filter

router = APIRouter()


# Schemas
class CountryResponse(BaseModel):
    id: int
    code: str
    name_en: Optional[str]
    name_ru: Optional[str]
    center_lat: Optional[float]
    center_lng: Optional[float]
    default_currency: str
    
    class Config:
        from_attributes = True


class CityResponse(BaseModel):
    id: int
    country_id: int
    slug: str
    name_en: Optional[str]
    name_ru: Optional[str]
    center_lat: Optional[float]
    center_lng: Optional[float]
    default_zoom: int
    
    class Config:
        from_attributes = True


class DistrictResponse(BaseModel):
    id: int
    city_id: int
    slug: str
    name_en: Optional[str]
    name_ru: Optional[str]
    description_en: Optional[str]
    description_ru: Optional[str]
    advantages_en: Optional[str]
    advantages_ru: Optional[str]
    target_audience_en: Optional[str]
    target_audience_ru: Optional[str]
    center_lat: Optional[float]
    center_lng: Optional[float]
    boundary_geojson: Optional[dict]
    projects_count: int
    min_price_usd: Optional[float]
    max_price_usd: Optional[float]
    cover_image_url: Optional[str]
    gallery: Optional[List[str]]
    visibility: str
    
    class Config:
        from_attributes = True


class InfrastructureResponse(BaseModel):
    id: int
    district_id: Optional[int]
    name_en: Optional[str]
    name_ru: Optional[str]
    poi_type: str
    poi_category: Optional[str]
    lat: float
    lng: float
    address_en: Optional[str]
    address_ru: Optional[str]
    icon: Optional[str]
    is_featured: bool
    
    class Config:
        from_attributes = True


# Endpoints
@router.get("/countries", response_model=List[CountryResponse])
async def list_countries(
    db: AsyncSession = Depends(get_db)
):
    """List all active countries."""
    result = await db.execute(
        select(Country).where(Country.is_active == True)
    )
    return result.scalars().all()


@router.get("/cities", response_model=List[CityResponse])
async def list_cities(
    country_id: Optional[int] = None,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List cities, optionally filtered by country."""
    visibility = get_visibility_filter(current_user)
    
    query = select(City).where(
        City.is_active == True,
        City.visibility.in_(visibility)
    )
    
    if country_id:
        query = query.where(City.country_id == country_id)
    
    query = query.order_by(City.sort_order, City.name_en)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/districts", response_model=List[DistrictResponse])
async def list_districts(
    city_id: Optional[int] = None,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List districts, optionally filtered by city."""
    visibility = get_visibility_filter(current_user)
    
    query = select(District).where(
        District.is_active == True,
        District.visibility.in_(visibility)
    )
    
    if city_id:
        query = query.where(District.city_id == city_id)
    
    query = query.order_by(District.sort_order, District.name_en)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/districts/{district_id}", response_model=DistrictResponse)
async def get_district(
    district_id: int,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get district details."""
    visibility = get_visibility_filter(current_user)
    
    result = await db.execute(
        select(District).where(
            District.id == district_id,
            District.is_active == True,
            District.visibility.in_(visibility)
        )
    )
    district = result.scalar_one_or_none()
    
    if not district:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="District not found"
        )
    
    return district


@router.get("/infrastructure", response_model=List[InfrastructureResponse])
async def list_infrastructure(
    district_id: Optional[int] = None,
    poi_type: Optional[str] = None,
    bounds_north: Optional[float] = None,
    bounds_south: Optional[float] = None,
    bounds_east: Optional[float] = None,
    bounds_west: Optional[float] = None,
    db: AsyncSession = Depends(get_db)
):
    """List infrastructure/POI points."""
    query = select(Infrastructure).where(Infrastructure.is_active == True)
    
    if district_id:
        query = query.where(Infrastructure.district_id == district_id)
    
    if poi_type:
        query = query.where(Infrastructure.poi_type == poi_type)
    
    # Map bounds filter
    if all([bounds_north, bounds_south, bounds_east, bounds_west]):
        query = query.where(
            Infrastructure.lat <= bounds_north,
            Infrastructure.lat >= bounds_south,
            Infrastructure.lng <= bounds_east,
            Infrastructure.lng >= bounds_west
        )
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/poi-types")
async def get_poi_types(
    db: AsyncSession = Depends(get_db)
):
    """Get list of available POI types."""
    from sqlalchemy import distinct
    
    result = await db.execute(
        select(distinct(Infrastructure.poi_type)).where(
            Infrastructure.is_active == True
        )
    )
    types = result.scalars().all()
    
    # POI type labels
    labels = {
        "beach": {"en": "Beach", "ru": "Пляж", "icon": "beach"},
        "school": {"en": "School", "ru": "Школа", "icon": "school"},
        "hospital": {"en": "Hospital", "ru": "Больница", "icon": "hospital"},
        "mall": {"en": "Shopping Mall", "ru": "ТЦ", "icon": "shopping"},
        "restaurant": {"en": "Restaurant", "ru": "Ресторан", "icon": "restaurant"},
        "airport": {"en": "Airport", "ru": "Аэропорт", "icon": "airport"},
        "golf": {"en": "Golf Course", "ru": "Гольф-клуб", "icon": "golf"},
        "spa": {"en": "Spa & Wellness", "ru": "СПА", "icon": "spa"},
        "supermarket": {"en": "Supermarket", "ru": "Супермаркет", "icon": "store"},
        "gym": {"en": "Gym & Fitness", "ru": "Фитнес", "icon": "fitness"},
        "park": {"en": "Park", "ru": "Парк", "icon": "park"},
        "marina": {"en": "Marina", "ru": "Марина", "icon": "boat"},
    }
    
    return [
        {
            "type": t,
            "label_en": labels.get(t, {}).get("en", t.title()),
            "label_ru": labels.get(t, {}).get("ru", t.title()),
            "icon": labels.get(t, {}).get("icon", "place"),
        }
        for t in types
    ]
