import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getNotifications, markNotificationRead, markAllNotificationsRead } from '../api'
import { useNotificationCount } from '../components/NotificationToast'
import PageHeader from '../components/PageHeader'
import EmptyState from '../components/EmptyState'
import { Skeleton } from '../components/Skeleton'
import { BellIcon, CheckIcon, EnvelopeOpenIcon } from '@heroicons/react/24/outline'
import { cn } from '../utils/classNames'
import { relativeTime } from '../utils/dates'

const EVENT_ICONS = {
  comment_added: '💬',
  review_submitted: '📝',
  pr_state_changed: '🔄',
  comment_resolved: '✅',
}

export default function NotificationsPage() {
  const queryClient = useQueryClient()
  const { resetCount } = useNotificationCount()
  const [filter, setFilter] = useState('all')

  const { data, isLoading } = useQuery({
    queryKey: ['notifications', filter],
    queryFn: () => getNotifications(filter === 'unread'),
  })

  const markReadMutation = useMutation({
    mutationFn: markNotificationRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })

  const markAllMutation = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
      resetCount()
    },
  })

  const notifications = data?.data?.results || []

  const grouped = {}
  for (const n of notifications) {
    const dateKey = new Date(n.created_at).toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
    if (!grouped[dateKey]) grouped[dateKey] = []
    grouped[dateKey].push(n)
  }

  return (
    <div>
      <PageHeader
        breadcrumbs={[{ label: 'Notifications' }]}
        actions={
          <div className="flex items-center gap-2">
            <div className="flex rounded-lg border border-zinc-200 dark:border-zinc-700 overflow-hidden">
              {['all', 'unread'].map((f) => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={cn(
                    'px-3 py-1.5 text-[12px] font-medium capitalize transition-colors',
                    filter === f
                      ? 'bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400'
                      : 'text-zinc-500 dark:text-zinc-400 hover:bg-zinc-50 dark:hover:bg-zinc-800'
                  )}
                >
                  {f}
                </button>
              ))}
            </div>
            <button
              onClick={() => markAllMutation.mutate()}
              disabled={markAllMutation.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors disabled:opacity-50"
            >
              <EnvelopeOpenIcon className="h-3.5 w-3.5" />
              Mark all read
            </button>
          </div>
        }
      />

      <div className="max-w-3xl mx-auto px-6 py-6">
        {isLoading ? (
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-16 rounded-lg" />
            ))}
          </div>
        ) : notifications.length === 0 ? (
          <EmptyState
            icon={BellIcon}
            title="No notifications"
            description={filter === 'unread' ? "You're all caught up!" : 'Notifications will appear here when someone comments on your PRs, submits reviews, or changes PR status.'}
          />
        ) : (
          <div className="space-y-6">
            {Object.entries(grouped).map(([date, items]) => (
              <div key={date}>
                <h3 className="text-[11px] font-semibold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider mb-2 px-1">
                  {date}
                </h3>
                <div className="space-y-1">
                  {items.map((n) => (
                    <div
                      key={n.id}
                      className={cn(
                        'flex items-start gap-3 p-3 rounded-lg transition-colors group',
                        !n.is_read
                          ? 'bg-indigo-50/50 dark:bg-indigo-500/5 border-l-2 border-indigo-500'
                          : 'hover:bg-zinc-50 dark:hover:bg-zinc-800/50 border-l-2 border-transparent'
                      )}
                    >
                      <span className="text-base mt-0.5 flex-shrink-0">
                        {EVENT_ICONS[n.event_type] || '🔔'}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className={cn(
                          'text-[13px]',
                          !n.is_read
                            ? 'font-medium text-zinc-900 dark:text-zinc-100'
                            : 'text-zinc-600 dark:text-zinc-400'
                        )}>
                          {n.message}
                        </p>
                        <p className="text-[11px] text-zinc-400 dark:text-zinc-500 mt-0.5">
                          {relativeTime(n.created_at)}
                        </p>
                      </div>
                      {!n.is_read && (
                        <button
                          onClick={() => markReadMutation.mutate(n.id)}
                          disabled={markReadMutation.isPending}
                          className="opacity-0 group-hover:opacity-100 p-1 rounded text-zinc-400 hover:text-indigo-500 transition-all"
                          title="Mark as read"
                        >
                          <CheckIcon className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
