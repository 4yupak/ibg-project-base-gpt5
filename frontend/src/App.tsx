import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'

// Layouts
import MainLayout from './components/layout/MainLayout'
import AuthLayout from './components/layout/AuthLayout'
import AdminLayout from './components/layout/AdminLayout'

// Pages
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import ProjectsPage from './pages/ProjectsPage'
import ProjectDetailPage from './pages/ProjectDetailPage'
import CollectionsPage from './pages/CollectionsPage'
import CollectionDetailPage from './pages/CollectionDetailPage'
import PublicCollectionPage from './pages/PublicCollectionPage'
import AnalyticsPage from './pages/AnalyticsPage'
import SettingsPage from './pages/SettingsPage'
import PriceIngestionPage from './pages/PriceIngestionPage'
import NotionSyncPage from './pages/NotionSyncPage'
import SmartParserPage from './pages/SmartParserPage'

// Admin Pages
import AdminDashboardPage from './pages/admin/AdminDashboardPage'
import AdminProjectsPage from './pages/admin/AdminProjectsPage'
import AdminProjectEditPage from './pages/admin/AdminProjectEditPage'

// Protected Route component
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore()
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  
  return <>{children}</>
}

function App() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/c/:token" element={<PublicCollectionPage />} />
      
      {/* Auth routes */}
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
      </Route>
      
      {/* Admin routes */}
      <Route
        element={
          <ProtectedRoute>
            <AdminLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/admin" element={<AdminDashboardPage />} />
        <Route path="/admin/projects" element={<AdminProjectsPage />} />
        <Route path="/admin/projects/new" element={<AdminProjectEditPage />} />
        <Route path="/admin/projects/:id" element={<AdminProjectEditPage />} />
        <Route path="/admin/parser" element={<SmartParserPage />} />
        {/* Placeholder routes - will be implemented */}
        <Route path="/admin/units" element={<div className="p-6"><h1 className="text-2xl font-bold">Units Management</h1><p className="text-gray-500 mt-2">Coming soon...</p></div>} />
        <Route path="/admin/media" element={<div className="p-6"><h1 className="text-2xl font-bold">Media Library</h1><p className="text-gray-500 mt-2">Coming soon...</p></div>} />
        <Route path="/admin/users" element={<div className="p-6"><h1 className="text-2xl font-bold">Users Management</h1><p className="text-gray-500 mt-2">Coming soon...</p></div>} />
        <Route path="/admin/settings" element={<div className="p-6"><h1 className="text-2xl font-bold">Admin Settings</h1><p className="text-gray-500 mt-2">Coming soon...</p></div>} />
      </Route>
      
      {/* Protected routes - main app */}
      <Route
        element={
          <ProtectedRoute>
            <MainLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<Navigate to="/projects" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/projects" element={<ProjectsPage />} />
        <Route path="/projects/:id" element={<ProjectDetailPage />} />
        <Route path="/collections" element={<CollectionsPage />} />
        <Route path="/collections/:id" element={<CollectionDetailPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/price-ingestion" element={<PriceIngestionPage />} />
        <Route path="/smart-parser" element={<SmartParserPage />} />
        <Route path="/notion-sync" element={<NotionSyncPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
      
      {/* 404 */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
