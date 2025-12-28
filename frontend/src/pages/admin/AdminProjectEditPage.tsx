import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Save,
  ArrowLeft,
  Building2,
  MapPin,
  DollarSign,
  Image as ImageIcon,
  Trash2,
  Plus,
  Upload,
  X,
  AlertCircle,
  CheckCircle,
  Loader2,
  FileImage,
  Link as LinkIcon,
  Calendar,
  Home,
  Percent,
} from 'lucide-react'
import { useI18n } from '../../i18n'
import { projectsApi, locationsApi, adminApi } from '../../services/api'
import clsx from 'clsx'

// Interfaces
interface District {
  id: number
  name_en: string
  name_ru?: string
  slug: string
}

interface ProjectFormData {
  name_en: string
  name_ru: string
  slug: string
  description_en: string
  description_ru: string
  property_types: string[]
  status: string
  ownership_type: string
  leasehold_years?: number
  
  // Location
  district_id?: number
  address_en: string
  address_ru: string
  lat?: number
  lng?: number
  
  // Pricing
  min_price?: number
  max_price?: number
  min_price_per_sqm?: number
  original_currency: string
  
  // Units
  total_units: number
  available_units: number
  
  // Dates
  completion_date?: string
  completion_year?: number
  completion_quarter?: string
  
  // Media
  cover_image_url: string
  gallery: string[]
  video_url: string
  virtual_tour_url: string
  master_plan_url: string
  
  // Features
  amenities: string[]
  features: string[]
  
  // Status flags
  is_active: boolean
  is_featured: boolean
  is_verified: boolean
}

const initialFormData: ProjectFormData = {
  name_en: '',
  name_ru: '',
  slug: '',
  description_en: '',
  description_ru: '',
  property_types: [],
  status: 'under_construction',
  ownership_type: 'freehold',
  district_id: undefined,
  address_en: '',
  address_ru: '',
  min_price: undefined,
  max_price: undefined,
  min_price_per_sqm: undefined,
  original_currency: 'THB',
  total_units: 0,
  available_units: 0,
  cover_image_url: '',
  gallery: [],
  video_url: '',
  virtual_tour_url: '',
  master_plan_url: '',
  amenities: [],
  features: [],
  is_active: true,
  is_featured: false,
  is_verified: false,
}

const propertyTypeOptions = [
  { value: 'apartment', labelEn: 'Apartment', labelRu: 'Апартамент' },
  { value: 'villa', labelEn: 'Villa', labelRu: 'Вилла' },
  { value: 'townhouse', labelEn: 'Townhouse', labelRu: 'Таунхаус' },
  { value: 'penthouse', labelEn: 'Penthouse', labelRu: 'Пентхаус' },
  { value: 'studio', labelEn: 'Studio', labelRu: 'Студия' },
  { value: 'duplex', labelEn: 'Duplex', labelRu: 'Дуплекс' },
  { value: 'land', labelEn: 'Land', labelRu: 'Земля' },
]

const statusOptions = [
  { value: 'presale', labelEn: 'Presale', labelRu: 'Предпродажа' },
  { value: 'under_construction', labelEn: 'Under Construction', labelRu: 'Строится' },
  { value: 'ready', labelEn: 'Ready', labelRu: 'Готов' },
  { value: 'completed', labelEn: 'Completed', labelRu: 'Завершён' },
  { value: 'sold_out', labelEn: 'Sold Out', labelRu: 'Распродан' },
]

const ownershipOptions = [
  { value: 'freehold', labelEn: 'Freehold', labelRu: 'Собственность' },
  { value: 'leasehold', labelEn: 'Leasehold', labelRu: 'Аренда' },
  { value: 'mixed', labelEn: 'Mixed', labelRu: 'Смешанное' },
]

const currencies = ['THB', 'USD', 'EUR', 'RUB', 'IDR']

