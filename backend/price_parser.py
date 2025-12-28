"""
Price Parser Module - Parses price lists from Excel, PDF, and Google Sheets.
Supports various formats used by real estate developers in Phuket.
"""
import re
import httpx
import pdfplumber
import pandas as pd
from io import BytesIO
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class UnitStatus(str, Enum):
    AVAILABLE = "available"
    SOLD = "sold"
    RESERVED = "reserved"
    BOOKED = "booked"


@dataclass
class ParsedUnit:
    """Parsed unit from price list"""
    unit_number: str
    unit_type: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    area: Optional[float] = None
    floor: Optional[int] = None
    building: Optional[str] = None
    view: Optional[str] = None
    price: Optional[float] = None
    price_per_sqm: Optional[float] = None
    status: UnitStatus = UnitStatus.AVAILABLE
    raw_data: Optional[Dict] = None


@dataclass
class ParseResult:
    """Result of parsing a price list"""
    success: bool
    units: List[ParsedUnit]
    errors: List[str]
    warnings: List[str]
    source_type: str
    currency: str = "THB"
    raw_data: Optional[Any] = None


# Column name mappings for auto-detection
COLUMN_MAPPINGS = {
    "unit_number": [
        "unit", "unit_number", "unit no", "unit_no", "№ of unit", "no", "юнит", 
        "номер", "room", "квартира", "apt", "apartment", "condo"
    ],
    "unit_type": [
        "type", "unit type", "unit_type", "apartment type", "тип", "room type",
        "layout", "планировка", "br", "bedroom type"
    ],
    "bedrooms": [
        "bedrooms", "bedroom", "br", "bed", "beds", "спальни", "спален", 
        "комнат", "rooms"
    ],
    "area": [
        "area", "sqm", "sq.m", "size", "площадь", "m2", "м2", "square", 
        "sq m", "sqm.", "s общая", "общая", "total area"
    ],
    "floor": [
        "floor", "этаж", "level", "flr", "этаже"
    ],
    "building": [
        "building", "bldg", "tower", "корпус", "block", "секция", "section"
    ],
    "view": [
        "view", "вид", "facing", "ambience", "orientation"
    ],
    "price": [
        "price", "цена", "стоимость", "amount", "cost", "total", "leasehold",
        "freehold", "apartment price", "unit price", "стоимость тыс"
    ],
    "price_per_sqm": [
        "price per sqm", "price/sqm", "per sqm", "sqm price", "стоимость м2",
        "цена за м2", "price per m2", "$/sqm", "thb/sqm"
    ],
    "status": [
        "status", "статус", "availability", "booking status", "available",
        "состояние", "продано"
    ]
}

# Status mappings
STATUS_MAPPINGS = {
    UnitStatus.AVAILABLE: [
        "available", "свободна", "свободно", "free", "в продаже", "продается", 
        "for sale", "open", "vacant"
    ],
    UnitStatus.SOLD: [
        "sold", "продано", "продана", "закрыта", "closed", "sold out"
    ],
    UnitStatus.RESERVED: [
        "reserved", "reserve", "забронировано", "бронь", "резерв", "hold",
        "on hold", "pending"
    ],
    UnitStatus.BOOKED: [
        "booked", "booking", "бронирование", "deposit", "задаток"
    ]
}


def normalize_column_name(name: str) -> str:
    """Normalize column name for matching"""
    if not name:
        return ""
    return str(name).lower().strip().replace("_", " ").replace("-", " ")


def detect_column_type(col_name: str) -> Optional[str]:
    """Detect column type from name"""
    normalized = normalize_column_name(col_name)
    for field, patterns in COLUMN_MAPPINGS.items():
        for pattern in patterns:
            if pattern in normalized or normalized in pattern:
                return field
    return None


def parse_status(value: Any) -> UnitStatus:
    """Parse status from various formats"""
    if not value:
        return UnitStatus.AVAILABLE
    
    value_lower = str(value).lower().strip()
    
    for status, patterns in STATUS_MAPPINGS.items():
        for pattern in patterns:
            if pattern in value_lower:
                return status
    
    return UnitStatus.AVAILABLE


