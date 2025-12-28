import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'
import { useAuthStore } from '../store/authStore'

// Production API URL - fallback to Railway when env var not set
const API_URL = import.meta.env.VITE_API_URL || 'https://ibg-project-base-production.up.railway.app/api/v1'

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor - add auth token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = useAuthStore.getState().accessToken
    
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor - handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }
    
    // If 401 and not already retrying, try to refresh token
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      
      try {
        await useAuthStore.getState().refreshAccessToken()
        const newToken = useAuthStore.getState().accessToken
        
        if (newToken) {
          originalRequest.headers.Authorization = `Bearer ${newToken}`
          return api(originalRequest)
        }
      } catch {
        useAuthStore.getState().logout()
      }
    }
    
    return Promise.reject(error)
  }
)

// API helper functions - all return data directly (no need for .data in components)
export const projectsApi = {
  list: (params?: Record<string, unknown>) => api.get('/projects', { params }).then(res => res.data),
  get: (id: number) => api.get(`/projects/${id}`).then(res => res.data),
  getBySlug: (slug: string) => api.get(`/projects/slug/${slug}`).then(res => res.data),
  getMapMarkers: (params?: Record<string, unknown>) => api.get('/projects/map', { params }).then(res => res.data),
}

export const unitsApi = {
  listByProject: (projectId: number, params?: Record<string, unknown>) => 
    api.get(`/units/project/${projectId}`, { params }).then(res => res.data),
  get: (id: number) => api.get(`/units/${id}`).then(res => res.data),
  compare: (ids: number[]) => api.get('/units/compare', { params: { unit_ids: ids.join(',') } }).then(res => res.data),
}

export const collectionsApi = {
  list: (params?: Record<string, unknown>) => api.get('/collections', { params }).then(res => res.data),
  get: (id: number) => api.get(`/collections/${id}`).then(res => res.data),
  create: (data: unknown) => api.post('/collections', data).then(res => res.data),
  update: (id: number, data: unknown) => api.patch(`/collections/${id}`, data).then(res => res.data),
  delete: (id: number) => api.delete(`/collections/${id}`).then(res => res.data),
  addItem: (collectionId: number, data: unknown) => api.post(`/collections/${collectionId}/items`, data).then(res => res.data),
  removeItem: (collectionId: number, itemId: number) => api.delete(`/collections/${collectionId}/items/${itemId}`).then(res => res.data),
  getPublic: (token: string) => api.get(`/collections/share/${token}`).then(res => res.data),
  submitInquiry: (token: string, data: unknown) => api.post(`/collections/share/${token}/inquiry`, data).then(res => res.data),
}

export const locationsApi = {
  getCountries: () => api.get('/locations/countries').then(res => res.data),
  getCities: (countryId?: number) => api.get('/locations/cities', { params: { country_id: countryId } }).then(res => res.data),
  getDistricts: (cityId?: number) => api.get('/locations/districts', { params: { city_id: cityId } }).then(res => res.data),
  getInfrastructure: (params?: Record<string, unknown>) => api.get('/locations/infrastructure', { params }).then(res => res.data),
  getPoiTypes: () => api.get('/locations/poi-types').then(res => res.data),
}

export const searchApi = {
  quick: (q: string) => api.get('/search/quick', { params: { q } }).then(res => res.data),
  advanced: (filters: unknown, params?: Record<string, unknown>) => 
    api.post('/search/advanced', filters, { params }).then(res => res.data),
  suggestions: (q: string) => api.get('/search/suggestions', { params: { q } }).then(res => res.data),
}

export const analyticsApi = {
  dashboard: () => api.get('/analytics/dashboard').then(res => res.data),
  project: (projectId: number) => api.get(`/analytics/project/${projectId}`).then(res => res.data),
  parsingErrors: (params?: Record<string, unknown>) => api.get('/analytics/parsing-errors', { params }).then(res => res.data),
  exportUnits: (params?: Record<string, unknown>) => api.get('/analytics/export/units', { 
    params, 
    responseType: 'blob' 
  }),
}

export const pricesApi = {
  versions: (projectId: number, params?: Record<string, unknown>) => 
    api.get(`/prices/versions/project/${projectId}`, { params }).then(res => res.data),
  version: (id: number) => api.get(`/prices/versions/${id}`).then(res => res.data),
  review: (id: number, data: { approve: boolean; notes?: string }) => 
    api.post(`/prices/versions/${id}/review`, data).then(res => res.data),
  unitHistory: (unitId: number) => api.get(`/prices/history/unit/${unitId}`).then(res => res.data),
  projectHistory: (projectId: number) => api.get(`/prices/history/project/${projectId}`).then(res => res.data),
  paymentPlans: (projectId: number) => api.get(`/prices/payment-plans/project/${projectId}`).then(res => res.data),
  requiresReview: (params?: Record<string, unknown>) => api.get('/prices/requires-review', { params }).then(res => res.data),
}

