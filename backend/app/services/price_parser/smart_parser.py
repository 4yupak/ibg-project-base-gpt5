"""
Smart Price Parser - Price parser with learning capabilities.
Combines file parsing with user feedback for improved accuracy.
"""
import os
import uuid
import tempfile
import pandas as pd
import pdfplumber
from io import BytesIO
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import logging
import hashlib
import re

from .feedback_store import FeedbackStore, ColumnFeedback, get_feedback_store
from .base import ParsedUnit, ParsedPriceData, ParsingResult, UnitStatus

logger = logging.getLogger(__name__)


@dataclass
class ColumnDetection:
    """Result of column detection for a single column."""
    index: int
    header: str
    header_normalized: str
    suggested_field: str
    confidence: float
    approved: Optional[bool] = None
    correct_field: Optional[str] = None


@dataclass
class ParseSession:
    """Parsing session state."""
    session_id: str
    file_name: str
    file_type: str  # excel, pdf, csv
    file_hash: str
    created_at: str
    
    # Raw data
    headers: List[str] = field(default_factory=list)
    raw_rows: List[Dict[str, Any]] = field(default_factory=list)
    total_rows: int = 0
    
    # Column detection
    column_detections: List[ColumnDetection] = field(default_factory=list)
    confirmed_mappings: Dict[str, int] = field(default_factory=dict)  # field -> col_index
    
    # Parsing result
    parsed_units: List[ParsedUnit] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # State
    state: str = "uploaded"  # uploaded, detected, confirmed, parsed
    
    def to_dict(self) -> dict:
        return {
            'session_id': self.session_id,
            'file_name': self.file_name,
            'file_type': self.file_type,
            'total_rows': self.total_rows,
            'state': self.state,
            'columns_detected': [
                {
                    'index': c.index,
                    'header': c.header,
                    'suggested_field': c.suggested_field,
                    'confidence': c.confidence,
                }
                for c in self.column_detections
            ],
            'preview_rows': self.raw_rows[:10],
            'created_at': self.created_at,
        }