def parse_number(value: Any) -> Optional[float]:
    """Parse number from various formats"""
    if value is None or pd.isna(value):
        return None
    
    if isinstance(value, (int, float)):
        return float(value)
    
    # Clean string
    text = str(value).strip()
    text = re.sub(r'[^\d.,\-]', '', text)  # Keep only digits, dots, commas, minus
    text = text.replace(',', '')  # Remove thousand separators
    
    try:
        return float(text) if text else None
    except ValueError:
        return None


def parse_unit_type(value: Any) -> Tuple[Optional[str], Optional[int]]:
    """Parse unit type and extract bedrooms if mentioned"""
    if not value:
        return None, None
    
    text = str(value).strip().lower()
    bedrooms = None
    unit_type = str(value).strip()
    
    # Extract bedroom count
    br_match = re.search(r'(\d+)\s*(?:br|bed|bedroom|комнат|спальн)', text)
    if br_match:
        bedrooms = int(br_match.group(1))
    elif 'studio' in text or 'студия' in text:
        bedrooms = 0
        unit_type = "Studio"
    elif '1 br' in text or '1br' in text:
        bedrooms = 1
    elif '2 br' in text or '2br' in text:
        bedrooms = 2
    elif '3 br' in text or '3br' in text:
        bedrooms = 3
    
    return unit_type, bedrooms


def parse_excel(file_content: bytes, sheet_name: Optional[str] = None) -> ParseResult:
    """Parse Excel file"""
    errors = []
    warnings = []
    units = []
    
    try:
        xlsx = pd.ExcelFile(BytesIO(file_content))
        
        # Select sheet
        if sheet_name and sheet_name in xlsx.sheet_names:
            sheets_to_parse = [sheet_name]
        else:
            # Try to find price-related sheets
            sheets_to_parse = []
            for name in xlsx.sheet_names:
                name_lower = name.lower()
                if any(kw in name_lower for kw in ['price', 'unit', 'прайс', 'цен', 'продаж']):
                    sheets_to_parse.append(name)
            
            if not sheets_to_parse:
                sheets_to_parse = xlsx.sheet_names[:1]  # Default to first sheet
        
        for sheet in sheets_to_parse:
            df = pd.read_excel(xlsx, sheet_name=sheet)
            
            # Find header row (row with most column matches)
            best_header_row = 0
            best_matches = 0
            
            for i in range(min(10, len(df))):
                row = df.iloc[i]
                matches = sum(1 for v in row if detect_column_type(str(v)) is not None)
                if matches > best_matches:
                    best_matches = matches
                    best_header_row = i
            
            if best_header_row > 0:
                df.columns = df.iloc[best_header_row]
                df = df.iloc[best_header_row + 1:].reset_index(drop=True)
            
            # Map columns
            column_map = {}
            for col in df.columns:
                col_type = detect_column_type(str(col))
                if col_type:
                    column_map[col_type] = col
            
            # Parse rows
            for idx, row in df.iterrows():
                try:
                    unit_number = None
                    if "unit_number" in column_map:
                        unit_number = str(row[column_map["unit_number"]]).strip()
                    
                    if not unit_number or unit_number == 'nan':
                        continue
                    
                    # Parse unit type and bedrooms
                    unit_type = None
                    bedrooms = None
                    if "unit_type" in column_map:
                        unit_type, bedrooms = parse_unit_type(row[column_map["unit_type"]])
                    if "bedrooms" in column_map and bedrooms is None:
                        bedrooms = parse_number(row[column_map["bedrooms"]])
                        if bedrooms:
                            bedrooms = int(bedrooms)
                    
                    unit = ParsedUnit(
                        unit_number=unit_number,
                        unit_type=unit_type,
                        bedrooms=bedrooms,
                        area=parse_number(row.get(column_map.get("area"))),
                        floor=int(parse_number(row.get(column_map.get("floor"))) or 0) or None,
                        building=str(row.get(column_map.get("building"), "")).strip() or None,
                        view=str(row.get(column_map.get("view"), "")).strip() or None,
                        price=parse_number(row.get(column_map.get("price"))),
                        price_per_sqm=parse_number(row.get(column_map.get("price_per_sqm"))),
                        status=parse_status(row.get(column_map.get("status"))),
                        raw_data=row.to_dict()
                    )
                    
                    units.append(unit)
                    
                except Exception as e:
                    warnings.append(f"Row {idx}: {str(e)}")
        
        return ParseResult(
            success=True,
            units=units,
            errors=errors,
            warnings=warnings,
            source_type="excel",
            currency="THB"
        )
        
    except Exception as e:
        errors.append(f"Failed to parse Excel: {str(e)}")
        return ParseResult(
            success=False,
            units=[],
            errors=errors,
            warnings=warnings,
            source_type="excel"
        )


