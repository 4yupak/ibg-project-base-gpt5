"""
Простой демо-сервер с mock данными для тестирования фронтенда.
Не требует базы данных - все данные в памяти.
"""
import asyncio
from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import jwt
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

# Config
JWT_SECRET = os.getenv("JWT_SECRET", "demo-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app = FastAPI(title="PropBase Demo API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

# ===================
# Mock Data
# ===================

DEMO_USERS = {
    "demo@propbase.io": {
        "id": 1,
        "email": "demo@propbase.io",
        "password": "demo123",
        "first_name": "Demo",
        "last_name": "User",
        "role": "agent",
        "preferred_language": "en",
        "preferred_currency": "USD",
        "agency_name": "PropBase Realty",
        "avatar_url": None,
        "agency_logo_url": None,
    }
}

DEMO_DISTRICTS = [
    {"id": 1, "name_en": "Rawai", "name_ru": "Равай", "city_id": 1, "slug": "rawai", "projects_count": 5, "is_active": True},
    {"id": 2, "name_en": "Patong", "name_ru": "Патонг", "city_id": 1, "slug": "patong", "projects_count": 8, "is_active": True},
    {"id": 3, "name_en": "Kata", "name_ru": "Ката", "city_id": 1, "slug": "kata", "projects_count": 3, "is_active": True},
    {"id": 4, "name_en": "Kamala", "name_ru": "Камала", "city_id": 1, "slug": "kamala", "projects_count": 4, "is_active": True},
    {"id": 5, "name_en": "Bang Tao", "name_ru": "Банг Тао", "city_id": 1, "slug": "bang-tao", "projects_count": 6, "is_active": True},
]

DEMO_PROJECTS = [
    {
        "id": 1,
        "name_en": "PHUKET Luxury Residence",
        "name_ru": "PHUKET Luxury Residence",
        "slug": "phuket-luxury-residence",
        "district_id": 1,
        "district": DEMO_DISTRICTS[0],
        "status": "under_construction",
        "property_types": ["apartment", "penthouse"],
        "min_price_usd": 150000,
        "max_price_usd": 850000,
        "min_price_per_sqm_usd": 3500,
        "max_price_per_sqm_usd": 5500,
        "total_units": 120,
        "available_units": 45,
        "sold_units": 75,
        "reserved_units": 0,
        "completion_year": 2025,
        "completion_quarter": "Q4 2025",
        "construction_progress": 65,
        "lat": 7.7823,
        "lng": 98.3075,
        "cover_image_url": "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=800",
        "gallery": [
            "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=800",
            "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=800",
        ],
        "ownership_type": "freehold",
        "is_featured": True,
        "is_active": True,
        "visibility": "public",
        "notion_page_id": None,
        "amenities": ["pool", "gym", "parking", "security", "garden"],
        "description_en": "Premium luxury apartments in Rawai with stunning sea views.",
        "description_ru": "Премиальные апартаменты класса люкс в Равае с потрясающим видом на море.",
        "min_bedrooms": 1,
        "max_bedrooms": 3,
        "min_area": 45.0,
        "max_area": 180.0,
    },
    {
        "id": 2,
        "name_en": "Ocean View Villas",
        "name_ru": "Виллы с видом на океан",
        "slug": "ocean-view-villas",
        "district_id": 2,
        "district": DEMO_DISTRICTS[1],
        "status": "presale",
        "property_types": ["villa"],
        "min_price_usd": 450000,
        "max_price_usd": 1200000,
        "min_price_per_sqm_usd": 4500,
        "max_price_per_sqm_usd": 6000,
        "total_units": 24,
        "available_units": 18,
        "sold_units": 6,
        "reserved_units": 0,
        "completion_year": 2026,
        "completion_quarter": "Q2 2026",
        "construction_progress": 15,
        "lat": 7.8977,
        "lng": 98.2946,
        "cover_image_url": "https://images.unsplash.com/photo-1613490493576-7fde63acd811?w=800",
        "gallery": [],
        "ownership_type": "freehold",
        "is_featured": True,
        "is_active": True,
        "visibility": "public",
        "notion_page_id": None,
        "amenities": ["pool", "garden", "parking"],
        "description_en": "Exclusive hillside villas with panoramic ocean views.",
        "description_ru": "Эксклюзивные виллы на холме с панорамным видом на океан.",
        "min_bedrooms": 3,
        "max_bedrooms": 5,
        "min_area": 250.0,
        "max_area": 450.0,
    },
    {
        "id": 3,
        "name_en": "Kata Beach Condos",
        "name_ru": "Кондо на пляже Ката",
        "slug": "kata-beach-condos",
        "district_id": 3,
        "district": DEMO_DISTRICTS[2],
        "status": "ready",
        "property_types": ["apartment", "studio"],
        "min_price_usd": 85000,
        "max_price_usd": 280000,
        "min_price_per_sqm_usd": 2800,
        "max_price_per_sqm_usd": 3800,
        "total_units": 80,
        "available_units": 12,
        "sold_units": 68,
        "reserved_units": 0,
        "completion_year": 2023,
        "completion_quarter": "Q3 2023",
        "construction_progress": 100,
        "lat": 7.8206,
        "lng": 98.2980,
        "cover_image_url": "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=800",
        "gallery": [],
        "ownership_type": "leasehold",
        "leasehold_years": 30,
        "is_featured": False,
        "is_active": True,
        "visibility": "public",
        "notion_page_id": None,
        "amenities": ["pool", "gym", "beach_access"],
        "description_en": "Modern condominiums steps away from Kata Beach.",
        "description_ru": "Современные кондоминиумы в нескольких шагах от пляжа Ката.",
        "min_bedrooms": 0,
        "max_bedrooms": 2,
        "min_area": 28.0,
        "max_area": 95.0,
    },
]

DEMO_UNITS = [
    {"id": 1, "project_id": 1, "unit_number": "A101", "unit_type": "studio", "bedrooms": 0, "bathrooms": 1, "area": 32.0, "price": 120000, "price_usd": 120000, "floor": 1, "building": "A", "status": "available", "view_type": "garden"},
    {"id": 2, "project_id": 1, "unit_number": "A102", "unit_type": "one_bedroom", "bedrooms": 1, "bathrooms": 1, "area": 45.0, "price": 165000, "price_usd": 165000, "floor": 1, "building": "A", "status": "available", "view_type": "pool"},
    {"id": 3, "project_id": 1, "unit_number": "A201", "unit_type": "two_bedroom", "bedrooms": 2, "bathrooms": 2, "area": 72.0, "price": 285000, "price_usd": 285000, "floor": 2, "building": "A", "status": "sold", "view_type": "sea"},
    {"id": 4, "project_id": 1, "unit_number": "B301", "unit_type": "penthouse", "bedrooms": 3, "bathrooms": 3, "area": 150.0, "price": 750000, "price_usd": 750000, "floor": 3, "building": "B", "status": "available", "view_type": "sea"},
    {"id": 5, "project_id": 2, "unit_number": "V01", "unit_type": "villa", "bedrooms": 4, "bathrooms": 4, "area": 350.0, "price": 950000, "price_usd": 950000, "floor": None, "building": None, "status": "available", "view_type": "sea"},
]

DEMO_COLLECTIONS = [
    {
        "id": 1,
        "owner_id": 1,
        "name": "Best Investment Options",
        "name_ru": "Лучшие инвестиционные варианты",
        "client_name": "John Smith",
        "client_email": "john@example.com",
        "share_token": "demo-share-token-123",
        "is_public": True,
        "view_count": 25,
        "items_count": 3,
        "created_at": (datetime.now() - timedelta(days=7)).isoformat(),
    }
]

# ===================
# Pydantic Models
# ===================

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: Optional[str]
    role: str
    preferred_language: str
    preferred_currency: str
    agency_name: Optional[str]
    avatar_url: Optional[str]
    agency_logo_url: Optional[str]

# ===================
# Auth Helpers
# ===================

def create_token(user_id: int, expires_delta: timedelta = timedelta(hours=24)) -> str:
    expire = datetime.utcnow() + expires_delta
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def get_user_from_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = int(payload.get("sub"))
        for user in DEMO_USERS.values():
            if user["id"] == user_id:
                return user
    except:
        pass
    return None

async def get_current_user(token: str = Depends(oauth2_scheme)) -> Optional[dict]:
    if token:
        return get_user_from_token(token)
    return None

# ===================
# AUTH Endpoints
# ===================

@app.post("/api/v1/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = DEMO_USERS.get(form_data.username)
    if not user or user["password"] != form_data.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_token(user["id"])
    refresh_token = create_token(user["id"], timedelta(days=7))
    
    return Token(access_token=access_token, refresh_token=refresh_token)

@app.post("/api/v1/auth/register")
async def register(request: Request):
    data = await request.json()
    # In demo mode, just return success
    return {"message": "Registration successful"}

@app.get("/api/v1/auth/me", response_model=UserResponse)
async def get_me(user: dict = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return UserResponse(**{k: v for k, v in user.items() if k != "password"})

@app.post("/api/v1/auth/refresh")
async def refresh_token(request: Request):
    data = await request.json()
    token = data.get("refresh_token")
    user = get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    access_token = create_token(user["id"])
    refresh_token = create_token(user["id"], timedelta(days=7))
    return {"access_token": access_token, "refresh_token": refresh_token}

# ===================
# PROJECTS Endpoints
# ===================

@app.get("/api/v1/projects")
async def list_projects(
    page: int = 1,
    page_size: int = 20,
    district_id: Optional[int] = None,
    status: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
):
    projects = DEMO_PROJECTS.copy()
    
    if district_id:
        projects = [p for p in projects if p["district_id"] == district_id]
    if status:
        projects = [p for p in projects if p["status"] == status]
    if min_price:
        projects = [p for p in projects if p.get("min_price_usd", 0) >= min_price]
    if max_price:
        projects = [p for p in projects if p.get("max_price_usd", float('inf')) <= max_price]
    
    total = len(projects)
    start = (page - 1) * page_size
    end = start + page_size
    
    return {
        "items": projects[start:end],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }

@app.get("/api/v1/projects/map")
async def get_map_markers():
    return [
        {
            "id": p["id"],
            "name_en": p["name_en"],
            "name_ru": p.get("name_ru"),
            "lat": p["lat"],
            "lng": p["lng"],
            "min_price_usd": p.get("min_price_usd"),
            "status": p["status"],
            "property_types": p.get("property_types", []),
            "available_units": p.get("available_units", 0),
        }
        for p in DEMO_PROJECTS if p.get("lat") and p.get("lng")
    ]

@app.get("/api/v1/projects/{project_id}")
async def get_project(project_id: int):
    for p in DEMO_PROJECTS:
        if p["id"] == project_id:
            # Add units
            units = [u for u in DEMO_UNITS if u["project_id"] == project_id]
            return {**p, "units": units}
    raise HTTPException(status_code=404, detail="Project not found")

# ===================
# UNITS Endpoints
# ===================

@app.get("/api/v1/units/project/{project_id}")
async def list_units(project_id: int, page: int = 1, page_size: int = 50):
    units = [u for u in DEMO_UNITS if u["project_id"] == project_id]
    total = len(units)
    start = (page - 1) * page_size
    end = start + page_size
    
    return {
        "items": units[start:end],
        "total": total,
        "page": page,
        "page_size": page_size
    }

@app.get("/api/v1/units/{unit_id}")
async def get_unit(unit_id: int):
    for u in DEMO_UNITS:
        if u["id"] == unit_id:
            return u
    raise HTTPException(status_code=404, detail="Unit not found")

# ===================
# LOCATIONS Endpoints
# ===================

@app.get("/api/v1/locations/countries")
async def list_countries():
    return {"items": [{"id": 1, "name_en": "Thailand", "name_ru": "Таиланд", "code": "THA", "default_currency": "THB"}]}

@app.get("/api/v1/locations/cities")
async def list_cities(country_id: Optional[int] = None):
    return {"items": [{"id": 1, "name_en": "Phuket", "name_ru": "Пхукет", "slug": "phuket", "country_id": 1}]}

@app.get("/api/v1/locations/districts")
async def list_districts(city_id: Optional[int] = None):
    return {"items": DEMO_DISTRICTS}

@app.get("/api/v1/locations/poi-types")
async def get_poi_types():
    return ["beach", "school", "hospital", "mall", "restaurant", "airport", "gym", "pharmacy"]

# ===================
# COLLECTIONS Endpoints
# ===================

@app.get("/api/v1/collections")
async def list_collections(user: dict = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401)
    return {"items": DEMO_COLLECTIONS, "total": len(DEMO_COLLECTIONS)}

@app.get("/api/v1/collections/{collection_id}")
async def get_collection(collection_id: int):
    for c in DEMO_COLLECTIONS:
        if c["id"] == collection_id:
            return {**c, "items": DEMO_PROJECTS[:2]}
    raise HTTPException(status_code=404)

@app.get("/api/v1/collections/share/{token}")
async def get_public_collection(token: str):
    for c in DEMO_COLLECTIONS:
        if c["share_token"] == token:
            return {**c, "items": DEMO_PROJECTS[:2]}
    raise HTTPException(status_code=404)

# ===================
# ANALYTICS Endpoints
# ===================

@app.get("/api/v1/analytics/dashboard")
async def get_dashboard():
    return {
        "total_projects": len(DEMO_PROJECTS),
        "total_units": len(DEMO_UNITS),
        "available_units": sum(1 for u in DEMO_UNITS if u["status"] == "available"),
        "sold_units": sum(1 for u in DEMO_UNITS if u["status"] == "sold"),
        "total_collections": len(DEMO_COLLECTIONS),
        "price_updates_today": 5,
        "projects_by_status": {
            "presale": 1,
            "under_construction": 1,
            "ready": 1,
            "completed": 0,
            "sold_out": 0,
        },
        "recent_price_versions": [],
    }

@app.get("/api/v1/analytics/parsing-errors")
async def get_parsing_errors():
    return {"items": [], "total": 0}

# ===================
# PRICES Endpoints
# ===================

@app.get("/api/v1/prices/versions/project/{project_id}")
async def get_price_versions(project_id: int):
    return {"items": [], "total": 0}

@app.get("/api/v1/prices/requires-review")
async def get_requires_review():
    return {"items": [], "total": 0}

@app.get("/api/v1/prices/history/project/{project_id}")
async def get_project_price_history(project_id: int):
    return {"items": [], "total": 0}

@app.get("/api/v1/prices/payment-plans/project/{project_id}")
async def get_payment_plans(project_id: int):
    return {"items": [], "total": 0}

# ===================
# FILES Endpoints
# ===================

@app.post("/api/v1/files/upload")
async def upload_file(request: Request):
    return {"file_id": "demo-file-123", "filename": "uploaded_file.xlsx", "size": 1024}

@app.post("/api/v1/files/validate")
async def validate_file(request: Request):
    return {
        "valid": True,
        "file_type": "excel",
        "detected_columns": ["Unit", "Type", "Area", "Price", "Status"],
        "row_count": 50
    }

@app.post("/api/v1/files/preview")
async def preview_file(request: Request):
    return {
        "columns": ["unit_number", "unit_type", "area", "price", "status"],
        "preview_rows": [
            {"unit_number": "A101", "unit_type": "Studio", "area": 32.0, "price": 3500000, "status": "Available"},
            {"unit_number": "A102", "unit_type": "1 BR", "area": 45.0, "price": 4800000, "status": "Available"},
        ],
        "total_rows": 50,
        "currency": "THB"
    }

@app.post("/api/v1/files/ingest-price")
async def ingest_price(request: Request):
    return {
        "price_version_id": 1,
        "status": "processing",
        "message": "Price ingestion started"
    }

# ===================
# NOTION Endpoints
# ===================

@app.get("/api/v1/notion/config-status")
async def get_notion_config():
    return {
        "configured": bool(NOTION_API_KEY and NOTION_DATABASE_ID),
        "api_key_set": bool(NOTION_API_KEY),
        "database_id_set": bool(NOTION_DATABASE_ID),
        "database_id": NOTION_DATABASE_ID[:8] + "..." if NOTION_DATABASE_ID else None,
    }

@app.get("/api/v1/notion/test-connection")
async def test_notion_connection():
    if not NOTION_API_KEY or not NOTION_DATABASE_ID:
        return {"connected": False, "error": "Notion API key or Database ID not configured"}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}",
                headers={
                    "Authorization": f"Bearer {NOTION_API_KEY}",
                    "Notion-Version": "2022-06-28"
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "connected": True,
                    "database_name": data.get("title", [{}])[0].get("plain_text", "Unknown"),
                    "properties_count": len(data.get("properties", {})),
                }
            else:
                return {"connected": False, "error": f"API error: {response.status_code}"}
    except Exception as e:
        return {"connected": False, "error": str(e)}

@app.get("/api/v1/notion/schema")
async def get_notion_schema():
    if not NOTION_API_KEY or not NOTION_DATABASE_ID:
        raise HTTPException(status_code=400, detail="Notion not configured")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}",
                headers={
                    "Authorization": f"Bearer {NOTION_API_KEY}",
                    "Notion-Version": "2022-06-28"
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                properties = []
                for name, prop in data.get("properties", {}).items():
                    properties.append({
                        "name": name,
                        "type": prop.get("type"),
                        "id": prop.get("id"),
                    })
                return {
                    "database_name": data.get("title", [{}])[0].get("plain_text", "Unknown"),
                    "properties": properties
                }
            else:
                raise HTTPException(status_code=response.status_code, detail="Failed to fetch schema")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/notion/field-mapping")
async def get_field_mapping():
    return {
        "mappings": [
            {"notion_field": "Name", "notion_type": "title", "app_field": "name_en", "description": "Project name"},
            {"notion_field": "🏢 type", "notion_type": "select", "app_field": "property_types", "description": "Property type"},
            {"notion_field": "🆔 property ID", "notion_type": "rich_text", "app_field": "internal_code", "description": "Internal code"},
            {"notion_field": "📍 latitude", "notion_type": "number", "app_field": "lat", "description": "Latitude"},
            {"notion_field": "🌐 longitude", "notion_type": "number", "app_field": "lng", "description": "Longitude"},
            {"notion_field": "🏘 Area", "notion_type": "relation", "app_field": "district_id", "description": "District relation"},
            {"notion_field": "📍 project address", "notion_type": "rich_text", "app_field": "address_en", "description": "Address"},
            {"notion_field": "🌐 website", "notion_type": "url", "app_field": "website_url", "description": "Website"},
            {"notion_field": "📹 videos", "notion_type": "files", "app_field": "video_url", "description": "Video URL"},
            {"notion_field": "📸 gallery", "notion_type": "files", "app_field": "gallery", "description": "Image gallery"},
            {"notion_field": "💰 price per m²", "notion_type": "number", "app_field": "min_price_per_sqm", "description": "Price per sqm"},
            {"notion_field": "📈 ROI %", "notion_type": "number", "app_field": "roi", "description": "Return on investment"},
            {"notion_field": "💳 installment plan", "notion_type": "checkbox", "app_field": "has_payment_plan", "description": "Has payment plan"},
            {"notion_field": "🏷 price list", "notion_type": "files", "app_field": "price_files", "description": "Price list files"},
        ]
    }

@app.post("/api/v1/notion/preview")
async def preview_notion_data(limit: int = 5):
    if not NOTION_API_KEY or not NOTION_DATABASE_ID:
        raise HTTPException(status_code=400, detail="Notion not configured")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query",
                headers={
                    "Authorization": f"Bearer {NOTION_API_KEY}",
                    "Notion-Version": "2022-06-28",
                    "Content-Type": "application/json"
                },
                json={"page_size": limit},
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                pages = []
                for page in data.get("results", []):
                    props = page.get("properties", {})
                    
                    # Extract title
                    name = ""
                    for key, val in props.items():
                        if val.get("type") == "title":
                            title_arr = val.get("title", [])
                            if title_arr:
                                name = title_arr[0].get("plain_text", "")
                            break
                    
                    pages.append({
                        "id": page.get("id"),
                        "name": name,
                        "properties": {k: {"type": v.get("type")} for k, v in props.items()},
                        "url": page.get("url"),
                    })
                
                return {
                    "total": len(pages),
                    "pages": pages
                }
            else:
                raise HTTPException(status_code=response.status_code, detail="Failed to query database")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/notion/sync")
async def sync_notion(dry_run: bool = False):
    if not NOTION_API_KEY or not NOTION_DATABASE_ID:
        raise HTTPException(status_code=400, detail="Notion not configured")
    
    # In demo mode, return a simulated result
    return {
        "success": True,
        "dry_run": dry_run,
        "total_pages": 3,
        "projects_created": 0 if dry_run else 2,
        "projects_updated": 0 if dry_run else 1,
        "errors": [],
        "warnings": ["Some price files could not be processed"],
    }

@app.get("/api/v1/notion/price-files")
async def get_notion_price_files():
    if not NOTION_API_KEY or not NOTION_DATABASE_ID:
        raise HTTPException(status_code=400, detail="Notion not configured")
    
    return {
        "files": [
            {"project_name": "PHUKET Luxury Residence", "file_name": "pricelist_2024.pdf", "file_url": "https://...", "file_type": "pdf"},
        ]
    }

# ===================
# SEARCH Endpoints
# ===================

@app.get("/api/v1/search/quick")
async def quick_search(q: str):
    results = []
    q_lower = q.lower()
    
    for p in DEMO_PROJECTS:
        if q_lower in p["name_en"].lower() or q_lower in p.get("name_ru", "").lower():
            results.append({
                "type": "project",
                "id": p["id"],
                "name": p["name_en"],
                "slug": p["slug"],
            })
    
    return {"items": results[:10], "total": len(results)}

@app.get("/api/v1/search/suggestions")
async def get_suggestions(q: str):
    suggestions = [p["name_en"] for p in DEMO_PROJECTS if q.lower() in p["name_en"].lower()]
    return suggestions[:5]

# ===================
# Health Check
# ===================

@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "ok",
        "mode": "demo",
        "notion_configured": bool(NOTION_API_KEY and NOTION_DATABASE_ID),
        "openai_configured": bool(OPENAI_API_KEY),
    }

@app.get("/")
async def root():
    return {"message": "PropBase Demo API", "docs": "/docs"}

# ===================
# Extended Notion Sync - Full Data Load
# ===================

@app.post("/api/v1/notion/full-sync")
async def full_sync_notion():
    """Full sync: load all projects from Notion and store in memory"""
    if not NOTION_API_KEY or not NOTION_DATABASE_ID:
        raise HTTPException(status_code=400, detail="Notion not configured")
    
    try:
        async with httpx.AsyncClient() as client:
            all_pages = []
            has_more = True
            start_cursor = None
            
            while has_more:
                payload = {"page_size": 100}
                if start_cursor:
                    payload["start_cursor"] = start_cursor
                
                response = await client.post(
                    f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query",
                    headers={
                        "Authorization": f"Bearer {NOTION_API_KEY}",
                        "Notion-Version": "2022-06-28",
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=60.0
                )
                
                if response.status_code != 200:
                    raise HTTPException(status_code=response.status_code, detail=f"Notion API error: {response.text}")
                
                data = response.json()
                all_pages.extend(data.get("results", []))
                has_more = data.get("has_more", False)
                start_cursor = data.get("next_cursor")
            
            # Parse pages into projects
            synced_projects = []
            errors = []
            
            for page in all_pages:
                try:
                    project = parse_notion_page(page)
                    if project:
                        synced_projects.append(project)
                        # Update DEMO_PROJECTS
                        existing = next((p for p in DEMO_PROJECTS if p.get("notion_page_id") == page["id"]), None)
                        if existing:
                            existing.update(project)
                        else:
                            project["id"] = len(DEMO_PROJECTS) + 1
                            DEMO_PROJECTS.append(project)
                except Exception as e:
                    errors.append({"page_id": page["id"], "error": str(e)})
            
            return {
                "success": True,
                "total_pages": len(all_pages),
                "synced_projects": len(synced_projects),
                "projects": synced_projects,
                "errors": errors
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def parse_notion_page(page: dict) -> dict | None:
    """Parse a Notion page into a project dict"""
    props = page.get("properties", {})
    
    # Extract title (Name)
    name = ""
    for key, val in props.items():
        if val.get("type") == "title":
            title_arr = val.get("title", [])
            if title_arr:
                name = title_arr[0].get("plain_text", "")
            break
    
    if not name:
        return None
    
    # Helper functions
    def get_rich_text(prop_name: str) -> str | None:
        prop = props.get(prop_name, {})
        if prop.get("type") == "rich_text":
            texts = prop.get("rich_text", [])
            if texts:
                return texts[0].get("plain_text")
        return None
    
    def get_number(prop_name: str) -> float | None:
        prop = props.get(prop_name, {})
        if prop.get("type") == "number":
            return prop.get("number")
        return None
    
    def get_select(prop_name: str) -> str | None:
        prop = props.get(prop_name, {})
        if prop.get("type") == "select":
            sel = prop.get("select")
            if sel:
                return sel.get("name")
        return None
    
    def get_multi_select(prop_name: str) -> list:
        prop = props.get(prop_name, {})
        if prop.get("type") == "multi_select":
            return [s.get("name") for s in prop.get("multi_select", [])]
        return []
    
    def get_url(prop_name: str) -> str | None:
        prop = props.get(prop_name, {})
        if prop.get("type") == "url":
            return prop.get("url")
        return None
    
    def get_checkbox(prop_name: str) -> bool:
        prop = props.get(prop_name, {})
        if prop.get("type") == "checkbox":
            return prop.get("checkbox", False)
        return False
    
    def get_files(prop_name: str) -> list:
        prop = props.get(prop_name, {})
        if prop.get("type") == "files":
            files = prop.get("files", [])
            urls = []
            for f in files:
                if f.get("type") == "file":
                    urls.append(f.get("file", {}).get("url"))
                elif f.get("type") == "external":
                    urls.append(f.get("external", {}).get("url"))
            return [u for u in urls if u]
        return []
    
    def get_relation_names(prop_name: str) -> list:
        prop = props.get(prop_name, {})
        if prop.get("type") == "relation":
            # Relations only have IDs, not names - would need separate API calls
            return [r.get("id") for r in prop.get("relation", [])]
        return []
    
    # Build project
    slug = name.lower().replace(" ", "-").replace("(", "").replace(")", "")[:100]
    
    # Get coordinates (both use 🌐 emoji in Notion)
    lat = get_number("🌐 latitude")
    lng = get_number("🌐 longitude")
    
    # Get property type
    prop_type = get_select("🏢 type")
    property_types = [prop_type.lower()] if prop_type else ["apartment"]
    
    # Get price per sqm
    price_per_sqm = get_number("💰 price per m²")
    
    # Get gallery
    gallery = get_files("📸 gallery")
    
    # Get videos
    video_url = get_url("📹 videos")
    
    # Get website
    website = get_url("🌐 website / telegram / teletype")
    
    # Get address
    address = get_rich_text("📍 project address")
    
    # Get internal code
    internal_code = get_rich_text("🆔 property ID")
    
    # Get ROI
    roi_str = get_select("📈 ROI %")
    roi = None
    if roi_str:
        try:
            roi = float(roi_str.replace("%", "").strip())
        except:
            pass
    
    # Get amenities
    amenities = get_multi_select("🧺 services & operations")
    
    # Get price files
    price_files = get_files("🏷 price list")
    
    # Smart home
    smart_home = get_select("💡 smart home")
    
    # Has payment plan
    has_payment_plan = get_checkbox("💳 installment plan")
    
    project = {
        "notion_page_id": page["id"],
        "notion_url": page.get("url"),
        "name_en": name,
        "name_ru": name,  # Same for now
        "slug": slug,
        "internal_code": internal_code,
        "property_types": property_types,
        "status": "under_construction",
        "lat": lat,
        "lng": lng,
        "address_en": address,
        "address_ru": address,
        "website_url": website,
        "video_url": video_url,
        "gallery": gallery[:10] if gallery else [],
        "cover_image_url": gallery[0] if gallery else None,
        "min_price_per_sqm": price_per_sqm,
        "max_price_per_sqm": price_per_sqm,
        "min_price_per_sqm_usd": price_per_sqm,  # Assuming USD
        "max_price_per_sqm_usd": price_per_sqm,
        "roi": roi,
        "amenities": amenities,
        "price_files": price_files,
        "has_payment_plan": has_payment_plan,
        "smart_home": smart_home,
        "is_featured": False,
        "is_active": True,
        "visibility": "public",
        "district_id": 1,  # Default to Rawai
        "district": DEMO_DISTRICTS[0],
        "total_units": 0,
        "available_units": 0,
        "sold_units": 0,
        "reserved_units": 0,
    }
    
    return project

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