class SmartPriceParser:
    """
    Smart Price Parser with learning capabilities.
    
    Workflow:
    1. upload() - Upload and extract raw data
    2. detect_columns() - Auto-detect column mappings with confidence scores
    3. confirm_mappings() - User confirms/corrects mappings (feedback loop)
    4. parse() - Parse data using confirmed mappings
    """
    
    # Target fields for price lists
    TARGET_FIELDS = [
        'unit_number', 'bedrooms', 'bathrooms', 'area', 'floor',
        'building', 'price', 'price_per_sqm', 'status', 'view', 'layout', 'phase'
    ]
    
    def __init__(self, feedback_store: Optional[FeedbackStore] = None):
        """
        Initialize smart parser.
        
        Args:
            feedback_store: FeedbackStore instance for learning. Uses singleton if not provided.
        """
        self.feedback_store = feedback_store or get_feedback_store()
        self.sessions: Dict[str, ParseSession] = {}
    
    async def upload(
        self,
        file_content: bytes,
        filename: str,
        sheet_name: Optional[str] = None
    ) -> ParseSession:
        """
        Upload and extract raw data from file.
        
        Args:
            file_content: Raw file bytes
            filename: Original filename
            sheet_name: Sheet name for Excel files (optional)
            
        Returns:
            ParseSession with extracted data
        """
        # Generate session
        session_id = str(uuid.uuid4())
        file_hash = hashlib.sha256(file_content).hexdigest()[:16]
        file_ext = Path(filename).suffix.lower()
        
        session = ParseSession(
            session_id=session_id,
            file_name=filename,
            file_type=self._detect_file_type(file_ext),
            file_hash=file_hash,
            created_at=datetime.utcnow().isoformat(),
        )
        
        try:
            # Extract raw data based on file type
            if file_ext == '.pdf':
                headers, rows = self._extract_pdf(file_content)
            elif file_ext in ['.xlsx', '.xls']:
                headers, rows = self._extract_excel(file_content, sheet_name)
            elif file_ext == '.csv':
                headers, rows = self._extract_csv(file_content)
            else:
                raise ValueError(f"Unsupported file type: {file_ext}")
            
            session.headers = headers
            session.raw_rows = rows
            session.total_rows = len(rows)
            session.state = "uploaded"
            
            # Auto-detect columns
            self._detect_columns(session)
            
            # Store session
            self.sessions[session_id] = session
            
            logger.info(f"Session {session_id}: Uploaded {filename}, {len(rows)} rows, {len(headers)} columns")
            
        except Exception as e:
            session.errors.append(str(e))
            session.state = "error"
            logger.error(f"Session {session_id}: Upload failed - {e}")
        
        return session
    
    def _detect_file_type(self, ext: str) -> str:
        """Detect file type from extension."""
        ext = ext.lower()
        if ext == '.pdf':
            return 'pdf'
        elif ext in ['.xlsx', '.xls']:
            return 'excel'
        elif ext == '.csv':
            return 'csv'
        return 'unknown'
    
    def _extract_excel(
        self,
        file_content: bytes,
        sheet_name: Optional[str] = None
    ) -> Tuple[List[str], List[Dict]]:
        """Extract data from Excel file."""
        xlsx = pd.ExcelFile(BytesIO(file_content))
        
        # Select sheet
        if sheet_name and sheet_name in xlsx.sheet_names:
            selected_sheet = sheet_name
        else:
            # Try to find price-related sheet
            selected_sheet = None
            for name in xlsx.sheet_names:
                name_lower = name.lower()
                if any(kw in name_lower for kw in ['price', 'unit', 'прайс', 'цен', 'продаж']):
                    selected_sheet = name
                    break
            
            if not selected_sheet:
                selected_sheet = xlsx.sheet_names[0]
        
        df = pd.read_excel(xlsx, sheet_name=selected_sheet)
        
        # Find header row (row with most non-empty values matching our patterns)
        best_header_row = self._find_header_row(df)
        
        if best_header_row > 0:
            # Use that row as headers
            df.columns = df.iloc[best_header_row].astype(str)
            df = df.iloc[best_header_row + 1:].reset_index(drop=True)
        
        # Clean headers
        headers = [str(h).strip() if pd.notna(h) else f'Column_{i}' for i, h in enumerate(df.columns)]
        
        # Convert to list of dicts
        rows = []
        for _, row in df.iterrows():
            row_dict = {}
            for i, h in enumerate(headers):
                val = row.iloc[i] if i < len(row) else None
                row_dict[h] = val if pd.notna(val) else None
            rows.append(row_dict)
        
        # Filter empty rows
        rows = [r for r in rows if any(v is not None for v in r.values())]
        
        return headers, rows
    
    def _extract_csv(self, file_content: bytes) -> Tuple[List[str], List[Dict]]:
        """Extract data from CSV file."""
        # Try different encodings
        for encoding in ['utf-8', 'cp1251', 'latin1']:
            try:
                df = pd.read_csv(BytesIO(file_content), encoding=encoding)
                break
            except:
                continue
        else:
            raise ValueError("Could not decode CSV file")
        
        headers = [str(h).strip() for h in df.columns]
        rows = df.to_dict('records')
        rows = [r for r in rows if any(v is not None and pd.notna(v) for v in r.values())]
        
        return headers, rows
    
    def _extract_pdf(self, file_content: bytes) -> Tuple[List[str], List[Dict]]:
        """Extract data from PDF file."""
        headers = []
        rows = []
        
        with pdfplumber.open(BytesIO(file_content)) as pdf:
            for page_num, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                
                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    
                    # Find header row
                    header_row_idx = self._find_header_row_in_list(table)
                    
                    if not headers:
                        # Use first table's headers
                        headers = [str(h).strip() if h else f'Column_{i}' 
                                   for i, h in enumerate(table[header_row_idx])]
                    
                    # Extract rows
                    for row in table[header_row_idx + 1:]:
                        if not row or all(cell is None or str(cell).strip() == '' for cell in row):
                            continue
                        
                        row_dict = {}
                        for i, header in enumerate(headers):
                            val = row[i] if i < len(row) else None
                            row_dict[header] = val.strip() if val and isinstance(val, str) else val
                        rows.append(row_dict)
        
        return headers, rows
    
    def _find_header_row(self, df: pd.DataFrame, max_rows: int = 10) -> int:
        """Find the header row in a DataFrame."""
        best_row = 0
        best_score = 0
        
        for i in range(min(max_rows, len(df))):
            row = df.iloc[i]
            score = 0
            
            for val in row:
                if pd.notna(val):
                    val_str = str(val).lower()
                    # Check if it looks like a header (matches our patterns)
                    field, confidence = self.feedback_store.suggest_field(val_str)
                    if field != 'unknown' and confidence > 0.3:
                        score += confidence
            
            if score > best_score:
                best_score = score
                best_row = i
        
        return best_row
    
    def _find_header_row_in_list(self, table: List[List], max_rows: int = 5) -> int:
        """Find header row in a list-based table."""
        best_row = 0
        best_score = 0
        
        for i in range(min(max_rows, len(table))):
            row = table[i]
            if not row:
                continue
            
            score = sum(
                1 for cell in row 
                if cell and self.feedback_store.suggest_field(str(cell))[0] != 'unknown'
            )
            
            if score > best_score:
                best_score = score
                best_row = i
        
        return best_row
    
    def _detect_columns(self, session: ParseSession) -> None:
        """Detect column mappings using feedback store."""
        suggestions = self.feedback_store.suggest_all_columns(session.headers)
        
        session.column_detections = [
            ColumnDetection(
                index=s['index'],
                header=s['header'],
                header_normalized=s['header_normalized'],
                suggested_field=s['suggested_field'],
                confidence=s['confidence'],
            )
            for s in suggestions
        ]
        
        session.state = "detected"
        
        logger.info(
            f"Session {session.session_id}: Detected {len(session.column_detections)} columns, "
            f"avg confidence: {sum(c.confidence for c in session.column_detections) / max(1, len(session.column_detections)):.2f}"
        )
    
    def confirm_mappings(
        self,
        session_id: str,
        mappings: List[Dict]
    ) -> bool:
        """
        Confirm or correct column mappings.
        
        Args:
            session_id: Session ID
            mappings: List of dicts with:
                - column_index: int
                - field: str (current suggested field)
                - approved: bool
                - correct_field: str (only if approved=False)
                
        Returns:
            True if successful
        """
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        feedbacks = []
        confirmed = {}
        
        for mapping in mappings:
            col_idx = mapping['column_index']
            
            # Find detection
            detection = next(
                (d for d in session.column_detections if d.index == col_idx),
                None
            )
            if not detection:
                continue
            
            approved = mapping.get('approved', True)
            correct_field = mapping.get('correct_field', detection.suggested_field)
            
            if not approved and not correct_field:
                correct_field = 'unknown'
            elif approved:
                correct_field = detection.suggested_field
            
            # Update detection
            detection.approved = approved
            detection.correct_field = correct_field
            
            # Store confirmed mapping
            if correct_field != 'unknown':
                confirmed[correct_field] = col_idx
            
            # Create feedback
            feedbacks.append(ColumnFeedback(
                header_text=detection.header,
                header_normalized=detection.header_normalized,
                suggested_field=detection.suggested_field,
                correct_field=correct_field,
                approved=approved,
                file_type=session.file_type,
                file_name=session.file_name,
            ))
        
        # Add feedbacks to store (learning)
        self.feedback_store.add_feedbacks_batch(feedbacks)
        
        # Update session
        session.confirmed_mappings = confirmed
        session.state = "confirmed"
        
        logger.info(
            f"Session {session_id}: Confirmed {len(confirmed)} mappings, "
            f"learned from {len(feedbacks)} feedbacks"
        )
        
        return True
    
    def parse(
        self,
        session_id: str,
        currency: str = "THB"
    ) -> ParsingResult:
        """
        Parse data using confirmed mappings.
        
        Args:
            session_id: Session ID
            currency: Currency code
            
        Returns:
            ParsingResult with parsed units
        """
        session = self.sessions.get(session_id)
        if not session:
            return ParsingResult(
                success=False,
                error_message=f"Session not found: {session_id}",
                error_type="session_not_found"
            )
        
        if session.state not in ("detected", "confirmed"):
            return ParsingResult(
                success=False,
                error_message=f"Session not ready for parsing. State: {session.state}",
                error_type="invalid_state"
            )
        
        # Use confirmed mappings or auto-detected ones
        mappings = session.confirmed_mappings
        if not mappings:
            # Auto-confirm high-confidence detections
            mappings = {}
            for det in session.column_detections:
                if det.confidence >= 0.5 and det.suggested_field != 'unknown':
                    mappings[det.suggested_field] = det.index
        
        if 'unit_number' not in mappings:
            return ParsingResult(
                success=False,
                error_message="Unit number column not identified",
                error_type="missing_required_column"
            )
        
        # Parse rows
        units = []
        warnings = []
        
        for row_idx, row_data in enumerate(session.raw_rows):
            try:
                unit = self._parse_row(row_data, mappings, session.headers, currency)
                if unit:
                    units.append(unit)
            except Exception as e:
                warnings.append(f"Row {row_idx + 1}: {str(e)}")
        
        # Create result
        parsed_data = ParsedPriceData(
            units=units,
            currency=currency,
            raw_headers=session.headers,
        )
        
        session.parsed_units = units
        session.warnings = warnings
        session.state = "parsed"
        
        logger.info(
            f"Session {session_id}: Parsed {len(units)} units from {len(session.raw_rows)} rows"
        )
        
        return ParsingResult(
            success=True,
            data=parsed_data,
            warnings=warnings,
            parsing_method="smart_parser",
        )
    
    def _parse_row(
        self,
        row_data: Dict,
        mappings: Dict[str, int],
        headers: List[str],
        currency: str
    ) -> Optional[ParsedUnit]:
        """Parse a single row using confirmed mappings."""
        
        def get_value(field: str) -> Any:
            if field not in mappings:
                return None
            col_idx = mappings[field]
            if col_idx >= len(headers):
                return None
            header = headers[col_idx]
            return row_data.get(header)
        
        # Get unit number (required)
        unit_number = get_value('unit_number')
        if not unit_number or (isinstance(unit_number, float) and pd.isna(unit_number)):
            return None
        unit_number = str(unit_number).strip()
        if not unit_number or unit_number.lower() in ['nan', 'none', '']:
            return None
        
        # Parse other fields
        unit = ParsedUnit(
            unit_number=unit_number,
            bedrooms=self._parse_int(get_value('bedrooms')),
            bathrooms=self._parse_int(get_value('bathrooms')),
            area_sqm=self._parse_float(get_value('area')),
            floor=self._parse_int(get_value('floor')),
            building=self._parse_string(get_value('building')),
            price=self._parse_float(get_value('price')),
            price_per_sqm=self._parse_float(get_value('price_per_sqm')),
            currency=currency,
            layout_type=self._parse_string(get_value('layout')),
            view_type=self._parse_string(get_value('view')),
            status=self._parse_status(get_value('status')),
            phase=self._parse_string(get_value('phase')),
            raw_row=row_data,
        )
        
        # Try to extract bedrooms from layout if missing
        if unit.bedrooms is None and unit.layout_type:
            unit.bedrooms = self._extract_bedrooms(unit.layout_type)
        
        return unit
    
    def _parse_int(self, value: Any) -> Optional[int]:
        """Parse integer value."""
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        try:
            # Extract number from string
            text = str(value).strip()
            match = re.search(r'(\d+)', text)
            if match:
                return int(match.group(1))
        except:
            pass
        return None
    
    def _parse_float(self, value: Any) -> Optional[float]:
        """Parse float value."""
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        if isinstance(value, (int, float)):
            return float(value)
        try:
            text = str(value).strip()
            # Remove currency symbols and spaces
            text = re.sub(r'[฿$€₽\s,]', '', text)
            # Handle M/K suffixes
            if text.lower().endswith('m'):
                return float(text[:-1]) * 1_000_000
            if text.lower().endswith('k'):
                return float(text[:-1]) * 1_000
            return float(text) if text else None
        except:
            return None
    
    def _parse_string(self, value: Any) -> Optional[str]:
        """Parse string value."""
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        text = str(value).strip()
        return text if text and text.lower() not in ['nan', 'none'] else None
    
    def _parse_status(self, value: Any) -> UnitStatus:
        """Parse status value."""
        if not value or (isinstance(value, float) and pd.isna(value)):
            return UnitStatus.UNKNOWN
        
        text = str(value).lower().strip()
        
        if any(kw in text for kw in ['available', 'avail', 'свободен', 'в продаже', 'open']):
            return UnitStatus.AVAILABLE
        if any(kw in text for kw in ['sold', 'продан', 'closed']):
            return UnitStatus.SOLD
        if any(kw in text for kw in ['reserved', 'бронь', 'hold', 'резерв']):
            return UnitStatus.RESERVED
        
        return UnitStatus.UNKNOWN
    
    def _extract_bedrooms(self, layout: str) -> Optional[int]:
        """Extract bedrooms from layout string."""
        layout_lower = layout.lower()
        
        if 'studio' in layout_lower:
            return 0
        
        match = re.search(r'(\d+)\s*(?:br|bed|bedroom|комнат|спальн)', layout_lower)
        if match:
            return int(match.group(1))
        
        # Try simple number patterns like "1BR", "2 BR"
        match = re.search(r'(\d+)\s*br', layout_lower)
        if match:
            return int(match.group(1))
        
        return None
    
    def get_session(self, session_id: str) -> Optional[ParseSession]:
        """Get session by ID."""
        return self.sessions.get(session_id)
    
    def get_learning_stats(self) -> Dict:
        """Get learning statistics from feedback store."""
        return self.feedback_store.get_stats()
    
    def cleanup_session(self, session_id: str) -> bool:
        """Remove session from memory."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False


# Singleton instance
_smart_parser: Optional[SmartPriceParser] = None


def get_smart_parser() -> SmartPriceParser:
    """Get or create singleton SmartPriceParser instance."""
    global _smart_parser
    if _smart_parser is None:
        _smart_parser = SmartPriceParser()
    return _smart_parser
