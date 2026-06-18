import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { ArrowRightOnRectangleIcon } from '@heroicons/react/24/outline'

export default function Navbar() {
  const { user, logout } = useAuth()

  if (!user) return null

  return (
    <nav className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
      <div className="flex items-center gap-6">
        <Link to="/" className="text-lg font-semibold text-gray-900">
          CodeReview
        </Link>
      </div>
      <div className="flex items-center gap-4">
        <span className="text-sm text-gray-600">{user.username}</span>
        <span className="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-600">{user.role}</span>
        <button onClick={logout} className="text-gray-400 hover:text-gray-600" title="Logout">
          <ArrowRightOnRectangleIcon className="h-5 w-5" />
        </button>
      </div>
    </nav>
  )
}
