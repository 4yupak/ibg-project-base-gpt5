import { useState } from 'react'
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
import { useI18n } from '../../i18n'
import {
  LayoutDashboard,
  Building2,
  Home,
  Users,
  FileSpreadsheet,
  Image,
  Settings,
  LogOut,
  Menu,
  X,
  User,
  ChevronLeft,
  Database,
  Upload,
  Brain,
  Shield,
} from 'lucide-react'
import clsx from 'clsx'

const adminNavigation = [
  { key: 'dashboard', href: '/admin', icon: LayoutDashboard, labelEn: 'Dashboard', labelRu: 'Панель' },
  { key: 'projects', href: '/admin/projects', icon: Building2, labelEn: 'Projects', labelRu: 'Проекты' },
  { key: 'units', href: '/admin/units', icon: Home, labelEn: 'Units', labelRu: 'Юниты' },
  { key: 'parser', href: '/admin/parser', icon: Brain, labelEn: 'Smart Parser', labelRu: 'Парсер' },
  { key: 'media', href: '/admin/media', icon: Image, labelEn: 'Media Library', labelRu: 'Медиатека' },
  { key: 'users', href: '/admin/users', icon: Users, labelEn: 'Users', labelRu: 'Пользователи' },
  { key: 'settings', href: '/admin/settings', icon: Settings, labelEn: 'Settings', labelRu: 'Настройки' },
]

export default function AdminLayout() {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
  const { language } = useI18n()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const isAdmin = user?.role === 'admin' || user?.role === 'analyst'

  if (!isAdmin) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <Shield className="w-16 h-16 mx-auto text-gray-400 mb-4" />
          <h1 className="text-xl font-semibold text-gray-900 mb-2">
            {language === 'ru' ? 'Доступ запрещён' : 'Access Denied'}
          </h1>
          <p className="text-gray-500 mb-4">
            {language === 'ru' 
              ? 'У вас нет прав для доступа к этой странице'
              : 'You do not have permission to access this page'}
          </p>
          <Link
            to="/"
            className="text-blue-600 hover:text-blue-700 font-medium"
          >
            {language === 'ru' ? 'Вернуться на главную' : 'Back to Home'}
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={clsx(
          'fixed inset-y-0 left-0 z-50 w-64 bg-gray-900 transform transition-transform duration-200 ease-in-out lg:translate-x-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* Logo */}
        <div className="flex items-center justify-between h-16 px-4 border-b border-gray-800">
          <Link to="/admin" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <Database className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="text-lg font-bold text-white">PropBase</span>
              <span className="ml-2 text-xs text-gray-400 bg-gray-800 px-2 py-0.5 rounded">Admin</span>
            </div>
          </Link>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden p-1 text-gray-400 hover:text-white"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Back to main site */}
        <div className="px-3 py-3 border-b border-gray-800">
          <Link
            to="/"
            className="flex items-center gap-2 px-3 py-2 text-sm text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
            {language === 'ru' ? 'На сайт' : 'Back to Site'}
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {adminNavigation.map((item) => {
            const isActive = item.href === '/admin' 
              ? location.pathname === '/admin'
              : location.pathname.startsWith(item.href)
            return (
              <Link
                key={item.key}
                to={item.href}
                onClick={() => setSidebarOpen(false)}
                className={clsx(
                  'flex items-center gap-3 px-3 py-2 rounded-lg font-medium transition-colors',
                  isActive
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                )}
              >
                <item.icon className="w-5 h-5" />
                {language === 'ru' ? item.labelRu : item.labelEn}
              </Link>
            )
          })}
        </nav>

        {/* User info */}
        <div className="p-4 border-t border-gray-800">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 bg-gray-700 rounded-full flex items-center justify-center">
              {user?.avatar_url ? (
                <img src={user.avatar_url} alt="" className="w-10 h-10 rounded-full" />
              ) : (
                <User className="w-5 h-5 text-gray-400" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">
                {user?.first_name} {user?.last_name}
              </p>
              <p className="text-xs text-gray-400 truncate">{user?.role}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 w-full px-3 py-2 text-sm text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
          >
            <LogOut className="w-4 h-4" />
            {language === 'ru' ? 'Выйти' : 'Logout'}
          </button>
        </div>
      </aside>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Top header */}
        <header className="sticky top-0 z-30 bg-white border-b border-gray-200 shadow-sm">
          <div className="flex items-center justify-between h-16 px-4">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
            >
              <Menu className="w-5 h-5" />
            </button>

            <div className="flex-1" />

            {/* Breadcrumb placeholder */}
            <div className="text-sm text-gray-500">
              {location.pathname.replace('/admin', '').split('/').filter(Boolean).join(' / ') || 'Dashboard'}
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
