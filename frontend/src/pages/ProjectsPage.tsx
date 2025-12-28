import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { projectsApi, locationsApi } from '../services/api'
import type { Project, District, MapMarker } from '../types'
import {
  Search,
  Filter,
  Map,
  List,
  ChevronDown,
  Building2,
  MapPin,
  Calendar,
  DollarSign,
  Home,
  Loader2,
} from 'lucide-react'
import clsx from 'clsx'
import mapboxgl from 'mapbox-gl'

// Mapbox token - fallback to production token
const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN || 'pk.eyJ1IjoiNHl1cGFrIiwiYSI6ImNtamxvMjd4MTExbWYzaHExb3hxMjhmbm0ifQ.oQrJJpeI0d5sEp-52g750A'

export default function ProjectsPage() {
  const [view, setView] = useState<'list' | 'split'>('split')
  const [search, setSearch] = useState('')
  const [selectedDistricts, setSelectedDistricts] = useState<number[]>([])
  const [priceRange, setPriceRange] = useState<[number | null, number | null]>([null, null])
  const [bedrooms, setBedrooms] = useState<number | null>(null)
  const [showFilters, setShowFilters] = useState(false)
  const [page, setPage] = useState(1)

  const mapContainer = useRef<HTMLDivElement>(null)
  const map = useRef<mapboxgl.Map | null>(null)
  const markersRef = useRef<mapboxgl.Marker[]>([])

  // Fetch districts
  const { data: districts } = useQuery({
    queryKey: ['districts'],
    queryFn: () => locationsApi.getDistricts(),
  })

  // Build query params
  const queryParams = {
    page,
    page_size: 20,
    search: search || undefined,
    district_ids: selectedDistricts.length > 0 ? selectedDistricts.join(',') : undefined,
    price_min: priceRange[0] || undefined,
    price_max: priceRange[1] || undefined,
    bedrooms_min: bedrooms || undefined,
  }

  // Fetch projects
  const { data: projectsData, isLoading } = useQuery({
    queryKey: ['projects', queryParams],
    queryFn: () => projectsApi.list(queryParams),
  })

  // Fetch map markers
  const { data: mapData } = useQuery({
    queryKey: ['projects-map', queryParams],
    queryFn: () => projectsApi.getMapMarkers(queryParams),
    enabled: view === 'split',
  })

  // Initialize map
  useEffect(() => {
    if (!mapContainer.current || !MAPBOX_TOKEN || view !== 'split') return

    mapboxgl.accessToken = MAPBOX_TOKEN

    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/streets-v12',
      center: [98.3923, 7.8804], // Phuket
      zoom: 10,
    })

    map.current.addControl(new mapboxgl.NavigationControl(), 'top-right')

    return () => {
      map.current?.remove()
    }
  }, [view])

  // Update markers when map data changes
  useEffect(() => {
    if (!map.current || !mapData?.markers) return

    // Clear existing markers
    markersRef.current.forEach((m) => m.remove())
    markersRef.current = []

    // Add new markers
    mapData.markers.forEach((marker: MapMarker) => {
      const el = document.createElement('div')
      el.className = 'w-8 h-8 bg-primary-600 rounded-full border-2 border-white shadow-lg flex items-center justify-center cursor-pointer hover:bg-primary-700 transition-colors'
      el.innerHTML = '<svg class="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20"><path d="M10.707 2.293a1 1 0 00-1.414 0l-7 7a1 1 0 001.414 1.414L4 10.414V17a1 1 0 001 1h2a1 1 0 001-1v-2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 001 1h2a1 1 0 001-1v-6.586l.293.293a1 1 0 001.414-1.414l-7-7z"></path></svg>'

      const popup = new mapboxgl.Popup({ offset: 25 }).setHTML(`
        <div class="p-3 min-w-[200px]">
          <img src="${marker.cover_image_url || '/placeholder.jpg'}" alt="" class="w-full h-24 object-cover rounded-lg mb-2" />
          <h3 class="font-semibold text-gray-900">${marker.name_en || marker.name_ru || 'Project'}</h3>
          <p class="text-sm text-gray-600 mt-1">From $${marker.min_price_usd?.toLocaleString() || 'N/A'}</p>
          <p class="text-xs text-gray-500 mt-1">${marker.available_units} units available</p>
          <a href="/projects/${marker.id}" class="mt-2 inline-block text-sm text-primary-600 hover:text-primary-700 font-medium">View details →</a>
        </div>
      `)

      const m = new mapboxgl.Marker(el)
        .setLngLat([marker.lng, marker.lat])
        .setPopup(popup)
        .addTo(map.current!)

      markersRef.current.push(m)
    })

    // Fit bounds if we have markers
    if (mapData.bounds && markersRef.current.length > 0) {
      map.current.fitBounds(
        [[mapData.bounds.west, mapData.bounds.south], [mapData.bounds.east, mapData.bounds.north]],
        { padding: 50 }
      )
    }
  }, [mapData])

  const projects: Project[] = projectsData?.items || []
  const totalProjects = projectsData?.total || 0

  return (
    <div className="h-[calc(100vh-8rem)]">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Projects</h1>
          <p className="text-sm text-gray-500">{totalProjects} projects found</p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setView('list')}
            className={clsx(
              'p-2 rounded-lg transition-colors',
              view === 'list' ? 'bg-primary-100 text-primary-700' : 'text-gray-500 hover:bg-gray-100'
            )}
          >
            <List className="w-5 h-5" />
          </button>
          <button
            onClick={() => setView('split')}
            className={clsx(
              'p-2 rounded-lg transition-colors',
              view === 'split' ? 'bg-primary-100 text-primary-700' : 'text-gray-500 hover:bg-gray-100'
            )}
          >
            <Map className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4 mb-4">
        {/* Search */}
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search projects..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input pl-10"
          />
        </div>

        {/* District filter */}
        <div className="relative">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="btn-secondary"
          >
            <Filter className="w-4 h-4 mr-2" />
            Filters
            {selectedDistricts.length > 0 && (
              <span className="ml-2 px-1.5 py-0.5 bg-primary-100 text-primary-700 text-xs rounded">
                {selectedDistricts.length}
              </span>
            )}
            <ChevronDown className="w-4 h-4 ml-2" />
          </button>

          {showFilters && (
            <div className="absolute top-full left-0 mt-2 w-80 bg-white rounded-xl shadow-lg border border-gray-200 p-4 z-20">
              <h4 className="font-medium text-gray-900 mb-3">Districts</h4>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {districts?.map((d: District) => (
                  <label key={d.id} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectedDistricts.includes(d.id)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedDistricts([...selectedDistricts, d.id])
                        } else {
                          setSelectedDistricts(selectedDistricts.filter((id) => id !== d.id))
                        }
                      }}
                      className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                    <span className="text-sm text-gray-700">{d.name_en}</span>
                  </label>
                ))}
              </div>

              <h4 className="font-medium text-gray-900 mt-4 mb-3">Price Range (USD)</h4>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  placeholder="Min"
                  value={priceRange[0] || ''}
                  onChange={(e) => setPriceRange([e.target.value ? Number(e.target.value) : null, priceRange[1]])}
                  className="input text-sm"
                />
                <span className="text-gray-400">-</span>
                <input
                  type="number"
                  placeholder="Max"
                  value={priceRange[1] || ''}
                  onChange={(e) => setPriceRange([priceRange[0], e.target.value ? Number(e.target.value) : null])}
                  className="input text-sm"
                />
              </div>

              <h4 className="font-medium text-gray-900 mt-4 mb-3">Bedrooms</h4>
              <div className="flex gap-2">
                {[null, 1, 2, 3, 4].map((b) => (
                  <button
                    key={b ?? 'all'}
                    onClick={() => setBedrooms(b)}
                    className={clsx(
                      'px-3 py-1.5 text-sm rounded-lg transition-colors',
                      bedrooms === b
                        ? 'bg-primary-100 text-primary-700'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    )}
                  >
                    {b === null ? 'All' : `${b}+`}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Content */}
      <div className={clsx('flex gap-4', view === 'split' ? 'h-[calc(100%-8rem)]' : '')}>
        {/* Project list */}
        <div className={clsx('overflow-y-auto', view === 'split' ? 'w-1/2' : 'w-full')}>
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
            </div>
          ) : projects.length === 0 ? (
            <div className="text-center py-12">
              <Building2 className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">No projects found</p>
            </div>
          ) : (
            <div className={clsx('grid gap-4', view === 'list' ? 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3' : 'grid-cols-1')}>
              {projects.map((project) => (
                <ProjectCard key={project.id} project={project} />
              ))}
            </div>
          )}

          {/* Pagination */}
          {totalProjects > 20 && (
            <div className="flex justify-center gap-2 mt-6">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="btn-secondary"
              >
                Previous
              </button>
              <span className="px-4 py-2 text-sm text-gray-600">
                Page {page} of {Math.ceil(totalProjects / 20)}
              </span>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={page >= Math.ceil(totalProjects / 20)}
                className="btn-secondary"
              >
                Next
              </button>
            </div>
          )}
        </div>

        {/* Map */}
        {view === 'split' && (
          <div className="w-1/2 rounded-xl overflow-hidden border border-gray-200">
            <div ref={mapContainer} className="w-full h-full" />
          </div>
        )}
      </div>
    </div>
  )
}

