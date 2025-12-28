import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useAuthStore } from '../store/authStore'
import { api } from '../services/api'
import {
  User,
  Globe,
  Palette,
  Bell,
  Shield,
  Key,
  Building2,
  Upload,
  Camera,
  Check,
  Loader2,
  Plug,
  ExternalLink,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import clsx from 'clsx'

type Tab = 'profile' | 'agency' | 'preferences' | 'notifications' | 'security' | 'integrations'

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<Tab>('profile')

  const tabs: { id: Tab; label: string; icon: typeof User }[] = [
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'agency', label: 'Agency', icon: Building2 },
    { id: 'preferences', label: 'Preferences', icon: Palette },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'security', label: 'Security', icon: Shield },
    { id: 'integrations', label: 'Integrations', icon: Plug },
  ]

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Settings</h1>

      <div className="flex gap-6">
        {/* Sidebar */}
        <div className="w-48 flex-shrink-0">
          <nav className="space-y-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={clsx(
                  'w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                  activeTab === tab.id
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                )}
              >
                <tab.icon className="w-5 h-5" />
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1">
          {activeTab === 'profile' && <ProfileSettings />}
          {activeTab === 'agency' && <AgencySettings />}
          {activeTab === 'preferences' && <PreferencesSettings />}
          {activeTab === 'notifications' && <NotificationSettings />}
          {activeTab === 'security' && <SecuritySettings />}
          {activeTab === 'integrations' && <IntegrationsSettings />}
        </div>
      </div>
    </div>
  )
}

