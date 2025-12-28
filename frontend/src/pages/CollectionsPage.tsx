import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { collectionsApi } from '../services/api'
import {
  Plus,
  Folder,
  MoreVertical,
  ExternalLink,
  Copy,
  Trash2,
  Edit,
  Share2,
  Clock,
  Users,
  Building2,
  Loader2,
  Search,
  Grid,
  List,
  X,
} from 'lucide-react'
import clsx from 'clsx'

interface Collection {
  id: number
  name: string
  description?: string
  share_token: string
  is_public: boolean
  client_name?: string
  client_email?: string
  client_phone?: string
  items_count: number
  created_at: string
  updated_at: string
  expires_at?: string
}

export default function CollectionsPage() {
  const queryClient = useQueryClient()
  const [view, setView] = useState<'grid' | 'list'>('grid')
  const [search, setSearch] = useState('')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editCollection, setEditCollection] = useState<Collection | null>(null)
  const [activeMenu, setActiveMenu] = useState<number | null>(null)

  // Fetch collections
  const { data: collectionsData, isLoading } = useQuery({
    queryKey: ['collections', search],
    queryFn: () => collectionsApi.list({ search: search || undefined }),
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: number) => collectionsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['collections'] })
    },
  })

  const collections: Collection[] = collectionsData?.items || []

  const handleCopyLink = (token: string) => {
    const url = `${window.location.origin}/c/${token}`
    navigator.clipboard.writeText(url)
    // TODO: Show toast notification
    alert('Link copied to clipboard!')
  }

  const handleDelete = (id: number) => {
    if (confirm('Are you sure you want to delete this collection?')) {
      deleteMutation.mutate(id)
    }
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Collections</h1>
          <p className="text-sm text-gray-500 mt-1">
            Create and share property selections with your clients
          </p>
        </div>

        <button
          onClick={() => setShowCreateModal(true)}
          className="btn-primary"
        >
          <Plus className="w-4 h-4 mr-2" />
          New Collection
        </button>
      </div>

      {/* Toolbar */}
      <div className="flex items-center justify-between mb-6">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search collections..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input pl-10"
          />
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setView('grid')}
            className={clsx(
              'p-2 rounded-lg transition-colors',
              view === 'grid' ? 'bg-primary-100 text-primary-700' : 'text-gray-500 hover:bg-gray-100'
            )}
          >
            <Grid className="w-5 h-5" />
          </button>
          <button
            onClick={() => setView('list')}
            className={clsx(
              'p-2 rounded-lg transition-colors',
              view === 'list' ? 'bg-primary-100 text-primary-700' : 'text-gray-500 hover:bg-gray-100'
            )}
          >
            <List className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Collections */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
        </div>
      ) : collections.length === 0 ? (
        <div className="text-center py-12 card">
          <Folder className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No collections yet</h3>
          <p className="text-gray-500 mb-6">
            Create your first collection to start sharing properties with clients
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="btn-primary"
          >
            <Plus className="w-4 h-4 mr-2" />
            Create Collection
          </button>
        </div>
      ) : view === 'grid' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {collections.map((collection) => (
            <CollectionCard
              key={collection.id}
              collection={collection}
              onCopyLink={() => handleCopyLink(collection.share_token)}
              onEdit={() => setEditCollection(collection)}
              onDelete={() => handleDelete(collection.id)}
              activeMenu={activeMenu}
              setActiveMenu={setActiveMenu}
            />
          ))}
        </div>
      ) : (
        <div className="card divide-y divide-gray-200">
          {collections.map((collection) => (
            <CollectionRow
              key={collection.id}
              collection={collection}
              onCopyLink={() => handleCopyLink(collection.share_token)}
              onEdit={() => setEditCollection(collection)}
              onDelete={() => handleDelete(collection.id)}
            />
          ))}
        </div>
      )}

      {/* Create/Edit Modal */}
      {(showCreateModal || editCollection) && (
        <CreateEditModal
          collection={editCollection}
          onClose={() => {
            setShowCreateModal(false)
            setEditCollection(null)
          }}
        />
      )}
    </div>
  )
}

