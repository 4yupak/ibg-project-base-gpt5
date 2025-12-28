import { Outlet, Navigate } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
import { Building2 } from 'lucide-react'

export default function AuthLayout() {
  const { isAuthenticated } = useAuthStore()

  if (isAuthenticated) {
    return <Navigate to="/" replace />
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      {/* Logo */}
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex items-center justify-center gap-2">
          <div className="w-12 h-12 bg-primary-600 rounded-xl flex items-center justify-center">
            <Building2 className="w-7 h-7 text-white" />
          </div>
        </div>
        <h2 className="mt-4 text-center text-3xl font-bold text-gray-900">
          PropBase
        </h2>
        <p className="mt-2 text-center text-sm text-gray-600">
          Real Estate Property Database Platform
        </p>
      </div>

      {/* Form container */}
      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow-sm rounded-xl sm:px-10 border border-gray-200">
          <Outlet />
        </div>
      </div>
    </div>
  )
}
