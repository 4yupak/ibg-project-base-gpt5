import { useQuery } from '@tanstack/react-query'
import { analyticsApi } from '../services/api'
import {
  Building2,
  Home,
  DollarSign,
  AlertTriangle,
  TrendingUp,
  Clock,
  Loader2,
} from 'lucide-react'

export default function DashboardPage() {
  const { data: dashboard, isLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => analyticsApi.dashboard(),
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    )
  }

  const stats = [
    {
      name: 'Total Projects',
      value: dashboard?.total_projects || 0,
      icon: Building2,
      color: 'bg-blue-500',
    },
    {
      name: 'Total Units',
      value: dashboard?.total_units || 0,
      icon: Home,
      color: 'bg-green-500',
    },
    {
      name: 'Available Units',
      value: dashboard?.available_units || 0,
      icon: TrendingUp,
      color: 'bg-purple-500',
    },
    {
      name: 'Avg Price',
      value: dashboard?.average_price_usd
        ? `$${(dashboard.average_price_usd / 1000).toFixed(0)}K`
        : 'N/A',
      icon: DollarSign,
      color: 'bg-yellow-500',
    },
  ]

  const alerts = [
    {
      name: 'Pending Reviews',
      value: dashboard?.pending_reviews || 0,
      icon: Clock,
      color: 'text-orange-600 bg-orange-100',
    },
    {
      name: 'Parsing Errors',
      value: dashboard?.parsing_errors || 0,
      icon: AlertTriangle,
      color: 'text-red-600 bg-red-100',
    },
    {
      name: 'Recent Updates',
      value: dashboard?.recent_price_updates || 0,
      icon: TrendingUp,
      color: 'text-green-600 bg-green-100',
    },
  ]

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h1>

      {/* Stats grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {stats.map((stat) => (
          <div key={stat.name} className="card p-6">
            <div className="flex items-center gap-4">
              <div className={`w-12 h-12 ${stat.color} rounded-lg flex items-center justify-center`}>
                <stat.icon className="w-6 h-6 text-white" />
              </div>
              <div>
                <p className="text-sm text-gray-500">{stat.name}</p>
                <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Alerts */}
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        {alerts.map((alert) => (
          <div key={alert.name} className="card p-4 flex items-center gap-4">
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${alert.color}`}>
              <alert.icon className="w-5 h-5" />
            </div>
            <div>
              <p className="text-sm text-gray-500">{alert.name}</p>
              <p className="text-xl font-semibold text-gray-900">{alert.value}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Projects by Status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Projects by Status</h3>
          <div className="space-y-3">
            {dashboard?.projects_by_status &&
              Object.entries(dashboard.projects_by_status).map(([status, count]) => (
                <div key={status} className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 capitalize">
                    {status.replace('_', ' ')}
                  </span>
                  <span className="font-medium text-gray-900">{count as number}</span>
                </div>
              ))}
          </div>
        </div>

        <div className="card p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Units by Type</h3>
          <div className="space-y-3">
            {dashboard?.units_by_type &&
              Object.entries(dashboard.units_by_type).map(([type, count]) => (
                <div key={type} className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 capitalize">
                    {type.replace('_', ' ')}
                  </span>
                  <span className="font-medium text-gray-900">{count as number}</span>
                </div>
              ))}
          </div>
        </div>
      </div>
    </div>
  )
}