function CollectionCard({
  collection,
  onCopyLink,
  onEdit,
  onDelete,
  activeMenu,
  setActiveMenu,
}: {
  collection: Collection
  onCopyLink: () => void
  onEdit: () => void
  onDelete: () => void
  activeMenu: number | null
  setActiveMenu: (id: number | null) => void
}) {
  const isMenuOpen = activeMenu === collection.id

  return (
    <div className="card p-4 relative group">
      {/* Header */}
      <div className="flex items-start justify-between">
        <Link to={`/collections/${collection.id}`} className="flex-1">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-primary-100 flex items-center justify-center">
              <Folder className="w-5 h-5 text-primary-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 hover:text-primary-600 transition-colors">
                {collection.name}
              </h3>
              {collection.client_name && (
                <p className="text-sm text-gray-500">{collection.client_name}</p>
              )}
            </div>
          </div>
        </Link>

        <div className="relative">
          <button
            onClick={() => setActiveMenu(isMenuOpen ? null : collection.id)}
            className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100"
          >
            <MoreVertical className="w-4 h-4" />
          </button>

          {isMenuOpen && (
            <div className="absolute right-0 top-8 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-10 w-40">
              <button
                onClick={() => {
                  onEdit()
                  setActiveMenu(null)
                }}
                className="w-full px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 flex items-center gap-2"
              >
                <Edit className="w-4 h-4" />
                Edit
              </button>
              <button
                onClick={() => {
                  onCopyLink()
                  setActiveMenu(null)
                }}
                className="w-full px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 flex items-center gap-2"
              >
                <Copy className="w-4 h-4" />
                Copy Link
              </button>
              <a
                href={`/c/${collection.share_token}`}
                target="_blank"
                rel="noopener noreferrer"
                className="w-full px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 flex items-center gap-2"
              >
                <ExternalLink className="w-4 h-4" />
                Preview
              </a>
              <button
                onClick={() => {
                  onDelete()
                  setActiveMenu(null)
                }}
                className="w-full px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center gap-2"
              >
                <Trash2 className="w-4 h-4" />
                Delete
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Description */}
      {collection.description && (
        <p className="text-sm text-gray-600 mt-3 line-clamp-2">{collection.description}</p>
      )}

      {/* Stats */}
      <div className="flex items-center gap-4 mt-4 text-sm text-gray-500">
        <span className="flex items-center gap-1">
          <Building2 className="w-4 h-4" />
          {collection.items_count} units
        </span>
        <span className="flex items-center gap-1">
          <Clock className="w-4 h-4" />
          {new Date(collection.updated_at).toLocaleDateString()}
        </span>
      </div>

      {/* Status badge */}
      <div className="mt-3 flex items-center gap-2">
        {collection.is_public ? (
          <span className="badge-success flex items-center gap-1">
            <Share2 className="w-3 h-3" />
            Public
          </span>
        ) : (
          <span className="badge-gray flex items-center gap-1">
            <Users className="w-3 h-3" />
            Private
          </span>
        )}
        {collection.expires_at && new Date(collection.expires_at) < new Date() && (
          <span className="badge-warning">Expired</span>
        )}
      </div>
    </div>
  )
}

function CollectionRow({
  collection,
  onCopyLink,
  onEdit,
  onDelete,
}: {
  collection: Collection
  onCopyLink: () => void
  onEdit: () => void
  onDelete: () => void
}) {
  return (
    <div className="flex items-center justify-between p-4 hover:bg-gray-50">
      <Link to={`/collections/${collection.id}`} className="flex items-center gap-4 flex-1">
        <div className="w-10 h-10 rounded-lg bg-primary-100 flex items-center justify-center">
          <Folder className="w-5 h-5 text-primary-600" />
        </div>
        <div>
          <h3 className="font-semibold text-gray-900">{collection.name}</h3>
          <div className="flex items-center gap-3 text-sm text-gray-500 mt-0.5">
            {collection.client_name && <span>{collection.client_name}</span>}
            <span>{collection.items_count} units</span>
            <span>{new Date(collection.updated_at).toLocaleDateString()}</span>
          </div>
        </div>
      </Link>

      <div className="flex items-center gap-2">
        {collection.is_public ? (
          <span className="badge-success">Public</span>
        ) : (
          <span className="badge-gray">Private</span>
        )}

        <button
          onClick={onCopyLink}
          className="p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100"
          title="Copy Link"
        >
          <Copy className="w-4 h-4" />
        </button>
        <button
          onClick={onEdit}
          className="p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100"
          title="Edit"
        >
          <Edit className="w-4 h-4" />
        </button>
        <button
          onClick={onDelete}
          className="p-2 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50"
          title="Delete"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}

function CreateEditModal({
  collection,
  onClose,
}: {
  collection: Collection | null
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const [form, setForm] = useState({
    name: collection?.name || '',
    description: collection?.description || '',
    client_name: collection?.client_name || '',
    client_email: collection?.client_email || '',
    client_phone: collection?.client_phone || '',
    is_public: collection?.is_public ?? true,
  })

  const createMutation = useMutation({
    mutationFn: (data: typeof form) => collectionsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['collections'] })
      onClose()
    },
  })

  const updateMutation = useMutation({
    mutationFn: (data: typeof form) => collectionsApi.update(collection!.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['collections'] })
      onClose()
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (collection) {
      updateMutation.mutate(form)
    } else {
      createMutation.mutate(form)
    }
  }

  const isLoading = createMutation.isPending || updateMutation.isPending

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">
            {collection ? 'Edit Collection' : 'Create Collection'}
          </h2>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="input"
              placeholder="e.g., Beachfront Villas for John"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              className="input"
              rows={3}
              placeholder="Optional notes about this collection..."
            />
          </div>

          <div className="border-t border-gray-200 pt-4">
            <h3 className="text-sm font-medium text-gray-700 mb-3">Client Information</h3>
            <div className="space-y-3">
              <input
                type="text"
                value={form.client_name}
                onChange={(e) => setForm({ ...form, client_name: e.target.value })}
                className="input"
                placeholder="Client name"
              />
              <input
                type="email"
                value={form.client_email}
                onChange={(e) => setForm({ ...form, client_email: e.target.value })}
                className="input"
                placeholder="Client email"
              />
              <input
                type="tel"
                value={form.client_phone}
                onChange={(e) => setForm({ ...form, client_phone: e.target.value })}
                className="input"
                placeholder="Client phone"
              />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={form.is_public}
                onChange={(e) => setForm({ ...form, is_public: e.target.checked })}
                className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm text-gray-700">Make collection publicly accessible</span>
            </label>
          </div>

          <div className="flex items-center gap-3 pt-4 border-t border-gray-200">
            <button type="button" onClick={onClose} className="btn-secondary flex-1">
              Cancel
            </button>
            <button type="submit" className="btn-primary flex-1" disabled={isLoading}>
              {isLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : collection ? (
                'Update'
              ) : (
                'Create'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
