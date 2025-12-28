"""
Notion Integration API endpoints.

Provides:
- Test connection
- Get database schema
- Sync projects from Notion
- Get price list files for parsing
"""
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import logging

from app.db.database import get_db
from app.models.user import User, UserRole
from app.api.v1.endpoints.auth import get_current_user
from app.api.v1.endpoints.users import require_roles

# Helper function for admin check
get_current_admin_user = require_roles(UserRole.ADMIN)
from app.services.notion import NotionSyncService
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


# ===== Schemas =====

class NotionConnectionTest(BaseModel):
    """Response for connection test."""
    success: bool
    database_id: Optional[str] = None
    title: Optional[str] = None
    properties_count: Optional[int] = None
    properties: Optional[List[str]] = None
    error: Optional[str] = None


class NotionPropertySchema(BaseModel):
    """Schema for a Notion property."""
    type: str
    id: str
    options: Optional[List[str]] = None


class NotionDatabaseSchema(BaseModel):
    """Response for database schema."""
    success: bool
    database_id: Optional[str] = None
    title: Optional[str] = None
    properties: Optional[dict[str, NotionPropertySchema]] = None
    error: Optional[str] = None


class SyncResultResponse(BaseModel):
    """Response for sync operation."""
    success: bool = True
    projects_created: int = 0
    projects_updated: int = 0
    projects_skipped: int = 0
    projects_failed: int = 0
    errors: List[str] = []
    warnings: List[str] = []
    price_files_found: List[dict] = []
    synced_at: str


class PriceFileInfo(BaseModel):
    """Price list file information."""
    project_name: str
    notion_page_id: str
    price_urls: List[str]
    layout_urls: Optional[List[str]] = None


class FieldMappingInfo(BaseModel):
    """Field mapping information."""
    notion_field: str
    propbase_field: str
    notion_type: str
    description: str
    required: bool = False


class FieldMappingResponse(BaseModel):
    """Response for field mapping."""
    mappings: List[FieldMappingInfo]
    district_mappings: dict[str, str]
    property_type_mappings: dict[str, Optional[str]]


# ===== Helper Functions =====

def get_notion_service() -> NotionSyncService:
    """Get Notion service instance."""
    if not settings.NOTION_API_KEY:
        raise HTTPException(
            status_code=400,
            detail="NOTION_API_KEY is not configured"
        )
    if not settings.NOTION_DATABASE_ID:
        raise HTTPException(
            status_code=400,
            detail="NOTION_DATABASE_ID is not configured"
        )
    
    return NotionSyncService(
        api_key=settings.NOTION_API_KEY,
        database_id=settings.NOTION_DATABASE_ID,
    )


# ===== Endpoints =====

@router.get("/test-connection", response_model=NotionConnectionTest)
async def test_notion_connection(
    current_user: User = Depends(get_current_admin_user),
):
    """
    Test Notion API connection.
    
    Returns database info if successful.
    """
    try:
        service = get_notion_service()
        result = await service.test_connection()
        return NotionConnectionTest(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Notion connection test error: {e}")
        return NotionConnectionTest(
            success=False,
            error=str(e),
        )


@router.get("/schema", response_model=NotionDatabaseSchema)
async def get_database_schema(
    current_user: User = Depends(get_current_admin_user),
):
    """
    Get Notion database schema (properties).
    
    Returns all properties with their types and options.
    """
    try:
        service = get_notion_service()
        result = await service.get_database_schema()
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting database schema: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/field-mapping", response_model=FieldMappingResponse)
async def get_field_mapping(
    current_user: User = Depends(get_current_admin_user),
):
    """
    Get current field mapping configuration.
    
    Shows how Notion fields map to PropBase fields.
    """
    from app.services.notion.notion_field_mapping import NotionFieldMapping
    
    mapping = NotionFieldMapping()
    
    mappings = []
    for notion_field, field_mapping in mapping.mappings.items():
        mappings.append(FieldMappingInfo(
            notion_field=notion_field,
            propbase_field=field_mapping.propbase_field,
            notion_type=field_mapping.notion_type.value,
            description=field_mapping.description,
            required=field_mapping.required,
        ))
    
    return FieldMappingResponse(
        mappings=mappings,
        district_mappings=mapping.district_mapping,
        property_type_mappings=mapping.property_type_mapping,
    )


@router.post("/sync", response_model=SyncResultResponse)
async def sync_all_projects(
    dry_run: bool = Query(False, description="If true, don't actually save changes"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Sync all projects from Notion database.
    
    - Creates new projects that don't exist in PropBase
    - Updates existing projects (matched by notion_page_id)
    - Returns list of price list files found for parsing
    """
    try:
        service = get_notion_service()
        result = await service.sync_all(db=db, dry_run=dry_run)
        
        return SyncResultResponse(
            success=result.success,
            projects_created=result.projects_created,
            projects_updated=result.projects_updated,
            projects_skipped=result.projects_skipped,
            projects_failed=result.projects_failed,
            errors=result.errors,
            warnings=result.warnings,
            price_files_found=result.price_files_found,
            synced_at=result.synced_at.isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sync error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/{page_id}", response_model=SyncResultResponse)
async def sync_single_project(
    page_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Sync a single project by Notion page ID.
    """
    try:
        service = get_notion_service()
        result = await service.sync_single_by_page_id(db=db, page_id=page_id)
        
        return SyncResultResponse(
            success=result.success,
            projects_created=result.projects_created,
            projects_updated=result.projects_updated,
            projects_skipped=result.projects_skipped,
            projects_failed=result.projects_failed,
            errors=result.errors,
            warnings=result.warnings,
            price_files_found=result.price_files_found,
            synced_at=result.synced_at.isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sync error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/price-files", response_model=List[PriceFileInfo])
async def get_price_list_files(
    current_user: User = Depends(get_current_admin_user),
):
    """
    Get all price list files from Notion projects.
    
    Returns URLs to price list PDFs/Excel files that can be parsed.
    """
    try:
        service = get_notion_service()
        files = await service.get_price_list_files()
        
        return [PriceFileInfo(**f) for f in files]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting price files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preview")
async def preview_notion_projects(
    limit: int = Query(5, description="Number of projects to preview", ge=1, le=20),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Preview projects from Notion without syncing.
    
    Returns parsed data for first N projects.
    """
    try:
        service = get_notion_service()
        projects = await service.fetch_all_projects()
        
        preview_data = []
        for project in projects[:limit]:
            preview_data.append({
                "notion_page_id": project.notion_page_id,
                "name": project.name,
                "parsed_data": project.parsed_data,
                "price_list_urls": project.price_list_urls,
                "layout_urls": project.layout_urls,
                "gallery_urls": project.gallery_urls,
                "errors": project.errors,
            })
        
        return {
            "total_projects": len(projects),
            "previewed": len(preview_data),
            "projects": preview_data,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Preview error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config-status")
async def get_notion_config_status(
    current_user: User = Depends(get_current_admin_user),
):
    """
    Get Notion configuration status.
    
    Shows whether API key and database ID are configured.
    """
    return {
        "api_key_configured": bool(settings.NOTION_API_KEY),
        "database_id_configured": bool(settings.NOTION_DATABASE_ID),
        "database_id": settings.NOTION_DATABASE_ID if settings.NOTION_DATABASE_ID else None,
    }