function ProjectCard({ project }: { project: Project }) {
  return (
    <Link to={`/projects/${project.id}`} className="card-hover overflow-hidden block">
      {/* Image */}
      <div className="aspect-video bg-gray-100 relative">
        {project.cover_image_url ? (
          <img
            src={project.cover_image_url}
            alt={project.name_en || ''}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <Building2 className="w-12 h-12 text-gray-300" />
          </div>
        )}
        {project.is_featured && (
          <span className="absolute top-2 left-2 badge-primary">Featured</span>
        )}
      </div>

      {/* Content */}
      <div className="p-4">
        <h3 className="font-semibold text-gray-900 truncate">
          {project.name_en || project.name_ru}
        </h3>

        {project.developer && (
          <p className="text-sm text-gray-500 mt-1">
            by {project.developer.name_en || project.developer.name_ru}
          </p>
        )}

        <div className="flex items-center gap-3 mt-3 text-sm text-gray-600">
          {project.district && (
            <span className="flex items-center gap-1">
              <MapPin className="w-3.5 h-3.5" />
              {project.district.name_en}
            </span>
          )}
          {project.completion_quarter && (
            <span className="flex items-center gap-1">
              <Calendar className="w-3.5 h-3.5" />
              {project.completion_quarter}
            </span>
          )}
        </div>

        <div className="flex items-center justify-between mt-4">
          <div className="flex items-center gap-1 text-primary-600 font-semibold">
            <DollarSign className="w-4 h-4" />
            {project.min_price_usd
              ? `${(project.min_price_usd / 1000).toFixed(0)}K`
              : 'Price TBD'}
            {project.max_price_usd && project.min_price_usd !== project.max_price_usd && (
              <span className="text-gray-400 font-normal">
                - ${(project.max_price_usd / 1000).toFixed(0)}K
              </span>
            )}
          </div>

          <span className="flex items-center gap-1 text-sm text-gray-500">
            <Home className="w-3.5 h-3.5" />
            {project.available_units} units
          </span>
        </div>
      </div>
    </Link>
  )
}
