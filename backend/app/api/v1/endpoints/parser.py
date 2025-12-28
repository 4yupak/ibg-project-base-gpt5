"""
Smart Parser API Endpoints - Price parsing with learning capabilities.

Endpoints:
- POST /upload - Upload file and get column detection
- POST /confirm-mapping - Confirm/correct column mappings
- POST /parse - Parse with confirmed mappings
- GET /session/{session_id} - Get session status
- GET /learning-stats - Get learning statistics
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.user import User, UserRole
from app.services.price_parser.smart_parser import get_smart_parser, SmartPriceParser
from app.api.v1.endpoints.auth import get_current_user
from app.api.v1.endpoints.users import require_roles

router = APIRouter()


# ============== Pydantic Models ==============

class ColumnDetectionResponse(BaseModel):
    """Column detection result."""
    index: int
    header: str
    suggested_field: str
    confidence: float


class UploadResponse(BaseModel):
    """Response from file upload."""
    session_id: str
    file_name: str
    file_type: str
    total_rows: int
    columns_detected: List[ColumnDetectionResponse]
    preview_rows: List[dict]
    state: str


class ColumnMappingInput(BaseModel):
    """Input for confirming a single column mapping."""
    column_index: int
    field: str = Field(..., description="Current suggested field")
    approved: bool = Field(True, description="True if user approves suggestion")
    correct_field: Optional[str] = Field(None, description="Correct field if not approved")


class ConfirmMappingRequest(BaseModel):
    """Request to confirm column mappings."""
    session_id: str
    mappings: List[ColumnMappingInput]


class ConfirmMappingResponse(BaseModel):
    """Response from confirming mappings."""
    success: bool
    learning_updated: bool
    confirmed_fields: List[str]


class ParseRequest(BaseModel):
    """Request to parse with confirmed mappings."""
    session_id: str
    project_id: Optional[int] = None
    currency: str = Field("THB", description="Currency code")


class ParsedUnitResponse(BaseModel):
    """Single parsed unit."""
    unit_number: str
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    area_sqm: Optional[float] = None
    floor: Optional[int] = None
    building: Optional[str] = None
    price: Optional[float] = None
    price_per_sqm: Optional[float] = None
    currency: str = "THB"
    layout_type: Optional[str] = None
    view_type: Optional[str] = None
    status: str = "unknown"
    is_valid: bool = True


class ParseResponse(BaseModel):
    """Response from parsing."""
    success: bool
    units_parsed: int
    valid_units: int
    invalid_units: int
    units: List[ParsedUnitResponse]
    errors: List[str]
    warnings: List[str]


class SessionStatusResponse(BaseModel):
    """Session status response."""
    session_id: str
    file_name: str
    file_type: str
    total_rows: int
    state: str
    columns_detected: List[ColumnDetectionResponse]
    confirmed_mappings: dict
    parsed_units_count: int
    errors: List[str]
    warnings: List[str]


class LearningStatsResponse(BaseModel):
    """Learning statistics response."""
    total_feedbacks: int
    approved_count: int
    corrected_count: int
    patterns_learned: int
    accuracy_rate: float
    patterns_by_field: dict


class AvailableFieldsResponse(BaseModel):
    """Available fields for mapping."""
    fields: List[dict]


# ============== Endpoints ==============

@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    sheet_name: Optional[str] = Query(None, description="Sheet name for Excel files"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a price file and get automatic column detection.
    
    Supported formats: PDF, Excel (.xlsx, .xls), CSV
    
    Returns:
    - session_id: Use this for subsequent operations
    - columns_detected: Auto-detected column mappings with confidence scores
    - preview_rows: First 10 rows for preview
    """
    # Validate file type
    allowed_extensions = ['.pdf', '.xlsx', '.xls', '.csv']
    file_ext = '.' + file.filename.split('.')[-1].lower() if '.' in file.filename else ''
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
        )
    
    # Check file size (50MB max)
    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size is 50MB"
        )
    
    # Get parser and process
    parser = get_smart_parser()
    
    try:
        session = await parser.upload(
            file_content=content,
            filename=file.filename,
            sheet_name=sheet_name
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process file: {str(e)}"
        )
    
    if session.state == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=session.errors[0] if session.errors else "Unknown error"
        )
    
    return UploadResponse(
        session_id=session.session_id,
        file_name=session.file_name,
        file_type=session.file_type,
        total_rows=session.total_rows,
        columns_detected=[
            ColumnDetectionResponse(
                index=c.index,
                header=c.header,
                suggested_field=c.suggested_field,
                confidence=c.confidence
            )
            for c in session.column_detections
        ],
        preview_rows=session.raw_rows[:10],
        state=session.state
    )


