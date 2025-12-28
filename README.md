# PropBase - Real Estate Property Database Platform

## Project Overview

**PropBase** is a comprehensive real estate platform for agents managing property listings across Southeast Asia (Phuket, Pattaya, Bali). It enables agents to filter projects/units, create collections in under 5 minutes, share branded presentations with clients, and track price updates.

## Production URLs

| Service | URL |
|---------|-----|
| **Frontend (Vercel)** | https://ibg-project-base.vercel.app |
| **Backend API (Railway)** | https://ibg-project-base-production.up.railway.app |
| **API Health** | https://ibg-project-base-production.up.railway.app/api/v1/health |
| **API Docs** | https://ibg-project-base-production.up.railway.app/docs |
| **GitHub** | https://github.com/4yupak/ibg-project-base |

### Demo Credentials
- Email: `demo@propbase.io`
- Password: `demo123`

### Admin Credentials
- Email: `admin@propbase.io`
- Password: `admin2024`

## Tech Stack

**Backend:**
- FastAPI (Python 3.11)
- **Supabase PostgreSQL** (production database)
- psycopg2
- Notion API integration
- Price Parser (PDF, Excel, Google Sheets)

**Frontend:**
- React 18 + TypeScript
- Vite build
- TailwindCSS
- Mapbox GL JS
- Tanstack Query (React Query)
- Zustand state management
- react-router-dom v6
- Lucide icons

**Deployment:**
- Railway (Backend API)
- Vercel (Frontend)
- Supabase (PostgreSQL Database)

## Current Database Status

- **Projects in database:** 399
- **Projects with coordinates (map markers):** 195  
- **Projects with price files:** 151
- **Districts (Phuket):** 14

## Notion Integration

PropBase syncs projects from Notion database.

### Correct Field Mapping (Updated)

| Notion Field | PropBase Field | Type |
|--------------|---------------|------|
| `🏷️ Project Name` | `project.name_en` | title |
| `🏢 type` | `project.property_types` | select |
| `🆔 property ID` | `project.internal_code` | rich_text |
| `🌐 longitude` | `project.lng` | number |
| `🌐 latitude` | `project.lat` | number |
| `🏝️ area` | → `district_id` | select |
| `🗺️ project address` | `project.address_en` | rich_text |
| `🌐 website` | `project.website_url` | url |
| `🎥 videos` | `project.video_url` | url |
| `📸 sales gallery (etc)` | `project.gallery` | files |
| `🏷 price per m²` | `project.min_price_per_sqm` | number |
| `📈 ROI %` | `features.roi_percent` | select |
| `💳 installment plan` | `features.has_payment_plan` | select |
| `🏷️ price list` | → Price URLs for parsing | files |
| `🧺 services & operations` | `project.amenities` | multi_select |
| `💡smart home` | `features.smart_home` | select |

### API Endpoints for Notion

- `GET /api/v1/notion/test-connection` - Test Notion API connection
- `GET /api/v1/notion/config-status` - Check configuration status
- `POST /api/v1/notion/sync?dry_run=false` - Sync all projects
- `GET /api/v1/notion/price-files` - Get price list files found in Notion

## Environment Variables

### Railway (Backend)
```env
DATABASE_URL=postgresql://postgres.xxx:password@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres
NOTION_API_KEY=ntn_xxx
NOTION_DATABASE_ID=1af48102146280d6b99bedca9ea90abf
JWT_SECRET=your-secret-key
```

### Vercel (Frontend)
```env
VITE_API_URL=https://ibg-project-base-production.up.railway.app/api/v1
VITE_MAPBOX_TOKEN=pk.xxx
```

## Recent Fixes (2024-12-28)

### Completed ✅
1. **Auth endpoint fixed** - Now accepts `application/x-www-form-urlencoded` format (OAuth2PasswordRequestForm)
2. **User response format fixed** - `/auth/me` returns `first_name`/`last_name` (not `full_name`)
3. **API fallback URLs added** - Frontend uses production API URL if env var not set
4. **Mapbox token fallback** - Map works without env var configuration
5. **Notion field mapping corrected** - `🏷️ Project Name` instead of `Name`
6. **Notion sync endpoint fixed** - Now runs directly instead of subprocess

### Action Required ⚠️

1. **Re-sync Notion data** - After Railway deploys new code:
   ```bash
   # Via API (requires auth token)
   curl -X POST "https://ibg-project-base-production.up.railway.app/api/v1/notion/sync?dry_run=false" \
     -H "Authorization: Bearer YOUR_TOKEN"
   
   # Or via frontend at /notion-sync page
   ```

2. **Vercel environment variables** - Set in Vercel dashboard (Settings → Environment Variables):
   - `VITE_API_URL=https://ibg-project-base-production.up.railway.app/api/v1`
   - `VITE_MAPBOX_TOKEN=pk.eyJ1...` (your Mapbox token)

3. **Railway environment variables** - Verify in Railway dashboard:
   - `DATABASE_URL` - Supabase PostgreSQL connection string
   - `NOTION_API_KEY` - Notion integration token
   - `NOTION_DATABASE_ID` - Notion database ID

## Frontend Routes

| Route | Description |
|-------|-------------|
| `/login` | Login page |
| `/projects` | Projects listing with map |
| `/projects/:id` | Project detail with units |
| `/collections` | User's collections |
| `/collections/:id` | Collection detail |
| `/c/:token` | Public collection share page |
| `/analytics` | Analytics dashboard |
| `/price-ingestion` | Price file upload page |
| `/notion-sync` | Notion integration & sync |
| `/settings` | User settings |

## API Endpoints

**Authentication:**
- `POST /api/v1/auth/login` - Login (form data: username, password)
- `POST /api/v1/auth/refresh` - Refresh token
- `GET /api/v1/auth/me` - Current user

**Projects:**
- `GET /api/v1/projects` - List with filters
- `GET /api/v1/projects/map` - Map markers
- `GET /api/v1/projects/{id}` - Project detail

**Collections:**
- `GET /api/v1/collections` - User's collections
- `POST /api/v1/collections` - Create
- `GET /api/v1/collections/share/{token}` - Public view

## Known Issues / TODO

### High Priority
- [ ] **Notion sync needed** - Project names show as "Unnamed Project" until re-sync

### Medium Priority
- [ ] Improve Excel parser for Russian files (complex headers)
- [ ] Google Sheets parser improvements
- [ ] LLM fallback for complex PDFs (GPT-4 Vision)

### Low Priority
- [ ] Custom domain setup
- [ ] Celery/scheduler for periodic Notion sync
- [ ] PDF generation for collections
- [ ] amoCRM integration

## License

Proprietary - All rights reserved
