import { Link } from 'react-router-dom'
import { ChevronRightIcon } from '@heroicons/react/20/solid'

export default function PageHeader({ breadcrumbs = [], actions }) {
  return (
    <header className="sticky top-0 z-10 h-14 flex items-center justify-between px-6 border-b border-zinc-200 dark:border-zinc-800 bg-white/80 dark:bg-zinc-900/80 backdrop-blur-sm">
      <nav className="flex items-center gap-1 text-sm">
        {breadcrumbs.map((crumb, i) => (
          <span key={i} className="flex items-center gap-1">
            {i > 0 && <ChevronRightIcon className="h-4 w-4 text-zinc-300 dark:text-zinc-600" />}
            {crumb.to ? (
              <Link
                to={crumb.to}
                className="text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 transition-colors"
              >
                {crumb.label}
              </Link>
            ) : (
              <span className="font-medium text-zinc-900 dark:text-zinc-100">{crumb.label}</span>
            )}
          </span>
        ))}
      </nav>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </header>
  )
}