function ProfileSettings() {
  const { user, updateUser } = useAuthStore()
  const [form, setForm] = useState({
    first_name: user?.first_name || '',
    last_name: user?.last_name || '',
    email: user?.email || '',
    phone: '',
  })

  const updateMutation = useMutation({
    mutationFn: (data: typeof form) => api.patch('/users/me', data),
    onSuccess: (response) => {
      updateUser(response.data)
      alert('Profile updated successfully!')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    updateMutation.mutate(form)
  }

  return (
    <div className="card p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-6">Profile Information</h2>

      {/* Avatar */}
      <div className="flex items-center gap-4 mb-6 pb-6 border-b border-gray-200">
        <div className="relative">
          {user?.avatar_url ? (
            <img
              src={user.avatar_url}
              alt=""
              className="w-20 h-20 rounded-full object-cover"
            />
          ) : (
            <div className="w-20 h-20 rounded-full bg-primary-100 flex items-center justify-center">
              <span className="text-2xl font-semibold text-primary-600">
                {user?.first_name?.[0] || 'U'}
              </span>
            </div>
          )}
          <button className="absolute bottom-0 right-0 p-1.5 bg-white rounded-full shadow-lg border border-gray-200 text-gray-500 hover:text-gray-700">
            <Camera className="w-4 h-4" />
          </button>
        </div>
        <div>
          <h3 className="font-medium text-gray-900">
            {user?.first_name} {user?.last_name}
          </h3>
          <p className="text-sm text-gray-500 capitalize">{user?.role}</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">First Name</label>
            <input
              type="text"
              value={form.first_name}
              onChange={(e) => setForm({ ...form, first_name: e.target.value })}
              className="input"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Last Name</label>
            <input
              type="text"
              value={form.last_name}
              onChange={(e) => setForm({ ...form, last_name: e.target.value })}
              className="input"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
          <input
            type="email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            className="input"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
          <input
            type="tel"
            value={form.phone}
            onChange={(e) => setForm({ ...form, phone: e.target.value })}
            className="input"
            placeholder="+66 XX XXX XXXX"
          />
        </div>

        <div className="pt-4">
          <button type="submit" className="btn-primary" disabled={updateMutation.isPending}>
            {updateMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin mr-2" />
            ) : (
              <Check className="w-4 h-4 mr-2" />
            )}
            Save Changes
          </button>
        </div>
      </form>
    </div>
  )
}

function AgencySettings() {
  const { user } = useAuthStore()
  const [form, setForm] = useState({
    agency_name: user?.agency_name || '',
    agency_website: '',
    agency_phone: '',
    agency_address: '',
  })

  return (
    <div className="card p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-6">Agency Information</h2>

      {/* Logo */}
      <div className="flex items-center gap-4 mb-6 pb-6 border-b border-gray-200">
        <div className="w-24 h-16 bg-gray-100 rounded-lg flex items-center justify-center border-2 border-dashed border-gray-300">
          {user?.agency_logo_url ? (
            <img
              src={user.agency_logo_url}
              alt=""
              className="w-full h-full object-contain p-2"
            />
          ) : (
            <Upload className="w-6 h-6 text-gray-400" />
          )}
        </div>
        <div>
          <button className="btn-secondary">Upload Logo</button>
          <p className="text-xs text-gray-500 mt-1">PNG, JPG up to 2MB. Recommended: 200x100px</p>
        </div>
      </div>

      <form className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Agency Name</label>
          <input
            type="text"
            value={form.agency_name}
            onChange={(e) => setForm({ ...form, agency_name: e.target.value })}
            className="input"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Website</label>
          <input
            type="url"
            value={form.agency_website}
            onChange={(e) => setForm({ ...form, agency_website: e.target.value })}
            className="input"
            placeholder="https://example.com"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
          <input
            type="tel"
            value={form.agency_phone}
            onChange={(e) => setForm({ ...form, agency_phone: e.target.value })}
            className="input"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Address</label>
          <textarea
            value={form.agency_address}
            onChange={(e) => setForm({ ...form, agency_address: e.target.value })}
            className="input"
            rows={2}
          />
        </div>

        <div className="pt-4">
          <button type="submit" className="btn-primary">
            <Check className="w-4 h-4 mr-2" />
            Save Changes
          </button>
        </div>
      </form>
    </div>
  )
}

function PreferencesSettings() {
  const { user } = useAuthStore()
  const [form, setForm] = useState({
    preferred_language: user?.preferred_language || 'en',
    preferred_currency: user?.preferred_currency || 'USD',
    theme: 'light',
    default_view: 'split',
  })

  return (
    <div className="card p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-6">Preferences</h2>

      <form className="space-y-6">
        {/* Language */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            <Globe className="w-4 h-4 inline mr-2" />
            Language
          </label>
          <select
            value={form.preferred_language}
            onChange={(e) => setForm({ ...form, preferred_language: e.target.value })}
            className="input"
          >
            <option value="en">English</option>
            <option value="ru">Русский</option>
          </select>
        </div>

        {/* Currency */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Default Currency
          </label>
          <select
            value={form.preferred_currency}
            onChange={(e) => setForm({ ...form, preferred_currency: e.target.value })}
            className="input"
          >
            <option value="USD">USD - US Dollar</option>
            <option value="THB">THB - Thai Baht</option>
            <option value="IDR">IDR - Indonesian Rupiah</option>
            <option value="EUR">EUR - Euro</option>
            <option value="RUB">RUB - Russian Ruble</option>
          </select>
        </div>

        {/* Theme */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            <Palette className="w-4 h-4 inline mr-2" />
            Theme
          </label>
          <div className="flex gap-3">
            {['light', 'dark', 'system'].map((theme) => (
              <button
                key={theme}
                type="button"
                onClick={() => setForm({ ...form, theme })}
                className={clsx(
                  'px-4 py-2 rounded-lg border text-sm font-medium capitalize transition-colors',
                  form.theme === theme
                    ? 'border-primary-500 bg-primary-50 text-primary-700'
                    : 'border-gray-200 text-gray-600 hover:border-gray-300'
                )}
              >
                {theme}
              </button>
            ))}
          </div>
        </div>

        {/* Default view */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Default Projects View
          </label>
          <div className="flex gap-3">
            {[
              { id: 'split', label: 'Split (List + Map)' },
              { id: 'list', label: 'List Only' },
            ].map((view) => (
              <button
                key={view.id}
                type="button"
                onClick={() => setForm({ ...form, default_view: view.id })}
                className={clsx(
                  'px-4 py-2 rounded-lg border text-sm font-medium transition-colors',
                  form.default_view === view.id
                    ? 'border-primary-500 bg-primary-50 text-primary-700'
                    : 'border-gray-200 text-gray-600 hover:border-gray-300'
                )}
              >
                {view.label}
              </button>
            ))}
          </div>
        </div>

        <div className="pt-4">
          <button type="submit" className="btn-primary">
            <Check className="w-4 h-4 mr-2" />
            Save Preferences
          </button>
        </div>
      </form>
    </div>
  )
}

function NotificationSettings() {
  const [settings, setSettings] = useState({
    email_new_lead: true,
    email_collection_viewed: true,
    email_price_update: false,
    email_weekly_digest: true,
    push_new_lead: true,
    push_collection_inquiry: true,
    telegram_enabled: false,
    telegram_chat_id: '',
  })

  const toggleSetting = (key: keyof typeof settings) => {
    setSettings((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  return (
    <div className="card p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-6">Notification Settings</h2>

      <div className="space-y-6">
        {/* Email notifications */}
        <div>
          <h3 className="text-sm font-medium text-gray-900 mb-4">Email Notifications</h3>
          <div className="space-y-3">
            {[
              { key: 'email_new_lead', label: 'New lead from collection' },
              { key: 'email_collection_viewed', label: 'Collection viewed by client' },
              { key: 'email_price_update', label: 'Price updates for saved projects' },
              { key: 'email_weekly_digest', label: 'Weekly activity digest' },
            ].map((item) => (
              <label key={item.key} className="flex items-center justify-between cursor-pointer">
                <span className="text-sm text-gray-700">{item.label}</span>
                <button
                  type="button"
                  onClick={() => toggleSetting(item.key as keyof typeof settings)}
                  className={clsx(
                    'w-10 h-6 rounded-full transition-colors',
                    settings[item.key as keyof typeof settings] ? 'bg-primary-600' : 'bg-gray-300'
                  )}
                >
                  <span
                    className={clsx(
                      'block w-4 h-4 bg-white rounded-full shadow transform transition-transform',
                      settings[item.key as keyof typeof settings] ? 'translate-x-5' : 'translate-x-1'
                    )}
                  />
                </button>
              </label>
            ))}
          </div>
        </div>

        {/* Push notifications */}
        <div className="pt-6 border-t border-gray-200">
          <h3 className="text-sm font-medium text-gray-900 mb-4">Push Notifications</h3>
          <div className="space-y-3">
            {[
              { key: 'push_new_lead', label: 'New lead notification' },
              { key: 'push_collection_inquiry', label: 'Collection inquiry' },
            ].map((item) => (
              <label key={item.key} className="flex items-center justify-between cursor-pointer">
                <span className="text-sm text-gray-700">{item.label}</span>
                <button
                  type="button"
                  onClick={() => toggleSetting(item.key as keyof typeof settings)}
                  className={clsx(
                    'w-10 h-6 rounded-full transition-colors',
                    settings[item.key as keyof typeof settings] ? 'bg-primary-600' : 'bg-gray-300'
                  )}
                >
                  <span
                    className={clsx(
                      'block w-4 h-4 bg-white rounded-full shadow transform transition-transform',
                      settings[item.key as keyof typeof settings] ? 'translate-x-5' : 'translate-x-1'
                    )}
                  />
                </button>
              </label>
            ))}
          </div>
        </div>

        {/* Telegram */}
        <div className="pt-6 border-t border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-gray-900">Telegram Notifications</h3>
            <button
              type="button"
              onClick={() => toggleSetting('telegram_enabled')}
              className={clsx(
                'w-10 h-6 rounded-full transition-colors',
                settings.telegram_enabled ? 'bg-primary-600' : 'bg-gray-300'
              )}
            >
              <span
                className={clsx(
                  'block w-4 h-4 bg-white rounded-full shadow transform transition-transform',
                  settings.telegram_enabled ? 'translate-x-5' : 'translate-x-1'
                )}
              />
            </button>
          </div>
          {settings.telegram_enabled && (
            <div>
              <label className="block text-sm text-gray-600 mb-1">Telegram Chat ID</label>
              <input
                type="text"
                value={settings.telegram_chat_id}
                onChange={(e) => setSettings({ ...settings, telegram_chat_id: e.target.value })}
                className="input"
                placeholder="Your Telegram chat ID"
              />
              <p className="text-xs text-gray-500 mt-1">
                Start a chat with @PropBaseBot to get your chat ID
              </p>
            </div>
          )}
        </div>

        <div className="pt-4">
          <button type="submit" className="btn-primary">
            <Check className="w-4 h-4 mr-2" />
            Save Settings
          </button>
        </div>
      </div>
    </div>
  )
}

function SecuritySettings() {
  const [showChangePassword, setShowChangePassword] = useState(false)
  const [passwords, setPasswords] = useState({
    current: '',
    new: '',
    confirm: '',
  })

  return (
    <div className="space-y-6">
      {/* Change password */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Password</h2>
            <p className="text-sm text-gray-500">Change your account password</p>
          </div>
          <button
            onClick={() => setShowChangePassword(!showChangePassword)}
            className="btn-secondary"
          >
            <Key className="w-4 h-4 mr-2" />
            Change Password
          </button>
        </div>

        {showChangePassword && (
          <form className="space-y-4 pt-4 border-t border-gray-200">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Current Password
              </label>
              <input
                type="password"
                value={passwords.current}
                onChange={(e) => setPasswords({ ...passwords, current: e.target.value })}
                className="input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                New Password
              </label>
              <input
                type="password"
                value={passwords.new}
                onChange={(e) => setPasswords({ ...passwords, new: e.target.value })}
                className="input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Confirm New Password
              </label>
              <input
                type="password"
                value={passwords.confirm}
                onChange={(e) => setPasswords({ ...passwords, confirm: e.target.value })}
                className="input"
              />
            </div>
            <div className="flex gap-3">
              <button type="submit" className="btn-primary">
                Update Password
              </button>
              <button
                type="button"
                onClick={() => setShowChangePassword(false)}
                className="btn-secondary"
              >
                Cancel
              </button>
            </div>
          </form>
        )}
      </div>

      {/* Sessions */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Active Sessions</h2>
        <div className="space-y-3">
          <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div>
              <p className="font-medium text-gray-900">Current Session</p>
              <p className="text-sm text-gray-500">Chrome on MacOS • Bangkok, Thailand</p>
            </div>
            <span className="badge-success">Active</span>
          </div>
        </div>
        <button className="text-sm text-red-600 hover:text-red-700 mt-4">
          Sign out all other sessions
        </button>
      </div>

      {/* Danger zone */}
      <div className="card p-6 border-red-200">
        <h2 className="text-lg font-semibold text-red-600 mb-2">Danger Zone</h2>
        <p className="text-sm text-gray-600 mb-4">
          Once you delete your account, there is no going back. Please be certain.
        </p>
        <button className="text-sm text-red-600 hover:text-red-700 font-medium">
          Delete my account
        </button>
      </div>
    </div>
  )
}

function IntegrationsSettings() {
  const integrations = [
    {
      id: 'notion',
      name: 'Notion',
      description: 'Sync projects from Notion database',
      icon: '📝',
      link: '/notion-sync',
      color: 'bg-gray-100',
    },
    {
      id: 'price-ingestion',
      name: 'Price Ingestion',
      description: 'Upload and parse price lists (PDF, Excel, Google Sheets)',
      icon: '📊',
      link: '/price-ingestion',
      color: 'bg-blue-100',
    },
    {
      id: 'amocrm',
      name: 'amoCRM',
      description: 'Sync leads and contacts with amoCRM',
      icon: '🔗',
      link: null,
      color: 'bg-yellow-100',
      comingSoon: true,
    },
    {
      id: 'telegram',
      name: 'Telegram Bot',
      description: 'Receive notifications via Telegram',
      icon: '📱',
      link: null,
      color: 'bg-blue-100',
      comingSoon: true,
    },
  ]

  return (
    <div className="space-y-6">
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-2">Integrations</h2>
        <p className="text-gray-500 mb-6">Connect external services to PropBase</p>

        <div className="space-y-4">
          {integrations.map((integration) => (
            <div
              key={integration.id}
              className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50"
            >
              <div className="flex items-center gap-4">
                <div className={`w-12 h-12 ${integration.color} rounded-lg flex items-center justify-center text-2xl`}>
                  {integration.icon}
                </div>
                <div>
                  <h3 className="font-medium text-gray-900">
                    {integration.name}
                    {integration.comingSoon && (
                      <span className="ml-2 px-2 py-0.5 bg-gray-200 text-gray-600 text-xs rounded-full">
                        Coming soon
                      </span>
                    )}
                  </h3>
                  <p className="text-sm text-gray-500">{integration.description}</p>
                </div>
              </div>
              {integration.link ? (
                <Link
                  to={integration.link}
                  className="flex items-center gap-1 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                >
                  Configure
                  <ExternalLink className="w-4 h-4" />
                </Link>
              ) : (
                <button
                  disabled
                  className="px-4 py-2 bg-gray-100 text-gray-400 rounded-lg cursor-not-allowed"
                >
                  Configure
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Quick links */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-2 gap-4">
          <Link
            to="/notion-sync"
            className="p-4 border rounded-lg hover:bg-gray-50 flex items-center gap-3"
          >
            <span className="text-2xl">📝</span>
            <div>
              <h3 className="font-medium text-gray-900">Sync from Notion</h3>
              <p className="text-sm text-gray-500">Import projects</p>
            </div>
          </Link>
          <Link
            to="/price-ingestion"
            className="p-4 border rounded-lg hover:bg-gray-50 flex items-center gap-3"
          >
            <span className="text-2xl">📊</span>
            <div>
              <h3 className="font-medium text-gray-900">Upload Prices</h3>
              <p className="text-sm text-gray-500">Parse price lists</p>
            </div>
          </Link>
        </div>
      </div>
    </div>
  )
}
