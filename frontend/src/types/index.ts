// Project types
export interface Project {
  id: number
  slug: string
  name_en: string | null
  name_ru: string | null
  cover_image_url: string | null
  gallery: string[] | null
  lat: number | null
  lng: number | null
  district: DistrictBrief | null
  developer: DeveloperBrief | null
  property_types: string[]
  status: string
  construction_progress: number | null
  completion_date: string | null
  completion_quarter: string | null
  completion_year: number | null
  min_price_usd: number | null
  max_price_usd: number | null
  min_price_per_sqm_usd: number | null
  original_currency: string
  last_price_update: string | null
  total_units: number
  available_units: number
  min_bedrooms: number | null
  max_bedrooms: number | null
  is_featured: boolean
  requires_review: boolean
}

export interface ProjectDetail extends Project {
  description_en: string | null
  description_ru: string | null
  sales_points_en: string | null
  sales_points_ru: string | null
  address_en: string | null
  address_ru: string | null
  ownership_type: string
  leasehold_years: number | null
  master_plan_url: string | null
  video_url: string | null
  virtual_tour_url: string | null
  construction_photos: string[] | null
  amenities: string[] | null
  features: string[] | null
  internal_infrastructure_en: string | null
  internal_infrastructure_ru: string | null
  min_area: number | null
  max_area: number | null
  sold_units: number
  reserved_units: number
}

export interface DeveloperBrief {
  id: number
  name_en: string | null
  name_ru: string | null
  logo_url: string | null
}

export interface DistrictBrief {
  id: number
  name_en: string | null
  name_ru: string | null
  slug: string
}

// Unit types
export interface Unit {
  id: number
  unit_number: string
  building: string | null
  floor: number | null
  unit_type: string
  bedrooms: number
  bathrooms: number | null
  layout_name: string | null
  layout_image_url: string | null
  area_sqm: number
  area_sqft: number | null
  view_type: string | null
  view_description: string | null
  price: number | null
  currency: string
  price_usd: number | null
  price_per_sqm: number | null
  price_per_sqm_usd: number | null
  previous_price_usd: number | null
  price_change_percent: number | null
  downpayment_percent: number | null
  downpayment_amount_usd: number | null
  status: string
  is_active: boolean
}

export interface UnitDetail extends Unit {
  project_id: number
  phase_id: number | null
  indoor_area: number | null
  outdoor_area: number | null
  land_area: number | null
  features: string[] | null
  furniture: string | null
  images: string[] | null
  floor_plan_url: string | null
  last_price_update: string | null
}

// Collection types
export interface Collection {
  id: number
  owner_id: number
  name: string
  name_ru: string | null
  description: string | null
  description_ru: string | null
  ai_description: string | null
  ai_description_ru: string | null
  client_name: string | null
  client_email: string | null
  client_phone: string | null
  share_token: string
  is_public: boolean
  expires_at: string | null
  show_prices: boolean
  show_availability: boolean
  default_currency: string
  default_language: string
  show_agent_branding: boolean
  show_agency_branding: boolean
  view_count: number
  pdf_download_count: number
  last_viewed_at: string | null
  created_at: string
  updated_at: string
  items_count: number
}

export interface CollectionItem {
  id: number
  project_id: number
  unit_id: number | null
  note: string | null
  note_ru: string | null
  is_featured: boolean
  sort_order: number
  price_snapshot_usd: number | null
}

// Location types
export interface Country {
  id: number
  code: string
  name_en: string | null
  name_ru: string | null
  center_lat: number | null
  center_lng: number | null
  default_currency: string
}

export interface City {
  id: number
  country_id: number
  slug: string
  name_en: string | null
  name_ru: string | null
  center_lat: number | null
  center_lng: number | null
  default_zoom: number
}

export interface District {
  id: number
  city_id: number
  slug: string
  name_en: string | null
  name_ru: string | null
  description_en: string | null
  description_ru: string | null
  center_lat: number | null
  center_lng: number | null
  projects_count: number
  min_price_usd: number | null
  max_price_usd: number | null
  cover_image_url: string | null
}

export interface Infrastructure {
  id: number
  district_id: number | null
  name_en: string | null
  name_ru: string | null
  poi_type: string
  poi_category: string | null
  lat: number
  lng: number
  address_en: string | null
  address_ru: string | null
  icon: string | null
  is_featured: boolean
}

// Map types
export interface MapMarker {
  id: number
  slug: string
  name_en: string | null
  name_ru: string | null
  lat: number
  lng: number
  property_types: string[]
  min_price_usd: number | null
  available_units: number
  cover_image_url: string | null
}

// Analytics types
export interface DashboardSummary {
  total_projects: number
  total_units: number
  available_units: number
  sold_units: number
  average_price_usd: number | null
  projects_by_status: Record<string, number>
  units_by_type: Record<string, number>
  recent_price_updates: number
  pending_reviews: number
  parsing_errors: number
}

// Price types
export interface PriceVersion {
  id: number
  project_id: number
  version_number: number
  source_type: string
  source_file_name: string | null
  status: string
  processing_started_at: string | null
  processing_completed_at: string | null
  units_created: number
  units_updated: number
  units_unchanged: number
  units_errors: number
  original_currency: string
  exchange_rate_usd: number | null
  errors: Array<{ message: string }> | null
  warnings: Array<{ message: string }> | null
  reviewed_at: string | null
  review_notes: string | null
  created_at: string
}

export interface PriceHistory {
  id: number
  unit_id: number
  price_version_id: number
  old_price: number | null
  old_price_usd: number | null
  new_price: number | null
  new_price_usd: number | null
  price_change: number | null
  price_change_percent: number | null
  change_type: string
  currency: string
  created_at: string
}

// Filter types
export interface ProjectFilters {
  search?: string
  country_id?: number
  city_id?: number
  district_ids?: number[]
  developer_id?: number
  price_min?: number
  price_max?: number
  property_types?: string[]
  bedrooms_min?: number
  bedrooms_max?: number
  completion_year_min?: number
  completion_year_max?: number
  status?: string[]
  ownership_type?: string
}

export interface UnitFilters {
  price_min?: number
  price_max?: number
  area_min?: number
  area_max?: number
  floor_min?: number
  floor_max?: number
  unit_types?: string[]
  bedrooms?: number[]
  view_types?: string[]
  status?: string[]
  phase_id?: number
}

// Pagination
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}
