const STATUS_CONFIG = {
  draft:     { bg: 'bg-gray-100 dark:bg-zinc-700/50',     text: 'text-gray-700 dark:text-zinc-300',   dot: 'bg-gray-400 dark:bg-zinc-400' },
  open:      { bg: 'bg-blue-100 dark:bg-blue-500/15',     text: 'text-blue-700 dark:text-blue-400',   dot: 'bg-blue-500' },
  in_review: { bg: 'bg-yellow-100 dark:bg-yellow-500/15', text: 'text-yellow-700 dark:text-yellow-400', dot: 'bg-yellow-500' },
  approved:  { bg: 'bg-green-100 dark:bg-green-500/15',   text: 'text-green-700 dark:text-green-400', dot: 'bg-green-500' },
  merged:    { bg: 'bg-purple-100 dark:bg-purple-500/15', text: 'text-purple-700 dark:text-purple-400', dot: 'bg-purple-500' },
  closed:    { bg: 'bg-red-100 dark:bg-red-500/15',       text: 'text-red-700 dark:text-red-400',     dot: 'bg-red-500' },
}

const STATUS_LABELS = {
  draft: 'Draft',
  open: 'Open',
  in_review: 'In Review',
  approved: 'Approved',
  merged: 'Merged',
  closed: 'Closed',
}

export default function StatusBadge({ status }) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.draft
  const label = STATUS_LABELS[status] || status

  return (
    <span
      data-testid="status-badge"
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${config.bg} ${config.text}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${config.dot}`} />
      {label}
    </span>
  )
}
