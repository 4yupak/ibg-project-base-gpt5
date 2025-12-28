import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { analyticsApi, pricesApi } from '../services/api'
import {
  TrendingUp,
  TrendingDown,
  Building2,
  Home,
  DollarSign,
  AlertTriangle,
  BarChart3,
  PieChart,
  Download,
  RefreshCw,
  Loader2,
  ChevronRight,
  Clock,
  CheckCircle,
  XCircle,
  FileWarning,
  Upload,
} from 'lucide-react'
import clsx from 'clsx'

interface DashboardStats {
  total_projects: number
  total_units: number
  available_units: number
  sold_percent: number
  average_price_usd: number
  price_change_weekly: number
  total_collections: number
  active_leads: number
}

interface ParsingError {
  id: number
  project_name: string
  file_name: string
  error_type: string
  error_message: string
  created_at: string
}

interface PriceVersion {
  id: number
  project_id: number
  project_name: string
  status: string
  total_units: number
  new_units: number
  updated_units: number
  price_changes: number
  created_at: string
}

export default function AnalyticsPage() {
  const [activeTab, setActiveTab] = useState<'overview' | 'parsing' | 'prices'>('overview')

  // Fetch dashboard stats
  const { data: stats, isLoading: statsLoading, refetch: refetchStats } = useQuery({
    queryKey: ['analytics-dashboard'],
    queryFn: () => analyticsApi.dashboard(),
  })

  // Fetch parsing errors
  const { data: parsingErrors, isLoading: errorsLoading } = useQuery({
    queryKey: ['parsing-errors'],
    queryFn: () => analyticsApi.parsingErrors({ limit: 50 }),
    enabled: activeTab === 'parsing',
  })

  // Fetch price versions requiring review
  const { data: priceVersions, isLoading: pricesLoading } = useQuery({
    queryKey: ['price-versions-review'],
    queryFn: () => pricesApi.requiresReview({ limit: 50 }),
    enabled: activeTab === 'prices',
  })

  const handleExport = async () => {
    try {
      const response = await analyticsApi.exportUnits({})
      const blob = response.data
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `units_export_${new Date().toISOString().split('T')[0]}.csv`
      a.click()
      URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Export failed:', error)
      alert('Export failed. Please try again.')
    }
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
          <p className="text-sm text-gray-500 mt-1">
            Dashboard, parsing status, and price updates
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button onClick={() => refetchStats()} className="btn-secondary">
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </button>
          <Link to="/price-ingestion" className="btn-secondary">
            <Upload className="w-4 h-4 mr-2" />
            Upload Prices
          </Link>
          <button onClick={handleExport} className="btn-primary">
            <Download className="w-4 h-4 mr-2" />
            Export Data
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 bg-gray-100 p-1 rounded-lg w-fit mb-6">
        {[
          { id: 'overview', label: 'Overview', icon: BarChart3 },
          { id: 'parsing', label: 'Parsing Errors', icon: FileWarning },
          { id: 'prices', label: 'Price Updates', icon: DollarSign },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as typeof activeTab)}
            className={clsx(
              'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
              activeTab === tab.id
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            )}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {activeTab === 'overview' && (
        <OverviewTab stats={stats} isLoading={statsLoading} />
      )}

      {activeTab === 'parsing' && (
        <ParsingErrorsTab errors={parsingErrors?.items} isLoading={errorsLoading} />
      )}

      {activeTab === 'prices' && (
        <PriceUpdatesTab versions={priceVersions?.items} isLoading={pricesLoading} />
      )}
    </div>
  )
}

