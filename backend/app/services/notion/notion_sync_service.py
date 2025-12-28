"""
Notion Sync Service - synchronizes projects from Notion database to PropBase.

Handles:
- Full sync (all projects)
- Incremental sync (changed since last sync)
- Single project sync
- Price list file extraction for parsing
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import re
import httpx

from notion_client import Client as NotionClient
from notion_client.errors import APIResponseError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.project import Project, ProjectStatus, PropertyType, OwnershipType, Developer
from app.models.location import District, City
from .notion_field_mapping import (
    NotionFieldMapping,
    NotionPropertyType,
    extract_text_from_rich_text,
    extract_url_from_files,
    extract_all_urls_from_files,
    extract_multi_select_values,
)

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Result of sync operation."""
    success: bool = True
    projects_created: int = 0
    projects_updated: int = 0
    projects_skipped: int = 0
    projects_failed: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    price_files_found: List[Dict[str, Any]] = field(default_factory=list)
    synced_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class NotionProject:
    """Parsed project data from Notion."""
    notion_page_id: str
    name: str
    raw_properties: Dict[str, Any]
    parsed_data: Dict[str, Any] = field(default_factory=dict)
    price_list_urls: List[str] = field(default_factory=list)
    layout_urls: List[str] = field(default_factory=list)
    gallery_urls: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class NotionSyncService:
    """Service for synchronizing Notion database with PropBase."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        database_id: Optional[str] = None,
    ):
        """Initialize Notion sync service."""
        self.api_key = api_key or settings.NOTION_API_KEY
        self.database_id = database_id or settings.NOTION_DATABASE_ID
        
        if not self.api_key:
            raise ValueError("NOTION_API_KEY is required")
        if not self.database_id:
            raise ValueError("NOTION_DATABASE_ID is required")
        
        # Clean database ID (remove URL parts if full URL provided)
        self.database_id = self._clean_database_id(self.database_id)
        
        self.client = NotionClient(auth=self.api_key)
        self.field_mapping = NotionFieldMapping()
        
        # Cache for districts
        self._district_cache: Dict[str, int] = {}
        self._developer_cache: Dict[str, int] = {}
    
    def _clean_database_id(self, database_id: str) -> str:
        """Extract database ID from URL or return as-is."""
        # Handle full Notion URL
        if "notion.so" in database_id:
            # Extract ID from URL like: https://www.notion.so/1af48102146280d6b99bedca9ea90abf?v=...
            match = re.search(r'([a-f0-9]{32})', database_id)
            if match:
                raw_id = match.group(1)
                # Format as UUID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
                return f"{raw_id[:8]}-{raw_id[8:12]}-{raw_id[12:16]}-{raw_id[16:20]}-{raw_id[20:]}"
        
        # Already formatted or just ID
        return database_id
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test Notion API connection and return database info."""
        try:
            database = self.client.databases.retrieve(database_id=self.database_id)
            return {
                "success": True,
                "database_id": self.database_id,
                "title": self._extract_title(database.get("title", [])),
                "properties_count": len(database.get("properties", {})),
                "properties": list(database.get("properties", {}).keys()),
            }
        except APIResponseError as e:
            logger.error(f"Notion API error: {e}")
            return {
                "success": False,
                "error": str(e),
                "database_id": self.database_id,
            }
        except Exception as e:
            logger.error(f"Notion connection error: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    
    def _extract_title(self, title_prop: List[Dict]) -> str:
        """Extract title from Notion title property."""
        if not title_prop:
            return ""
        return "".join([t.get("plain_text", "") for t in title_prop])
    
    async def get_database_schema(self) -> Dict[str, Any]:
        """Get database schema (properties) from Notion."""
        try:
            database = self.client.databases.retrieve(database_id=self.database_id)
            properties = database.get("properties", {})
            
            schema = {}
            for name, prop in properties.items():
                schema[name] = {
                    "type": prop.get("type"),
                    "id": prop.get("id"),
                }
                
                # Add options for select/multi_select
                if prop.get("type") == "select":
                    schema[name]["options"] = [
                        opt.get("name") for opt in prop.get("select", {}).get("options", [])
                    ]
                elif prop.get("type") == "multi_select":
                    schema[name]["options"] = [
                        opt.get("name") for opt in prop.get("multi_select", {}).get("options", [])
                    ]
                elif prop.get("type") == "status":
                    schema[name]["options"] = [
                        opt.get("name") for opt in prop.get("status", {}).get("options", [])
                    ]
            
            return {
                "success": True,
                "database_id": self.database_id,
                "title": self._extract_title(database.get("title", [])),
                "properties": schema,
            }
        except Exception as e:
            logger.error(f"Error getting database schema: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    
    async def fetch_all_projects(
        self,
        filter_condition: Optional[Dict] = None,
        sorts: Optional[List[Dict]] = None,
    ) -> List[NotionProject]:
        """Fetch all projects from Notion database."""
        projects = []
        has_more = True
        start_cursor = None
        
        while has_more:
            try:
                query_params = {
                    "database_id": self.database_id,
                    "page_size": 100,
                }
                
                if start_cursor:
                    query_params["start_cursor"] = start_cursor
                if filter_condition:
                    query_params["filter"] = filter_condition
                if sorts:
                    query_params["sorts"] = sorts
                
                response = self.client.databases.query(**query_params)
                
                for page in response.get("results", []):
                    project = self._parse_notion_page(page)
                    if project:
                        projects.append(project)
                
                has_more = response.get("has_more", False)
                start_cursor = response.get("next_cursor")
                
            except APIResponseError as e:
                logger.error(f"Notion API error during fetch: {e}")
                break
            except Exception as e:
                logger.error(f"Error fetching projects: {e}")
                break
        
        logger.info(f"Fetched {len(projects)} projects from Notion")
        return projects
    
    def _parse_notion_page(self, page: Dict) -> Optional[NotionProject]:
        """Parse a Notion page into NotionProject."""
        try:
            page_id = page.get("id")
            properties = page.get("properties", {})
            
            # Get project name (required)
            name_prop = properties.get("Name", {})
            name = self._extract_title(name_prop.get("title", []))
            
            if not name:
                logger.warning(f"Skipping page {page_id}: no name")
                return None
            
            project = NotionProject(
                notion_page_id=page_id,
                name=name,
                raw_properties=properties,
            )
            
            # Parse all mapped fields
            for notion_field, mapping in self.field_mapping.mappings.items():
                prop = properties.get(notion_field)
                if not prop:
                    continue
                
                value = self._extract_property_value(prop, mapping.notion_type)
                
                # Apply transformer if defined
                if mapping.transformer and value is not None:
                    try:
                        value = mapping.transformer(value)
                    except Exception as e:
                        project.errors.append(f"Transform error for {notion_field}: {e}")
                        continue
                
                if value is not None:
                    project.parsed_data[mapping.propbase_field] = value
            
            # Extract special file URLs
            price_list_prop = properties.get("🏷 price list", {})
            if price_list_prop.get("type") == "files":
                project.price_list_urls = extract_all_urls_from_files(
                    price_list_prop.get("files", [])
                )
            
            layout_prop = properties.get("📐 unit layouts file", {})
            if layout_prop.get("type") == "files":
                project.layout_urls = extract_all_urls_from_files(
                    layout_prop.get("files", [])
                )
            
            gallery_prop = properties.get("📸 gallery", {})
            if gallery_prop.get("type") == "files":
                project.gallery_urls = extract_all_urls_from_files(
                    gallery_prop.get("files", [])
                )
            
            return project
            
        except Exception as e:
            logger.error(f"Error parsing page: {e}")
            return None
    
    def _extract_property_value(
        self,
        prop: Dict,
        expected_type: NotionPropertyType
    ) -> Any:
        """Extract value from Notion property based on type."""
        prop_type = prop.get("type")
        
        if prop_type == "title":
            return self._extract_title(prop.get("title", []))
        
        elif prop_type == "rich_text":
            return extract_text_from_rich_text(prop.get("rich_text", []))
        
        elif prop_type == "number":
            return prop.get("number")
        
        elif prop_type == "select":
            select_value = prop.get("select")
            return select_value.get("name") if select_value else None
        
        elif prop_type == "multi_select":
            return extract_multi_select_values(prop.get("multi_select", []))
        
        elif prop_type == "status":
            status_value = prop.get("status")
            return status_value.get("name") if status_value else None
        
        elif prop_type == "checkbox":
            return prop.get("checkbox", False)
        
        elif prop_type == "url":
            return prop.get("url")
        
        elif prop_type == "email":
            return prop.get("email")
        
        elif prop_type == "phone_number":
            return prop.get("phone_number")
        
        elif prop_type == "date":
            date_value = prop.get("date")
            if date_value:
                return date_value.get("start")
            return None
        
        elif prop_type == "files":
            return prop.get("files", [])
        
        elif prop_type == "relation":
            return [r.get("id") for r in prop.get("relation", [])]
        
        elif prop_type == "formula":
            formula = prop.get("formula", {})
            formula_type = formula.get("type")
            return formula.get(formula_type)
        
        elif prop_type == "created_time":
            return prop.get("created_time")
        
        elif prop_type == "last_edited_time":
            return prop.get("last_edited_time")
        
        return None
    
    async def sync_all(
        self,
        db: AsyncSession,
        dry_run: bool = False,
    ) -> SyncResult:
        """Sync all projects from Notion to PropBase."""
        result = SyncResult()
        
        # Load caches
        await self._load_district_cache(db)
        
        # Fetch all projects from Notion
        notion_projects = await self.fetch_all_projects()
        
        for notion_project in notion_projects:
            try:
                sync_status = await self._sync_single_project(
                    db=db,
                    notion_project=notion_project,
                    dry_run=dry_run,
                )
                
                if sync_status == "created":
                    result.projects_created += 1
                elif sync_status == "updated":
                    result.projects_updated += 1
                elif sync_status == "skipped":
                    result.projects_skipped += 1
                
                # Collect price list files for later parsing
                if notion_project.price_list_urls:
                    result.price_files_found.append({
                        "project_name": notion_project.name,
                        "notion_page_id": notion_project.notion_page_id,
                        "price_urls": notion_project.price_list_urls,
                    })
                
                if notion_project.errors:
                    result.warnings.extend(notion_project.errors)
                
            except Exception as e:
                logger.error(f"Error syncing project {notion_project.name}: {e}")
                result.projects_failed += 1
                result.errors.append(f"{notion_project.name}: {str(e)}")
        
        if not dry_run:
            await db.commit()
        
        logger.info(
            f"Sync completed: {result.projects_created} created, "
            f"{result.projects_updated} updated, {result.projects_skipped} skipped, "
            f"{result.projects_failed} failed"
        )
        
        return result
    
    async def _load_district_cache(self, db: AsyncSession):
        """Load district name -> id mapping."""
        stmt = select(District.id, District.slug, District.name_en, District.name_ru)
        result = await db.execute(stmt)
        
        for row in result.fetchall():
            # Cache by slug and names
            self._district_cache[row.slug.lower()] = row.id
            if row.name_en:
                self._district_cache[row.name_en.lower()] = row.id
            if row.name_ru:
                self._district_cache[row.name_ru.lower()] = row.id
    
    def _find_district_id(self, area_name: str) -> Optional[int]:
        """Find district ID by area name."""
        if not area_name:
            return None
        
        area_lower = area_name.lower().strip()
        
        # Direct match
        if area_lower in self._district_cache:
            return self._district_cache[area_lower]
        
        # Try slug format
        slug = area_lower.replace(" ", "-")
        if slug in self._district_cache:
            return self._district_cache[slug]
        
        # Partial match
        for cached_name, district_id in self._district_cache.items():
            if area_lower in cached_name or cached_name in area_lower:
                return district_id
        
        return None
    
    async def _sync_single_project(
        self,
        db: AsyncSession,
        notion_project: NotionProject,
        dry_run: bool = False,
    ) -> str:
        """Sync a single project. Returns: 'created', 'updated', or 'skipped'."""
        
        # Check if project already exists by notion_page_id
        stmt = select(Project).where(Project.notion_page_id == notion_project.notion_page_id)
        result = await db.execute(stmt)
        existing_project = result.scalar_one_or_none()
        
        # Build project data
        project_data = self._build_project_data(notion_project)
        
        if dry_run:
            if existing_project:
                return "updated"
            return "created"
        
        if existing_project:
            # Update existing project
            for field, value in project_data.items():
                if hasattr(existing_project, field) and value is not None:
                    setattr(existing_project, field, value)
            existing_project.updated_at = datetime.now(timezone.utc)
            return "updated"
        else:
            # Create new project
            new_project = Project(**project_data)
            db.add(new_project)
            return "created"
    
    def _build_project_data(self, notion_project: NotionProject) -> Dict[str, Any]:
        """Build project data dict from NotionProject."""
        data = {
            "notion_page_id": notion_project.notion_page_id,
            "name_en": notion_project.name,
            "name_ru": notion_project.name,  # Can be translated later
            "slug": self._generate_slug(notion_project.name),
            "is_active": True,
            "original_currency": "THB",
        }
        
        parsed = notion_project.parsed_data
        
        # Direct mappings
        if "internal_code" in parsed:
            data["internal_code"] = parsed["internal_code"]
        
        if "lng" in parsed:
            data["lng"] = parsed["lng"]
        
        if "lat" in parsed:
            data["lat"] = parsed["lat"]
        
        if "address_en" in parsed:
            data["address_en"] = parsed["address_en"]
            data["address_ru"] = parsed["address_en"]  # Can be translated
        
        # Website URL - can be in different fields
        website = parsed.get("website_url")
        if website:
            data["website_url"] = website if hasattr(Project, 'website_url') else None
        
        if "video_url" in parsed:
            data["video_url"] = parsed["video_url"]
        
        if "gallery" in parsed and parsed["gallery"]:
            data["gallery"] = parsed["gallery"]
            # Set first image as cover
            if not data.get("cover_image_url"):
                data["cover_image_url"] = parsed["gallery"][0]
        
        # Property types
        if "property_types" in parsed and parsed["property_types"]:
            data["property_types"] = parsed["property_types"]
        
        # Price per sqm
        if "min_price_per_sqm" in parsed:
            data["min_price_per_sqm"] = parsed["min_price_per_sqm"]
            data["max_price_per_sqm"] = parsed["min_price_per_sqm"]
        
        # Amenities
        if "amenities" in parsed:
            data["amenities"] = parsed["amenities"]
        
        # Features (combine various fields)
        features = {}
        if "_roi_percent" in parsed:
            features["roi_percent"] = parsed["_roi_percent"]
        if "_smart_home" in parsed:
            features["smart_home"] = parsed["_smart_home"]
        if "_ceiling_height" in parsed:
            features["ceiling_height"] = parsed["_ceiling_height"]
        if "_has_payment_plan" in parsed:
            features["has_payment_plan"] = parsed["_has_payment_plan"]
        if "_payment_plan_details" in parsed:
            features["payment_plan_details"] = parsed["_payment_plan_details"]
        if "_booking_fee" in parsed:
            features["booking_fee"] = parsed["_booking_fee"]
        if "_green_areas" in parsed:
            features["green_areas"] = parsed["_green_areas"]
        
        if features:
            data["features"] = features
        
        # District mapping
        if "_district_name" in parsed:
            district_id = self._find_district_id(parsed["_district_name"])
            if district_id:
                data["district_id"] = district_id
        
        # Default district if not found (first Phuket district)
        if "district_id" not in data:
            # Will need to be set manually or use a default
            first_district_id = next(iter(self._district_cache.values()), None)
            if first_district_id:
                data["district_id"] = first_district_id
        
        return data
    
    def _generate_slug(self, name: str) -> str:
        """Generate URL slug from project name."""
        # Remove special characters, lowercase, replace spaces with hyphens
        slug = re.sub(r'[^\w\s-]', '', name.lower())
        slug = re.sub(r'[-\s]+', '-', slug).strip('-')
        return slug[:150]  # Max length
    
    async def sync_single_by_page_id(
        self,
        db: AsyncSession,
        page_id: str,
    ) -> SyncResult:
        """Sync a single project by Notion page ID."""
        result = SyncResult()
        
        try:
            # Load caches
            await self._load_district_cache(db)
            
            # Fetch single page from Notion
            page = self.client.pages.retrieve(page_id=page_id)
            notion_project = self._parse_notion_page(page)
            
            if not notion_project:
                result.success = False
                result.errors.append(f"Could not parse page {page_id}")
                return result
            
            sync_status = await self._sync_single_project(
                db=db,
                notion_project=notion_project,
                dry_run=False,
            )
            
            await db.commit()
            
            if sync_status == "created":
                result.projects_created = 1
            elif sync_status == "updated":
                result.projects_updated = 1
            
            if notion_project.price_list_urls:
                result.price_files_found.append({
                    "project_name": notion_project.name,
                    "notion_page_id": notion_project.notion_page_id,
                    "price_urls": notion_project.price_list_urls,
                })
            
        except Exception as e:
            logger.error(f"Error syncing page {page_id}: {e}")
            result.success = False
            result.errors.append(str(e))
        
        return result
    
    async def get_price_list_files(self) -> List[Dict[str, Any]]:
        """Get all price list files from Notion projects."""
        projects = await self.fetch_all_projects()
        
        price_files = []
        for project in projects:
            if project.price_list_urls:
                price_files.append({
                    "project_name": project.name,
                    "notion_page_id": project.notion_page_id,
                    "price_urls": project.price_list_urls,
                    "layout_urls": project.layout_urls,
                })
        
        return price_files
    
    async def download_file(self, url: str, timeout: int = 30) -> bytes:
        """Download file from Notion (handles temporary URLs)."""
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=timeout, follow_redirects=True)
            response.raise_for_status()
            return response.content


# Factory function
def create_notion_sync_service(
    api_key: Optional[str] = None,
    database_id: Optional[str] = None,
) -> NotionSyncService:
    """Create NotionSyncService instance."""
    return NotionSyncService(
        api_key=api_key,
        database_id=database_id,
    )
