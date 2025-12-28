"""
Admin API endpoints for PropBase.
Full CRUD operations for projects, units, and media management.
Replaces Notion as the primary data source.
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, delete, update
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field
import boto3
from botocore.config import Config
import uuid
import os

from app.db.database import get_db
from app.models.project import Project, Developer, ProjectStatus, PropertyType, OwnershipType
from app.models.location import District
from app.models.unit import Unit, UnitStatus, UnitType
from app.models.user import User, UserRole
from app.api.v1.endpoints.auth import get_current_user, require_roles
from app.core.config import settings

router = APIRouter()


# ============ SCHEMAS ============

class ProjectCreate(BaseModel):
    name_en: str
    name_ru: Optional[str] = None
    slug: str
    description_en: Optional[str] = None
    description_ru: Optional[str] = None
    property_types: List[str] = []
    status: str = "under_construction"
    ownership_type: str = "freehold"
    leasehold_years: Optional[int] = None
    
    # Location
    district_id: Optional[int] = None
    address_en: Optional[str] = None
    address_ru: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    
    # Pricing
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_price_per_sqm: Optional[float] = None
    original_currency: str = "THB"
    
    # Units
    total_units: int = 0
    available_units: int = 0
    
    # Dates
    completion_date: Optional[str] = None
    completion_year: Optional[int] = None
    completion_quarter: Optional[str] = None
    
    # Media
    cover_image_url: Optional[str] = None
    gallery: List[str] = []
    video_url: Optional[str] = None
    virtual_tour_url: Optional[str] = None
    master_plan_url: Optional[str] = None
    
    # Features
    amenities: List[str] = []
    features: List[str] = []
    
    # Status flags
    is_active: bool = True
    is_featured: bool = False
    is_verified: bool = False


class ProjectUpdate(ProjectCreate):
    name_en: Optional[str] = None
    slug: Optional[str] = None


class ProjectResponse(BaseModel):
    id: int
    name_en: Optional[str]
    name_ru: Optional[str]
    slug: str
    description_en: Optional[str]
    description_ru: Optional[str]
    property_types: List[str]
    status: str
    ownership_type: str
    leasehold_years: Optional[int]
    district_id: Optional[int]
    address_en: Optional[str]
    address_ru: Optional[str]
    lat: Optional[float]
    lng: Optional[float]
    min_price: Optional[float]
    max_price: Optional[float]
    min_price_per_sqm: Optional[float]
    original_currency: str
    total_units: int
    available_units: int
    completion_date: Optional[str]
    completion_year: Optional[int]
    completion_quarter: Optional[str]
    cover_image_url: Optional[str]
    gallery: List[str]
    video_url: Optional[str]
    virtual_tour_url: Optional[str]
    master_plan_url: Optional[str]
    amenities: List[str]
    features: List[str]
    is_active: bool
    is_featured: bool
    is_verified: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class UnitCreate(BaseModel):
    project_id: int
    unit_number: str
    building: Optional[str] = None
    floor: Optional[int] = None
    unit_type: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    area_sqm: Optional[float] = None
    land_area: Optional[float] = None
    pool_size: Optional[str] = None
    price: Optional[float] = None
    price_per_sqm: Optional[float] = None
    currency: str = "THB"
    status: str = "available"
    view_type: Optional[str] = None
    layout_name: Optional[str] = None
    layout_image_url: Optional[str] = None
    features: List[str] = []
    images: List[str] = []
    is_active: bool = True


class UnitUpdate(BaseModel):
    unit_number: Optional[str] = None
    building: Optional[str] = None
    floor: Optional[int] = None
    unit_type: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    area_sqm: Optional[float] = None
    land_area: Optional[float] = None
    pool_size: Optional[str] = None
    price: Optional[float] = None
    price_per_sqm: Optional[float] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    view_type: Optional[str] = None
    layout_name: Optional[str] = None
    layout_image_url: Optional[str] = None
    features: Optional[List[str]] = None
    images: Optional[List[str]] = None
    is_active: Optional[bool] = None


class UnitResponse(BaseModel):
    id: int
    project_id: int
    unit_number: str
    building: Optional[str]
    floor: Optional[int]
    unit_type: Optional[str]
    bedrooms: Optional[int]
    bathrooms: Optional[int]
    area_sqm: Optional[float]
    land_area: Optional[float]
    pool_size: Optional[str]
    price: Optional[float]
    price_per_sqm: Optional[float]
    currency: str
    status: str
    view_type: Optional[str]
    layout_name: Optional[str]
    features: List[str]
    images: List[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class MediaUploadResponse(BaseModel):
    url: str
    path: str
    size: int
    content_type: str


class AdminStatsResponse(BaseModel):
    total_projects: int
    active_projects: int
    total_units: int
    available_units: int
    sold_units: int
    reserved_units: int


# ============ STORAGE HELPERS ============

def get_storage_client():
    """Get Supabase/S3-compatible storage client."""
    # Try Supabase Storage first, fallback to Cloudflare R2
    storage_url = getattr(settings, 'SUPABASE_URL', None) or getattr(settings, 'R2_ENDPOINT', None)
    access_key = getattr(settings, 'SUPABASE_SERVICE_KEY', None) or getattr(settings, 'R2_ACCESS_KEY', None)
    secret_key = getattr(settings, 'SUPABASE_SERVICE_KEY', None) or getattr(settings, 'R2_SECRET_KEY', None)
    
    if not all([storage_url, access_key, secret_key]):
        return None
    
    # For Supabase, use their storage API
    # For R2/S3, use boto3
    if 'supabase' in str(storage_url).lower():
        return {
            'type': 'supabase',
            'url': storage_url,
            'key': access_key
        }
    else:
        return boto3.client(
            's3',
            endpoint_url=storage_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version='s3v4')
        )


async def upload_to_storage(file: UploadFile, folder: str = "projects") -> dict:
    """Upload file to storage and return URL."""
    # Generate unique filename
    ext = os.path.splitext(file.filename)[1] if file.filename else '.jpg'
    filename = f"{folder}/{uuid.uuid4()}{ext}"
    
    # Read file content
    content = await file.read()
    
    # Get storage client
    client = get_storage_client()
    
    if client is None:
        # Fallback: return a placeholder URL for development
        # In production, this should use actual storage
        return {
            'url': f"https://placeholder.storage/{filename}",
            'path': filename,
            'size': len(content),
            'content_type': file.content_type or 'image/jpeg'
        }
    
    if isinstance(client, dict) and client.get('type') == 'supabase':
        # Use Supabase Storage API
        import httpx
        async with httpx.AsyncClient() as http:
            response = await http.post(
                f"{client['url']}/storage/v1/object/project-images/{filename}",
                headers={
                    'Authorization': f"Bearer {client['key']}",
                    'Content-Type': file.content_type or 'image/jpeg'
                },
                content=content
            )
            if response.status_code not in [200, 201]:
                raise HTTPException(status_code=500, detail="Failed to upload to storage")
            
            return {
                'url': f"{client['url']}/storage/v1/object/public/project-images/{filename}",
                'path': filename,
                'size': len(content),
                'content_type': file.content_type or 'image/jpeg'
            }
    else:
        # Use S3-compatible storage
        bucket = getattr(settings, 'STORAGE_BUCKET', 'propbase-media')
        client.put_object(
            Bucket=bucket,
            Key=filename,
            Body=content,
            ContentType=file.content_type or 'image/jpeg'
        )
        
        # Get public URL
        storage_url = getattr(settings, 'STORAGE_PUBLIC_URL', settings.R2_ENDPOINT)
        public_url = f"{storage_url}/{bucket}/{filename}"
        
        return {
            'url': public_url,
            'path': filename,
            'size': len(content),
            'content_type': file.content_type or 'image/jpeg'
        }


# ============ PROJECT ENDPOINTS ============

@router.post("/projects", response_model=ProjectResponse)
async def create_project(
    data: ProjectCreate,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.CONTENT_MANAGER])),
    db: AsyncSession = Depends(get_db)
):
    """Create a new project."""
    # Check if slug already exists
    existing = await db.execute(
        select(Project).where(Project.slug == data.slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project with this slug already exists"
        )
    
    # Create project
    project = Project(
        name_en=data.name_en,
        name_ru=data.name_ru,
        slug=data.slug,
        description_en=data.description_en,
        description_ru=data.description_ru,
        property_types=data.property_types,
        status=data.status,
        ownership_type=data.ownership_type,
        leasehold_years=data.leasehold_years,
        district_id=data.district_id,
        address_en=data.address_en,
        address_ru=data.address_ru,
        lat=data.lat,
        lng=data.lng,
        min_price=data.min_price,
        max_price=data.max_price,
        min_price_per_sqm=data.min_price_per_sqm,
        original_currency=data.original_currency,
        total_units=data.total_units,
        available_units=data.available_units,
        completion_year=data.completion_year,
        completion_quarter=data.completion_quarter,
        cover_image_url=data.cover_image_url,
        gallery=data.gallery,
        video_url=data.video_url,
        virtual_tour_url=data.virtual_tour_url,
        master_plan_url=data.master_plan_url,
        amenities=data.amenities,
        features=data.features,
        is_active=data.is_active,
        is_featured=data.is_featured,
        is_verified=data.is_verified,
        created_at=datetime.utcnow()
    )
    
    db.add(project)
    await db.commit()
    await db.refresh(project)
    
    return project


@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    data: ProjectUpdate,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.CONTENT_MANAGER])),
    db: AsyncSession = Depends(get_db)
):
    """Update an existing project."""
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check slug uniqueness if changing
    if data.slug and data.slug != project.slug:
        existing = await db.execute(
            select(Project).where(
                Project.slug == data.slug,
                Project.id != project_id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project with this slug already exists"
            )
    
    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(project, field):
            setattr(project, field, value)
    
    project.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(project)
    
    return project


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: int,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """Delete a project (soft delete)."""
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Soft delete
    project.deleted_at = datetime.utcnow()
    project.is_active = False
    
    await db.commit()
    
    return {"success": True, "message": "Project deleted"}


# ============ UNIT ENDPOINTS ============

@router.get("/units", response_model=List[UnitResponse])
async def list_units(
    project_id: Optional[int] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.CONTENT_MANAGER, UserRole.ANALYST])),
    db: AsyncSession = Depends(get_db)
):
    """List units with filters."""
    query = select(Unit).where(Unit.is_active == True)
    
    if project_id:
        query = query.where(Unit.project_id == project_id)
    if status:
        query = query.where(Unit.status == status)
    
    query = query.order_by(Unit.project_id, Unit.building, Unit.floor, Unit.unit_number)
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    units = result.scalars().all()
    
    return units


@router.post("/units", response_model=UnitResponse)
async def create_unit(
    data: UnitCreate,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.CONTENT_MANAGER])),
    db: AsyncSession = Depends(get_db)
):
    """Create a new unit."""
    # Check if project exists
    project = await db.execute(
        select(Project).where(Project.id == data.project_id)
    )
    if not project.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check for duplicate unit number in project
    existing = await db.execute(
        select(Unit).where(
            Unit.project_id == data.project_id,
            Unit.unit_number == data.unit_number
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unit with this number already exists in project"
        )
    
    unit = Unit(
        project_id=data.project_id,
        unit_number=data.unit_number,
        building=data.building,
        floor=data.floor,
        unit_type=data.unit_type,
        bedrooms=data.bedrooms,
        bathrooms=data.bathrooms,
        area_sqm=data.area_sqm,
        land_area=data.land_area,
        price=data.price,
        price_per_sqm=data.price_per_sqm,
        currency=data.currency,
        status=data.status,
        view_type=data.view_type,
        layout_name=data.layout_name,
        layout_image_url=data.layout_image_url,
        features=data.features,
        images=data.images,
        is_active=data.is_active,
        created_at=datetime.utcnow()
    )
    
    db.add(unit)
    await db.commit()
    await db.refresh(unit)
    
    return unit


@router.put("/units/{unit_id}", response_model=UnitResponse)
async def update_unit(
    unit_id: int,
    data: UnitUpdate,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.CONTENT_MANAGER])),
    db: AsyncSession = Depends(get_db)
):
    """Update an existing unit."""
    result = await db.execute(
        select(Unit).where(Unit.id == unit_id)
    )
    unit = result.scalar_one_or_none()
    
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit not found"
        )
    
    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(unit, field):
            setattr(unit, field, value)
    
    unit.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(unit)
    
    return unit


@router.delete("/units/{unit_id}")
async def delete_unit(
    unit_id: int,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """Delete a unit."""
    result = await db.execute(
        select(Unit).where(Unit.id == unit_id)
    )
    unit = result.scalar_one_or_none()
    
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit not found"
        )
    
    # Soft delete
    unit.is_active = False
    await db.commit()
    
    return {"success": True, "message": "Unit deleted"}


# ============ MEDIA ENDPOINTS ============

@router.post("/media/upload", response_model=MediaUploadResponse)
async def upload_media(
    file: UploadFile = File(...),
    folder: str = Query("projects", regex="^(projects|units|gallery|plans)$"),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.CONTENT_MANAGER])),
):
    """Upload media file to storage."""
    # Validate file type
    allowed_types = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(allowed_types)}"
        )
    
    # Validate file size (max 10MB)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size is 10MB"
        )
    
    # Reset file position
    await file.seek(0)
    
    # Upload to storage
    result = await upload_to_storage(file, folder)
    
    return MediaUploadResponse(**result)


@router.delete("/media")
async def delete_media(
    path: str,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
):
    """Delete media file from storage."""
    client = get_storage_client()
    
    if client is None:
        return {"success": True, "message": "No storage configured"}
    
    try:
        if isinstance(client, dict) and client.get('type') == 'supabase':
            import httpx
            async with httpx.AsyncClient() as http:
                response = await http.delete(
                    f"{client['url']}/storage/v1/object/project-images/{path}",
                    headers={'Authorization': f"Bearer {client['key']}"}
                )
                if response.status_code not in [200, 204]:
                    raise HTTPException(status_code=500, detail="Failed to delete from storage")
        else:
            bucket = getattr(settings, 'STORAGE_BUCKET', 'propbase-media')
            client.delete_object(Bucket=bucket, Key=path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")
    
    return {"success": True, "message": "File deleted"}


# ============ STATS ENDPOINTS ============

@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats(
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.ANALYST])),
    db: AsyncSession = Depends(get_db)
):
    """Get admin dashboard statistics."""
    # Projects count
    total_projects_result = await db.execute(
        select(func.count(Project.id)).where(Project.deleted_at.is_(None))
    )
    total_projects = total_projects_result.scalar() or 0
    
    active_projects_result = await db.execute(
        select(func.count(Project.id)).where(
            Project.is_active == True,
            Project.deleted_at.is_(None)
        )
    )
    active_projects = active_projects_result.scalar() or 0
    
    # Units count
    total_units_result = await db.execute(
        select(func.count(Unit.id)).where(Unit.is_active == True)
    )
    total_units = total_units_result.scalar() or 0
    
    available_units_result = await db.execute(
        select(func.count(Unit.id)).where(
            Unit.is_active == True,
            Unit.status == 'available'
        )
    )
    available_units = available_units_result.scalar() or 0
    
    sold_units_result = await db.execute(
        select(func.count(Unit.id)).where(
            Unit.is_active == True,
            Unit.status == 'sold'
        )
    )
    sold_units = sold_units_result.scalar() or 0
    
    reserved_units_result = await db.execute(
        select(func.count(Unit.id)).where(
            Unit.is_active == True,
            Unit.status == 'reserved'
        )
    )
    reserved_units = reserved_units_result.scalar() or 0
    
    return AdminStatsResponse(
        total_projects=total_projects,
        active_projects=active_projects,
        total_units=total_units,
        available_units=available_units,
        sold_units=sold_units,
        reserved_units=reserved_units
    )