def parse_pdf(file_content: bytes) -> ParseResult:
    """Parse PDF file using pdfplumber"""
    errors = []
    warnings = []
    units = []
    
    try:
        pdf = pdfplumber.open(BytesIO(file_content))
        
        for page_num, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            
            if not tables:
                # Try text extraction as fallback
                text = page.extract_text()
                if text:
                    warnings.append(f"Page {page_num + 1}: No tables found, text extracted")
                continue
            
            for table in tables:
                if not table or len(table) < 2:
                    continue
                
                # Find header row
                header_row = 0
                for i, row in enumerate(table[:5]):
                    matches = sum(1 for cell in row if cell and detect_column_type(str(cell)))
                    if matches >= 3:
                        header_row = i
                        break
                
                headers = table[header_row]
                
                # Map columns
                column_map = {}
                for i, header in enumerate(headers):
                    col_type = detect_column_type(str(header) if header else "")
                    if col_type:
                        column_map[col_type] = i
                
                # Parse rows
                for row_idx, row in enumerate(table[header_row + 1:]):
                    try:
                        unit_number = None
                        if "unit_number" in column_map:
                            cell = row[column_map["unit_number"]]
                            unit_number = str(cell).strip() if cell else None
                        
                        if not unit_number or unit_number == 'None':
                            continue
                        
                        # Parse unit type and bedrooms
                        unit_type = None
                        bedrooms = None
                        if "unit_type" in column_map:
                            cell = row[column_map["unit_type"]]
                            if cell:
                                unit_type, bedrooms = parse_unit_type(cell)
                        
                        def get_cell(field):
                            if field in column_map:
                                return row[column_map[field]]
                            return None
                        
                        unit = ParsedUnit(
                            unit_number=unit_number,
                            unit_type=unit_type,
                            bedrooms=bedrooms,
                            area=parse_number(get_cell("area")),
                            floor=int(parse_number(get_cell("floor")) or 0) or None,
                            building=str(get_cell("building") or "").strip() or None,
                            view=str(get_cell("view") or "").strip() or None,
                            price=parse_number(get_cell("price")),
                            price_per_sqm=parse_number(get_cell("price_per_sqm")),
                            status=parse_status(get_cell("status")),
                            raw_data=dict(zip(headers, row))
                        )
                        
                        units.append(unit)
                        
                    except Exception as e:
                        warnings.append(f"Page {page_num + 1}, Row {row_idx}: {str(e)}")
        
        pdf.close()
        
        return ParseResult(
            success=True,
            units=units,
            errors=errors,
            warnings=warnings,
            source_type="pdf",
            currency="THB"
        )
        
    except Exception as e:
        errors.append(f"Failed to parse PDF: {str(e)}")
        return ParseResult(
            success=False,
            units=[],
            errors=errors,
            warnings=warnings,
            source_type="pdf"
        )


def parse_google_sheet(url: str) -> ParseResult:
    """Parse Google Sheet by URL"""
    errors = []
    warnings = []
    
    try:
        # Extract spreadsheet ID from URL
        match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
        if not match:
            errors.append("Invalid Google Sheets URL")
            return ParseResult(
                success=False,
                units=[],
                errors=errors,
                warnings=warnings,
                source_type="google_sheets"
            )
        
        spreadsheet_id = match.group(1)
        export_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=xlsx"
        
        response = httpx.get(export_url, follow_redirects=True, timeout=30)
        
        if response.status_code != 200:
            errors.append(f"Failed to download Google Sheet: HTTP {response.status_code}")
            return ParseResult(
                success=False,
                units=[],
                errors=errors,
                warnings=warnings,
                source_type="google_sheets"
            )
        
        result = parse_excel(response.content)
        result.source_type = "google_sheets"
        return result
        
    except Exception as e:
        errors.append(f"Failed to fetch Google Sheet: {str(e)}")
        return ParseResult(
            success=False,
            units=[],
            errors=errors,
            warnings=warnings,
            source_type="google_sheets"
        )


