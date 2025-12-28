"""
API v1 Router - aggregates all endpoint routers.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    users,
    projects,
    units,
    collections,
    locations,
    prices,
    analytics,
    search,
    files,
    notion,
    parser,
    admin,
)

api_router = APIRouter()

# Authentication
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"]
)

# Users
api_router.include_router(
    users.router,
    prefix="/users",
    tags=["Users"]
)

# Locations (Countries, Cities, Districts)
api_router.include_router(
    locations.router,
    prefix="/locations",
    tags=["Locations"]
)

# Projects
api_router.include_router(
    projects.router,
    prefix="/projects",
    tags=["Projects"]
)

# Units
api_router.include_router(
    units.router,
    prefix="/units",
    tags=["Units"]
)

# Collections (Selections for clients)
api_router.include_router(
    collections.router,
    prefix="/collections",
    tags=["Collections"]
)

# Prices (Price versions, history, ingestion)
api_router.include_router(
    prices.router,
    prefix="/prices",
    tags=["Prices"]
)

# Analytics
api_router.include_router(
    analytics.router,
    prefix="/analytics",
    tags=["Analytics"]
)

# Search (Advanced search, map search)
api_router.include_router(
    search.router,
    prefix="/search",
    tags=["Search"]
)

# Files (Upload, download, parsing)
api_router.include_router(
    files.router,
    prefix="/files",
    tags=["Files"]
)

# Notion Integration
api_router.include_router(
    notion.router,
    prefix="/notion",
    tags=["Notion Integration"]
)

# Smart Parser (Price parsing with learning)
api_router.include_router(
    parser.router,
    prefix="/parser",
    tags=["Smart Parser"]
)

# Admin Panel API (CRUD for projects, units, media)
api_router.include_router(
    admin.router,
    prefix="/admin",
    tags=["Admin Panel"]
)