export const filesApi = {
  upload: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/files/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }).then(res => res.data)
  },
  validate: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/files/validate', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }).then(res => res.data)
  },
  preview: (file: File, currency: string = 'THB') => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('currency', currency)
    return api.post('/files/preview', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }).then(res => res.data)
  },
  ingestPrice: (data: FormData) => api.post('/files/ingest-price', data, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }).then(res => res.data),
  ingestFromUrl: (data: {
    project_id: number;
    source_type: string;
    source_url: string;
    currency?: string;
    sheet_name?: string;
  }) => api.post('/files/ingest-from-url', data).then(res => res.data),
  getIngestionStatus: (versionId: number) => api.get(`/files/price-version/${versionId}/status`).then(res => res.data),
  retryProcessing: (versionId: number) => api.post(`/files/price-version/${versionId}/retry`).then(res => res.data),
}

export const notionApi = {
  testConnection: () => api.get('/notion/test-connection').then(res => res.data),
  getSchema: () => api.get('/notion/schema').then(res => res.data),
  getFieldMapping: () => api.get('/notion/field-mapping').then(res => res.data),
  syncAll: (dryRun: boolean = false) => api.post(`/notion/sync?dry_run=${dryRun}`).then(res => res.data),
  syncSingle: (pageId: string) => api.post(`/notion/sync/${pageId}`).then(res => res.data),
  getPriceFiles: () => api.get('/notion/price-files').then(res => res.data),
  preview: (limit: number = 5) => api.post(`/notion/preview?limit=${limit}`).then(res => res.data),
  getConfigStatus: () => api.get('/notion/config-status').then(res => res.data),
}

// Admin API - CRUD operations for admin panel
export const adminApi = {
  // Projects CRUD
  createProject: (data: unknown) => api.post('/admin/projects', data).then(res => res.data),
  updateProject: (id: number, data: unknown) => api.put(`/admin/projects/${id}`, data).then(res => res.data),
  deleteProject: (id: number) => api.delete(`/admin/projects/${id}`).then(res => res.data),
  
  // Units CRUD
  listUnits: (params?: Record<string, unknown>) => api.get('/admin/units', { params }).then(res => res.data),
  createUnit: (data: unknown) => api.post('/admin/units', data).then(res => res.data),
  updateUnit: (id: number, data: unknown) => api.put(`/admin/units/${id}`, data).then(res => res.data),
  deleteUnit: (id: number) => api.delete(`/admin/units/${id}`).then(res => res.data),
  
  // Media upload (Supabase Storage)
  uploadImage: (formData: FormData) => api.post('/admin/media/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }).then(res => res.data),
  
  deleteImage: (path: string) => api.delete('/admin/media', { params: { path } }).then(res => res.data),
  
  // Dashboard stats
  getStats: () => api.get('/admin/stats').then(res => res.data),
}

// Smart Parser API - Price parsing with learning
export const parserApi = {
  // Upload file and get column detection
  upload: (file: File, sheetName?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    const params = sheetName ? { sheet_name: sheetName } : {}
    return api.post('/parser/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      params
    }).then(res => res.data)
  },
  
  // Confirm or correct column mappings
  confirmMappings: (sessionId: string, mappings: Array<{
    column_index: number;
    field: string;
    approved: boolean;
    correct_field?: string;
  }>) => api.post('/parser/confirm-mapping', {
    session_id: sessionId,
    mappings
  }).then(res => res.data),
  
  // Parse data with confirmed mappings
  parse: (sessionId: string, projectId?: number, currency: string = 'THB') => 
    api.post('/parser/parse', {
      session_id: sessionId,
      project_id: projectId,
      currency
    }).then(res => res.data),
  
  // Get session status
  getSession: (sessionId: string) => 
    api.get(`/parser/session/${sessionId}`).then(res => res.data),
  
  // Delete session
  deleteSession: (sessionId: string) => 
    api.delete(`/parser/session/${sessionId}`).then(res => res.data),
  
  // Get learning statistics
  getLearningStats: () => api.get('/parser/learning-stats').then(res => res.data),
  
  // Get available fields for mapping
  getAvailableFields: () => api.get('/parser/available-fields').then(res => res.data),
  
  // Reset learning (admin only)
  resetLearning: () => api.post('/parser/reset-learning').then(res => res.data),
}
