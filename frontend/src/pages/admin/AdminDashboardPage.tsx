import { useQuery } from '@tanstack/react-query'
import { 
  Building2, 
  Home, 
  Users, 
  MapPin, 
  TrendingUp, 
  AlertCircle,
  CheckCircle,
  Clock,
  FileSpreadsheet,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { useI18n } from '../../i18n'
import { projectsApi } from '../../services/api'

interface StatCardProps {
  title: string
  value: string | number
  icon: React.ElementType
  color: string
  change?: string
  link?: string
}

function StatCard({ title, value, icon: Icon, color, change, link }: StatCardProps) {
  const content = (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className="text-3xl font-bold text-gray-900 mt-2">{value}</p>
          {change && (
            <p className="text-sm text-green-600 mt-1 flex items-center gap-1">
              <TrendingUp className="w-4 h-4" />
              {change}
            </p>
          )}
        </div>
        <div className={`p-3 rounded-lg ${color}`}>
          <Icon className="w-6 h-6 text-white" />
        </div>
      </div>
    </div>
  )

  return link ? <Link to={link}>{content}</Link> : content
}

export default function AdminDashboardPage() {
  const { language } = useI18n()

  // Fetch projects stats
  const { data: projectsData } = useQuery({
    queryKey: ['admin-projects-stats'],
    queryFn: () => projectsApi.list({ page_size: 1 }),
  })

  const stats = {
    totalProjects: projectsData?.total || 0,
    activeProjects: projectsData?.total || 0,
    totalUnits: 0,
    availableUnits: 0,
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          {language === 'ru' ? 'Панель управления' : 'Admin Dashboard'}
        </h1>
        <p className="text-gray-500 mt-1">
          {language === 'ru' 
            ? 'Управление проектами и данными PropBase'
            : 'Manage PropBase projects and data'}
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title={language === 'ru' ? 'Всего проектов' : 'Total Projects'}
          value={stats.totalProjects}
          icon={Building2}
          color="bg-blue-500"
          link="/admin/projects"
        />
        <StatCard
          title={language === 'ru' ? 'Активных' : 'Active'}
          value={stats.activeProjects}
          icon={CheckCircle}
          color="bg-green-500"
        />
        <StatCard
          title={language === 'ru' ? 'Всего юнитов' : 'Total Units'}
          value={stats.totalUnits}
          icon={Home}
          color="bg-purple-500"
        />
        <StatCard
          title={language === 'ru' ? 'Доступно' : 'Available'}
          value={stats.availableUnits}
          icon={Clock}
          color="bg-orange-500"
        />
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          {language === 'ru' ? 'Быстрые действия' : 'Quick Actions'}
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link
            to="/admin/projects/new"
            className="flex items-center gap-3 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <div className="p-2 bg-blue-100 rounded-lg">
              <Building2 className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="font-medium text-gray-900">
                {language === 'ru' ? 'Добавить проект' : 'Add Project'}
              </p>
              <p className="text-sm text-gray-500">
                {language === 'ru' ? 'Создать новый объект' : 'Create new project'}
              </p>
            </div>
          </Link>

          <Link
            to="/admin/parser"
            className="flex items-center gap-3 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <div className="p-2 bg-green-100 rounded-lg">
              <FileSpreadsheet className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="font-medium text-gray-900">
                {language === 'ru' ? 'Загрузить прайс' : 'Upload Price List'}
              </p>
              <p className="text-sm text-gray-500">
                {language === 'ru' ? 'PDF, Excel, CSV' : 'PDF, Excel, CSV'}
              </p>
            </div>
          </Link>

          <Link
            to="/admin/media"
            className="flex items-center gap-3 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <div className="p-2 bg-purple-100 rounded-lg">
              <MapPin className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <p className="font-medium text-gray-900">
                {language === 'ru' ? 'Медиатека' : 'Media Library'}
              </p>
              <p className="text-sm text-gray-500">
                {language === 'ru' ? 'Управление файлами' : 'Manage files'}
              </p>
            </div>
          </Link>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          {language === 'ru' ? 'Последние изменения' : 'Recent Activity'}
        </h2>
        <div className="text-center py-8 text-gray-500">
          <AlertCircle className="w-12 h-12 mx-auto mb-3 text-gray-300" />
          <p>{language === 'ru' ? 'Нет активности' : 'No recent activity'}</p>
        </div>
      </div>
    </div>
  )
}
