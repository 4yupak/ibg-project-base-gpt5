"""
Files endpoints - upload, download, and price parsing.
"""
import os
import tempfile
import hashlib
import logging
from typing import List, Optional
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from app.db.database import get_db
from app.models.price import PriceVersion, PriceSourceType, PriceVersionStatus
from app.models.project import Project
from app.models.user import User, UserRole
from app.api.v1.endpoints.auth import require_roles, get_current_user
from app.services.price_parser import PriceParserFactory, ParsingResult
from app.services.price_ingestion_service import ingest_price_data

logger = logging.getLogger(__name__)
router = APIRouter()


# Schemas
class FileUploadResponse(BaseModel):
    filename: str
    file_url: str
    file_hash: str
    size_bytes: int


class PriceIngestionRequest(BaseModel):
    project_id: int
    source_type: str
    source_url: Optional[str] = None  # For Google Sheets, links
    currency: str = "THB"
    sheet_name: Optional[str] = None  # For Google Sheets


class PriceIngestionResponse(BaseModel):
    price_version_id: int
    status: str
    message: str


class ValidationResponse(BaseModel):
    valid: bool
    file_type: Optional[str]
    parser_type: Optional[str]
    file_info: dict
    warnings: List[str]
    error: Optional[str] = None


class ParsePreviewResponse(BaseModel):
    success: bool
    total_units: int
    valid_units: int
    invalid_units: int
    currency: Optional[str]
    project_name: Optional[str]
    sample_units: List[dict]
    warnings: List[str]
    error: Optional[str] = None


class ProcessingStatusResponse(BaseModel):
    id: int
    status: str
    processing_started_at: Optional[datetime]
    processing_completed_at: Optional[datetime]
    units_created: int
    units_updated: int
    units_unchanged: int
    units_errors: int
    errors: Optional[List[dict]]
    warnings: Optional[List[dict]]


# Helper functions
def get_file_hash(content: bytes) -> str:
    """Calculate SHA256 hash of file content."""
    return hashlib.sha256(content).hexdigest()


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    allowed_extensions = {'.pdf', '.xlsx', '.xls', '.csv'}
    ext = Path(filename).suffix.lower()
    return ext in allowed_extensions


async def save_temp_file(content: bytes, filename: str) -> str:
    """Save content to temp file and return path."""
    ext = Path(filename).suffix.lower()
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(content)
        return tmp.name


# Endpoints
@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ANALYST)),
    db: AsyncSession = Depends(get_db)
):
    """Upload a file to storage."""
    
    # Validate file type
    if not allowed_file(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File type not allowed. Allowed types: PDF, Excel, CSV"
        )
    
    # Read file content
    content = await file.read()
    
    # Check file size (max 50MB)
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size is 50MB"
        )
    
    # Calculate hash
    file_hash = get_file_hash(content)
    
    # TODO: Upload to S3/MinIO storage
    # For now, return placeholder URL
    file_url = f"/files/{file_hash}/{file.filename}"
    
    return FileUploadResponse(
        filename=file.filename,
        file_url=file_url,
        file_hash=file_hash,
        size_bytes=len(content)
    )


@router.post("/validate")
async def validate_file(
    file: UploadFile = File(...),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ANALYST))
) -> ValidationResponse:
    """
    Validate a price file without processing.
    Returns file info and whether it can be parsed.
    """
    if not allowed_file(file.filename):
        return ValidationResponse(
            valid=False,
            file_type=None,
            parser_type=None,
            file_info={},
            warnings=[],
            error="File type not allowed. Allowed types: PDF, Excel, CSV"
        )
    
    content = await file.read()
    
    if len(content) > 50 * 1024 * 1024:
        return ValidationResponse(
            valid=False,
            file_type=None,
            parser_type=None,
            file_info={'size_bytes': len(content)},
            warnings=[],
            error="File too large. Maximum size is 50MB"
        )
    
    # Save to temp file for validation
    tmp_path = await save_temp_file(content, file.filename)
    
    try:
        factory = PriceParserFactory(
            openai_api_key=os.getenv('OPENAI_API_KEY'),
            google_credentials_path=os.getenv('GOOGLE_CREDENTIALS_PATH')
        )
        
        result = await factory.validate_file(tmp_path)
        
        return ValidationResponse(
            valid=result['valid'],
            file_type=result.get('file_type'),
            parser_type=result.get('parser_type'),
            file_info=result.get('file_info', {}),
            warnings=result.get('warnings', []),
            error=result.get('error')
        )
    finally:
        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


