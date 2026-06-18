import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listRepos, createRepo } from '../api'
import { relativeTime } from '../utils/dates'
import Modal from '../components/Modal'
import PageHeader from '../components/PageHeader'
import EmptyState from '../components/EmptyState'
import { SkeletonCard } from '../components/Skeleton'
import { PlusIcon, FolderIcon, ArrowTopRightOnSquareIcon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

export default function RepositoryListPage() {
  const [showModal, setShowModal] = useState(false)
  const [name, setName] = useState('')
  const [githubUrl, setGithubUrl] = useState('')
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['repos'],
    queryFn: () => listRepos().then((res) => res.data),
  })

  const createMut = useMutation({
    mutationFn: (repoData) => createRepo(repoData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['repos'] })
      setShowModal(false)
      setName('')
      setGithubUrl('')
      toast.success('Repository created')
    },
    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Failed to create repository')
    },
  })

  const handleCreate = (e) => {
    e.preventDefault()
    createMut.mutate({ name, github_url: githubUrl })
  }

  const repos = data?.results || data || []

  return (
    <div className="min-h-screen">
      <PageHeader
        breadcrumbs={[{ label: 'Repositories' }]}
        actions={
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-700 text-white px-3.5 py-2 rounded-lg text-[13px] font-medium transition-colors"
          >
            <PlusIcon className="h-4 w-4" />
            New Repository
          </button>
        }
      />

      <div className="p-6 max-w-6xl mx-auto">
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        ) : repos.length === 0 ? (
          <EmptyState
            icon={FolderIcon}
            title="No repositories yet"
            description="Create a repository to start reviewing code with your team."
            action={
              <button
                onClick={() => setShowModal(true)}
                className="flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              >
                <PlusIcon className="h-4 w-4" />
                New Repository
              </button>
            }
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {repos.map((repo) => (
              <Link
                key={repo.id}
                to={`/repos/${repo.id}/prs`}
                className="group block bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-5 hover:shadow-lg hover:shadow-zinc-200/50 dark:hover:shadow-zinc-900/50 hover:border-zinc-300 dark:hover:border-zinc-700 transition-all duration-200 hover:-translate-y-0.5"
              >
                <div className="flex items-start gap-3">
                  <div className="h-9 w-9 rounded-lg bg-indigo-50 dark:bg-indigo-500/10 flex items-center justify-center flex-shrink-0 group-hover:bg-indigo-100 dark:group-hover:bg-indigo-500/20 transition-colors">
                    <FolderIcon className="h-4.5 w-4.5 text-indigo-500 h-[18px] w-[18px]" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 truncate group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                      {repo.name}
                    </h3>
                    <div className="flex items-center gap-2 mt-1.5">
                      <div className="h-4 w-4 rounded-full bg-zinc-200 dark:bg-zinc-700 flex items-center justify-center text-[8px] font-bold text-zinc-500 dark:text-zinc-400">
                        {(repo.owner?.username || 'U')[0].toUpperCase()}
                      </div>
                      <span className="text-xs text-zinc-500 dark:text-zinc-400">
                        {repo.owner?.username || repo.owner}
                      </span>
                      <span className="text-zinc-300 dark:text-zinc-600">&middot;</span>
                      <span className="text-xs text-zinc-400 dark:text-zinc-500">
                        {relativeTime(repo.created_at)}
                      </span>
                    </div>
                    {repo.github_url && (
                      <div className="flex items-center gap-1 mt-2">
                        <ArrowTopRightOnSquareIcon className="h-3 w-3 text-zinc-400" />
                        <span className="text-[11px] text-zinc-400 dark:text-zinc-500 truncate">
                          {repo.github_url}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      <Modal open={showModal} onClose={() => setShowModal(false)} title="New Repository">
        <form onSubmit={handleCreate} className="space-y-4">
          <div>
            <label className="block text-[13px] font-medium text-zinc-700 dark:text-zinc-300 mb-1.5">Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="w-full border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800/50 text-zinc-900 dark:text-zinc-100 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-colors"
              placeholder="my-project"
            />
          </div>
          <div>
            <label className="block text-[13px] font-medium text-zinc-700 dark:text-zinc-300 mb-1.5">GitHub URL (optional)</label>
            <input
              type="url"
              value={githubUrl}
              onChange={(e) => setGithubUrl(e.target.value)}
              className="w-full border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800/50 text-zinc-900 dark:text-zinc-100 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-colors"
              placeholder="https://github.com/..."
            />
          </div>
          <button
            type="submit"
            disabled={createMut.isPending}
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white py-2.5 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {createMut.isPending && (
              <div className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            )}
            {createMut.isPending ? 'Creating...' : 'Create Repository'}
          </button>
        </form>
      </Modal>
    </div>
  )
}
