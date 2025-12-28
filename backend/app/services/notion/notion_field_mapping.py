"""
Notion Field Mapping - defines mapping between Notion database fields and PropBase models.

Based on user's Notion database structure:
Database: Projects — PHUKET
ID: 1af48102-1462-80d6-b99b-edca9ea90abf
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import re


class NotionPropertyType(str, Enum):
    """Notion property types."""
    TITLE = "title"
    RICH_TEXT = "rich_text"
    NUMBER = "number"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    STATUS = "status"
    DATE = "date"
    CHECKBOX = "checkbox"
    URL = "url"
    EMAIL = "email"
    PHONE_NUMBER = "phone_number"
    FILES = "files"
    RELATION = "relation"
    FORMULA = "formula"
    ROLLUP = "rollup"
    CREATED_TIME = "created_time"
    CREATED_BY = "created_by"
    LAST_EDITED_TIME = "last_edited_time"
    LAST_EDITED_BY = "last_edited_by"


@dataclass
class FieldMapping:
    """Mapping for a single field."""
    notion_field: str  # Notion property name (with emoji)
    propbase_field: str  # PropBase model field name
    notion_type: NotionPropertyType
    propbase_model: str = "project"  # project, unit, developer, district
    transformer: Optional[Callable[[Any], Any]] = None  # Optional transformation function
    required: bool = False
    default: Any = None
    description: str = ""


def parse_property_type(value: str) -> Optional[str]:
    """Parse property type from Notion select (e.g., 'Condo' -> 'apartment')."""
    type_mapping = {
        "condo": "apartment",
        "villa": "villa",
        "townhouse": "townhouse",
        "land plot": "land",
        "commercial": None,  # Skip commercial for now
    }
    return type_mapping.get(value.lower().strip()) if value else None


def parse_roi_percentage(value: str) -> Optional[float]:
    """Parse ROI percentage from Notion select (e.g., '02. 🟡 Acceptable (6–7.9%)' -> 7.0)."""
    if not value:
        return None
    # Try to extract number from brackets
    match = re.search(r'\((\d+(?:\.\d+)?)', value)
    if match:
        return float(match.group(1))
    # Try to extract just a number
    match = re.search(r'(\d+(?:\.\d+)?)', value)
    if match:
        return float(match.group(1))
    return None


def parse_price_per_sqm(value: Any) -> Optional[float]:
    """Parse price per sqm from Notion."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # Remove non-numeric characters except decimal point
        cleaned = re.sub(r'[^\d.]', '', value)
        if cleaned:
            return float(cleaned)
    return None