@router.post("/preview")
async def preview_file(
    file: UploadFile = File(...),
    currency: str = Form("THB"),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ANALYST))
) -> ParsePreviewResponse:
    """
    Parse file and return preview without saving to database.
    Useful for reviewing data before committing.
    """
    if not allowed_file(file.filename):
        return ParsePreviewResponse(
            success=False,
            total_units=0,
            valid_units=0,
            invalid_units=0,
            currency=None,
            project_name=None,
            sample_units=[],
            warnings=[],
            error="File type not allowed"
        )
    
    content = await file.read()
    tmp_path = await save_temp_file(content, file.filename)
    
    try:
        factory = PriceParserFactory(
            openai_api_key=os.getenv('OPENAI_API_KEY')
        )
        
        result = await factory.parse(tmp_path, currency=currency)
        
        if not result.success:
            return ParsePreviewResponse(
                success=False,
                total_units=0,
                valid_units=0,
                invalid_units=0,
                currency=None,
                project_name=None,
                sample_units=[],
                warnings=result.warnings,
                error=result.error_message
            )
        
        data = result.data
        
        # Get sample units (first 10 valid units)
        sample_units = [
            {
                'unit_number': u.unit_number,
                'bedrooms': u.bedrooms,
                'area_sqm': u.area_sqm,
                'floor': u.floor,
                'price': u.price,
                'price_per_sqm': u.price_per_sqm,
                'status': u.status.value if u.status else None,
                'view_type': u.view_type,
                'building': u.building,
                'validation_errors': u.validation_errors
            }
            for u in data.valid_units[:10]
        ]
        
        # Add some invalid units for review
        if data.invalid_units:
            sample_units.extend([
                {
                    'unit_number': u.unit_number,
                    'bedrooms': u.bedrooms,
                    'area_sqm': u.area_sqm,
                    'floor': u.floor,
                    'price': u.price,
                    'status': u.status.value if u.status else None,
                    'is_invalid': True,
                    'validation_errors': u.validation_errors
                }
                for u in data.invalid_units[:5]
            ])
        
        return ParsePreviewResponse(
            success=True,
            total_units=data.total_count,
            valid_units=data.valid_count,
            invalid_units=data.invalid_count,
            currency=data.currency,
            project_name=data.project_name,
            sample_units=sample_units,
            warnings=result.warnings
        )
        
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


@router.post("/ingest-price", response_model=PriceIngestionResponse)
async def ingest_price_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(None),
    project_id: int = Form(...),
    source_type: str = Form(...),
    source_url: Optional[str] = Form(None),
    currency: str = Form("THB"),
    process_async: bool = Form(True),  # Whether to process in background
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ANALYST)),
    db: AsyncSession = Depends(get_db)
):
    """
    Ingest price data from file or URL.
    Creates a PriceVersion and processes the data.
    """
    
    # Validate source type
    try:
        source_type_enum = PriceSourceType(source_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid source type. Allowed: {[t.value for t in PriceSourceType]}"
        )
    
    # Validate project exists
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check if file or URL is provided
    if source_type_enum in [PriceSourceType.PDF, PriceSourceType.EXCEL] and not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is required for PDF/Excel source types"
        )
    
    if source_type_enum == PriceSourceType.GOOGLE_SHEETS and not source_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source URL is required for Google Sheets"
        )
    
    # Read file content if provided
    file_content = None
    file_hash = None
    filename = None
    tmp_path = None
    
    if file:
        if not allowed_file(file.filename):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File type not allowed"
            )
        
        file_content = await file.read()
        file_hash = get_file_hash(file_content)
        filename = file.filename
        
        # Check for duplicate
        existing = await db.execute(
            select(PriceVersion).where(
                PriceVersion.project_id == project_id,
                PriceVersion.source_file_hash == file_hash,
                PriceVersion.status.in_([
                    PriceVersionStatus.COMPLETED,
                    PriceVersionStatus.APPROVED
                ])
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This file has already been processed"
            )
        
        # Save to temp file for processing
        tmp_path = await save_temp_file(file_content, filename)
    
    # Get next version number
    max_version = await db.execute(
        select(func.max(PriceVersion.version_number)).where(
            PriceVersion.project_id == project_id
        )
    )
    version_number = (max_version.scalar() or 0) + 1
    
    # Create price version
    price_version = PriceVersion(
        project_id=project_id,
        version_number=version_number,
        source_type=source_type_enum,
        source_url=source_url,
        source_file_name=filename,
        source_file_hash=file_hash,
        status=PriceVersionStatus.PENDING,
        original_currency=currency,
        created_by_id=current_user.id
    )
    
    db.add(price_version)
    await db.commit()
    await db.refresh(price_version)
    
    # Process based on source type
    if process_async:
        # Queue background task
        from app.tasks.price_tasks import process_price_file, process_google_sheet
        
        if source_type_enum == PriceSourceType.GOOGLE_SHEETS:
            process_google_sheet.delay(
                price_version_id=price_version.id,
                sheet_url=source_url,
                project_id=project_id,
                user_id=current_user.id
            )
        elif tmp_path:
            process_price_file.delay(
                price_version_id=price_version.id,
                file_path=tmp_path,
                source_type=source_type_enum.value,
                project_id=project_id,
                user_id=current_user.id
            )
        
        return PriceIngestionResponse(
            price_version_id=price_version.id,
            status=price_version.status.value,
            message="Price ingestion started. Check status using the price version ID."
        )
    else:
        # Process synchronously
        try:
            factory = PriceParserFactory(
                openai_api_key=os.getenv('OPENAI_API_KEY'),
                google_credentials_path=os.getenv('GOOGLE_CREDENTIALS_PATH')
            )
            
            if source_type_enum == PriceSourceType.GOOGLE_SHEETS:
                result = await factory.parse(source_url, currency=currency)
            else:
                result = await factory.parse(tmp_path, currency=currency)
            
            if not result.success:
                price_version.status = PriceVersionStatus.FAILED
                price_version.errors = [{'message': result.error_message}]
                await db.commit()
                
                return PriceIngestionResponse(
                    price_version_id=price_version.id,
                    status='failed',
                    message=f"Parsing failed: {result.error_message}"
                )
            
            # Ingest data
            ingestion_result = await ingest_price_data(
                db=db,
                project_id=project_id,
                price_version_id=price_version.id,
                parsed_data=result.data,
                user_id=current_user.id
            )
            
            return PriceIngestionResponse(
                price_version_id=price_version.id,
                status=ingestion_result['status'],
                message=f"Processed: {ingestion_result.get('statistics', {}).get('created', 0)} created, "
                        f"{ingestion_result.get('statistics', {}).get('updated', 0)} updated"
            )
            
        except Exception as e:
            logger.exception(f"Price ingestion failed: {e}")
            price_version.status = PriceVersionStatus.FAILED
            price_version.errors = [{'message': str(e)}]
            await db.commit()
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Processing failed: {str(e)}"
            )
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass


