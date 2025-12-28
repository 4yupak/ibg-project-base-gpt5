#!/usr/bin/env python3
"""
Migration script: Notion → Supabase
Downloads all project data and images from Notion and uploads to Supabase.

Usage:
    python scripts/migrate_notion_to_supabase.py --dry-run  # Preview only
    python scripts/migrate_notion_to_supabase.py           # Full migration
"""
import asyncio
import argparse
import os
import sys
import json
import httpx
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse, unquote

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from notion_client import Client as NotionClient
from supabase import create_client, Client as SupabaseClient


# Configuration from environment
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
STORAGE_BUCKET = "project-images"


class NotionToSupabaseMigrator:
    """Migrates data from Notion to Supabase."""
    
    def __init__(
        self,
        notion_api_key: str,
        notion_database_id: str,
        supabase_url: str,
        supabase_key: str,
        dry_run: bool = False
    ):
        self.notion = NotionClient(auth=notion_api_key)
        # Add trailing slash to URL if missing
        if not supabase_url.endswith('/'):
            supabase_url = supabase_url + '/'
        self.supabase = create_client(supabase_url.rstrip('/'), supabase_key)
        self.supabase_url = supabase_url.rstrip('/')
        self.supabase_key = supabase_key
        self.database_id = self._clean_database_id(notion_database_id)
        self.dry_run = dry_run
        
        # Stats
        self.stats = {
            "projects_processed": 0,
            "projects_with_images": 0,
            "images_uploaded": 0,
            "images_skipped": 0,
            "images_failed": 0,
            "projects_updated": 0,
            "errors": []
        }
    
    def _clean_database_id(self, database_id: str) -> str:
        """Extract database ID from URL if needed."""
        if "notion.so" in database_id:
            import re
            match = re.search(r'([a-f0-9]{32})', database_id)
            if match:
                raw_id = match.group(1)
                return f"{raw_id[:8]}-{raw_id[8:12]}-{raw_id[12:16]}-{raw_id[16:20]}-{raw_id[20:]}"
        return database_id
    
    def run_sync(self):
        """Run the migration synchronously."""
        print("=" * 60)
        print("NOTION → SUPABASE MIGRATION")
        print(f"Mode: {'DRY RUN (no changes)' if self.dry_run else 'LIVE'}")
        print("=" * 60)
        
        # Test connections
        print("\n1. Testing connections...")
        self._test_connections()
        
        # Ensure storage bucket exists
        if not self.dry_run:
            print("\n2. Setting up storage bucket...")
            self._ensure_bucket()
        else:
            print("\n2. Skipping bucket setup (dry run)")
        
        # Fetch all projects from Notion
        print("\n3. Fetching projects from Notion...")
        projects = self._fetch_all_notion_projects()
        print(f"   Found {len(projects)} projects")
        
        # Process each project
        print("\n4. Processing projects...")
        for i, project in enumerate(projects, 1):
            self._process_project_sync(project, i, len(projects))
        
        # Print summary
        self._print_summary()
        
        return self.stats
    
    def _test_connections(self):
        """Test Notion and Supabase connections."""
        # Test Notion
        try:
            db = self.notion.databases.retrieve(self.database_id)
            print(f"   ✅ Notion: Connected to '{self._extract_title(db.get('title', []))}'")
        except Exception as e:
            print(f"   ❌ Notion: {e}")
            raise
        
        # Test Supabase
        try:
            buckets = self.supabase.storage.list_buckets()
            print(f"   ✅ Supabase: Connected ({len(buckets)} buckets)")
        except Exception as e:
            print(f"   ❌ Supabase: {e}")
            raise
    
    def _ensure_bucket(self):
        """Ensure storage bucket exists."""
        try:
            buckets = self.supabase.storage.list_buckets()
            bucket_names = [b.name for b in buckets]
            
            if STORAGE_BUCKET not in bucket_names:
                print(f"   Creating bucket '{STORAGE_BUCKET}'...")
                self.supabase.storage.create_bucket(
                    STORAGE_BUCKET,
                    options={"public": True}
                )
                print(f"   ✅ Bucket created")
            else:
                print(f"   ✅ Bucket '{STORAGE_BUCKET}' already exists")
        except Exception as e:
            print(f"   ⚠️ Bucket setup: {e}")
    
    def _fetch_all_notion_projects(self) -> List[Dict]:
        """Fetch all projects from Notion database."""
        projects = []
        has_more = True
        start_cursor = None
        
        while has_more:
            query_params = {
                "database_id": self.database_id,
                "page_size": 100
            }
            if start_cursor:
                query_params["start_cursor"] = start_cursor
            
            response = self.notion.databases.query(**query_params)
            projects.extend(response.get("results", []))
            
            has_more = response.get("has_more", False)
            start_cursor = response.get("next_cursor")
        
        return projects
    
    def _process_project_sync(self, notion_page: Dict, index: int, total: int):
        """Process a single project synchronously."""
        try:
            page_id = notion_page.get("id", "").replace("-", "")
            properties = notion_page.get("properties", {})
            
            # Get project name (field is "🏷️ Project Name" in Notion)
            name_prop = properties.get("🏷️ Project Name", {}) or properties.get("Name", {})
            name = self._extract_title(name_prop.get("title", []))
            
            if not name:
                return
            
            self.stats["projects_processed"] += 1
            
            # Extract all file URLs from Notion
            # Correct field names from the Notion database
            image_fields = {
                "📸 sales gallery (etc)": "gallery",
                "📸 show unit": "show_unit", 
                "🏙️ exterior": "exterior",
                "🛋️ interior": "interior",
                "🗺️ master plan": "master_plan",
                "🗺️ location (map)": "location_map",
                "🏁 floor plans": "floor_plans",
                "🛏️ unit renders": "unit_renders",
                "🧭 3D Tour": "tour_3d",
                "🧱 construction photos/videos": "construction",
                "🧱 infrastructure": "infrastructure",
                "🛎️ facilities": "facilities",
                "🌇 rooftop/drone view": "rooftop",
                "🎥 videos": "videos",
                "🏷️ price list": "price_list",
                "📐 unit layouts file": "layouts",
                "📢 UPDATES (files, links)": "updates",
            }
            
            all_urls = {}
            total_files = 0
            
            for notion_field, folder in image_fields.items():
                prop = properties.get(notion_field, {})
                if prop.get("type") == "files":
                    files = prop.get("files", [])
                    if files:
                        urls = self._extract_file_urls(files)
                        if urls:
                            all_urls[folder] = urls
                            total_files += len(urls)
            
            # Only print if has files
            if total_files > 0:
                print(f"\n   [{index}/{total}] {name} ({total_files} files)")
                self.stats["projects_with_images"] += 1
                
                # Process files
                uploaded_urls = {}
                for folder, urls in all_urls.items():
                    uploaded = self._upload_files_sync(urls, page_id, folder)
                    if uploaded:
                        uploaded_urls[folder] = uploaded
                
                # Update database
                if uploaded_urls and not self.dry_run:
                    self._update_project_in_db(page_id, name, uploaded_urls)
            else:
                # Progress indicator for projects without images
                if index % 50 == 0:
                    print(f"   [{index}/{total}] Processing... (no images in last batch)")
                    
        except Exception as e:
            print(f"      ❌ Error: {e}")
            self.stats["errors"].append(f"{name if 'name' in dir() else 'Unknown'}: {str(e)}")
    
    def _extract_file_urls(self, files: List[Dict]) -> List[str]:
        """Extract URLs from Notion file objects.
        Only returns direct downloadable URLs (S3, etc.), not Google Drive links.
        """
        urls = []
        for file_obj in files:
            url = None
            if file_obj.get("type") == "file":
                # Direct Notion/S3 files - these are downloadable
                url = file_obj.get("file", {}).get("url")
            elif file_obj.get("type") == "external":
                # External links - check if direct file or just folder link
                ext_url = file_obj.get("external", {}).get("url", "")
                # Skip Google Drive folder links (not directly downloadable)
                if "drive.google.com/drive/folders" in ext_url:
                    continue
                # Skip generic Google Drive links that aren't direct downloads
                if "drive.google.com" in ext_url and "/file/d/" not in ext_url:
                    continue
                url = ext_url
            
            if url:
                urls.append(url)
        return urls
    
    def _upload_files_sync(self, urls: List[str], project_id: str, folder: str) -> List[str]:
        """Upload files to Supabase Storage synchronously."""
        uploaded_urls = []
        
        for url in urls:
            try:
                # Generate storage path
                file_name = self._get_filename_from_url(url)
                storage_path = f"projects/{project_id}/{folder}/{file_name}"
                
                if self.dry_run:
                    uploaded_urls.append(f"[DRY] {storage_path}")
                    self.stats["images_skipped"] += 1
                    continue
                
                # Download file
                with httpx.Client(timeout=60, follow_redirects=True) as client:
                    response = client.get(url)
                    response.raise_for_status()
                    content = response.content
                    content_type = response.headers.get("content-type", "image/jpeg")
                
                # Skip if too small (likely error page)
                if len(content) < 1000:
                    self.stats["images_skipped"] += 1
                    continue
                
                # Upload to Supabase Storage
                try:
                    self.supabase.storage.from_(STORAGE_BUCKET).upload(
                        storage_path,
                        content,
                        {"content-type": content_type, "upsert": "true"}
                    )
                except Exception as upload_err:
                    # Try to update if exists
                    if "Duplicate" in str(upload_err) or "already exists" in str(upload_err):
                        self.supabase.storage.from_(STORAGE_BUCKET).update(
                            storage_path,
                            content,
                            {"content-type": content_type}
                        )
                
                # Get public URL
                public_url = f"{self.supabase_url}/storage/v1/object/public/{STORAGE_BUCKET}/{storage_path}"
                uploaded_urls.append(public_url)
                self.stats["images_uploaded"] += 1
                print(f"      ✓ {folder}/{file_name}")
                
            except Exception as e:
                print(f"      ✗ Failed: {str(e)[:50]}")
                self.stats["images_failed"] += 1
        
        return uploaded_urls
    
    def _get_filename_from_url(self, url: str) -> str:
        """Extract or generate filename from URL."""
        parsed = urlparse(url)
        path = unquote(parsed.path)
        
        # Get filename from path
        if path:
            filename = path.split("/")[-1]
            # Remove query params
            filename = filename.split("?")[0]
            # Clean up
            filename = filename.replace(" ", "_")
            if filename and len(filename) > 3:
                # Ensure has extension
                if "." not in filename:
                    filename = filename + ".jpg"
                return filename[:100]  # Limit length
        
        # Generate hash-based filename
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        return f"image_{url_hash}.jpg"
    
    def _update_project_in_db(self, notion_page_id: str, name: str, uploaded_urls: Dict):
        """Update project in Supabase database with new URLs."""
        try:
            update_data = {}
            
            # Gallery images
            if "gallery" in uploaded_urls and uploaded_urls["gallery"]:
                update_data["gallery"] = uploaded_urls["gallery"]
                update_data["cover_image_url"] = uploaded_urls["gallery"][0]
            
            # Show unit images → add to gallery
            if "show_unit" in uploaded_urls:
                existing_gallery = update_data.get("gallery", [])
                update_data["gallery"] = existing_gallery + uploaded_urls["show_unit"]
            
            if update_data:
                # Format notion_page_id with dashes for DB lookup
                formatted_id = notion_page_id
                if len(formatted_id) == 32 and "-" not in formatted_id:
                    formatted_id = f"{formatted_id[:8]}-{formatted_id[8:12]}-{formatted_id[12:16]}-{formatted_id[16:20]}-{formatted_id[20:]}"
                
                result = self.supabase.table("projects").update(update_data).eq(
                    "notion_page_id", formatted_id
                ).execute()
                
                if result.data:
                    self.stats["projects_updated"] += 1
                    print(f"      📝 DB updated")
                else:
                    print(f"      ⚠️ Project not found in DB: {formatted_id[:20]}...")
                
        except Exception as e:
            print(f"      ⚠️ DB update failed: {e}")
    
    def _extract_title(self, title_prop: List) -> str:
        """Extract title from Notion title property."""
        if not title_prop:
            return ""
        return "".join([t.get("plain_text", "") for t in title_prop])
    
    def _print_summary(self):
        """Print migration summary."""
        print("\n" + "=" * 60)
        print("MIGRATION SUMMARY")
        print("=" * 60)
        print(f"Projects processed:    {self.stats['projects_processed']}")
        print(f"Projects with images:  {self.stats['projects_with_images']}")
        print(f"Projects updated (DB): {self.stats['projects_updated']}")
        print(f"Images uploaded:       {self.stats['images_uploaded']}")
        print(f"Images skipped:        {self.stats['images_skipped']}")
        print(f"Images failed:         {self.stats['images_failed']}")
        
        if self.stats["errors"]:
            print(f"\nErrors ({len(self.stats['errors'])}):")
            for error in self.stats["errors"][:10]:
                print(f"  - {error}")
            if len(self.stats["errors"]) > 10:
                print(f"  ... and {len(self.stats['errors']) - 10} more")
        
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Migrate Notion data to Supabase")
    parser.add_argument("--dry-run", action="store_true", help="Preview without making changes")
    args = parser.parse_args()
    
    # Check required env vars
    required_vars = [
        ("NOTION_API_KEY", NOTION_API_KEY),
        ("NOTION_DATABASE_ID", NOTION_DATABASE_ID),
        ("SUPABASE_URL", SUPABASE_URL),
        ("SUPABASE_SERVICE_KEY", SUPABASE_SERVICE_KEY),
    ]
    
    missing = [name for name, value in required_vars if not value]
    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        print("\nSet them before running:")
        for name in missing:
            print(f"  export {name}='your-value'")
        sys.exit(1)
    
    migrator = NotionToSupabaseMigrator(
        notion_api_key=NOTION_API_KEY,
        notion_database_id=NOTION_DATABASE_ID,
        supabase_url=SUPABASE_URL,
        supabase_key=SUPABASE_SERVICE_KEY,
        dry_run=args.dry_run
    )
    
    migrator.run_sync()


if __name__ == "__main__":
    main()
