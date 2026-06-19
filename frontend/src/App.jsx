import { useState } from 'react'
import { Routes, Route } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import { NotificationProvider } from './components/NotificationToast'
import Sidebar from './components/Sidebar'
import ProtectedRoute from './components/ProtectedRoute'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import RepositoryListPage from './pages/RepositoryListPage'
import PRListPage from './pages/PRListPage'
import PRDetailPage from './pages/PRDetailPage'
import NotificationsPage from './pages/NotificationsPage'
import { cn } from './utils/classNames'

export default function App() {
  const { user } = useAuth()
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  return (
    <NotificationProvider>
      <div className="min-h-screen bg-zinc-50 dark:bg-zinc-900 transition-colors">
        {user && (
          <Sidebar
            collapsed={sidebarCollapsed}
            onToggle={() => setSidebarCollapsed((p) => !p)}
          />
        )}
        <main
          className={cn(
            'min-h-screen transition-[padding] duration-200',
            user && (sidebarCollapsed ? 'pl-16' : 'pl-60')
          )}
        >
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/" element={<ProtectedRoute><RepositoryListPage /></ProtectedRoute>} />
            <Route path="/repos/:repoId/prs" element={<ProtectedRoute><PRListPage /></ProtectedRoute>} />
            <Route path="/prs/:id" element={<ProtectedRoute><PRDetailPage /></ProtectedRoute>} />
            <Route path="/prs" element={<ProtectedRoute><PlaceholderPage title="Pull Requests" /></ProtectedRoute>} />
            <Route path="/notifications" element={<ProtectedRoute><NotificationsPage /></ProtectedRoute>} />
          </Routes>
        </main>
      </div>
    </NotificationProvider>
  )
}

function PlaceholderPage({ title }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh]">
      <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">{title}</p>
      <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">Coming soon</p>
    </div>
  )
}
