"""
Base classes and data models for price parsing.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime
import re


class UnitStatus(str, Enum):
    """Unit availability status."""
    AVAILABLE = "available"
    RESERVED = "reserved"
    SOLD = "sold"
    HOLD = "hold"
    UNKNOWN = "unknown"


@dataclass
class ParsedUnit:
    """Parsed unit data from price list."""
    
    # Identifiers
    unit_number: str
    raw_row: Optional[Dict[str, Any]] = None  # Original row data for debugging
    
    # Core attributes
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    area_sqm: Optional[float] = None
    floor: Optional[int] = None
    building: Optional[str] = None
    
    # Price info
    price: Optional[float] = None
    price_per_sqm: Optional[float] = None
    currency: str = "THB"
    
    # Additional details
    layout_type: Optional[str] = None  # e.g., "1BR-A", "Studio-B"
    view_type: Optional[str] = None  # e.g., "Sea View", "Garden View"
    status: UnitStatus = UnitStatus.UNKNOWN
    phase: Optional[str] = None
    
    # Payment info (if available)
    downpayment: Optional[float] = None
    downpayment_percent: Optional[float] = None
    
    # Validation
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Normalize and validate data after initialization."""
        self._normalize()
        self._validate()
    
    def _normalize(self):
        """Normalize unit data."""
        # Normalize unit number
        if self.unit_number:
            self.unit_number = str(self.unit_number).strip().upper()
        
        # Normalize status
        if isinstance(self.status, str):
            self.status = self._parse_status(self.status)
        
        # Calculate price per sqm if missing
        if self.price and self.area_sqm and not self.price_per_sqm:
            self.price_per_sqm = round(self.price / self.area_sqm, 2)
        
        # Try to extract bedrooms from layout_type if missing
        if self.layout_type and not self.bedrooms:
            self.bedrooms = self._extract_bedrooms_from_layout(self.layout_type)
    
    def _validate(self):
        """Validate unit data."""
        self.validation_errors = []
        
        if not self.unit_number:
            self.validation_errors.append("Missing unit number")
        
        if self.price is not None and self.price <= 0:
            self.validation_errors.append(f"Invalid price: {self.price}")
        
        if self.area_sqm is not None and self.area_sqm <= 0:
            self.validation_errors.append(f"Invalid area: {self.area_sqm}")
        
        if self.bedrooms is not None and (self.bedrooms < 0 or self.bedrooms > 10):
            self.validation_errors.append(f"Invalid bedrooms: {self.bedrooms}")
        
        self.is_valid = len(self.validation_errors) == 0
    
    @staticmethod
    def _parse_status(status_str: str) -> UnitStatus:
        """Parse status string to UnitStatus enum."""
        status_lower = status_str.lower().strip()
        
        # Available variations
        if status_lower in ['available', 'avail', 'open', 'for sale', 'свободен', 'в продаже', 'доступен']:
            return UnitStatus.AVAILABLE
        
        # Reserved variations
        if status_lower in ['reserved', 'res', 'booking', 'hold', 'бронь', 'забронирован', 'резерв']:
            return UnitStatus.RESERVED
        
        # Sold variations
        if status_lower in ['sold', 'closed', 'completed', 'продан', 'продано']:
            return UnitStatus.SOLD
        
        return UnitStatus.UNKNOWN
    
    @staticmethod
    def _extract_bedrooms_from_layout(layout: str) -> Optional[int]:
        """Extract bedrooms count from layout string like '1BR-A' or '2 Bedroom'."""
        layout_lower = layout.lower()
        
        # Pattern: "1BR", "2BR", etc.
        match = re.search(r'(\d+)\s*br', layout_lower)
        if match:
            return int(match.group(1))
        
        # Pattern: "1 bedroom", "2 bedrooms"
        match = re.search(r'(\d+)\s*bed', layout_lower)
        if match:
            return int(match.group(1))
        
        # Studio
        if 'studio' in layout_lower:
            return 0
        
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            'unit_number': self.unit_number,
            'bedrooms': self.bedrooms,
            'bathrooms': self.bathrooms,
            'area_sqm': self.area_sqm,
            'floor': self.floor,
            'building': self.building,
            'price_original': self.price,
            'price_per_sqm': self.price_per_sqm,
            'original_currency': self.currency,
            'layout_type': self.layout_type,
            'view_type': self.view_type,
            'status': self.status.value if isinstance(self.status, UnitStatus) else self.status,
            'phase': self.phase,
        }


