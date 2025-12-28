import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { collectionsApi } from '../services/api'
import {
  Building2,
  MapPin,
  Home,
  Phone,
  Mail,
  MessageSquare,
  ChevronDown,
  ChevronUp,
  Calendar,
  Ruler,
  Layers,
  Eye,
  CheckCircle,
  Loader2,
  X,
} from 'lucide-react'
import clsx from 'clsx'

interface CollectionItem {
  id: number
  unit_id?: number
  project_id: number
  notes?: string
  unit?: {
    id: number
    unit_number: string
    bedrooms: number
    area_sqm: number
    price_usd: number
    price_original: number
    original_currency: string
    status: string
    floor?: number
    view_type?: string
  }
  project?: {
    id: number
    name_en?: string
    name_ru?: string
    description_en?: string
    cover_image_url?: string
    gallery?: string[]
    district?: {
      name_en?: string
    }
    developer?: {
      name_en?: string
    }
    completion_quarter?: string
    min_price_usd?: number
    max_price_usd?: number
    available_units?: number
    amenities?: string[]
    ownership_type?: string
  }
}

interface PublicCollection {
  id: number
  name: string
  description?: string
  agent?: {
    first_name: string
    last_name?: string
    phone?: string
    email?: string
    avatar_url?: string
    agency_name?: string
    agency_logo_url?: string
  }
  items: CollectionItem[]
  created_at: string
}

