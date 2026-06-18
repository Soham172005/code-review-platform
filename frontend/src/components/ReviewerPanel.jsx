import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  CheckIcon,
  PencilSquareIcon,
  ArrowsPointingInIcon,
  XMarkIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline'
import StatusBadge from './StatusBadge'
import { transitionPR, submitReview } from '../api'
import { useAuth } from '../context/AuthContext'
import { cn } from '../utils/classNames'

const TRANSITIONS = {
  draft: [{ name: 'open_pr', label: 'Open PR', icon: ArrowPathIcon, style: 'bg-blue-600 hover:bg-blue-700 text-white' }],
  open: [{ name: 'submit_for_review', label: 'Request Review', icon: PencilSquareIcon, style: 'bg-amber-600 hover:bg-amber-700 text-white' }],
  in_review: [
    { name: 'approve', label: 'Approve', icon: CheckIcon, style: 'bg-green-600 hover:bg-green-700 text-white' },
  ],
  approved: [{ name: 'merge', label: 'Merge PR', icon: ArrowsPointingInIcon, style: 'bg-purple-600 hover:bg-purple-700 text-white' }],
}

export default function ReviewerPanel({ pr }) {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [reviewStatus, setReviewStatus] = useState('approved')

  const transitionMut = useMutation({
    mutationFn: ({ transition }) => transitionPR(pr.id, transition),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pr', pr.id] })
      toast.success('PR status updated')
    },
    onError: (err) => {
      toast.error(err.response?.data?.detail || err.response?.data?.error || 'Transition failed')
    },
  })

  const reviewMut = useMutation({
    mutationFn: (data) => submitReview(pr.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pr', pr.id] })
      toast.success('Review submitted')
    },
    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Review failed')
    },
  })

  const transitions = TRANSITIONS[pr.status] || []
  const canClose = ['draft', 'open', 'in_review', 'approved'].includes(pr.status)
  const canReopen = pr.status === 'closed'
  const isReviewerOrAdmin = user?.role === 'reviewer' || user?.role === 'admin'

  return (
    <div className="space-y-5">
      <Section label="Status">
        <StatusBadge status={pr.status} />
      </Section>

      <Section label="Author">
        <div className="flex items-center gap-2">
          <div className="h-6 w-6 rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-white text-[9px] font-semibold">
            {(pr.author?.username || 'U').slice(0, 2).toUpperCase()}
          </div>
          <span className="text-[13px] text-zinc-700 dark:text-zinc-300">
            {pr.author?.username || pr.author}
          </span>
        </div>
      </Section>

      <Section label="Branches">
        <div className="flex items-center gap-2 text-xs font-mono">
          <span className="px-2 py-1 rounded-md bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-100 dark:border-indigo-500/20">
            {pr.head_branch}
          </span>
          <span className="text-zinc-400 dark:text-zinc-500">&rarr;</span>
          <span className="px-2 py-1 rounded-md bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 border border-zinc-200 dark:border-zinc-700">
            {pr.base_branch}
          </span>
        </div>
      </Section>

      <Section label="Actions">
        <div className="space-y-2">
          {transitions.map((t) => {
            const Icon = t.icon
            return (
              <button
                key={t.name}
                onClick={() => transitionMut.mutate({ transition: t.name })}
                disabled={transitionMut.isPending}
                className={cn(
                  'w-full flex items-center justify-center gap-2 text-[13px] font-medium px-3 py-2.5 rounded-lg transition-colors disabled:opacity-50',
                  t.style
                )}
              >
                <Icon className="h-4 w-4" />
                {t.label}
              </button>
            )
          })}

          {canClose && (
            <button
              onClick={() => transitionMut.mutate({ transition: 'close' })}
              disabled={transitionMut.isPending}
              className="w-full flex items-center justify-center gap-2 text-[13px] font-medium px-3 py-2.5 rounded-lg border border-red-200 dark:border-red-800/50 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-500/10 transition-colors disabled:opacity-50"
            >
              <XMarkIcon className="h-4 w-4" />
              Close PR
            </button>
          )}

          {canReopen && (
            <button
              onClick={() => transitionMut.mutate({ transition: 'reopen' })}
              disabled={transitionMut.isPending}
              className="w-full flex items-center justify-center gap-2 text-[13px] font-medium px-3 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white transition-colors disabled:opacity-50"
            >
              <ArrowPathIcon className="h-4 w-4" />
              Reopen PR
            </button>
          )}
        </div>
      </Section>

      {pr.status === 'in_review' && isReviewerOrAdmin && (
        <Section label="Submit Review" divider>
          <div className="space-y-2.5">
            <select
              value={reviewStatus}
              onChange={(e) => setReviewStatus(e.target.value)}
              className="w-full text-[13px] border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-800/50 text-zinc-900 dark:text-zinc-100 rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-colors"
            >
              <option value="approved">Approve</option>
              <option value="changes_requested">Request Changes</option>
            </select>
            <button
              onClick={() => reviewMut.mutate({ status: reviewStatus })}
              disabled={reviewMut.isPending}
              className="w-full text-[13px] font-medium text-white px-3 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 transition-colors disabled:opacity-50"
            >
              Submit Review
            </button>
          </div>
        </Section>
      )}
    </div>
  )
}

function Section({ label, divider, children }) {
  return (
    <div className={cn(divider && 'pt-5 border-t border-zinc-200 dark:border-zinc-800')}>
      <h3 className="text-[11px] font-semibold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider mb-2.5">
        {label}
      </h3>
      {children}
    </div>
  )
}