@dataclass
class ParsedPriceData:
    """Container for all parsed data from a price file."""
    
    units: List[ParsedUnit] = field(default_factory=list)
    
    # Detected metadata
    project_name: Optional[str] = None
    developer_name: Optional[str] = None
    currency: str = "THB"
    price_date: Optional[datetime] = None
    
    # Phase information if detected
    phases: List[str] = field(default_factory=list)
    
    # Payment plans if detected
    payment_plans: List[Dict[str, Any]] = field(default_factory=list)
    
    # Raw data for reference
    raw_headers: List[str] = field(default_factory=list)
    raw_data: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def valid_units(self) -> List[ParsedUnit]:
        """Return only valid units."""
        return [u for u in self.units if u.is_valid]
    
    @property
    def invalid_units(self) -> List[ParsedUnit]:
        """Return only invalid units."""
        return [u for u in self.units if not u.is_valid]
    
    @property
    def total_count(self) -> int:
        return len(self.units)
    
    @property
    def valid_count(self) -> int:
        return len(self.valid_units)
    
    @property
    def invalid_count(self) -> int:
        return len(self.invalid_units)


@dataclass
class ParsingResult:
    """Result of a parsing operation."""
    
    success: bool = False
    data: Optional[ParsedPriceData] = None
    
    # Error info
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    
    # Warnings (non-fatal issues)
    warnings: List[str] = field(default_factory=list)
    
    # Method used
    parsing_method: str = "unknown"
    fallback_used: bool = False
    
    # Performance
    parsing_time_ms: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'success': self.success,
            'error_message': self.error_message,
            'error_type': self.error_type,
            'warnings': self.warnings,
            'parsing_method': self.parsing_method,
            'fallback_used': self.fallback_used,
            'parsing_time_ms': self.parsing_time_ms,
            'total_units': self.data.total_count if self.data else 0,
            'valid_units': self.data.valid_count if self.data else 0,
            'invalid_units': self.data.invalid_count if self.data else 0,
        }


