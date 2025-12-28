import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import {
  Plus,
  Search,
  Filter,
  MoreVertical,
  Edit,
  Trash2,
  Eye,
  Copy,
  Building2,
  MapPin,
  CheckCircle,
  XCircle,
  Clock,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import { useI18n } from '../../i18n'
import { projectsApi } from '../../services/api'
import clsx from 'clsx'

interface Project {
  id: number
  name_en: string
  name_ru?: string
  slug: string
  status: string
  property_types: string[]
  district?: { name_en: string; name_ru?: string }
  min_price?: number
  max_price?: number
  total_units: number
  available_units: number
  cover_image_url?: string
  is_active: boolean
  created_at: string
}

export default function AdminProjectsPage() {
  const { language } = useI18n()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [showFilters, setShowFilters] = useState(false)
  const [menuOpen, setMenuOpen] = useState<number | null>(null)

  const pageSize = 20

  // Fetch projects
  const { data, isLoading } = useQuery({
    queryKey: ['admin-projects', page, search, statusFilter],
    queryFn: () => projectsApi.list({
      page,
      page_size: pageSize,
      search: search || undefined,
      status: statusFilter || undefined,
    }),
  })

  const projects: Project[] = data?.items || []
  const totalPages = Math.ceil((data?.total || 0) / pageSize)

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: number) => projectsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-projects'] })
    },
  })

  const handleDelete = (id: number, name: string) => {
    if (confirm(`${language === 'ru' ? 'Удалить проект' : 'Delete project'} "${name}"?`)) {
      deleteMutation.mutate(id)
    }
  }

  const getStatusBadge = (status: string, isActive: boolean) => {
    if (!isActive) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
          <XCircle className="w-3 h-3" />
          {language === 'ru' ? 'Неактивен' : 'Inactive'}
        </span>
      )
    }

    const statusConfig: Record<string, { color: string; icon: React.ElementType; label: string; labelRu: string }> = {
      presale: { color: 'bg-blue-100 text-blue-700', icon: Clock, label: 'Presale', labelRu: 'Предпродажа' },
      under_construction: { color: 'bg-yellow-100 text-yellow-700', icon: Building2, label: 'Construction', labelRu: 'Строится' },
      ready: { color: 'bg-green-100 text-green-700', icon: CheckCircle, label: 'Ready', labelRu: 'Готов' },
      completed: { color: 'bg-green-100 text-green-700', icon: CheckCircle, label: 'Completed', labelRu: 'Завершён' },
      sold_out: { color: 'bg-red-100 text-red-700', icon: XCircle, label: 'Sold Out', labelRu: 'Продан' },
    }

    const config = statusConfig[status] || statusConfig.presale
    const Icon = config.icon

    return (
      <span className={clsx('inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium', config.color)}>
        <Icon className="w-3 h-3" />
        {language === 'ru' ? config.labelRu : config.label}
      </span>
    )
  }

  const formatPrice = (price?: number) => {
    if (!price) return '—'
    if (price >= 1000000) {
      return `${(price / 1000000).toFixed(1)}M`
    }
    return price.toLocaleString()
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {language === 'ru' ? 'Проекты' : 'Projects'}
          </h1>
          <p className="text-gray-500 mt-1">
            {data?.total || 0} {language === 'ru' ? 'объектов' : 'projects'}
          </p>
        </div>
        <Link
          to="/admin/projects/new"
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus className="w-5 h-5" />
          {language === 'ru' ? 'Добавить проект' : 'Add Project'}
        </Link>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <div className="flex flex-wrap items-center gap-4">
          {/* Search */}
          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder={language === 'ru' ? 'Поиск проектов...' : 'Search projects...'}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>

          {/* Status filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="">{language === 'ru' ? 'Все статусы' : 'All statuses'}</option>
            <option value="presale">{language === 'ru' ? 'Предпродажа' : 'Presale'}</option>
            <option value="under_construction">{language === 'ru' ? 'Строится' : 'Construction'}</option>
            <option value="ready">{language === 'ru' ? 'Готов' : 'Ready'}</option>
            <option value="completed">{language === 'ru' ? 'Завершён' : 'Completed'}</option>
            <option value="sold_out">{language === 'ru' ? 'Продан' : 'Sold Out'}</option>
          </select>
        </div>
      </div>

      {/* Projects Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  {language === 'ru' ? 'Проект' : 'Project'}
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  {language === 'ru' ? 'Район' : 'District'}
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  {language === 'ru' ? 'Статус' : 'Status'}
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  {language === 'ru' ? 'Юниты' : 'Units'}
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  {language === 'ru' ? 'Цена' : 'Price'}
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  {language === 'ru' ? 'Действия' : 'Actions'}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                    {language === 'ru' ? 'Загрузка...' : 'Loading...'}
                  </td>
                </tr>
              ) : projects.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                    {language === 'ru' ? 'Проекты не найдены' : 'No projects found'}
                  </td>
                </tr>
              ) : (
                projects.map((project) => (
                  <tr key={project.id} className="hover:bg-gray-50">
                    <td className="px-4 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-12 h-12 bg-gray-100 rounded-lg flex-shrink-0 overflow-hidden">
                          {project.cover_image_url ? (
                            <img
                              src={project.cover_image_url}
                              alt=""
                              className="w-full h-full object-cover"
                            />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center">
                              <Building2 className="w-6 h-6 text-gray-400" />
                            </div>
                          )}
                        </div>
                        <div>
                          <Link
                            to={`/admin/projects/${project.id}`}
                            className="font-medium text-gray-900 hover:text-blue-600"
                          >
                            {language === 'ru' ? project.name_ru || project.name_en : project.name_en}
                          </Link>
                          <p className="text-sm text-gray-500">
                            {project.property_types?.join(', ') || '—'}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex items-center gap-1 text-sm text-gray-600">
                        <MapPin className="w-4 h-4" />
                        {project.district 
                          ? (language === 'ru' ? project.district.name_ru || project.district.name_en : project.district.name_en)
                          : '—'}
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      {getStatusBadge(project.status, project.is_active)}
                    </td>
                    <td className="px-4 py-4">
                      <div className="text-sm">
                        <span className="text-green-600 font-medium">{project.available_units}</span>
                        <span className="text-gray-400"> / {project.total_units}</span>
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <div className="text-sm text-gray-900">
                        {project.min_price ? (
                          <>
                            {formatPrice(project.min_price)}
                            {project.max_price && project.max_price !== project.min_price && (
                              <> — {formatPrice(project.max_price)}</>
                            )}
                            <span className="text-gray-400 ml-1">THB</span>
                          </>
                        ) : (
                          '—'
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex items-center justify-end gap-2">
                        <Link
                          to={`/projects/${project.id}`}
                          className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg"
                          title={language === 'ru' ? 'Просмотр' : 'View'}
                        >
                          <Eye className="w-4 h-4" />
                        </Link>
                        <Link
                          to={`/admin/projects/${project.id}`}
                          className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg"
                          title={language === 'ru' ? 'Редактировать' : 'Edit'}
                        >
                          <Edit className="w-4 h-4" />
                        </Link>
                        <button
                          onClick={() => handleDelete(project.id, project.name_en)}
                          className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
                          title={language === 'ru' ? 'Удалить' : 'Delete'}
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200">
            <div className="text-sm text-gray-500">
              {language === 'ru' ? 'Страница' : 'Page'} {page} {language === 'ru' ? 'из' : 'of'} {totalPages}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="p-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