def parse_google_drive_file(url: str) -> ParseResult:
    """Parse file from Google Drive"""
    errors = []
    warnings = []
    
    try:
        # Extract file ID
        match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
        if not match:
            match = re.search(r'id=([a-zA-Z0-9-_]+)', url)
        
        if not match:
            errors.append("Invalid Google Drive URL")
            return ParseResult(
                success=False,
                units=[],
                errors=errors,
                warnings=warnings,
                source_type="google_drive"
            )
        
        file_id = match.group(1)
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        
        response = httpx.get(download_url, follow_redirects=True, timeout=60)
        
        if response.status_code != 200:
            errors.append(f"Failed to download file: HTTP {response.status_code}")
            return ParseResult(
                success=False,
                units=[],
                errors=errors,
                warnings=warnings,
                source_type="google_drive"
            )
        
        content = response.content
        content_type = response.headers.get('content-type', '')
        
        # Detect file type
        if content[:4] == b'%PDF':
            return parse_pdf(content)
        elif content[:4] == b'PK\x03\x04':  # ZIP header (xlsx)
            return parse_excel(content)
        elif 'spreadsheet' in content_type or 'excel' in content_type:
            return parse_excel(content)
        elif 'pdf' in content_type:
            return parse_pdf(content)
        else:
            # Try Excel first, then PDF
            try:
                result = parse_excel(content)
                if result.success and result.units:
                    return result
            except:
                pass
            
            return parse_pdf(content)
        
    except Exception as e:
        errors.append(f"Failed to parse Google Drive file: {str(e)}")
        return ParseResult(
            success=False,
            units=[],
            errors=errors,
            warnings=warnings,
            source_type="google_drive"
        )


def parse_price_file(file_content: bytes = None, url: str = None, file_type: str = None) -> ParseResult:
    """Main entry point for parsing price files"""
    
    if url:
        # Determine parser from URL
        if 'docs.google.com/spreadsheets' in url:
            return parse_google_sheet(url)
        elif 'drive.google.com' in url:
            return parse_google_drive_file(url)
        else:
            # Try to download and parse
            try:
                response = httpx.get(url, follow_redirects=True, timeout=60)
                file_content = response.content
            except Exception as e:
                return ParseResult(
                    success=False,
                    units=[],
                    errors=[f"Failed to download file: {str(e)}"],
                    warnings=[],
                    source_type="url"
                )
    
    if file_content:
        # Detect file type
        if file_type == 'pdf' or file_content[:4] == b'%PDF':
            return parse_pdf(file_content)
        elif file_type in ['xlsx', 'xls', 'excel'] or file_content[:4] == b'PK\x03\x04':
            return parse_excel(file_content)
        else:
            # Try both
            try:
                result = parse_excel(file_content)
                if result.success and result.units:
                    return result
            except:
                pass
            
            return parse_pdf(file_content)
    
    return ParseResult(
        success=False,
        units=[],
        errors=["No file content or URL provided"],
        warnings=[],
        source_type="unknown"
    )


async def parse_from_url(url: str) -> ParseResult:
    """Async wrapper for parsing from URL"""
    return parse_price_file(url=url)


# Test function
if __name__ == "__main__":
    # Test Google Sheet
    print("Testing Google Sheet parser...")
    result = parse_google_sheet("https://docs.google.com/spreadsheets/d/1NEGMTK62AzyIhWIeY4s4_bnN48WApslk/edit")
    print(f"Success: {result.success}")
    print(f"Units parsed: {len(result.units)}")
    print(f"Errors: {result.errors}")
    print(f"Warnings: {len(result.warnings)} warnings")
    
    if result.units:
        print("\nFirst 5 units:")
        for unit in result.units[:5]:
            print(f"  {unit.unit_number}: {unit.unit_type}, {unit.area}sqm, {unit.price} THB, {unit.status}")
    
    # Test PDF
    print("\n\nTesting PDF parser...")
    result2 = parse_google_drive_file("https://drive.google.com/file/d/17fzx7GUeziDyu08pnn0r6g3qDs-zobNE/view")
    print(f"Success: {result2.success}")
    print(f"Units parsed: {len(result2.units)}")
    print(f"Errors: {result2.errors}")
    
    if result2.units:
        print("\nFirst 5 units:")
        for unit in result2.units[:5]:
            print(f"  {unit.unit_number}: {unit.unit_type}, {unit.area}sqm, {unit.price} THB, {unit.status}")
