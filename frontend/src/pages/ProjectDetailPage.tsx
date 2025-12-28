import { useState, useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { projectsApi, unitsApi, collectionsApi } from '../services/api'
import { useI18n } from '../i18n'
import {
  ArrowLeft,
  MapPin,
  Calendar,
  Building2,
  Home,
  Plus,
  Loader2,
  Filter,
  ChevronDown,
  ChevronUp,
  X,
  Folder,
  Check,
  Play,
  ExternalLink,
} from 'lucide-react'
import clsx from 'clsx'
import type { Unit } from '../types'

interface Collection {
  id: number
  name: string
  items_count: number
}

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>()
  const projectId = Number(id)
  const { t, lang, formatPrice } = useI18n()
  const queryClient = useQueryClient()

  // Unit filters state
  const [showFilters, setShowFilters] = useState(false)
  const [filters, setFilters] = useState({
    priceMin: '',
    priceMax: '',
    areaMin: '',
    areaMax: '',
    floorMin: '',
    floorMax: '',
    bedrooms: null as number | null,
    status: '' as string,
    viewType: '' as string,
  })
  const [sortBy, setSortBy] = useState<'price_asc' | 'price_desc' | 'area_asc' | 'area_desc' | 'floor_asc'>('price_asc')

  // Add to collection modal
  const [showCollectionModal, setShowCollectionModal] = useState(false)
  const [selectedUnitId, setSelectedUnitId] = useState<number | null>(null)
  const [selectedUnitIds, setSelectedUnitIds] = useState<number[]>([])

  // Gallery state
  const [activeImage, setActiveImage] = useState(0)

  // Fetch project
  const { data: project, isLoading: projectLoading } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId),
    enabled: !!projectId,
  })

  // Fetch units
  const { data: unitsData, isLoading: unitsLoading } = useQuery({
    queryKey: ['units', projectId],
    queryFn: () => unitsApi.listByProject(projectId, { page_size: 500 }),
    enabled: !!projectId,
  })

  // Fetch user collections
  const { data: collectionsData } = useQuery({
    queryKey: ['collections-list'],
    queryFn: () => collectionsApi.list({ page_size: 100 }),
  })

  const allUnits: Unit[] = unitsData?.items || []
  const collections: Collection[] = collectionsData?.items || []

  // Get unique values for filters
  const filterOptions = useMemo(() => {
    const statuses = [...new Set(allUnits.map((u) => u.status).filter(Boolean))]
    const viewTypes = [...new Set(allUnits.map((u) => u.view_type).filter(Boolean))]
    const bedrooms = [...new Set(allUnits.map((u) => u.bedrooms).filter((b) => b !== null))].sort((a, b) => a - b)
    return { statuses, viewTypes, bedrooms }
  }, [allUnits])

  // Filter and sort units
  const filteredUnits = useMemo(() => {
    let result = [...allUnits]

    // Apply filters
    if (filters.priceMin) {
      result = result.filter((u) => u.price_usd && u.price_usd >= Number(filters.priceMin))
    }
    if (filters.priceMax) {
      result = result.filter((u) => u.price_usd && u.price_usd <= Number(filters.priceMax))
    }
    if (filters.areaMin) {
      result = result.filter((u) => u.area_sqm && u.area_sqm >= Number(filters.areaMin))
    }
    if (filters.areaMax) {
      result = result.filter((u) => u.area_sqm && u.area_sqm <= Number(filters.areaMax))
    }
    if (filters.floorMin) {
      result = result.filter((u) => u.floor && u.floor >= Number(filters.floorMin))
    }
    if (filters.floorMax) {
      result = result.filter((u) => u.floor && u.floor <= Number(filters.floorMax))
    }
    if (filters.bedrooms !== null) {
      result = result.filter((u) => u.bedrooms === filters.bedrooms)
    }
    if (filters.status) {
      result = result.filter((u) => u.status === filters.status)
    }
    if (filters.viewType) {
      result = result.filter((u) => u.view_type === filters.viewType)
    }

    // Sort
    switch (sortBy) {
      case 'price_asc':
        result.sort((a, b) => (a.price_usd || 0) - (b.price_usd || 0))
        break
      case 'price_desc':
        result.sort((a, b) => (b.price_usd || 0) - (a.price_usd || 0))
        break
      case 'area_asc':
        result.sort((a, b) => (a.area_sqm || 0) - (b.area_sqm || 0))
        break
      case 'area_desc':
        result.sort((a, b) => (b.area_sqm || 0) - (a.area_sqm || 0))
        break
      case 'floor_asc':
        result.sort((a, b) => (a.floor || 0) - (b.floor || 0))
        break
    }

    return result
  }, [allUnits, filters, sortBy])

  const activeFiltersCount = Object.values(filters).filter((v) => v !== '' && v !== null).length

  const resetFilters = () => {
    setFilters({
      priceMin: '',
      priceMax: '',
      areaMin: '',
      areaMax: '',
      floorMin: '',
      floorMax: '',
      bedrooms: null,
      status: '',
      viewType: '',
    })
  }

  const handleAddToCollection = (unitId: number) => {
    setSelectedUnitId(unitId)
    setShowCollectionModal(true)
  }

  const toggleUnitSelection = (unitId: number) => {
    setSelectedUnitIds((prev) =>
      prev.includes(unitId) ? prev.filter((id) => id !== unitId) : [...prev, unitId]
    )
  }

  const handleBulkAddToCollection = () => {
    if (selectedUnitIds.length === 0) return
    setSelectedUnitId(null)
    setShowCollectionModal(true)
  }

  if (projectLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    )
  }

  if (!project) {
    return (
      <div className="text-center py-12">
        <Building2 className="w-12 h-12 text-gray-300 mx-auto mb-4" />
        <p className="text-gray-500">{t('projects.noProjects')}</p>
      </div>
    )
  }

  const gallery = project.gallery || []
  const projectName = lang === 'ru' ? (project.name_ru || project.name_en) : (project.name_en || project.name_ru)
  const description = lang === 'ru' ? (project.description_ru || project.description_en) : (project.description_en || project.description_ru)

  return (
    <div>
      {/* Back link */}
      <Link to="/projects" className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 mb-4">
        <ArrowLeft className="w-4 h-4" />
        {t('projects.backToList')}
      </Link>

      {/* Header card with gallery */}
      <div className="card overflow-hidden mb-6">
        {/* Gallery */}
        <div className="relative">
          <div className="aspect-[21/9] bg-gray-100 relative">
            {project.cover_image_url || gallery.length > 0 ? (
              <img
                src={gallery[activeImage] || project.cover_image_url}
                alt={projectName}
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <Building2 className="w-16 h-16 text-gray-300" />
              </div>
            )}
            
            {/* Video/Tour buttons */}
            <div className="absolute bottom-4 right-4 flex gap-2">
              {project.video_url && (
                <a
                  href={project.video_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 px-3 py-2 bg-black/70 text-white rounded-lg hover:bg-black/80 transition-colors text-sm"
                >
                  <Play className="w-4 h-4" />
                  Video
                </a>
              )}
              {project.virtual_tour_url && (
                <a
                  href={project.virtual_tour_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 px-3 py-2 bg-black/70 text-white rounded-lg hover:bg-black/80 transition-colors text-sm"
                >
                  <ExternalLink className="w-4 h-4" />
                  3D Tour
                </a>
              )}
            </div>
          </div>

          {/* Gallery thumbnails */}
          {gallery.length > 1 && (
            <div className="flex gap-2 p-2 bg-gray-100 overflow-x-auto">
              {gallery.map((img, idx) => (
                <button
                  key={idx}
                  onClick={() => setActiveImage(idx)}
                  className={clsx(
                    'w-20 h-14 rounded overflow-hidden flex-shrink-0 transition-all',
                    activeImage === idx ? 'ring-2 ring-primary-500' : 'opacity-70 hover:opacity-100'
                  )}
                >
                  <img src={img} alt="" className="w-full h-full object-cover" />
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Project info */}
        <div className="p-6">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{projectName}</h1>
              {project.developer && (
                <p className="text-gray-600 mt-1">
                  {t('projects.developer')}: {lang === 'ru' 
                    ? (project.developer.name_ru || project.developer.name_en)
                    : (project.developer.name_en || project.developer.name_ru)}
                </p>
              )}

              <div className="flex flex-wrap items-center gap-3 mt-4 text-sm text-gray-600">
                {project.district && (
                  <span className="flex items-center gap-1">
                    <MapPin className="w-4 h-4" />
                    {lang === 'ru' ? (project.district.name_ru || project.district.name_en) : project.district.name_en}
                  </span>
                )}
                {project.completion_quarter && (
                  <span className="flex items-center gap-1">
                    <Calendar className="w-4 h-4" />
                    {project.completion_quarter}
                  </span>
                )}
                <span className="badge-gray">{project.status}</span>
                <span className="badge-gray">{project.ownership_type}</span>
              </div>
            </div>

            <div className="text-right">
              <div className="text-2xl font-bold text-primary-600">
                {formatPrice(project.min_price_usd)}
                {project.max_price_usd && project.min_price_usd !== project.max_price_usd && (
                  <span className="text-lg text-gray-400 font-normal">
                    {' - '}
                    {formatPrice(project.max_price_usd)}
                  </span>
                )}
              </div>
              <p className="text-sm text-gray-500 mt-1">
                {project.available_units} / {project.total_units} {t('common.units')}
              </p>
              {project.min_price_per_sqm_usd && (
                <p className="text-sm text-gray-500">
                  {t('projects.pricePerSqm')}: {formatPrice(project.min_price_per_sqm_usd)}/{t('common.sqm')}
                </p>
              )}
            </div>
          </div>

          {/* Description */}
          {description && (
            <div className="mt-6 pt-6 border-t border-gray-200">
              <h3 className="font-semibold text-gray-900 mb-2">{t('projects.description')}</h3>
              <p className="text-gray-600 whitespace-pre-line">{description}</p>
            </div>
          )}

          {/* Amenities */}
          {project.amenities && project.amenities.length > 0 && (
            <div className="mt-6 pt-6 border-t border-gray-200">
              <h3 className="font-semibold text-gray-900 mb-3">{t('projects.amenities')}</h3>
              <div className="flex flex-wrap gap-2">
                {project.amenities.map((amenity) => (
                  <span key={amenity} className="badge-gray">
                    {amenity}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Units section */}
      <div className="card p-6">
        {/* Units header */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">{t('units.title')}</h2>
            <p className="text-sm text-gray-500 mt-1">
              {t('units.showing', { count: filteredUnits.length, total: allUnits.length })}
            </p>
          </div>

          <div className="flex items-center gap-3">
            {/* Bulk add button */}
            {selectedUnitIds.length > 0 && (
              <button
                onClick={handleBulkAddToCollection}
                className="btn-primary"
              >
                <Plus className="w-4 h-4 mr-2" />
                {t('units.addToCollection')} ({selectedUnitIds.length})
              </button>
            )}

            {/* Sort */}
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
              className="input py-2 text-sm w-auto"
            >
              <option value="price_asc">{t('common.price')} ↑</option>
              <option value="price_desc">{t('common.price')} ↓</option>
              <option value="area_asc">{t('common.area')} ↑</option>
              <option value="area_desc">{t('common.area')} ↓</option>
              <option value="floor_asc">{t('common.floor')} ↑</option>
            </select>

            {/* Filters toggle */}
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={clsx(
                'btn-secondary',
                activeFiltersCount > 0 && 'ring-2 ring-primary-300'
              )}
            >
              <Filter className="w-4 h-4 mr-2" />
              {t('common.filters')}
              {activeFiltersCount > 0 && (
                <span className="ml-2 px-1.5 py-0.5 bg-primary-100 text-primary-700 text-xs rounded">
                  {activeFiltersCount}
                </span>
              )}
              {showFilters ? <ChevronUp className="w-4 h-4 ml-2" /> : <ChevronDown className="w-4 h-4 ml-2" />}
            </button>
          </div>
        </div>

        {/* Filters panel */}
        {showFilters && (
          <div className="mb-6 p-4 bg-gray-50 rounded-lg">
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {/* Price */}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">{t('units.filters.priceRange')}</label>
                <div className="flex gap-1">
                  <input
                    type="number"
                    placeholder={t('common.from')}
                    value={filters.priceMin}
                    onChange={(e) => setFilters({ ...filters, priceMin: e.target.value })}
                    className="input py-1 text-sm"
                  />
                  <input
                    type="number"
                    placeholder={t('common.to')}
                    value={filters.priceMax}
                    onChange={(e) => setFilters({ ...filters, priceMax: e.target.value })}
                    className="input py-1 text-sm"
                  />
                </div>
              </div>

              {/* Area */}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">{t('units.filters.areaRange')}</label>
                <div className="flex gap-1">
                  <input
                    type="number"
                    placeholder={t('common.from')}
                    value={filters.areaMin}
                    onChange={(e) => setFilters({ ...filters, areaMin: e.target.value })}
                    className="input py-1 text-sm"
                  />
                  <input
                    type="number"
                    placeholder={t('common.to')}
                    value={filters.areaMax}
                    onChange={(e) => setFilters({ ...filters, areaMax: e.target.value })}
                    className="input py-1 text-sm"
                  />
                </div>
              </div>

              {/* Floor */}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">{t('units.filters.floorRange')}</label>
                <div className="flex gap-1">
                  <input
                    type="number"
                    placeholder={t('common.from')}
                    value={filters.floorMin}
                    onChange={(e) => setFilters({ ...filters, floorMin: e.target.value })}
                    className="input py-1 text-sm"
                  />
                  <input
                    type="number"
                    placeholder={t('common.to')}
                    value={filters.floorMax}
                    onChange={(e) => setFilters({ ...filters, floorMax: e.target.value })}
                    className="input py-1 text-sm"
                  />
                </div>
              </div>

              {/* Bedrooms */}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">{t('common.bedrooms')}</label>
                <select
                  value={filters.bedrooms ?? ''}
                  onChange={(e) => setFilters({ ...filters, bedrooms: e.target.value ? Number(e.target.value) : null })}
                  className="input py-1 text-sm"
                >
                  <option value="">{t('common.all')}</option>
                  {filterOptions.bedrooms.map((b) => (
                    <option key={b} value={b}>{b} BR</option>
                  ))}
                </select>
              </div>

              {/* Status */}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">{t('common.status')}</label>
                <select
                  value={filters.status}
                  onChange={(e) => setFilters({ ...filters, status: e.target.value })}
                  className="input py-1 text-sm"
                >
                  <option value="">{t('common.all')}</option>
                  {filterOptions.statuses.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>

              {/* View Type */}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">{t('units.filters.viewType')}</label>
                <select
                  value={filters.viewType}
                  onChange={(e) => setFilters({ ...filters, viewType: e.target.value })}
                  className="input py-1 text-sm"
                >
                  <option value="">{t('common.all')}</option>
                  {filterOptions.viewTypes.map((v) => (
                    <option key={v} value={v}>{v}</option>
                  ))}
                </select>
              </div>
            </div>

            {activeFiltersCount > 0 && (
              <button onClick={resetFilters} className="mt-3 text-sm text-primary-600 hover:text-primary-700">
                {t('common.cancel')} {t('common.filters').toLowerCase()}
              </button>
            )}
          </div>
        )}

        {/* Units table */}
        {unitsLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-primary-600" />
          </div>
        ) : filteredUnits.length === 0 ? (
          <div className="text-center py-12">
            <Home className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">{t('units.noUnits')}</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-2 w-8">
                    <input
                      type="checkbox"
                      checked={selectedUnitIds.length === filteredUnits.length && filteredUnits.length > 0}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedUnitIds(filteredUnits.map((u) => u.id))
                        } else {
                          setSelectedUnitIds([])
                        }
                      }}
                      className="rounded border-gray-300 text-primary-600"
                    />
                  </th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">{t('units.unitNumber')}</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">{t('units.type')}</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">{t('common.area')}</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">{t('common.floor')}</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">{t('common.view')}</th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-gray-500">{t('common.price')}</th>
                  <th className="text-center py-3 px-4 text-sm font-medium text-gray-500">{t('common.status')}</th>
                  <th className="text-center py-3 px-4 text-sm font-medium text-gray-500 w-12"></th>
                </tr>
              </thead>
              <tbody>
                {filteredUnits.map((unit) => (
                  <tr 
                    key={unit.id} 
                    className={clsx(
                      'border-b border-gray-100 hover:bg-gray-50',
                      selectedUnitIds.includes(unit.id) && 'bg-primary-50'
                    )}
                  >
                    <td className="py-3 px-2">
                      <input
                        type="checkbox"
                        checked={selectedUnitIds.includes(unit.id)}
                        onChange={() => toggleUnitSelection(unit.id)}
                        className="rounded border-gray-300 text-primary-600"
                      />
                    </td>
                    <td className="py-3 px-4">
                      <span className="font-medium text-gray-900">{unit.unit_number}</span>
                    </td>
                    <td className="py-3 px-4">
                      <span className="text-gray-600">{unit.bedrooms} BR</span>
                    </td>
                    <td className="py-3 px-4">
                      <span className="text-gray-600">{unit.area_sqm} {t('common.sqm')}</span>
                    </td>
                    <td className="py-3 px-4">
                      <span className="text-gray-600">{unit.floor || '-'}</span>
                    </td>
                    <td className="py-3 px-4">
                      <span className="text-gray-600">{unit.view_type || '-'}</span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="font-medium text-gray-900">
                        {formatPrice(unit.price_usd)}
                      </div>
                      {unit.price_change_percent && (
                        <div
                          className={clsx(
                            'text-xs',
                            unit.price_change_percent > 0 ? 'text-red-600' : 'text-green-600'
                          )}
                        >
                          {unit.price_change_percent > 0 ? '+' : ''}
                          {unit.price_change_percent.toFixed(1)}%
                        </div>
                      )}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span
                        className={clsx(
                          'badge',
                          unit.status === 'available'
                            ? 'badge-success'
                            : unit.status === 'reserved'
                              ? 'badge-warning'
                              : 'badge-gray'
                        )}
                      >
                        {unit.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <button
                        onClick={() => handleAddToCollection(unit.id)}
                        className="p-1.5 text-gray-400 hover:text-primary-600 hover:bg-primary-50 rounded-lg transition-colors"
                        title={t('units.addToCollection')}
                      >
                        <Plus className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Add to Collection Modal */}
      {showCollectionModal && (
        <AddToCollectionModal
          unitIds={selectedUnitId ? [selectedUnitId] : selectedUnitIds}
          projectId={projectId}
          collections={collections}
          onClose={() => {
            setShowCollectionModal(false)
            setSelectedUnitId(null)
          }}
          onSuccess={() => {
            setShowCollectionModal(false)
            setSelectedUnitId(null)
            setSelectedUnitIds([])
          }}
        />
      )}
    </div>
  )
}

function AddToCollectionModal({
  unitIds,
  projectId,
  collections,
  onClose,
  onSuccess,
}: {
  unitIds: number[]
  projectId: number
  collections: Collection[]
  onClose: () => void
  onSuccess: () => void
}) {
  const { t } = useI18n()
  const queryClient = useQueryClient()
  const [selectedCollectionId, setSelectedCollectionId] = useState<number | null>(null)
  const [createNew, setCreateNew] = useState(false)
  const [newCollectionName, setNewCollectionName] = useState('')
  const [notes, setNotes] = useState('')

  // Create collection mutation
  const createMutation = useMutation({
    mutationFn: (name: string) => collectionsApi.create({ name, is_public: false }),
    onSuccess: async (response) => {
      const newCollectionId = response.data.id
      await addItemsToCollection(newCollectionId)
    },
  })

  // Add items mutation
  const addItemsMutation = useMutation({
    mutationFn: async (collectionId: number) => {
      for (const unitId of unitIds) {
        await collectionsApi.addItem(collectionId, {
          unit_id: unitId,
          project_id: projectId,
          notes: notes || undefined,
        })
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['collections'] })
      queryClient.invalidateQueries({ queryKey: ['collection'] })
      onSuccess()
    },
  })

  const addItemsToCollection = async (collectionId: number) => {
    addItemsMutation.mutate(collectionId)
  }

  const handleSubmit = () => {
    if (createNew && newCollectionName) {
      createMutation.mutate(newCollectionName)
    } else if (selectedCollectionId) {
      addItemsToCollection(selectedCollectionId)
    }
  }

  const isLoading = createMutation.isPending || addItemsMutation.isPending

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl max-w-md w-full">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">
            {t('units.addToCollection')}
          </h2>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-4">
          <p className="text-sm text-gray-600">
            Adding {unitIds.length} {unitIds.length === 1 ? 'unit' : 'units'}
          </p>

          {/* Existing collections */}
          {collections.length > 0 && !createNew && (
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700">
                Select collection
              </label>
              {collections.map((collection) => (
                <label
                  key={collection.id}
                  className={clsx(
                    'flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors',
                    selectedCollectionId === collection.id
                      ? 'border-primary-500 bg-primary-50'
                      : 'border-gray-200 hover:bg-gray-50'
                  )}
                >
                  <input
                    type="radio"
                    name="collection"
                    checked={selectedCollectionId === collection.id}
                    onChange={() => setSelectedCollectionId(collection.id)}
                    className="text-primary-600"
                  />
                  <Folder className="w-5 h-5 text-gray-400" />
                  <div className="flex-1">
                    <p className="font-medium text-gray-900">{collection.name}</p>
                    <p className="text-xs text-gray-500">{collection.items_count} items</p>
                  </div>
                </label>
              ))}
            </div>
          )}

          {/* Create new toggle */}
          <button
            type="button"
            onClick={() => {
              setCreateNew(!createNew)
              setSelectedCollectionId(null)
            }}
            className="text-sm text-primary-600 hover:text-primary-700"
          >
            {createNew ? '← Choose existing' : '+ Create new collection'}
          </button>

          {/* Create new form */}
          {createNew && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Collection name
              </label>
              <input
                type="text"
                value={newCollectionName}
                onChange={(e) => setNewCollectionName(e.target.value)}
                className="input"
                placeholder="e.g., Villas for John"
              />
            </div>
          )}

          {/* Notes */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Notes (optional)
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="input"
              rows={2}
              placeholder="Add notes about these units..."
            />
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200">
          <button onClick={onClose} className="btn-secondary">
            {t('common.cancel')}
          </button>
          <button
            onClick={handleSubmit}
            disabled={isLoading || (!selectedCollectionId && (!createNew || !newCollectionName))}
            className="btn-primary"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>
                <Check className="w-4 h-4 mr-2" />
                Add
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
