import { NavLink } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import {
  FolderIcon,
  CodeBracketSquareIcon,
  BellIcon,
  ArrowRightOnRectangleIcon,
  SunIcon,
  MoonIcon,
  Bars3Icon,
} from '@heroicons/react/24/outline'
import { cn } from '../utils/classNames'

const NAV_ITEMS = [
  { to: '/', icon: FolderIcon, label: 'Repositories', end: true },
  { to: '/prs', icon: CodeBracketSquareIcon, label: 'Pull Requests' },
  { to: '/notifications', icon: BellIcon, label: 'Notifications' },
]

export default function Sidebar({ collapsed, onToggle }) {
  const { user, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()

  if (!user) return null

  const initials = (user.username || 'U').slice(0, 2).toUpperCase()

  return (
    <aside
      className={cn(
        'fixed top-0 left-0 h-screen flex flex-col border-r z-40 transition-[width] duration-200',
        'bg-white dark:bg-zinc-950 border-zinc-200 dark:border-zinc-800',
        collapsed ? 'w-16' : 'w-60'
      )}
    >
      <div className={cn(
        'flex items-center h-14 border-b border-zinc-200 dark:border-zinc-800',
        collapsed ? 'justify-center px-2' : 'px-4'
      )}>
        <div className="flex items-center gap-3 min-w-0">
          <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center flex-shrink-0">
            <CodeBracketSquareIcon className="h-4.5 w-4.5 text-white h-[18px] w-[18px]" />
          </div>
          {!collapsed && (
            <span className="text-sm font-bold text-zinc-900 dark:text-zinc-100 tracking-tight">
              CodeReview
            </span>
          )}
        </div>
      </div>

      <nav className="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto">
        {NAV_ITEMS.map(({ to, icon: Icon, label, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) => cn(
              'flex items-center gap-3 rounded-lg text-[13px] font-medium transition-colors',
              collapsed ? 'justify-center px-0 py-2.5 mx-auto w-10 h-10' : 'px-3 py-2',
              isActive
                ? 'bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400'
                : 'text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800/70 hover:text-zinc-900 dark:hover:text-zinc-200'
            )}
          >
            <Icon className="h-[18px] w-[18px] flex-shrink-0" />
            {!collapsed && label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-zinc-200 dark:border-zinc-800 p-2 space-y-0.5">
        <button
          onClick={toggleTheme}
          className={cn(
            'flex items-center gap-3 w-full rounded-lg text-[13px] text-zinc-500 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800/70 hover:text-zinc-900 dark:hover:text-zinc-200 transition-colors',
            collapsed ? 'justify-center p-2.5' : 'px-3 py-2'
          )}
          title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {theme === 'dark' ? <SunIcon className="h-[18px] w-[18px]" /> : <MoonIcon className="h-[18px] w-[18px]" />}
          {!collapsed && (theme === 'dark' ? 'Light mode' : 'Dark mode')}
        </button>

        <button
          onClick={onToggle}
          className={cn(
            'flex items-center gap-3 w-full rounded-lg text-[13px] text-zinc-500 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800/70 hover:text-zinc-900 dark:hover:text-zinc-200 transition-colors',
            collapsed ? 'justify-center p-2.5' : 'px-3 py-2'
          )}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          <Bars3Icon className="h-[18px] w-[18px]" />
          {!collapsed && 'Collapse'}
        </button>

        <div className={cn(
          'flex items-center gap-3 rounded-lg mt-1 pt-2 border-t border-zinc-100 dark:border-zinc-800/50',
          collapsed ? 'justify-center px-0 py-1' : 'px-3 py-2'
        )}>
          <div className="h-8 w-8 rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-white text-xs font-semibold flex-shrink-0">
            {initials}
          </div>
          {!collapsed && (
            <>
              <div className="flex-1 min-w-0">
                <p className="text-[13px] font-medium text-zinc-900 dark:text-zinc-100 truncate">{user.username}</p>
                <p className="text-[11px] text-zinc-500 dark:text-zinc-500 capitalize">{user.role}</p>
              </div>
              <button
                onClick={logout}
                className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors"
                title="Sign out"
              >
                <ArrowRightOnRectangleIcon className="h-4 w-4" />
              </button>
            </>
          )}
        </div>
      </div>
    </aside>
  )
}