function OverviewTab({
  stats,
  isLoading,
}: {
  stats?: DashboardStats
  isLoading: boolean
}) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    )
  }

  const statCards = [
    {
      label: 'Total Projects',
      value: stats?.total_projects || 0,
      icon: Building2,
      color: 'bg-blue-100 text-blue-600',
    },
    {
      label: 'Total Units',
      value: stats?.total_units || 0,
      icon: Home,
      color: 'bg-green-100 text-green-600',
    },
    {
      label: 'Available Units',
      value: stats?.available_units || 0,
      icon: Home,
      color: 'bg-yellow-100 text-yellow-600',
    },
    {
      label: 'Sold %',
      value: `${(stats?.sold_percent || 0).toFixed(1)}%`,
      icon: PieChart,
      color: 'bg-purple-100 text-purple-600',
    },
    {
      label: 'Avg Price',
      value: `$${((stats?.average_price_usd || 0) / 1000).toFixed(0)}K`,
      icon: DollarSign,
      color: 'bg-pink-100 text-pink-600',
    },
    {
      label: 'Weekly Change',
      value: `${stats?.price_change_weekly && stats.price_change_weekly >= 0 ? '+' : ''}${(stats?.price_change_weekly || 0).toFixed(1)}%`,
      icon: stats?.price_change_weekly && stats.price_change_weekly >= 0 ? TrendingUp : TrendingDown,
      color: stats?.price_change_weekly && stats.price_change_weekly >= 0 
        ? 'bg-green-100 text-green-600' 
        : 'bg-red-100 text-red-600',
    },
  ]

  return (
    <div>
      {/* Stats grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
        {statCards.map((stat) => (
          <div key={stat.label} className="card p-4">
            <div className={clsx('w-10 h-10 rounded-lg flex items-center justify-center mb-3', stat.color)}>
              <stat.icon className="w-5 h-5" />
            </div>
            <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
            <p className="text-sm text-gray-500">{stat.label}</p>
          </div>
        ))}
      </div>

      {/* Additional metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Collections */}
        <div className="card p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Collections</h3>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-3xl font-bold text-gray-900">{stats?.total_collections || 0}</p>
              <p className="text-sm text-gray-500">Total collections</p>
            </div>
            <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center">
              <Building2 className="w-8 h-8 text-primary-600" />
            </div>
          </div>
        </div>

        {/* Leads */}
        <div className="card p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Active Leads</h3>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-3xl font-bold text-gray-900">{stats?.active_leads || 0}</p>
              <p className="text-sm text-gray-500">Leads this month</p>
            </div>
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
              <TrendingUp className="w-8 h-8 text-green-600" />
            </div>
          </div>
        </div>
      </div>

      {/* Chart placeholder */}
      <div className="card p-6 mt-6">
        <h3 className="font-semibold text-gray-900 mb-4">Price Trends (Coming Soon)</h3>
        <div className="h-64 bg-gray-50 rounded-lg flex items-center justify-center">
          <div className="text-center text-gray-400">
            <BarChart3 className="w-12 h-12 mx-auto mb-2" />
            <p>Chart visualization coming soon</p>
          </div>
        </div>
      </div>
    </div>
  )
}

function ParsingErrorsTab({
  errors,
  isLoading,
}: {
  errors?: ParsingError[]
  isLoading: boolean
}) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    )
  }

  if (!errors || errors.length === 0) {
    return (
      <div className="card p-12 text-center">
        <CheckCircle className="w-16 h-16 text-green-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">No Parsing Errors</h3>
        <p className="text-gray-500">All price files have been processed successfully</p>
      </div>
    )
  }

  return (
    <div className="card divide-y divide-gray-200">
      {errors.map((error) => (
        <div key={error.id} className="p-4 hover:bg-gray-50">
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 rounded-lg bg-red-100 flex items-center justify-center flex-shrink-0">
              <AlertTriangle className="w-5 h-5 text-red-600" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <h4 className="font-medium text-gray-900">{error.project_name}</h4>
                <span className="badge-warning text-xs">{error.error_type}</span>
              </div>
              <p className="text-sm text-gray-600 mt-1">{error.file_name}</p>
              <p className="text-sm text-red-600 mt-2">{error.error_message}</p>
              <p className="text-xs text-gray-400 mt-2 flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {new Date(error.created_at).toLocaleString()}
              </p>
            </div>
            <button className="btn-secondary text-sm">
              Review
              <ChevronRight className="w-4 h-4 ml-1" />
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}

function PriceUpdatesTab({
  versions,
  isLoading,
}: {
  versions?: PriceVersion[]
  isLoading: boolean
}) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    )
  }

  if (!versions || versions.length === 0) {
    return (
      <div className="card p-12 text-center">
        <CheckCircle className="w-16 h-16 text-green-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">All Caught Up</h3>
        <p className="text-gray-500">No price updates requiring review</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {versions.map((version) => (
        <div key={version.id} className="card p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-primary-100 flex items-center justify-center">
                <DollarSign className="w-6 h-6 text-primary-600" />
              </div>
              <div>
                <h4 className="font-medium text-gray-900">{version.project_name}</h4>
                <div className="flex items-center gap-4 text-sm text-gray-500 mt-1">
                  <span>{version.total_units} units</span>
                  {version.new_units > 0 && (
                    <span className="text-green-600">+{version.new_units} new</span>
                  )}
                  {version.price_changes > 0 && (
                    <span className="text-orange-600">{version.price_changes} price changes</span>
                  )}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <div className="text-right">
                <span
                  className={clsx(
                    'badge',
                    version.status === 'pending'
                      ? 'badge-warning'
                      : version.status === 'approved'
                        ? 'badge-success'
                        : 'badge-gray'
                  )}
                >
                  {version.status}
                </span>
                <p className="text-xs text-gray-400 mt-1">
                  {new Date(version.created_at).toLocaleDateString()}
                </p>
              </div>

              {version.status === 'pending' && (
                <div className="flex items-center gap-2">
                  <button className="p-2 rounded-lg text-green-600 hover:bg-green-50" title="Approve">
                    <CheckCircle className="w-5 h-5" />
                  </button>
                  <button className="p-2 rounded-lg text-red-600 hover:bg-red-50" title="Reject">
                    <XCircle className="w-5 h-5" />
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