def parse_coordinates(value: Any) -> Optional[float]:
    """Parse coordinates from Notion."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def parse_area_string(value: str) -> Optional[str]:
    """Extract area name from Notion select/relation."""
    if not value:
        return None
    return value.strip()


def parse_has_payment_plan(value: str) -> bool:
    """Parse installment plan availability."""
    if not value:
        return False
    return value.lower().strip() in ("yes", "да", "true", "1")


def parse_smart_home(value: str) -> Optional[str]:
    """Parse smart home availability."""
    if not value:
        return None
    mapping = {
        "yes": "full",
        "optional": "optional",
        "ai assistant ready": "ai_ready",
        "app-controlled": "app_controlled",
        "no": None,
    }
    return mapping.get(value.lower().strip())


def extract_text_from_rich_text(rich_text: List[Dict]) -> str:
    """Extract plain text from Notion rich_text property."""
    if not rich_text:
        return ""
    return "".join([t.get("plain_text", "") for t in rich_text])


def extract_url_from_files(files: List[Dict]) -> Optional[str]:
    """Extract first URL from Notion files property."""
    if not files:
        return None
    first_file = files[0]
    if first_file.get("type") == "external":
        return first_file.get("external", {}).get("url")
    elif first_file.get("type") == "file":
        return first_file.get("file", {}).get("url")
    return None


def extract_all_urls_from_files(files: List[Dict]) -> List[str]:
    """Extract all URLs from Notion files property."""
    urls = []
    for f in files:
        if f.get("type") == "external":
            url = f.get("external", {}).get("url")
        elif f.get("type") == "file":
            url = f.get("file", {}).get("url")
        else:
            url = None
        if url:
            urls.append(url)
    return urls


def extract_multi_select_values(multi_select: List[Dict]) -> List[str]:
    """Extract values from Notion multi_select property."""
    return [item.get("name", "") for item in multi_select if item.get("name")]


# Main mapping configuration
# Based on Notion database fields analysis
NOTION_TO_PROPBASE_MAPPING: Dict[str, FieldMapping] = {
    # ===== Core Project Fields =====
    "Name": FieldMapping(
        notion_field="Name",
        propbase_field="name_en",
        notion_type=NotionPropertyType.TITLE,
        required=True,
        description="Project name (title)"
    ),
    
    "🏢 type": FieldMapping(
        notion_field="🏢 type",
        propbase_field="property_types",
        notion_type=NotionPropertyType.SELECT,
        transformer=lambda v: [parse_property_type(v)] if parse_property_type(v) else [],
        description="Property type: Condo, Villa, Townhouse, Land Plot"
    ),
    
    "🆔 property ID": FieldMapping(
        notion_field="🆔 property ID",
        propbase_field="internal_code",
        notion_type=NotionPropertyType.RICH_TEXT,
        description="External/Internal ID from Notion"
    ),
    
    # ===== Location =====
    "🌐 longitude": FieldMapping(
        notion_field="🌐 longitude",
        propbase_field="lng",
        notion_type=NotionPropertyType.NUMBER,
        transformer=parse_coordinates,
        description="Longitude coordinate"
    ),
    
    "📍 latitude": FieldMapping(
        notion_field="📍 latitude", 
        propbase_field="lat",
        notion_type=NotionPropertyType.NUMBER,
        transformer=parse_coordinates,
        description="Latitude coordinate (note: using latitude from column analysis)"
    ),
    
    "🏘 Area": FieldMapping(
        notion_field="🏘 Area",
        propbase_field="_district_name",  # Will be resolved to district_id
        notion_type=NotionPropertyType.SELECT,
        transformer=parse_area_string,
        description="District/Area name (will be matched to districts table)"
    ),
    
    "📍 project address": FieldMapping(
        notion_field="📍 project address",
        propbase_field="address_en",
        notion_type=NotionPropertyType.RICH_TEXT,
        description="Full project address"
    ),
    
    # ===== Links & Media =====
    "🌐 website / telegram / teletype": FieldMapping(
        notion_field="🌐 website / telegram / teletype",
        propbase_field="website_url",
        notion_type=NotionPropertyType.URL,
        description="Website or Telegram link"
    ),
    
    "📹 videos": FieldMapping(
        notion_field="📹 videos",
        propbase_field="video_url",
        notion_type=NotionPropertyType.URL,
        description="Video tour URL (YouTube, etc.)"
    ),
    
    "📸 gallery": FieldMapping(
        notion_field="📸 gallery",
        propbase_field="gallery",
        notion_type=NotionPropertyType.FILES,
        transformer=extract_all_urls_from_files,
        description="Gallery images"
    ),
    
    "📸 show unit": FieldMapping(
        notion_field="📸 show unit",
        propbase_field="_show_unit_images",  # Stored separately
        notion_type=NotionPropertyType.FILES,
        transformer=extract_all_urls_from_files,
        description="Show unit images"
    ),
    
    "🧱 infrastructure": FieldMapping(
        notion_field="🧱 infrastructure",
        propbase_field="_infrastructure_files",
        notion_type=NotionPropertyType.FILES,
        transformer=extract_all_urls_from_files,
        description="Infrastructure images/files"
    ),
    
    # ===== Pricing =====
    "💰 price per m²": FieldMapping(
        notion_field="💰 price per m²",
        propbase_field="min_price_per_sqm",  # Use as base price per sqm
        notion_type=NotionPropertyType.NUMBER,
        transformer=parse_price_per_sqm,
        description="Price per square meter"
    ),
    
    "📈 ROI %": FieldMapping(
        notion_field="📈 ROI %",
        propbase_field="_roi_percent",  # Custom field, stored in features
        notion_type=NotionPropertyType.SELECT,
        transformer=parse_roi_percentage,
        description="Expected ROI percentage"
    ),
    
    # ===== Payment & Booking =====
    "💳 installment plan": FieldMapping(
        notion_field="💳 installment plan",
        propbase_field="_has_payment_plan",
        notion_type=NotionPropertyType.SELECT,
        transformer=parse_has_payment_plan,
        description="Has installment/payment plan"
    ),
    
    "📆 payment plan (details)": FieldMapping(
        notion_field="📆 payment plan (details)",
        propbase_field="_payment_plan_details",
        notion_type=NotionPropertyType.RICH_TEXT,
        description="Payment plan details text"
    ),
    
    "📄 booking fee THB": FieldMapping(
        notion_field="📄 booking fee THB",
        propbase_field="_booking_fee",
        notion_type=NotionPropertyType.RICH_TEXT,
        description="Booking/reservation fee"
    ),
    
    # ===== Documents & Files =====
    "🏷 price list": FieldMapping(
        notion_field="🏷 price list",
        propbase_field="_price_list_files",
        notion_type=NotionPropertyType.FILES,
        transformer=extract_all_urls_from_files,
        description="Price list PDF/Excel files for parsing"
    ),
    
    "📐 unit layouts file": FieldMapping(
        notion_field="📐 unit layouts file",
        propbase_field="_layout_files",
        notion_type=NotionPropertyType.FILES,
        transformer=extract_all_urls_from_files,
        description="Unit layout PDF files"
    ),
    
    # ===== Features & Amenities =====
    "🧺 services & operations": FieldMapping(
        notion_field="🧺 services & operations",
        propbase_field="amenities",
        notion_type=NotionPropertyType.MULTI_SELECT,
        transformer=extract_multi_select_values,
        description="Services: Concierge, Security, etc."
    ),
    
    "🌿 green & common areas": FieldMapping(
        notion_field="🌿 green & common areas",
        propbase_field="_green_areas",
        notion_type=NotionPropertyType.MULTI_SELECT,
        transformer=extract_multi_select_values,
        description="Green areas: Garden, Rooftop, etc."
    ),
    
    "💡 smart home": FieldMapping(
        notion_field="💡 smart home",
        propbase_field="_smart_home",
        notion_type=NotionPropertyType.SELECT,
        transformer=parse_smart_home,
        description="Smart home features"
    ),
    
    # ===== Technical Specs =====
    "📏 ceiling (m)": FieldMapping(
        notion_field="📏 ceiling (m)",
        propbase_field="_ceiling_height",
        notion_type=NotionPropertyType.RICH_TEXT,
        description="Ceiling height in meters"
    ),
    
    "📐 area m²": FieldMapping(
        notion_field="📐 area m²",
        propbase_field="_area_range",
        notion_type=NotionPropertyType.RICH_TEXT,
        description="Area range in square meters"
    ),
    
    "📐 layout range m²": FieldMapping(
        notion_field="📐 layout range m²",
        propbase_field="_layout_range",
        notion_type=NotionPropertyType.MULTI_SELECT,
        transformer=extract_multi_select_values,
        description="Available layout sizes"
    ),
    
    # ===== Status & Verification =====
    "✅ listing verification status": FieldMapping(
        notion_field="✅ listing verification status",
        propbase_field="_verification_status",
        notion_type=NotionPropertyType.STATUS,
        description="Listing verification status"
    ),
    
    "📢 UPDATES (files, links)": FieldMapping(
        notion_field="📢 UPDATES (files, links)",
        propbase_field="_update_files",
        notion_type=NotionPropertyType.FILES,
        transformer=extract_all_urls_from_files,
        description="Update documents/links"
    ),
}


# Fields from Notion that map to unit types (for creating units)
NOTION_UNIT_TYPE_FIELDS = [
    "Studio",
    "1 BR", "1BR", "1 Bed",
    "2 BR", "2BR", "2 Bed", 
    "3 BR", "3BR", "3 Bed",
    "4 BR", "4BR", "4 Bed",
    "Penthouse",
    "Duplex",
]


@dataclass
class NotionFieldMapping:
    """Complete field mapping configuration."""
    
    # Field mappings dictionary
    mappings: Dict[str, FieldMapping] = field(default_factory=lambda: NOTION_TO_PROPBASE_MAPPING)
    
    # District name mapping (Notion area name -> PropBase district slug)
    district_mapping: Dict[str, str] = field(default_factory=lambda: {
        # Phuket districts
        "Rawai": "rawai",
        "Nai Harn": "nai-harn",
        "Kata": "kata",
        "Karon": "karon",
        "Patong": "patong",
        "Kamala": "kamala",
        "Surin": "surin",
        "Bang Tao": "bang-tao",
        "Laguna": "laguna",
        "Layan": "layan",
        "Nai Yang": "nai-yang",
        "Mai Khao": "mai-khao",
        "Thalang": "thalang",
        "Phuket Town": "phuket-town",
        "Chalong": "chalong",
        "Kathu": "kathu",
        "Cherng Talay": "cherng-talay",
        # Pattaya districts
        "Jomtien": "jomtien",
        "Pratumnak": "pratumnak",
        "Central Pattaya": "central-pattaya",
        "North Pattaya": "north-pattaya",
        "Na Jomtien": "na-jomtien",
        # Bali districts
        "Seminyak": "seminyak",
        "Canggu": "canggu",
        "Ubud": "ubud",
        "Uluwatu": "uluwatu",
        "Sanur": "sanur",
    })
    
    # Property type mapping (Notion type -> PropBase PropertyType enum)
    property_type_mapping: Dict[str, str] = field(default_factory=lambda: {
        "Condo": "apartment",
        "condo": "apartment",
        "Villa": "villa",
        "villa": "villa",
        "Townhouse": "townhouse",
        "townhouse": "townhouse",
        "Land Plot": "land",
        "land plot": "land",
        "Land": "land",
        "Commercial": None,  # Skip
    })
    
    def get_mapping(self, notion_field: str) -> Optional[FieldMapping]:
        """Get mapping for a Notion field."""
        return self.mappings.get(notion_field)
    
    def get_district_slug(self, notion_area: str) -> Optional[str]:
        """Get PropBase district slug from Notion area name."""
        if not notion_area:
            return None
        # Try exact match first
        slug = self.district_mapping.get(notion_area)
        if slug:
            return slug
        # Try case-insensitive match
        for notion_name, district_slug in self.district_mapping.items():
            if notion_name.lower() == notion_area.lower():
                return district_slug
        # Return slugified version as fallback
        return notion_area.lower().replace(" ", "-")
    
    def get_property_type(self, notion_type: str) -> Optional[str]:
        """Get PropBase property type from Notion type."""
        return self.property_type_mapping.get(notion_type)
    
    def get_all_notion_fields(self) -> List[str]:
        """Get list of all mapped Notion field names."""
        return list(self.mappings.keys())
    
    def get_required_fields(self) -> List[str]:
        """Get list of required Notion field names."""
        return [name for name, mapping in self.mappings.items() if mapping.required]