export default function PublicCollectionPage() {
  const { token } = useParams<{ token: string }>()
  const [showInquiryForm, setShowInquiryForm] = useState(false)
  const [selectedItemId, setSelectedItemId] = useState<number | null>(null)

  // Fetch public collection
  const { data: collection, isLoading, error } = useQuery({
    queryKey: ['public-collection', token],
    queryFn: () => collectionsApi.getPublic(token!),
    enabled: !!token,
  })

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    )
  }

  if (error || !collection) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Building2 className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h1 className="text-xl font-semibold text-gray-900 mb-2">Collection Not Found</h1>
          <p className="text-gray-500">This collection may have expired or been removed.</p>
        </div>
      </div>
    )
  }

  const items: CollectionItem[] = collection.items || []
  const agent = collection.agent

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              {agent?.agency_logo_url && (
                <img
                  src={agent.agency_logo_url}
                  alt={agent.agency_name || ''}
                  className="h-10 object-contain"
                />
              )}
              {!agent?.agency_logo_url && agent?.agency_name && (
                <span className="text-lg font-semibold text-gray-900">{agent.agency_name}</span>
              )}
            </div>
            
            {agent && (
              <div className="flex items-center gap-4">
                {agent.phone && (
                  <a
                    href={`tel:${agent.phone}`}
                    className="flex items-center gap-2 text-gray-600 hover:text-primary-600"
                  >
                    <Phone className="w-4 h-4" />
                    <span className="hidden sm:inline">{agent.phone}</span>
                  </a>
                )}
                <button
                  onClick={() => setShowInquiryForm(true)}
                  className="btn-primary"
                >
                  <MessageSquare className="w-4 h-4 sm:mr-2" />
                  <span className="hidden sm:inline">Contact Agent</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Collection title */}
        <div className="mb-8">
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">{collection.name}</h1>
          {collection.description && (
            <p className="text-gray-600 mt-2">{collection.description}</p>
          )}
          <p className="text-sm text-gray-500 mt-2">
            {items.length} {items.length === 1 ? 'property' : 'properties'} selected for you
          </p>
        </div>

        {/* Properties */}
        {items.length === 0 ? (
          <div className="text-center py-12">
            <Building2 className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">No properties in this collection</p>
          </div>
        ) : (
          <div className="space-y-6">
            {items.map((item) => (
              <PropertyCard
                key={item.id}
                item={item}
                onInquire={() => {
                  setSelectedItemId(item.id)
                  setShowInquiryForm(true)
                }}
              />
            ))}
          </div>
        )}

        {/* Agent card (mobile bottom) */}
        {agent && (
          <div className="mt-8 sm:hidden">
            <AgentCard agent={agent} onContact={() => setShowInquiryForm(true)} />
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-12 py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-sm text-gray-500">
          <p>This collection was created by {agent?.first_name} {agent?.last_name}</p>
          <p className="mt-1">Powered by PropBase</p>
        </div>
      </footer>

      {/* Inquiry form modal */}
      {showInquiryForm && (
        <InquiryModal
          token={token!}
          itemId={selectedItemId}
          agentName={agent ? `${agent.first_name} ${agent.last_name || ''}` : 'Agent'}
          onClose={() => {
            setShowInquiryForm(false)
            setSelectedItemId(null)
          }}
        />
      )}
    </div>
  )
}

function PropertyCard({
  item,
  onInquire,
}: {
  item: CollectionItem
  onInquire: () => void
}) {
  const [expanded, setExpanded] = useState(false)
  const isUnit = !!item.unit
  const project = item.project
  const unit = item.unit

  return (
    <div className="bg-white rounded-xl shadow-sm overflow-hidden">
      {/* Main section */}
      <div className="md:flex">
        {/* Image */}
        <div className="md:w-1/3 aspect-video md:aspect-auto bg-gray-100 relative">
          {project?.cover_image_url ? (
            <img
              src={project.cover_image_url}
              alt=""
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <Building2 className="w-16 h-16 text-gray-300" />
            </div>
          )}
          
          {/* Type badge */}
          <span className="absolute top-3 left-3 px-2 py-1 bg-primary-600 text-white text-xs font-medium rounded">
            {isUnit ? 'Unit' : 'Project'}
          </span>
        </div>

        {/* Content */}
        <div className="flex-1 p-6">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-xl font-bold text-gray-900">
                {isUnit
                  ? `Unit ${unit?.unit_number}`
                  : project?.name_en || project?.name_ru}
              </h2>
              
              {isUnit && project && (
                <p className="text-gray-600">{project.name_en || project.name_ru}</p>
              )}

              {project?.developer && (
                <p className="text-sm text-gray-500 mt-1">by {project.developer.name_en}</p>
              )}
            </div>

            {/* Price */}
            <div className="text-right">
              <p className="text-2xl font-bold text-primary-600">
                ${isUnit
                  ? unit?.price_usd?.toLocaleString()
                  : project?.min_price_usd?.toLocaleString()}
                {!isUnit && project?.max_price_usd && project.min_price_usd !== project.max_price_usd && (
                  <span className="text-lg text-gray-400"> - ${(project.max_price_usd / 1000).toFixed(0)}K</span>
                )}
              </p>
              {isUnit && unit?.price_original && unit.original_currency !== 'USD' && (
                <p className="text-sm text-gray-500">
                  {unit.original_currency} {unit.price_original.toLocaleString()}
                </p>
              )}
            </div>
          </div>

          {/* Location & Details */}
          <div className="flex flex-wrap items-center gap-4 mt-4 text-sm text-gray-600">
            {project?.district && (
              <span className="flex items-center gap-1">
                <MapPin className="w-4 h-4" />
                {project.district.name_en}
              </span>
            )}
            
            {isUnit ? (
              <>
                <span className="flex items-center gap-1">
                  <Home className="w-4 h-4" />
                  {unit?.bedrooms} Bedroom
                </span>
                <span className="flex items-center gap-1">
                  <Ruler className="w-4 h-4" />
                  {unit?.area_sqm} sqm
                </span>
                {unit?.floor && (
                  <span className="flex items-center gap-1">
                    <Layers className="w-4 h-4" />
                    Floor {unit.floor}
                  </span>
                )}
                {unit?.view_type && (
                  <span className="flex items-center gap-1">
                    <Eye className="w-4 h-4" />
                    {unit.view_type}
                  </span>
                )}
              </>
            ) : (
              <>
                {project?.completion_quarter && (
                  <span className="flex items-center gap-1">
                    <Calendar className="w-4 h-4" />
                    {project.completion_quarter}
                  </span>
                )}
                {project?.available_units && (
                  <span className="flex items-center gap-1">
                    <Home className="w-4 h-4" />
                    {project.available_units} units available
                  </span>
                )}
                {project?.ownership_type && (
                  <span className="badge-gray">{project.ownership_type}</span>
                )}
              </>
            )}
          </div>

          {/* Status */}
          {isUnit && unit?.status && (
            <div className="mt-4">
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
            </div>
          )}

          {/* Agent notes */}
          {item.notes && (
            <div className="mt-4 p-3 bg-primary-50 rounded-lg">
              <p className="text-sm text-primary-800 italic">"{item.notes}"</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center gap-3 mt-6">
            <button onClick={onInquire} className="btn-primary flex-1 sm:flex-none">
              <MessageSquare className="w-4 h-4 mr-2" />
              Inquire
            </button>
            
            {(project?.description_en || project?.amenities?.length) && (
              <button
                onClick={() => setExpanded(!expanded)}
                className="btn-secondary"
              >
                {expanded ? (
                  <>
                    <ChevronUp className="w-4 h-4 mr-2" />
                    Less
                  </>
                ) : (
                  <>
                    <ChevronDown className="w-4 h-4 mr-2" />
                    More
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Expanded details */}
      {expanded && (
        <div className="p-6 border-t border-gray-100 bg-gray-50">
          {project?.description_en && (
            <div className="mb-4">
              <h3 className="font-medium text-gray-900 mb-2">Description</h3>
              <p className="text-gray-600">{project.description_en}</p>
            </div>
          )}
          
          {project?.amenities && project.amenities.length > 0 && (
            <div>
              <h3 className="font-medium text-gray-900 mb-2">Amenities</h3>
              <div className="flex flex-wrap gap-2">
                {project.amenities.map((amenity) => (
                  <span key={amenity} className="badge-gray">
                    {amenity}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Gallery */}
          {project?.gallery && project.gallery.length > 0 && (
            <div className="mt-4">
              <h3 className="font-medium text-gray-900 mb-2">Gallery</h3>
              <div className="flex gap-2 overflow-x-auto pb-2">
                {project.gallery.map((url, idx) => (
                  <img
                    key={idx}
                    src={url}
                    alt=""
                    className="w-32 h-24 object-cover rounded-lg flex-shrink-0"
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function AgentCard({
  agent,
  onContact,
}: {
  agent: {
    first_name: string
    last_name?: string
    phone?: string
    email?: string
    avatar_url?: string
    agency_name?: string
  }
  onContact: () => void
}) {
  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <div className="flex items-center gap-4">
        {agent.avatar_url ? (
          <img
            src={agent.avatar_url}
            alt=""
            className="w-16 h-16 rounded-full object-cover"
          />
        ) : (
          <div className="w-16 h-16 rounded-full bg-primary-100 flex items-center justify-center">
            <span className="text-xl font-semibold text-primary-600">
              {agent.first_name[0]}
            </span>
          </div>
        )}
        <div>
          <h3 className="font-semibold text-gray-900">
            {agent.first_name} {agent.last_name}
          </h3>
          {agent.agency_name && (
            <p className="text-sm text-gray-500">{agent.agency_name}</p>
          )}
        </div>
      </div>

      <div className="mt-4 space-y-2">
        {agent.phone && (
          <a
            href={`tel:${agent.phone}`}
            className="flex items-center gap-2 text-gray-600 hover:text-primary-600"
          >
            <Phone className="w-4 h-4" />
            {agent.phone}
          </a>
        )}
        {agent.email && (
          <a
            href={`mailto:${agent.email}`}
            className="flex items-center gap-2 text-gray-600 hover:text-primary-600"
          >
            <Mail className="w-4 h-4" />
            {agent.email}
          </a>
        )}
      </div>

      <button onClick={onContact} className="btn-primary w-full mt-4">
        <MessageSquare className="w-4 h-4 mr-2" />
        Contact Agent
      </button>
    </div>
  )
}

function InquiryModal({
  token,
  itemId,
  agentName,
  onClose,
}: {
  token: string
  itemId: number | null
  agentName: string
  onClose: () => void
}) {
  const [submitted, setSubmitted] = useState(false)
  const [form, setForm] = useState({
    name: '',
    email: '',
    phone: '',
    message: '',
  })

  const submitMutation = useMutation({
    mutationFn: (data: typeof form & { item_id?: number }) =>
      collectionsApi.submitInquiry(token, data),
    onSuccess: () => {
      setSubmitted(true)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    submitMutation.mutate({
      ...form,
      item_id: itemId || undefined,
    })
  }

  if (submitted) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-xl max-w-md w-full p-8 text-center">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircle className="w-8 h-8 text-green-600" />
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Thank You!</h2>
          <p className="text-gray-600 mb-6">
            Your inquiry has been sent to {agentName}. They will get back to you shortly.
          </p>
          <button onClick={onClose} className="btn-primary">
            Close
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Contact {agentName}</h2>
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
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email *</label>
            <input
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              className="input"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
            <input
              type="tel"
              value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
              className="input"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Message</label>
            <textarea
              value={form.message}
              onChange={(e) => setForm({ ...form, message: e.target.value })}
              className="input"
              rows={4}
              placeholder="I'm interested in this property..."
            />
          </div>

          <button
            type="submit"
            disabled={submitMutation.isPending}
            className="btn-primary w-full"
          >
            {submitMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              'Send Inquiry'
            )}
          </button>
        </form>
      </div>
    </div>
  )
}