@router.post("/ingest-from-url", response_model=PriceIngestionResponse)
async def ingest_from_url(
    background_tasks: BackgroundTasks,
    data: PriceIngestionRequest,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ANALYST)),
    db: AsyncSession = Depends(get_db)
):
    """Ingest price data from URL (Google Sheets, Yandex Disk, etc.)."""
    
    # Validate source type
    try:
        source_type_enum = PriceSourceType(data.source_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid source type"
        )
    
    if not data.source_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source URL is required"
        )
    
    # Validate project
    project = await db.get(Project, data.project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Get next version number
    max_version = await db.execute(
        select(func.max(PriceVersion.version_number)).where(
            PriceVersion.project_id == data.project_id
        )
    )
    version_number = (max_version.scalar() or 0) + 1
    
    # Create price version
    price_version = PriceVersion(
        project_id=data.project_id,
        version_number=version_number,
        source_type=source_type_enum,
        source_url=data.source_url,
        status=PriceVersionStatus.PENDING,
        original_currency=data.currency,
        created_by_id=current_user.id
    )
    
    db.add(price_version)
    await db.commit()
    await db.refresh(price_version)
    
    # Queue background task
    from app.tasks.price_tasks import process_google_sheet
    
    if source_type_enum == PriceSourceType.GOOGLE_SHEETS:
        process_google_sheet.delay(
            price_version_id=price_version.id,
            sheet_url=data.source_url,
            project_id=data.project_id,
            sheet_name=data.sheet_name,
            user_id=current_user.id
        )
    
    return PriceIngestionResponse(
        price_version_id=price_version.id,
        status=price_version.status.value,
        message="Price ingestion from URL started."
    )


@router.get("/price-version/{version_id}/status", response_model=ProcessingStatusResponse)
async def get_ingestion_status(
    version_id: int,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ANALYST)),
    db: AsyncSession = Depends(get_db)
):
    """Get status of price ingestion."""
    
    version = await db.get(PriceVersion, version_id)
    
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Price version not found"
        )
    
    return ProcessingStatusResponse(
        id=version.id,
        status=version.status.value,
        processing_started_at=version.processing_started_at,
        processing_completed_at=version.processing_completed_at,
        units_created=version.units_created or 0,
        units_updated=version.units_updated or 0,
        units_unchanged=version.units_unchanged or 0,
        units_errors=version.units_errors or 0,
        errors=version.errors,
        warnings=version.warnings
    )


@router.post("/price-version/{version_id}/retry")
async def retry_processing(
    version_id: int,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Retry processing a failed price version."""
    
    version = await db.get(PriceVersion, version_id)
    
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Price version not found"
        )
    
    if version.status not in [PriceVersionStatus.FAILED, PriceVersionStatus.REQUIRES_REVIEW]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only failed or review-required versions can be retried"
        )
    
    # Reset status
    version.status = PriceVersionStatus.PENDING
    version.errors = None
    version.warnings = None
    version.processing_started_at = None
    version.processing_completed_at = None
    await db.commit()
    
    # Queue task
    from app.tasks.price_tasks import process_google_sheet, parse_pdf_with_llm
    
    if version.source_type == PriceSourceType.GOOGLE_SHEETS and version.source_url:
        process_google_sheet.delay(
            price_version_id=version.id,
            sheet_url=version.source_url,
            project_id=version.project_id,
            user_id=current_user.id
        )
    else:
        # For failed PDF/Excel, try LLM parsing
        # Note: Original file would need to be re-uploaded or stored
        parse_pdf_with_llm.delay(
            price_version_id=version.id,
            file_path=version.source_url or '',  # Would need actual file path
            project_id=version.project_id,
            user_id=current_user.id
        )
    
    return {
        "message": "Processing retry queued",
        "price_version_id": version.id
    }
