import { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { collectionsApi, projectsApi } from '../services/api'
import {
  ArrowLeft,
  Share2,
  Copy,
  ExternalLink,
  Trash2,
  Plus,
  Building2,
  MapPin,
  DollarSign,
  X,
  Loader2,
  Search,
  FileDown,
} from 'lucide-react'
import clsx from 'clsx'
interface CollectionItem {
  id: number
  unit_id?: number
  project_id: number
  sort_order: number
  notes?: string
  unit?: {
    id: number
    unit_number: string
    bedrooms: number
    area_sqm: number
    price_usd: number
    status: string
    floor?: number
    view_type?: string
  }
  project?: {
    id: number
    name_en?: string
    name_ru?: string
    cover_image_url?: string
    district?: {
      name_en?: string
    }
    min_price_usd?: number
  }
}
interface Collection {
  id: number
  name: string
  description?: string
  share_token: string
  is_public: boolean
  client_name?: string
  client_email?: string
  client_phone?: string
  items: CollectionItem[]
  created_at: string
  updated_at: string
}
export default function CollectionDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const collectionId = Number(id)
  const [showAddModal, setShowAddModal] = useState(false)
  // Fetch collection
  const { data: collection, isLoading } = useQuery({
    queryKey: ['collection', collectionId],
    queryFn: () => collectionsApi.get(collectionId),
    enabled: !!collectionId,
  })
  // Delete item mutation
  const removeItemMutation = useMutation({
    mutationFn: (itemId: number) => collectionsApi.removeItem(collectionId, itemId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['collection', collectionId] })
    },
  })
  // Delete collection mutation
  const deleteCollectionMutation = useMutation({
    mutationFn: () => collectionsApi.delete(collectionId),
    onSuccess: () => {
      navigate('/collections')
    },
  })
  const handleCopyLink = () => {
    if (!collection) return
    const url = `${window.location.origin}/c/${collection.share_token}`
    navigator.clipboard.writeText(url)
    alert('Link copied to clipboard!')
  }
  const handleDelete = () => {
    if (confirm('Are you sure you want to delete this collection?')) {
      deleteCollectionMutation.mutate()
    }
  }
  const handleRemoveItem = (itemId: number) => {
    if (confirm('Remove this item from collection?')) {
      removeItemMutation.mutate(itemId)
    }
  }
  const handleDownloadPdf = () => {
    // TODO: Implement PDF generation
    alert('PDF generation coming soon!')
  }
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    )
  }
  if (!collection) {
    return (
      <div className="text-center py-12">
        <Building2 className="w-12 h-12 text-gray-300 mx-auto mb-4" />
        <p className="text-gray-500">Collection not found</p>
      </div>
    )
  }
  const items: CollectionItem[] = collection.items || []
  return (
    <div>
      {/* Back link */}
      <Link to="/collections" className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 mb-4">
        <ArrowLeft className="w-4 h-4" />
        Back to Collections
      </Link>
      {/* Header */}
      <div className="card p-6 mb-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{collection.name}</h1>
            {collection.description && (
              <p className="text-gray-600 mt-2">{collection.description}</p>
            )}
            
            {/* Client info */}
            {(collection.client_name || collection.client_email || collection.client_phone) && (
              <div className="mt-4 pt-4 border-t border-gray-200">
                <h3 className="text-sm font-medium text-gray-700 mb-2">Client</h3>
                <div className="text-sm text-gray-600 space-y-1">
                  {collection.client_name && <p>{collection.client_name}</p>}
                  {collection.client_email && <p>{collection.client_email}</p>}
                  {collection.client_phone && <p>{collection.client_phone}</p>}
                </div>
              </div>
            )}
          </div>
          {/* Actions */}
          <div className="flex items-center gap-2">
            <button
              onClick={handleCopyLink}
              className="btn-secondary"
              title="Copy share link"
            >
              <Copy className="w-4 h-4 mr-2" />
              Copy Link
            </button>
            <a
              href={`/c/${collection.share_token}`}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-secondary"
              title="Preview public page"
            >
              <ExternalLink className="w-4 h-4 mr-2" />
              Preview
            </a>
            <button
              onClick={handleDownloadPdf}
              className="btn-secondary"
              title="Download PDF"
            >
              <FileDown className="w-4 h-4" />
            </button>
            <button
              onClick={handleDelete}
              className="btn-secondary text-red-600 hover:bg-red-50"
              title="Delete collection"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>
        {/* Stats */}
        <div className="flex items-center gap-6 mt-6 pt-4 border-t border-gray-200 text-sm text-gray-500">
          <span>{items.length} items</span>
          <span>
            Created {new Date(collection.created_at).toLocaleDateString()}
          </span>
          <span>
            Updated {new Date(collection.updated_at).toLocaleDateString()}
          </span>
          {collection.is_public ? (
            <span className="badge-success flex items-center gap-1">
              <Share2 className="w-3 h-3" />
              Public
            </span>
          ) : (
            <span className="badge-gray">Private</span>
          )}
        </div>
      </div>
      {/* Items */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Collection Items</h2>
        <button onClick={() => setShowAddModal(true)} className="btn-primary">
          <Plus className="w-4 h-4 mr-2" />
          Add Items
        </button>
      </div>
      {items.length === 0 ? (
        <div className="card p-12 text-center">
          <Building2 className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No items yet</h3>
          <p className="text-gray-500 mb-6">
            Add projects or units to this collection
          </p>
          <button onClick={() => setShowAddModal(true)} className="btn-primary">
            <Plus className="w-4 h-4 mr-2" />
            Add Items
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map((item) => (
            <CollectionItemCard
              key={item.id}
              item={item}
              onRemove={() => handleRemoveItem(item.id)}
            />
          ))}
        </div>
      )}
      {/* Add Modal */}
      {showAddModal && (
        <AddItemsModal
          collectionId={collectionId}
          existingItemIds={items.map((i) => i.unit_id || i.project_id)}
          onClose={() => setShowAddModal(false)}
        />
      )}
    </div>
  )
}
function CollectionItemCard({
  item,
  onRemove,
}: {
  item: CollectionItem
  onRemove: () => void
}) {
  const isUnit = !!item.unit
  const project = item.project
  const unit = item.unit
  return (
    <div className="card overflow-hidden group">
      {/* Image */}
      <div className="aspect-video bg-gray-100 relative">
        {project?.cover_image_url ? (
          <img
            src={project.cover_image_url}
            alt=""
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <Building2 className="w-12 h-12 text-gray-300" />
          </div>
        )}
        
        {/* Remove button */}
        <button
          onClick={onRemove}
          className="absolute top-2 right-2 p-1.5 bg-white rounded-lg shadow opacity-0 group-hover:opacity-100 transition-opacity text-gray-400 hover:text-red-600"
        >
          <X className="w-4 h-4" />
        </button>
        {/* Type badge */}
        <span className="absolute top-2 left-2 badge-primary">
          {isUnit ? 'Unit' : 'Project'}
        </span>
      </div>
      {/* Content */}
      <div className="p-4">
        <h3 className="font-semibold text-gray-900">
          {isUnit
            ? `Unit ${unit?.unit_number}`
            : project?.name_en || project?.name_ru || 'Project'}
        </h3>
        {isUnit && project && (
          <p className="text-sm text-gray-500 mt-1">{project.name_en || project.name_ru}</p>
        )}
        {project?.district && (
          <p className="text-sm text-gray-500 mt-1 flex items-center gap-1">
            <MapPin className="w-3.5 h-3.5" />
            {project.district.name_en}
          </p>
        )}
        {/* Unit details */}
        {isUnit && unit && (
          <div className="flex items-center gap-3 mt-3 text-sm text-gray-600">
            <span>{unit.bedrooms} BR</span>
            <span>{unit.area_sqm} sqm</span>
            {unit.floor && <span>Floor {unit.floor}</span>}
          </div>
        )}
        {/* Price */}
        <div className="flex items-center justify-between mt-4">
          <span className="text-lg font-semibold text-primary-600 flex items-center gap-1">
            <DollarSign className="w-4 h-4" />
            {isUnit
              ? unit?.price_usd?.toLocaleString() || 'N/A'
              : project?.min_price_usd
                ? `${(project.min_price_usd / 1000).toFixed(0)}K`
                : 'N/A'}
          </span>
          
          {isUnit && unit?.status && (
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
          )}
        </div>
        {/* Notes */}
        {item.notes && (
          <p className="mt-3 pt-3 border-t border-gray-100 text-sm text-gray-600 italic">
            "{item.notes}"
          </p>
        )}
      </div>
    </div>
  )
}
function AddItemsModal({
  collectionId,
  existingItemIds,
  onClose,
}: {
  collectionId: number
  existingItemIds: number[]
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  // Fetch projects for selection
  const { data: projectsData, isLoading } = useQuery({
    queryKey: ['projects-for-collection', search],
    queryFn: () => projectsApi.list({ search: search || undefined, page_size: 50 }),
  })
  // Add items mutation
  const addItemsMutation = useMutation({
    mutationFn: async (ids: number[]) => {
      for (const projectId of ids) {
        await collectionsApi.addItem(collectionId, { project_id: projectId })
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['collection', collectionId] })
      onClose()
    },
  })
  const projects = projectsData?.items || []
  const availableProjects = projects.filter((p: { id: number }) => !existingItemIds.includes(p.id))
  const toggleProject = (id: number) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    )
  }
  const handleAdd = () => {
    if (selectedIds.length > 0) {
      addItemsMutation.mutate(selectedIds)
    }
  }
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl max-w-2xl w-full max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Add Items</h2>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        {/* Search */}
        <div className="p-4 border-b border-gray-200">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search projects..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input pl-10"
            />
          </div>
        </div>
        {/* List */}
        <div className="flex-1 overflow-y-auto p-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-primary-600" />
            </div>
          ) : availableProjects.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              No projects found
            </div>
          ) : (
            <div className="space-y-2">
              {availableProjects.map((project: { id: number; name_en?: string; name_ru?: string; cover_image_url?: string; min_price_usd?: number }) => (
                <label
                  key={project.id}
                  className={clsx(
                    'flex items-center gap-4 p-3 rounded-lg cursor-pointer transition-colors',
                    selectedIds.includes(project.id)
                      ? 'bg-primary-50 border border-primary-200'
                      : 'hover:bg-gray-50 border border-transparent'
                  )}
                >
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(project.id)}
                    onChange={() => toggleProject(project.id)}
                    className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <div className="w-16 h-12 bg-gray-100 rounded-lg overflow-hidden flex-shrink-0">
                    {project.cover_image_url ? (
                      <img src={project.cover_image_url} alt="" className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <Building2 className="w-6 h-6 text-gray-300" />
                      </div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 truncate">
                      {project.name_en || project.name_ru || 'Project'}
                    </p>
                    <p className="text-sm text-gray-500">
                      From ${project.min_price_usd?.toLocaleString() || 'N/A'}
                    </p>
                  </div>
                </label>
              ))}
            </div>
          )}
        </div>
        {/* Footer */}
        <div className="flex items-center justify-between p-4 border-t border-gray-200">
          <span className="text-sm text-gray-500">
            {selectedIds.length} selected
          </span>
          <div className="flex items-center gap-3">
            <button onClick={onClose} className="btn-secondary">
              Cancel
            </button>
            <button
              onClick={handleAdd}
              disabled={selectedIds.length === 0 || addItemsMutation.isPending}
              className="btn-primary"
            >
              {addItemsMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  <Plus className="w-4 h-4 mr-2" />
                  Add Selected
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
