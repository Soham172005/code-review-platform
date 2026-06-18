import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listPRs, createPR, getRepo } from '../api'
import { relativeTime } from '../utils/dates'
import Modal from '../components/Modal'
import PageHeader from '../components/PageHeader'
import StatusBadge from '../components/StatusBadge'
import EmptyState from '../components/EmptyState'
import { SkeletonRow } from '../components/Skeleton'
import { PlusIcon, CodeBracketSquareIcon } from '@heroicons/react/24/outline'
import { cn } from '../utils/classNames'
import toast from 'react-hot-toast'

const FILTER_TABS = [
  { key: 'all', label: 'All' },
  { key: 'open', label: 'Open' },
  { key: 'merged', label: 'Merged' },
  { key: 'closed', label: 'Closed' },
]

function filterPRs(prs, filter) {
  if (filter === 'all') return prs
  if (filter === 'open') return prs.filter(pr => ['draft', 'open', 'in_review', 'approved'].includes(pr.status))
  if (filter === 'merged') return prs.filter(pr => pr.status === 'merged')
  if (filter === 'closed') return prs.filter(pr => pr.status === 'closed')
  return prs
}

export default function PRListPage() {
  const { repoId } = useParams()
  const [showModal, setShowModal] = useState(false)
  const [filter, setFilter] = useState('all')
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [baseBranch, setBaseBranch] = useState('main')
  const [headBranch, setHeadBranch] = useState('')
  const queryClient = useQueryClient()

  const { data: repo } = useQuery({
    queryKey: ['repo', repoId],
    queryFn: () => getRepo(repoId).then((res) => res.data),
  })

  const { data, isLoading } = useQuery({
    queryKey: ['prs', repoId],
    queryFn: () => listPRs(repoId).then((res) => res.data),
  })

  const createMut = useMutation({
    mutationFn: (prData) => createPR(repoId, prData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prs', repoId] })
      setShowModal(false)
      setTitle('')
      setDescription('')
      setHeadBranch('')
      toast.success('Pull request created')
    },
    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Failed to create PR')
    },
  })

  const handleCreate = (e) => {
    e.preventDefault()
    createMut.mutate({
      title,
      description,
      base_branch: baseBranch,
      head_branch: headBranch,
    })
  }

  const prs = data?.results || data || []
  const filtered = filterPRs(prs, filter)

  return (
    <div className="min-h-screen">
      <PageHeader
        breadcrumbs={[
          { label: 'Repositories', to: '/' },
          { label: repo?.name || 'Repository' },
        ]}
        actions={
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-700 text-white px-3.5 py-2 rounded-lg text-[13px] font-medium transition-colors"
          >
            <PlusIcon className="h-4 w-4" />
            New PR
          </button>
        }
      />

      <div className="p-6 max-w-5xl mx-auto">
        <div className="flex items-center gap-1 mb-4 border-b border-zinc-200 dark:border-zinc-800">
          {FILTER_TABS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setFilter(key)}
              className={cn(
                'px-3.5 py-2.5 text-[13px] font-medium border-b-2 transition-colors -mb-px',
                filter === key
                  ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                  : 'border-transparent text-zinc-500 dark:text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-300 hover:border-zinc-300 dark:hover:border-zinc-600'
              )}
            >
              {label}
              {key !== 'all' && (
                <span className="ml-1.5 text-[11px] px-1.5 py-0.5 rounded-full bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400">
                  {filterPRs(prs, key).length}
                </span>
              )}
            </button>
          ))}
        </div>

        {isLoading ? (
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden">
            {Array.from({ length: 5 }).map((_, i) => (
              <SkeletonRow key={i} />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={CodeBracketSquareIcon}
            title={filter === 'all' ? 'No pull requests yet' : `No ${filter} pull requests`}
            description={filter === 'all' ? 'Create a pull request to start a code review.' : 'Try changing the filter.'}
            action={filter === 'all' && (
              <button
                onClick={() => setShowModal(true)}
                className="flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              >
                <PlusIcon className="h-4 w-4" />
                New Pull Request
              </button>
            )}
          />
        ) : (
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden divide-y divide-zinc-100 dark:divide-zinc-800/50">
            {filtered.map((pr) => (
              <Link
                key={pr.id}
                to={`/prs/${pr.id}`}
                className="flex items-center gap-4 px-5 py-3.5 hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-colors group"
              >
                <StatusBadge status={pr.status} />

                <div className="flex-1 min-w-0">
                  <h3 className="text-[13px] font-medium text-zinc-900 dark:text-zinc-100 truncate group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                    {pr.title}
                  </h3>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-[11px] text-zinc-400 dark:text-zinc-500">
                      #{pr.id}
                    </span>
                    <span className="text-zinc-300 dark:text-zinc-700">&middot;</span>
                    <span className="text-[11px] text-zinc-500 dark:text-zinc-400">
                      {pr.author?.username || pr.author}
                    </span>
                    {(pr.base_branch || pr.head_branch) && (
                      <>
                        <span className="text-zinc-300 dark:text-zinc-700">&middot;</span>
                        <span className="text-[11px] font-mono text-zinc-400 dark:text-zinc-500 truncate">
                          {pr.base_branch} &larr; {pr.head_branch}
                        </span>
                      </>
                    )}
                  </div>
                </div>

                <span className="text-[11px] text-zinc-400 dark:text-zinc-500 flex-shrink-0">
                  {relativeTime(pr.created_at)}
                </span>
              </Link>
            ))}
          </div>
        )}
      </div>

      <Modal open={showModal} onClose={() => setShowModal(false)} title="New Pull Request">
        <form onSubmit={handleCreate} className="space-y-4">
          <div>
            <label className="block text-[13px] font-medium text-zinc-700 dark:text-zinc-300 mb-1.5">Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              className="w-full border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800/50 text-zinc-900 dark:text-zinc-100 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-colors"
              placeholder="Feature: add dark mode"
            />
          </div>
          <div>
            <label className="block text-[13px] font-medium text-zinc-700 dark:text-zinc-300 mb-1.5">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800/50 text-zinc-900 dark:text-zinc-100 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-colors resize-none"
              placeholder="Describe your changes..."
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[13px] font-medium text-zinc-700 dark:text-zinc-300 mb-1.5">Base</label>
              <input
                type="text"
                value={baseBranch}
                onChange={(e) => setBaseBranch(e.target.value)}
                required
                className="w-full border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800/50 text-zinc-900 dark:text-zinc-100 rounded-lg px-3 py-2.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-colors"
              />
            </div>
            <div>
              <label className="block text-[13px] font-medium text-zinc-700 dark:text-zinc-300 mb-1.5">Head</label>
              <input
                type="text"
                value={headBranch}
                onChange={(e) => setHeadBranch(e.target.value)}
                required
                className="w-full border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800/50 text-zinc-900 dark:text-zinc-100 rounded-lg px-3 py-2.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-colors"
                placeholder="feature-branch"
              />
            </div>
          </div>
          <button
            type="submit"
            disabled={createMut.isPending}
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white py-2.5 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {createMut.isPending && (
              <div className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            )}
            {createMut.isPending ? 'Creating...' : 'Create Pull Request'}
          </button>
        </form>
      </Modal>
    </div>
  )
}