@router.post("/confirm-mapping", response_model=ConfirmMappingResponse)
async def confirm_mapping(
    request: ConfirmMappingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Confirm or correct column mappings.
    
    The parser learns from your corrections and improves for future files.
    
    For each column, provide:
    - column_index: Index of the column
    - field: Currently suggested field
    - approved: True if the suggestion is correct
    - correct_field: The correct field name if approved=False
    """
    parser = get_smart_parser()
    session = parser.get_session(request.session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {request.session_id}"
        )
    
    try:
        mappings_data = [
            {
                'column_index': m.column_index,
                'field': m.field,
                'approved': m.approved,
                'correct_field': m.correct_field
            }
            for m in request.mappings
        ]
        
        success = parser.confirm_mappings(request.session_id, mappings_data)
        
        return ConfirmMappingResponse(
            success=success,
            learning_updated=True,
            confirmed_fields=list(session.confirmed_mappings.keys())
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to confirm mappings: {str(e)}"
        )


@router.post("/parse", response_model=ParseResponse)
async def parse_file(
    request: ParseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Parse the uploaded file using confirmed column mappings.
    
    Returns parsed units ready for ingestion into the database.
    """
    parser = get_smart_parser()
    session = parser.get_session(request.session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {request.session_id}"
        )
    
    result = parser.parse(
        session_id=request.session_id,
        currency=request.currency
    )
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error_message or "Parsing failed"
        )
    
    units = []
    for unit in (result.data.units if result.data else []):
        units.append(ParsedUnitResponse(
            unit_number=unit.unit_number,
            bedrooms=unit.bedrooms,
            bathrooms=unit.bathrooms,
            area_sqm=unit.area_sqm,
            floor=unit.floor,
            building=unit.building,
            price=unit.price,
            price_per_sqm=unit.price_per_sqm,
            currency=unit.currency,
            layout_type=unit.layout_type,
            view_type=unit.view_type,
            status=unit.status.value if hasattr(unit.status, 'value') else str(unit.status),
            is_valid=unit.is_valid
        ))
    
    valid_count = sum(1 for u in units if u.is_valid)
    
    return ParseResponse(
        success=True,
        units_parsed=len(units),
        valid_units=valid_count,
        invalid_units=len(units) - valid_count,
        units=units,
        errors=session.errors,
        warnings=result.warnings or []
    )


@router.get("/session/{session_id}", response_model=SessionStatusResponse)
async def get_session_status(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current session status."""
    parser = get_smart_parser()
    session = parser.get_session(session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}"
        )
    
    return SessionStatusResponse(
        session_id=session.session_id,
        file_name=session.file_name,
        file_type=session.file_type,
        total_rows=session.total_rows,
        state=session.state,
        columns_detected=[
            ColumnDetectionResponse(
                index=c.index,
                header=c.header,
                suggested_field=c.suggested_field,
                confidence=c.confidence
            )
            for c in session.column_detections
        ],
        confirmed_mappings=session.confirmed_mappings,
        parsed_units_count=len(session.parsed_units),
        errors=session.errors,
        warnings=session.warnings
    )


@router.delete("/session/{session_id}")
async def cleanup_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cleanup and remove a session from memory."""
    parser = get_smart_parser()
    
    if parser.cleanup_session(session_id):
        return {"success": True, "message": f"Session {session_id} cleaned up"}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}"
        )


@router.get("/learning-stats", response_model=LearningStatsResponse)
async def get_learning_stats(
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ANALYST)),
    db: AsyncSession = Depends(get_db)
):
    """
    Get learning statistics for the parser.
    
    Shows how the parser has learned from user feedback.
    Admin/Analyst only.
    """
    parser = get_smart_parser()
    stats = parser.get_learning_stats()
    
    return LearningStatsResponse(
        total_feedbacks=stats.get('total_feedbacks', 0),
        approved_count=stats.get('approved_count', 0),
        corrected_count=stats.get('corrected_count', 0),
        patterns_learned=stats.get('patterns_learned', 0),
        accuracy_rate=stats.get('accuracy_rate', 0.0),
        patterns_by_field=stats.get('patterns_by_field', {})
    )


@router.get("/available-fields", response_model=AvailableFieldsResponse)
async def get_available_fields(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of available fields for column mapping.
    
    Returns field names with descriptions for UI display.
    """
    fields = [
        {
            "name": "unit_number",
            "label": "Unit Number",
            "label_ru": "Номер юнита",
            "description": "Unit identifier (required)",
            "required": True
        },
        {
            "name": "bedrooms",
            "label": "Bedrooms",
            "label_ru": "Спальни",
            "description": "Number of bedrooms",
            "required": False
        },
        {
            "name": "bathrooms",
            "label": "Bathrooms",
            "label_ru": "Санузлы",
            "description": "Number of bathrooms",
            "required": False
        },
        {
            "name": "area",
            "label": "Area (sqm)",
            "label_ru": "Площадь (м²)",
            "description": "Total area in square meters",
            "required": False
        },
        {
            "name": "floor",
            "label": "Floor",
            "label_ru": "Этаж",
            "description": "Floor number",
            "required": False
        },
        {
            "name": "building",
            "label": "Building",
            "label_ru": "Корпус",
            "description": "Building/tower name",
            "required": False
        },
        {
            "name": "price",
            "label": "Price",
            "label_ru": "Цена",
            "description": "Unit price",
            "required": False
        },
        {
            "name": "price_per_sqm",
            "label": "Price per sqm",
            "label_ru": "Цена за м²",
            "description": "Price per square meter",
            "required": False
        },
        {
            "name": "status",
            "label": "Status",
            "label_ru": "Статус",
            "description": "Availability status",
            "required": False
        },
        {
            "name": "view",
            "label": "View",
            "label_ru": "Вид",
            "description": "View type (sea, garden, etc.)",
            "required": False
        },
        {
            "name": "layout",
            "label": "Layout Type",
            "label_ru": "Планировка",
            "description": "Layout/apartment type",
            "required": False
        },
        {
            "name": "phase",
            "label": "Phase",
            "label_ru": "Фаза",
            "description": "Project phase",
            "required": False
        },
        {
            "name": "unknown",
            "label": "Skip / Unknown",
            "label_ru": "Пропустить",
            "description": "Don't use this column",
            "required": False
        },
    ]
    
    return AvailableFieldsResponse(fields=fields)


@router.post("/reset-learning")
async def reset_learning(
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """
    Reset all learned patterns.
    
    WARNING: This will delete all learned column mappings.
    Admin only.
    """
    parser = get_smart_parser()
    parser.feedback_store.reset()
    
    return {
        "success": True,
        "message": "Learning data reset successfully"
    }
