import { useState } from 'react'
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
import { useI18n } from '../../i18n'
import {
  Home,
  Building2,
  FolderOpen,
  BarChart3,
  Settings,
  LogOut,
  Menu,
  X,
  User,
  Globe,
  DollarSign,
  ChevronDown,
  Brain,
  Upload,
  Shield,
} from 'lucide-react'
import clsx from 'clsx'

const navigationItems = [
  { key: 'dashboard', href: '/dashboard', icon: Home },
  { key: 'projects', href: '/projects', icon: Building2 },
  { key: 'collections', href: '/collections', icon: FolderOpen },
  { key: 'analytics', href: '/analytics', icon: BarChart3 },
  { key: 'smartParser', href: '/smart-parser', icon: Brain },
  { key: 'priceIngestion', href: '/price-ingestion', icon: Upload },
  { key: 'settings', href: '/settings', icon: Settings },
]

// Admin-only navigation
const adminNavItem = { key: 'admin', href: '/admin', icon: Shield }

const currencies = ['USD', 'THB', 'IDR', 'EUR', 'RUB']

export default function MainLayout() {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
  const { t, lang, setLang, currency, setCurrency } = useI18n()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [showCurrencyDropdown, setShowCurrencyDropdown] = useState(false)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-gray-50">
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
          'fixed inset-y-0 left-0 z-50 w-64 bg-white border-r border-gray-200 transform transition-transform duration-200 ease-in-out lg:translate-x-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* Logo */}
        <div className="flex items-center justify-between h-16 px-4 border-b border-gray-200">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
              <Building2 className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold text-gray-900">PropBase</span>
          </Link>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden p-1 text-gray-500 hover:text-gray-700"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {navigationItems.map((item) => {
            const isActive = location.pathname.startsWith(item.href)
            return (
              <Link
                key={item.key}
                to={item.href}
                onClick={() => setSidebarOpen(false)}
                className={clsx(
                  'flex items-center gap-3 px-3 py-2 rounded-lg font-medium transition-colors',
                  isActive
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                )}
              >
                <item.icon className="w-5 h-5" />
                {t(`nav.${item.key}`)}
              </Link>
            )
          })}
          
          {/* Admin Panel Link - only for admins */}
          {(user?.role === 'admin' || user?.role === 'analyst' || user?.role === 'content_manager') && (
            <div className="pt-4 mt-4 border-t border-gray-200">
              <Link
                to={adminNavItem.href}
                onClick={() => setSidebarOpen(false)}
                className={clsx(
                  'flex items-center gap-3 px-3 py-2 rounded-lg font-medium transition-colors',
                  location.pathname.startsWith('/admin')
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                )}
              >
                <adminNavItem.icon className="w-5 h-5" />
                {lang === 'ru' ? 'Админ панель' : 'Admin Panel'}
              </Link>
            </div>
          )}
        </nav>

        {/* User info */}
        <div className="p-4 border-t border-gray-200">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 bg-gray-200 rounded-full flex items-center justify-center">
              {user?.avatar_url ? (
                <img src={user.avatar_url} alt="" className="w-10 h-10 rounded-full" />
              ) : (
                <User className="w-5 h-5 text-gray-500" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">
                {user?.first_name} {user?.last_name}
              </p>
              <p className="text-xs text-gray-500 truncate">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 w-full px-3 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <LogOut className="w-4 h-4" />
            {t('nav.logout')}
          </button>
        </div>
      </aside>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Top header */}
        <header className="sticky top-0 z-30 bg-white border-b border-gray-200">
          <div className="flex items-center justify-between h-16 px-4">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-2 text-gray-500 hover:text-gray-700"
            >
              <Menu className="w-5 h-5" />
            </button>

            <div className="flex-1" />

            {/* Language & Currency switchers */}
            <div className="flex items-center gap-2">
              {/* Language */}
              <button
                onClick={() => setLang(lang === 'en' ? 'ru' : 'en')}
                className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <Globe className="w-4 h-4" />
                {lang === 'en' ? 'EN' : 'RU'}
              </button>

              {/* Currency dropdown */}
              <div className="relative">
                <button
                  onClick={() => setShowCurrencyDropdown(!showCurrencyDropdown)}
                  className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <DollarSign className="w-4 h-4" />
                  {currency}
                  <ChevronDown className="w-3 h-3" />
                </button>
                
                {showCurrencyDropdown && (
                  <div className="absolute right-0 top-full mt-1 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50 min-w-[100px]">
                    {currencies.map((c) => (
                      <button
                        key={c}
                        onClick={() => {
                          setCurrency(c)
                          setShowCurrencyDropdown(false)
                        }}
                        className={clsx(
                          'w-full px-3 py-2 text-left text-sm hover:bg-gray-100',
                          currency === c ? 'text-primary-600 font-medium' : 'text-gray-700'
                        )}
                      >
                        {c}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="p-4 md:p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