const amenityOptions = [
  'pool', 'gym', 'spa', 'restaurant', 'parking', 'security', 
  'concierge', 'beach_access', 'golf', 'tennis', 'kids_area',
  'coworking', 'rooftop', 'garden', 'sauna', 'jacuzzi'
]

export default function AdminProjectEditPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { language } = useI18n()
  const isNew = id === 'new'

  const [formData, setFormData] = useState<ProjectFormData>(initialFormData)
  const [activeTab, setActiveTab] = useState<'general' | 'location' | 'pricing' | 'media' | 'features'>('general')
  const [uploading, setUploading] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [successMessage, setSuccessMessage] = useState('')

  // Fetch project if editing
  const { data: project, isLoading: projectLoading } = useQuery({
    queryKey: ['admin-project', id],
    queryFn: () => projectsApi.get(Number(id)),
    enabled: !isNew && !!id,
  })

  // Fetch districts
  const { data: districts = [] } = useQuery<District[]>({
    queryKey: ['districts'],
    queryFn: () => locationsApi.getDistricts(),
  })

  // Load project data into form
  useEffect(() => {
    if (project && !isNew) {
      setFormData({
        name_en: project.name_en || '',
        name_ru: project.name_ru || '',
        slug: project.slug || '',
        description_en: project.description_en || '',
        description_ru: project.description_ru || '',
        property_types: project.property_types || [],
        status: project.status || 'under_construction',
        ownership_type: project.ownership_type || 'freehold',
        leasehold_years: project.leasehold_years,
        district_id: project.district_id,
        address_en: project.address_en || '',
        address_ru: project.address_ru || '',
        lat: project.lat,
        lng: project.lng,
        min_price: project.min_price,
        max_price: project.max_price,
        min_price_per_sqm: project.min_price_per_sqm,
        original_currency: project.original_currency || 'THB',
        total_units: project.total_units || 0,
        available_units: project.available_units || 0,
        completion_date: project.completion_date,
        completion_year: project.completion_year,
        completion_quarter: project.completion_quarter,
        cover_image_url: project.cover_image_url || '',
        gallery: project.gallery || [],
        video_url: project.video_url || '',
        virtual_tour_url: project.virtual_tour_url || '',
        master_plan_url: project.master_plan_url || '',
        amenities: project.amenities || [],
        features: project.features || [],
        is_active: project.is_active ?? true,
        is_featured: project.is_featured ?? false,
        is_verified: project.is_verified ?? false,
      })
    }
  }, [project, isNew])

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: async (data: ProjectFormData) => {
      if (isNew) {
        return adminApi.createProject(data)
      } else {
        return adminApi.updateProject(Number(id), data)
      }
    },
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['admin-projects'] })
      queryClient.invalidateQueries({ queryKey: ['admin-project', id] })
      setSuccessMessage(language === 'ru' ? 'Проект сохранён' : 'Project saved')
      
      if (isNew && result?.id) {
        navigate(`/admin/projects/${result.id}`)
      }
      
      setTimeout(() => setSuccessMessage(''), 3000)
    },
    onError: (error: any) => {
      setErrors({ submit: error.response?.data?.detail || 'Failed to save project' })
    },
  })

  // Generate slug from name
  const generateSlug = (name: string) => {
    return name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/(^-|-$)/g, '')
  }

  // Handle form changes
  const handleChange = (field: keyof ProjectFormData, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    
    // Auto-generate slug from name
    if (field === 'name_en' && (isNew || !formData.slug)) {
      setFormData(prev => ({ ...prev, slug: generateSlug(value) }))
    }
  }

  // Handle property types toggle
  const togglePropertyType = (type: string) => {
    setFormData(prev => ({
      ...prev,
      property_types: prev.property_types.includes(type)
        ? prev.property_types.filter(t => t !== type)
        : [...prev.property_types, type]
    }))
  }

  // Handle amenities toggle
  const toggleAmenity = (amenity: string) => {
    setFormData(prev => ({
      ...prev,
      amenities: prev.amenities.includes(amenity)
        ? prev.amenities.filter(a => a !== amenity)
        : [...prev.amenities, amenity]
    }))
  }

  // Handle image upload
  const handleImageUpload = async (files: FileList, field: 'cover_image_url' | 'gallery' | 'master_plan_url') => {
    setUploading(true)
    try {
      const uploadPromises = Array.from(files).map(async (file) => {
        const formData = new FormData()
        formData.append('file', file)
        const result = await adminApi.uploadImage(formData)
        return result.url
      })
      
      const urls = await Promise.all(uploadPromises)
      
      if (field === 'gallery') {
        setFormData(prev => ({
          ...prev,
          gallery: [...prev.gallery, ...urls]
        }))
      } else {
        setFormData(prev => ({
          ...prev,
          [field]: urls[0]
        }))
      }
    } catch (error) {
      console.error('Upload failed:', error)
      setErrors({ upload: language === 'ru' ? 'Ошибка загрузки' : 'Upload failed' })
    } finally {
      setUploading(false)
    }
  }

  // Remove gallery image
  const removeGalleryImage = (index: number) => {
    setFormData(prev => ({
      ...prev,
      gallery: prev.gallery.filter((_, i) => i !== index)
    }))
  }

  // Validate form
  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {}
    
    if (!formData.name_en.trim()) {
      newErrors.name_en = language === 'ru' ? 'Введите название' : 'Name is required'
    }
    if (!formData.slug.trim()) {
      newErrors.slug = language === 'ru' ? 'Введите slug' : 'Slug is required'
    }
    
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  // Handle save
  const handleSave = () => {
    if (validateForm()) {
      saveMutation.mutate(formData)
    }
  }

  if (projectLoading && !isNew) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    )
  }

  const tabs = [
    { id: 'general', labelEn: 'General', labelRu: 'Основное', icon: Building2 },
    { id: 'location', labelEn: 'Location', labelRu: 'Локация', icon: MapPin },
    { id: 'pricing', labelEn: 'Pricing', labelRu: 'Цены', icon: DollarSign },
    { id: 'media', labelEn: 'Media', labelRu: 'Медиа', icon: ImageIcon },
    { id: 'features', labelEn: 'Features', labelRu: 'Удобства', icon: Home },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            to="/admin/projects"
            className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {isNew 
                ? (language === 'ru' ? 'Новый проект' : 'New Project')
                : (language === 'ru' ? formData.name_ru || formData.name_en : formData.name_en)
              }
            </h1>
            {!isNew && formData.slug && (
              <p className="text-sm text-gray-500">/{formData.slug}</p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3">
          {successMessage && (
            <div className="flex items-center gap-2 text-green-600 bg-green-50 px-3 py-2 rounded-lg">
              <CheckCircle className="w-4 h-4" />
              {successMessage}
            </div>
          )}
          
          <button
            onClick={handleSave}
            disabled={saveMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {saveMutation.isPending ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Save className="w-5 h-5" />
            )}
            {language === 'ru' ? 'Сохранить' : 'Save'}
          </button>
        </div>
      </div>

      {/* Error message */}
      {errors.submit && (
        <div className="flex items-center gap-2 p-4 bg-red-50 text-red-700 rounded-lg">
          <AlertCircle className="w-5 h-5" />
          {errors.submit}
        </div>
      )}

      {/* Tabs */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200">
        <div className="border-b border-gray-200">
          <nav className="flex overflow-x-auto">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={clsx(
                  'flex items-center gap-2 px-6 py-4 text-sm font-medium border-b-2 whitespace-nowrap transition-colors',
                  activeTab === tab.id
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                )}
              >
                <tab.icon className="w-4 h-4" />
                {language === 'ru' ? tab.labelRu : tab.labelEn}
              </button>
            ))}
          </nav>
        </div>

        <div className="p-6">
          {/* General Tab */}
          {activeTab === 'general' && (
            <div className="space-y-6">
              {/* Names */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    {language === 'ru' ? 'Название (EN) *' : 'Name (EN) *'}
                  </label>
                  <input
                    type="text"
                    value={formData.name_en}
                    onChange={(e) => handleChange('name_en', e.target.value)}
                    className={clsx(
                      'w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                      errors.name_en ? 'border-red-500' : 'border-gray-300'
                    )}
                    placeholder="Project Name"
                  />
                  {errors.name_en && (
                    <p className="mt-1 text-sm text-red-500">{errors.name_en}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    {language === 'ru' ? 'Название (RU)' : 'Name (RU)'}
                  </label>
                  <input
                    type="text"
                    value={formData.name_ru}
                    onChange={(e) => handleChange('name_ru', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Название проекта"
                  />
                </div>
              </div>

              {/* Slug */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Slug *
                </label>
                <input
                  type="text"
                  value={formData.slug}
                  onChange={(e) => handleChange('slug', e.target.value)}
                  className={clsx(
                    'w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                    errors.slug ? 'border-red-500' : 'border-gray-300'
                  )}
                  placeholder="project-name"
                />
                {errors.slug && (
                  <p className="mt-1 text-sm text-red-500">{errors.slug}</p>
                )}
              </div>

              {/* Descriptions */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    {language === 'ru' ? 'Описание (EN)' : 'Description (EN)'}
                  </label>
                  <textarea
                    value={formData.description_en}
                    onChange={(e) => handleChange('description_en', e.target.value)}
                    rows={4}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Project description..."
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    {language === 'ru' ? 'Описание (RU)' : 'Description (RU)'}
                  </label>
                  <textarea
                    value={formData.description_ru}
                    onChange={(e) => handleChange('description_ru', e.target.value)}
                    rows={4}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Описание проекта..."
                  />
                </div>
              </div>

              {/* Property Types */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  {language === 'ru' ? 'Тип недвижимости' : 'Property Types'}
                </label>
                <div className="flex flex-wrap gap-2">
                  {propertyTypeOptions.map((type) => (
                    <button
                      key={type.value}
                      type="button"
                      onClick={() => togglePropertyType(type.value)}
                      className={clsx(
                        'px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
                        formData.property_types.includes(type.value)
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      )}
                    >
                      {language === 'ru' ? type.labelRu : type.labelEn}
                    </button>
                  ))}
                </div>
              </div>

              {/* Status & Ownership */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    {language === 'ru' ? 'Статус' : 'Status'}
                  </label>
                  <select
                    value={formData.status}
                    onChange={(e) => handleChange('status', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    {statusOptions.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {language === 'ru' ? opt.labelRu : opt.labelEn}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    {language === 'ru' ? 'Тип владения' : 'Ownership'}
                  </label>
                  <select
                    value={formData.ownership_type}
                    onChange={(e) => handleChange('ownership_type', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    {ownershipOptions.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {language === 'ru' ? opt.labelRu : opt.labelEn}
                      </option>
                    ))}
                  </select>
                </div>

                {formData.ownership_type === 'leasehold' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      {language === 'ru' ? 'Срок аренды (лет)' : 'Lease Years'}
                    </label>
                    <input
                      type="number"
                      value={formData.leasehold_years || ''}
                      onChange={(e) => handleChange('leasehold_years', Number(e.target.value) || undefined)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="30"
                    />
                  </div>
                )}
              </div>

              {/* Status Flags */}
              <div className="flex flex-wrap gap-6">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.is_active}
                    onChange={(e) => handleChange('is_active', e.target.checked)}
                    className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                  />
                  <span className="text-sm text-gray-700">
                    {language === 'ru' ? 'Активен' : 'Active'}
                  </span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.is_featured}
                    onChange={(e) => handleChange('is_featured', e.target.checked)}
                    className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                  />
                  <span className="text-sm text-gray-700">
                    {language === 'ru' ? 'Рекомендуемый' : 'Featured'}
                  </span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.is_verified}
                    onChange={(e) => handleChange('is_verified', e.target.checked)}
                    className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                  />
                  <span className="text-sm text-gray-700">
                    {language === 'ru' ? 'Проверен' : 'Verified'}
                  </span>
                </label>
              </div>
            </div>
          )}

          {/* Location Tab */}
          {activeTab === 'location' && (
            <div className="space-y-6">
              {/* District */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  {language === 'ru' ? 'Район' : 'District'}
                </label>
                <select
                  value={formData.district_id || ''}
                  onChange={(e) => handleChange('district_id', Number(e.target.value) || undefined)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">{language === 'ru' ? 'Выберите район' : 'Select district'}</option>
                  {districts.map((district: District) => (
                    <option key={district.id} value={district.id}>
                      {language === 'ru' ? district.name_ru || district.name_en : district.name_en}
                    </option>
                  ))}
                </select>
              </div>

              {/* Addresses */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    {language === 'ru' ? 'Адрес (EN)' : 'Address (EN)'}
                  </label>
                  <input
                    type="text"
                    value={formData.address_en}
                    onChange={(e) => handleChange('address_en', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="123 Beach Road, Phuket"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    {language === 'ru' ? 'Адрес (RU)' : 'Address (RU)'}
                  </label>
                  <input
                    type="text"
                    value={formData.address_ru}
                    onChange={(e) => handleChange('address_ru', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="123 Пляжная улица, Пхукет"
                  />
                </div>
              </div>

              {/* Coordinates */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    {language === 'ru' ? 'Широта (Latitude)' : 'Latitude'}
                  </label>
                  <input
                    type="number"
                    step="any"
                    value={formData.lat || ''}
                    onChange={(e) => handleChange('lat', Number(e.target.value) || undefined)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="7.8804"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    {language === 'ru' ? 'Долгота (Longitude)' : 'Longitude'}
                  </label>
                  <input
                    type="number"
                    step="any"
                    value={formData.lng || ''}
                    onChange={(e) => handleChange('lng', Number(e.target.value) || undefined)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="98.3923"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Pricing Tab */}
          {activeTab === 'pricing' && (
            <div className="space-y-6">
              {/* Currency */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  {language === 'ru' ? 'Валюта' : 'Currency'}
                </label>
                <select
                  value={formData.original_currency}
                  onChange={(e) => handleChange('original_currency', e.target.value)}
                  className="w-full max-w-xs px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  {currencies.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>

              {/* Price Range */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    {language === 'ru' ? 'Мин. цена' : 'Min Price'}
                  </label>
                  <input
                    type="number"
                    value={formData.min_price || ''}
                    onChange={(e) => handleChange('min_price', Number(e.target.value) || undefined)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="5,000,000"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    {language === 'ru' ? 'Макс. цена' : 'Max Price'}
                  </label>
                  <input
                    type="number"
                    value={formData.max_price || ''}
                    onChange={(e) => handleChange('max_price', Number(e.target.value) || undefined)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="15,000,000"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    {language === 'ru' ? 'Цена за м²' : 'Price per sqm'}
                  </label>
                  <input
                    type="number"
                    value={formData.min_price_per_sqm || ''}
                    onChange={(e) => handleChange('min_price_per_sqm', Number(e.target.value) || undefined)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="150,000"
                  />
                </div>
              </div>

              {/* Units */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    {language === 'ru' ? 'Всего юнитов' : 'Total Units'}
                  </label>
                  <input
                    type="number"
                    value={formData.total_units}
                    onChange={(e) => handleChange('total_units', Number(e.target.value) || 0)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="100"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    {language === 'ru' ? 'Доступно' : 'Available Units'}
                  </label>
                  <input
                    type="number"
                    value={formData.available_units}
                    onChange={(e) => handleChange('available_units', Number(e.target.value) || 0)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="50"
                  />
                </div>
              </div>

              {/* Completion Date */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    {language === 'ru' ? 'Год сдачи' : 'Completion Year'}
                  </label>
                  <input
                    type="number"
                    value={formData.completion_year || ''}
                    onChange={(e) => handleChange('completion_year', Number(e.target.value) || undefined)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="2025"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    {language === 'ru' ? 'Квартал' : 'Quarter'}
                  </label>
                  <select
                    value={formData.completion_quarter || ''}
                    onChange={(e) => handleChange('completion_quarter', e.target.value || undefined)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="">—</option>
                    <option value="Q1">Q1</option>
                    <option value="Q2">Q2</option>
                    <option value="Q3">Q3</option>
                    <option value="Q4">Q4</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    {language === 'ru' ? 'Дата сдачи' : 'Completion Date'}
                  </label>
                  <input
                    type="date"
                    value={formData.completion_date || ''}
                    onChange={(e) => handleChange('completion_date', e.target.value || undefined)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Media Tab */}
          {activeTab === 'media' && (
            <div className="space-y-6">
              {/* Cover Image */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  {language === 'ru' ? 'Обложка' : 'Cover Image'}
                </label>
                <div className="flex items-start gap-4">
                  {formData.cover_image_url ? (
                    <div className="relative w-48 h-32 rounded-lg overflow-hidden bg-gray-100">
                      <img
                        src={formData.cover_image_url}
                        alt="Cover"
                        className="w-full h-full object-cover"
                      />
                      <button
                        onClick={() => handleChange('cover_image_url', '')}
                        className="absolute top-2 right-2 p-1 bg-red-500 text-white rounded-full hover:bg-red-600"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ) : (
                    <label className="flex flex-col items-center justify-center w-48 h-32 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-blue-500 hover:bg-blue-50 transition-colors">
                      <Upload className="w-8 h-8 text-gray-400" />
                      <span className="mt-2 text-sm text-gray-500">
                        {language === 'ru' ? 'Загрузить' : 'Upload'}
                      </span>
                      <input
                        type="file"
                        accept="image/*"
                        className="hidden"
                        onChange={(e) => e.target.files && handleImageUpload(e.target.files, 'cover_image_url')}
                      />
                    </label>
                  )}
                  <div className="flex-1">
                    <input
                      type="text"
                      value={formData.cover_image_url}
                      onChange={(e) => handleChange('cover_image_url', e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="https://example.com/image.jpg"
                    />
                    <p className="mt-1 text-xs text-gray-500">
                      {language === 'ru' ? 'Или вставьте URL изображения' : 'Or paste image URL'}
                    </p>
                  </div>
                </div>
              </div>

              {/* Gallery */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  {language === 'ru' ? 'Галерея' : 'Gallery'}
                </label>
                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                  {formData.gallery.map((url, index) => (
                    <div key={index} className="relative aspect-square rounded-lg overflow-hidden bg-gray-100">
                      <img
                        src={url}
                        alt={`Gallery ${index + 1}`}
                        className="w-full h-full object-cover"
                      />
                      <button
                        onClick={() => removeGalleryImage(index)}
                        className="absolute top-2 right-2 p-1 bg-red-500 text-white rounded-full hover:bg-red-600"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                  <label className="aspect-square flex flex-col items-center justify-center border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-blue-500 hover:bg-blue-50 transition-colors">
                    <Plus className="w-8 h-8 text-gray-400" />
                    <span className="mt-1 text-xs text-gray-500">
                      {language === 'ru' ? 'Добавить' : 'Add'}
                    </span>
                    <input
                      type="file"
                      accept="image/*"
                      multiple
                      className="hidden"
                      onChange={(e) => e.target.files && handleImageUpload(e.target.files, 'gallery')}
                    />
                  </label>
                </div>
              </div>

              {/* Video & Links */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    <LinkIcon className="w-4 h-4 inline mr-1" />
                    {language === 'ru' ? 'Видео (YouTube/Vimeo)' : 'Video URL'}
                  </label>
                  <input
                    type="text"
                    value={formData.video_url}
                    onChange={(e) => handleChange('video_url', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="https://youtube.com/watch?v=..."
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    <LinkIcon className="w-4 h-4 inline mr-1" />
                    {language === 'ru' ? 'Виртуальный тур' : 'Virtual Tour URL'}
                  </label>
                  <input
                    type="text"
                    value={formData.virtual_tour_url}
                    onChange={(e) => handleChange('virtual_tour_url', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="https://my.matterport.com/..."
                  />
                </div>
              </div>

              {/* Master Plan */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  {language === 'ru' ? 'Мастер-план' : 'Master Plan'}
                </label>
                <div className="flex items-start gap-4">
                  {formData.master_plan_url ? (
                    <div className="relative w-48 h-32 rounded-lg overflow-hidden bg-gray-100">
                      <img
                        src={formData.master_plan_url}
                        alt="Master Plan"
                        className="w-full h-full object-cover"
                      />
                      <button
                        onClick={() => handleChange('master_plan_url', '')}
                        className="absolute top-2 right-2 p-1 bg-red-500 text-white rounded-full hover:bg-red-600"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ) : (
                    <label className="flex flex-col items-center justify-center w-48 h-32 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-blue-500 hover:bg-blue-50 transition-colors">
                      <FileImage className="w-8 h-8 text-gray-400" />
                      <span className="mt-2 text-sm text-gray-500">
                        {language === 'ru' ? 'Загрузить' : 'Upload'}
                      </span>
                      <input
                        type="file"
                        accept="image/*"
                        className="hidden"
                        onChange={(e) => e.target.files && handleImageUpload(e.target.files, 'master_plan_url')}
                      />
                    </label>
                  )}
                  <input
                    type="text"
                    value={formData.master_plan_url}
                    onChange={(e) => handleChange('master_plan_url', e.target.value)}
                    className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="https://example.com/master-plan.jpg"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Features Tab */}
          {activeTab === 'features' && (
            <div className="space-y-6">
              {/* Amenities */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  {language === 'ru' ? 'Удобства' : 'Amenities'}
                </label>
                <div className="flex flex-wrap gap-2">
                  {amenityOptions.map((amenity) => (
                    <button
                      key={amenity}
                      type="button"
                      onClick={() => toggleAmenity(amenity)}
                      className={clsx(
                        'px-3 py-1.5 rounded-lg text-sm font-medium transition-colors capitalize',
                        formData.amenities.includes(amenity)
                          ? 'bg-green-600 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      )}
                    >
                      {amenity.replace(/_/g, ' ')}
                    </button>
                  ))}
                </div>
              </div>

              {/* Custom Features */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  {language === 'ru' ? 'Дополнительные особенности' : 'Additional Features'}
                </label>
                <div className="space-y-2">
                  {formData.features.map((feature, index) => (
                    <div key={index} className="flex items-center gap-2">
                      <input
                        type="text"
                        value={feature}
                        onChange={(e) => {
                          const newFeatures = [...formData.features]
                          newFeatures[index] = e.target.value
                          handleChange('features', newFeatures)
                        }}
                        className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      />
                      <button
                        onClick={() => handleChange('features', formData.features.filter((_, i) => i !== index))}
                        className="p-2 text-red-500 hover:bg-red-50 rounded-lg"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                  <button
                    type="button"
                    onClick={() => handleChange('features', [...formData.features, ''])}
                    className="flex items-center gap-2 px-4 py-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                  >
                    <Plus className="w-4 h-4" />
                    {language === 'ru' ? 'Добавить особенность' : 'Add Feature'}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
