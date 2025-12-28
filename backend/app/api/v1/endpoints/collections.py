"""
Collections endpoints - creating and sharing property selections.
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field

from app.db.database import get_db
from app.models.collection import Collection, CollectionItem, CollectionEvent
from app.models.project import Project
from app.models.unit import Unit
from app.models.user import User, UserRole
from app.api.v1.endpoints.auth import get_current_user, require_roles

router = APIRouter()


# Schemas
class CollectionItemCreate(BaseModel):
    project_id: int
    unit_id: Optional[int] = None
    note: Optional[str] = None
    note_ru: Optional[str] = None
    is_featured: bool = False


class CollectionCreate(BaseModel):
    name: str
    name_ru: Optional[str] = None
    description: Optional[str] = None
    description_ru: Optional[str] = None
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    client_phone: Optional[str] = None
    items: List[CollectionItemCreate] = []
    
    # Settings
    show_prices: bool = True
    show_availability: bool = True
    default_currency: str = "USD"
    default_language: str = "en"
    show_agent_branding: bool = True
    show_agency_branding: bool = True


class CollectionUpdate(BaseModel):
    name: Optional[str] = None
    name_ru: Optional[str] = None
    description: Optional[str] = None
    description_ru: Optional[str] = None
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    client_phone: Optional[str] = None
    is_public: Optional[bool] = None
    show_prices: Optional[bool] = None
    show_availability: Optional[bool] = None
    default_currency: Optional[str] = None
    default_language: Optional[str] = None


class CollectionItemResponse(BaseModel):
    id: int
    project_id: int
    unit_id: Optional[int]
    note: Optional[str]
    note_ru: Optional[str]
    is_featured: bool
    sort_order: int
    price_snapshot_usd: Optional[float]
    
    # Nested project/unit data will be loaded separately
    
    class Config:
        from_attributes = True


class CollectionResponse(BaseModel):
    id: int
    owner_id: int
    name: str
    name_ru: Optional[str]
    description: Optional[str]
    description_ru: Optional[str]
    ai_description: Optional[str]
    ai_description_ru: Optional[str]
    
    client_name: Optional[str]
    client_email: Optional[str]
    client_phone: Optional[str]
    
    share_token: str
    is_public: bool
    expires_at: Optional[datetime]
    
    show_prices: bool
    show_availability: bool
    default_currency: str
    default_language: str
    show_agent_branding: bool
    show_agency_branding: bool
    
    view_count: int
    pdf_download_count: int
    last_viewed_at: Optional[datetime]
    
    created_at: datetime
    updated_at: datetime
    
    items_count: int = 0
    
    class Config:
        from_attributes = True


class CollectionListResponse(BaseModel):
    items: List[CollectionResponse]
    total: int
    page: int
    page_size: int


class CollectionDetailResponse(CollectionResponse):
    items: List[CollectionItemResponse]
    
    class Config:
        from_attributes = True


class InquiryCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    message: Optional[str] = None


# Public collection view (for shared links)
class PublicProjectInfo(BaseModel):
    id: int
    slug: str
    name_en: Optional[str]
    name_ru: Optional[str]
    cover_image_url: Optional[str]
    gallery: Optional[List[str]]
    lat: Optional[float]
    lng: Optional[float]
    property_types: List[str]
    status: str
    completion_quarter: Optional[str]
    min_price_usd: Optional[float]
    max_price_usd: Optional[float]
    
    class Config:
        from_attributes = True


class PublicUnitInfo(BaseModel):
    id: int
    unit_number: str
    unit_type: str
    bedrooms: int
    area_sqm: float
    price_usd: Optional[float]
    price_per_sqm_usd: Optional[float]
    status: str
    view_type: Optional[str]
    floor: Optional[int]
    layout_image_url: Optional[str]
    
    class Config:
        from_attributes = True


class PublicCollectionItem(BaseModel):
    id: int
    note: Optional[str]
    note_ru: Optional[str]
    is_featured: bool
    project: PublicProjectInfo
    unit: Optional[PublicUnitInfo]


class PublicCollectionResponse(BaseModel):
    name: str
    name_ru: Optional[str]
    description: Optional[str]
    description_ru: Optional[str]
    ai_description: Optional[str]
    ai_description_ru: Optional[str]
    
    default_currency: str
    default_language: str
    show_prices: bool
    
    # Agent info (if branding enabled)
    agent_name: Optional[str]
    agent_phone: Optional[str]
    agent_email: Optional[str]
    agent_avatar: Optional[str]
    agency_name: Optional[str]
    agency_logo: Optional[str]
    
    items: List[PublicCollectionItem]


# Endpoints
@router.post("/", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
async def create_collection(
    data: CollectionCreate,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.AGENT, UserRole.PARTNER)),
    db: AsyncSession = Depends(get_db)
):
    """Create a new collection."""
    
    # Create collection
    collection = Collection(
        owner_id=current_user.id,
        name=data.name,
        name_ru=data.name_ru,
        description=data.description,
        description_ru=data.description_ru,
        client_name=data.client_name,
        client_email=data.client_email,
        client_phone=data.client_phone,
        show_prices=data.show_prices,
        show_availability=data.show_availability,
        default_currency=data.default_currency,
        default_language=data.default_language,
        show_agent_branding=data.show_agent_branding,
        show_agency_branding=data.show_agency_branding,
    )
    
    db.add(collection)
    await db.flush()  # Get the ID
    
    # Add items
    for i, item_data in enumerate(data.items):
        # Verify project exists
        project = await db.get(Project, item_data.project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Project {item_data.project_id} not found"
            )
        
        # Verify unit if provided
        unit = None
        price_snapshot = None
        if item_data.unit_id:
            unit = await db.get(Unit, item_data.unit_id)
            if not unit or unit.project_id != item_data.project_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unit {item_data.unit_id} not found in project {item_data.project_id}"
                )
            price_snapshot = unit.price_usd
        
        item = CollectionItem(
            collection_id=collection.id,
            project_id=item_data.project_id,
            unit_id=item_data.unit_id,
            note=item_data.note,
            note_ru=item_data.note_ru,
            is_featured=item_data.is_featured,
            sort_order=i,
            price_snapshot_usd=price_snapshot,
        )
        db.add(item)
    
    await db.commit()
    await db.refresh(collection)
    
    # Add items count
    collection.items_count = len(data.items)
    
    return collection


@router.get("/", response_model=CollectionListResponse)
async def list_collections(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List user's collections."""
    
    query = select(Collection).where(
        Collection.owner_id == current_user.id,
        Collection.is_active == True,
        Collection.deleted_at.is_(None)
    )
    
    if search:
        search_term = f"%{search}%"
        query = query.where(
            Collection.name.ilike(search_term) |
            Collection.client_name.ilike(search_term)
        )
    
    query = query.order_by(Collection.created_at.desc())
    
    # Count
    count_query = select(func.count(Collection.id)).where(
        Collection.owner_id == current_user.id,
        Collection.is_active == True,
        Collection.deleted_at.is_(None)
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    collections = result.scalars().all()
    
    # Add items count for each collection
    for c in collections:
        items_count = await db.execute(
            select(func.count(CollectionItem.id)).where(
                CollectionItem.collection_id == c.id
            )
        )
        c.items_count = items_count.scalar()
    
    return CollectionListResponse(
        items=collections,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{collection_id}", response_model=CollectionDetailResponse)
async def get_collection(
    collection_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get collection details."""
    
    result = await db.execute(
        select(Collection)
        .options(selectinload(Collection.items))
        .where(
            Collection.id == collection_id,
            Collection.is_active == True,
            Collection.deleted_at.is_(None)
        )
    )
    collection = result.scalar_one_or_none()
    
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found"
        )
    
    # Check ownership (admins can view all)
    if collection.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to view this collection"
        )
    
    collection.items_count = len(collection.items)
    
    return collection


@router.patch("/{collection_id}", response_model=CollectionResponse)
async def update_collection(
    collection_id: int,
    data: CollectionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update collection."""
    
    result = await db.execute(
        select(Collection).where(
            Collection.id == collection_id,
            Collection.is_active == True,
            Collection.deleted_at.is_(None)
        )
    )
    collection = result.scalar_one_or_none()
    
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found"
        )
    
    if collection.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to update this collection"
        )
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(collection, field, value)
    
    await db.commit()
    await db.refresh(collection)
    
    return collection


@router.post("/{collection_id}/items", response_model=CollectionItemResponse)
async def add_collection_item(
    collection_id: int,
    data: CollectionItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add item to collection."""
    
    result = await db.execute(
        select(Collection).where(
            Collection.id == collection_id,
            Collection.is_active == True
        )
    )
    collection = result.scalar_one_or_none()
    
    if not collection or collection.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found"
        )
    
    # Get max sort order
    max_order = await db.execute(
        select(func.max(CollectionItem.sort_order)).where(
            CollectionItem.collection_id == collection_id
        )
    )
    sort_order = (max_order.scalar() or 0) + 1
    
    # Get price snapshot
    price_snapshot = None
    if data.unit_id:
        unit = await db.get(Unit, data.unit_id)
        if unit:
            price_snapshot = unit.price_usd
    
    item = CollectionItem(
        collection_id=collection_id,
        project_id=data.project_id,
        unit_id=data.unit_id,
        note=data.note,
        note_ru=data.note_ru,
        is_featured=data.is_featured,
        sort_order=sort_order,
        price_snapshot_usd=price_snapshot,
    )
    
    db.add(item)
    await db.commit()
    await db.refresh(item)
    
    return item


@router.delete("/{collection_id}/items/{item_id}")
async def remove_collection_item(
    collection_id: int,
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove item from collection."""
    
    result = await db.execute(
        select(CollectionItem)
        .join(Collection)
        .where(
            CollectionItem.id == item_id,
            CollectionItem.collection_id == collection_id,
            Collection.owner_id == current_user.id
        )
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    await db.delete(item)
    await db.commit()
    
    return {"message": "Item removed"}


@router.delete("/{collection_id}")
async def delete_collection(
    collection_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Soft delete collection."""
    
    result = await db.execute(
        select(Collection).where(
            Collection.id == collection_id,
            Collection.is_active == True
        )
    )
    collection = result.scalar_one_or_none()
    
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found"
        )
    
    if collection.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to delete this collection"
        )
    
    collection.deleted_at = datetime.utcnow()
    collection.is_active = False
    await db.commit()
    
    return {"message": "Collection deleted"}


# Public endpoints (for shared links)
@router.get("/share/{share_token}", response_model=PublicCollectionResponse)
async def get_public_collection(
    share_token: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get collection by share token (public endpoint for clients)."""
    
    result = await db.execute(
        select(Collection)
        .options(
            selectinload(Collection.items),
            selectinload(Collection.owner)
        )
        .where(
            Collection.share_token == share_token,
            Collection.is_active == True,
            Collection.is_public == True
        )
    )
    collection = result.scalar_one_or_none()
    
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found"
        )
    
    # Check expiration
    if collection.is_expired:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This collection has expired"
        )
    
    # Update view count and log event
    collection.view_count += 1
    collection.last_viewed_at = datetime.utcnow()
    
    event = CollectionEvent(
        collection_id=collection.id,
        event_type="view",
        client_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        referrer=request.headers.get("referer"),
    )
    db.add(event)
    await db.commit()
    
    # Build response with project/unit data
    items_data = []
    for item in collection.items:
        project = await db.get(Project, item.project_id)
        unit = await db.get(Unit, item.unit_id) if item.unit_id else None
        
        items_data.append(PublicCollectionItem(
            id=item.id,
            note=item.note,
            note_ru=item.note_ru,
            is_featured=item.is_featured,
            project=PublicProjectInfo.model_validate(project),
            unit=PublicUnitInfo.model_validate(unit) if unit else None
        ))
    
    # Agent info
    owner = collection.owner
    
    return PublicCollectionResponse(
        name=collection.name,
        name_ru=collection.name_ru,
        description=collection.description,
        description_ru=collection.description_ru,
        ai_description=collection.ai_description,
        ai_description_ru=collection.ai_description_ru,
        default_currency=collection.default_currency,
        default_language=collection.default_language,
        show_prices=collection.show_prices,
        agent_name=owner.full_name if collection.show_agent_branding else None,
        agent_phone=owner.phone if collection.show_agent_branding else None,
        agent_email=owner.email if collection.show_agent_branding else None,
        agent_avatar=owner.avatar_url if collection.show_agent_branding else None,
        agency_name=owner.agency_name if collection.show_agency_branding else None,
        agency_logo=owner.agency_logo_url if collection.show_agency_branding else None,
        items=items_data
    )


@router.post("/share/{share_token}/inquiry")
async def submit_inquiry(
    share_token: str,
    data: InquiryCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Submit inquiry for a shared collection."""
    
    result = await db.execute(
        select(Collection).where(
            Collection.share_token == share_token,
            Collection.is_active == True,
            Collection.is_public == True
        )
    )
    collection = result.scalar_one_or_none()
    
    if not collection or collection.is_expired:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found"
        )
    
    # Log inquiry event
    event = CollectionEvent(
        collection_id=collection.id,
        event_type="inquiry",
        client_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        inquiry_name=data.name,
        inquiry_email=data.email,
        inquiry_phone=data.phone,
        inquiry_message=data.message,
    )
    db.add(event)
    await db.commit()
    
    # TODO: Send notification to agent
    # TODO: Create/update amoCRM lead
    
    return {"message": "Inquiry submitted successfully"}