class BasePriceParser(ABC):
    """Base class for price parsers."""
    
    # Column name mappings for auto-detection
    COLUMN_MAPPINGS = {
        'unit_number': [
            'unit', 'unit_number', 'unit no', 'unit #', 'no', 'номер', 
            'юнит', 'room', 'room no', 'unit id'
        ],
        'bedrooms': [
            'bedrooms', 'bedroom', 'br', 'bed', 'type', 'спальни', 
            'спален', 'комнат', 'beds', 'room type'
        ],
        'area': [
            'area', 'size', 'sqm', 'sq.m', 'площадь', 'm2', 'living area',
            'total area', 'area (sqm)', 'net area', 'gross area'
        ],
        'floor': [
            'floor', 'flr', 'этаж', 'level', 'storey', 'fl'
        ],
        'price': [
            'price', 'total price', 'цена', 'стоимость', 'amount',
            'sale price', 'selling price', 'price (thb)', 'price (usd)'
        ],
        'status': [
            'status', 'availability', 'статус', 'available', 'state',
            'avail', 'состояние'
        ],
        'view': [
            'view', 'вид', 'view type', 'facing', 'orientation'
        ],
        'building': [
            'building', 'tower', 'block', 'здание', 'корпус', 'bldg'
        ],
        'layout': [
            'layout', 'type', 'unit type', 'планировка', 'тип', 'plan'
        ],
        'phase': [
            'phase', 'фаза', 'stage', 'этап', 'batch'
        ],
    }
    
    @abstractmethod
    async def parse(self, file_path: str, **kwargs) -> ParsingResult:
        """Parse the file and return result."""
        pass
    
    @abstractmethod
    def can_parse(self, file_path: str) -> bool:
        """Check if this parser can handle the given file."""
        pass
    
    def detect_columns(self, headers: List[str]) -> Dict[str, int]:
        """
        Auto-detect column mappings from headers.
        Returns dict of field_name -> column_index.
        """
        mapping = {}
        headers_lower = [h.lower().strip() if h else '' for h in headers]
        
        for field, variations in self.COLUMN_MAPPINGS.items():
            for idx, header in enumerate(headers_lower):
                if header in variations or any(v in header for v in variations):
                    mapping[field] = idx
                    break
        
        return mapping
    
    def parse_price(self, value: Any) -> Optional[float]:
        """Parse price value from various formats."""
        if value is None:
            return None
        
        if isinstance(value, (int, float)):
            return float(value)
        
        # Convert to string and clean
        value_str = str(value).strip()
        
        # Remove currency symbols and spaces
        value_str = re.sub(r'[฿$€₽\s,]', '', value_str)
        
        # Remove "M" suffix for millions
        if value_str.lower().endswith('m'):
            value_str = value_str[:-1]
            try:
                return float(value_str) * 1_000_000
            except ValueError:
                pass
        
        # Remove "K" suffix for thousands
        if value_str.lower().endswith('k'):
            value_str = value_str[:-1]
            try:
                return float(value_str) * 1_000
            except ValueError:
                pass
        
        try:
            return float(value_str)
        except (ValueError, TypeError):
            return None
    
    def parse_area(self, value: Any) -> Optional[float]:
        """Parse area value from various formats."""
        if value is None:
            return None
        
        if isinstance(value, (int, float)):
            return float(value)
        
        value_str = str(value).strip()
        
        # Remove sqm suffixes
        value_str = re.sub(r'\s*(sqm|sq\.?m|м2|m2|sq\.?\s*m\.?)\s*$', '', value_str, flags=re.IGNORECASE)
        
        try:
            return float(value_str.replace(',', '').strip())
        except (ValueError, TypeError):
            return None
    
    def parse_floor(self, value: Any) -> Optional[int]:
        """Parse floor value."""
        if value is None:
            return None
        
        if isinstance(value, int):
            return value
        
        if isinstance(value, float):
            return int(value)
        
        value_str = str(value).strip()
        
        # Remove floor prefix
        value_str = re.sub(r'^(floor|fl\.?|этаж)\s*', '', value_str, flags=re.IGNORECASE)
        
        try:
            return int(float(value_str))
        except (ValueError, TypeError):
            return None
    
    def parse_bedrooms(self, value: Any) -> Optional[int]:
        """Parse bedrooms count."""
        if value is None:
            return None
        
        if isinstance(value, int):
            return value
        
        if isinstance(value, float):
            return int(value)
        
        value_str = str(value).strip().lower()
        
        # Studio
        if 'studio' in value_str or value_str == '0':
            return 0
        
        # Extract number
        match = re.search(r'(\d+)', value_str)
        if match:
            return int(match.group(1))
        
        return None
    
    def detect_currency(self, text: str) -> str:
        """Detect currency from text."""
        text_lower = text.lower()
        
        if '฿' in text or 'thb' in text_lower or 'baht' in text_lower:
            return 'THB'
        if '$' in text or 'usd' in text_lower or 'dollar' in text_lower:
            return 'USD'
        if '€' in text or 'eur' in text_lower:
            return 'EUR'
        if '₽' in text or 'rub' in text_lower or 'руб' in text_lower:
            return 'RUB'
        if 'idr' in text_lower or 'rupiah' in text_lower:
            return 'IDR'
        
        return 'THB'  # Default for Thailand
