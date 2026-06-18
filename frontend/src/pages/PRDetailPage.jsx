import { useParams } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import usePR from '../hooks/usePR'
import useDiff from '../hooks/useDiff'
import useComments from '../hooks/useComments'
import PageHeader from '../components/PageHeader'
import StatusBadge from '../components/StatusBadge'
import DiffViewer from '../components/DiffViewer'
import ReviewerPanel from '../components/ReviewerPanel'
import EmptyState from '../components/EmptyState'
import { Skeleton } from '../components/Skeleton'
import { addComment, resolveComment } from '../api'
import { DocumentIcon } from '@heroicons/react/24/outline'
import { cn } from '../utils/classNames'

export default function PRDetailPage() {
  const { id } = useParams()
  const queryClient = useQueryClient()
  const { data: pr, isLoading: prLoading } = usePR(id)
  const { data: diffData, isLoading: diffLoading } = useDiff(id)
  const { data: comments = [] } = useComments(id)

  const diffFiles = extractDiffFiles(diffData)

  const commentMut = useMutation({
    mutationFn: (data) => addComment(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['comments', id] })
      queryClient.invalidateQueries({ queryKey: ['pr', id] })
      toast.success('Comment added')
    },
    onError: () => toast.error('Failed to add comment'),
  })

  const resolveMut = useMutation({
    mutationFn: (commentId) => resolveComment(commentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['comments', id] })
      toast.success('Comment updated')
    },
    onError: () => toast.error('Failed to update comment'),
  })

  if (prLoading || diffLoading) {
    return (
      <div className="min-h-screen">
        <div className="h-14 border-b border-zinc-200 dark:border-zinc-800" />
        <div className="p-6 max-w-7xl mx-auto space-y-4">
          <Skeleton className="h-8 w-1/3" />
          <Skeleton className="h-4 w-1/2" />
          <div className="flex gap-6 mt-6">
            <div className="flex-1 space-y-3">
              <Skeleton className="h-10 w-full rounded-xl" />
              <Skeleton className="h-48 w-full rounded-xl" />
            </div>
            <div className="w-72 space-y-3">
              <Skeleton className="h-6 w-full" />
              <Skeleton className="h-6 w-2/3" />
              <Skeleton className="h-10 w-full rounded-lg" />
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (!pr) {
    return (
      <div className="min-h-screen">
        <PageHeader breadcrumbs={[{ label: 'Pull Requests', to: '/' }]} />
        <EmptyState
          icon={DocumentIcon}
          title="Pull request not found"
          description="The pull request you're looking for doesn't exist or has been removed."
        />
      </div>
    )
  }

  const handleCommentSubmit = (data) => {
    const firstDiffFile = diffFiles[0]
    commentMut.mutate({
      body: data.body,
      diff_file: firstDiffFile?.id,
      line_position: data.line_position,
      commit_sha: firstDiffFile?.commit_sha || '',
      parent: data.parent || null,
    })
  }

  return (
    <div className="min-h-screen">
      <PageHeader
        breadcrumbs={[
          { label: 'Repositories', to: '/' },
          { label: 'Pull Requests', to: `/repos/${pr.repo || pr.repository}/prs` },
          { label: `#${pr.id}` },
        ]}
      />

      <div className="p-6 max-w-7xl mx-auto">
        <div className="mb-6">
          <div className="flex items-start gap-3 mb-2">
            <h1 className="text-lg font-bold text-zinc-900 dark:text-zinc-100 flex-1">
              {pr.title}
            </h1>
            <StatusBadge status={pr.status} />
          </div>
          {pr.description && (
            <p className="text-[13px] text-zinc-500 dark:text-zinc-400 leading-relaxed">
              {pr.description}
            </p>
          )}
        </div>

        <div className="flex gap-6">
          <div className="flex-1 min-w-0">
            <DiffViewer
              diffFiles={diffFiles}
              comments={comments}
              onLineClick={() => {}}
              onCommentSubmit={handleCommentSubmit}
              onResolveComment={(commentId) => resolveMut.mutate(commentId)}
            />
            {diffFiles.length === 0 && (
              <EmptyState
                icon={DocumentIcon}
                title="No changes"
                description="This pull request has no file changes."
              />
            )}
          </div>

          <aside className="w-72 flex-shrink-0 space-y-5">
            <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-4">
              <h3 className="text-[11px] font-semibold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider mb-3">
                Changed Files
              </h3>
              {diffFiles.length === 0 ? (
                <p className="text-xs text-zinc-400 dark:text-zinc-500">No changed files</p>
              ) : (
                <div className="space-y-0.5">
                  {diffFiles.map((file, idx) => (
                    <div
                      key={idx}
                      className={cn(
                        'flex items-center gap-2 text-xs font-mono py-1.5 px-2 rounded-md hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors cursor-default',
                        file.change_type === 'added' && 'text-green-600 dark:text-green-400',
                        file.change_type === 'deleted' && 'text-red-600 dark:text-red-400',
                        file.change_type !== 'added' && file.change_type !== 'deleted' && 'text-zinc-600 dark:text-zinc-400'
                      )}
                    >
                      <DocumentIcon className="h-3.5 w-3.5 flex-shrink-0" />
                      <span className="truncate">{file.file_path}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-4">
              <ReviewerPanel pr={pr} />
            </div>
          </aside>
        </div>
      </div>
    </div>
  )
}

function extractDiffFiles(diffData) {
  if (!diffData) return []
  if (Array.isArray(diffData)) {
    return diffData.flatMap((commit) =>
      (commit.diff_files || []).map((df) => ({ ...df, commit_sha: commit.sha }))
    )
  }
  if (diffData.commits) {
    return diffData.commits.flatMap((commit) =>
      (commit.diff_files || []).map((df) => ({ ...df, commit_sha: commit.sha }))
    )
  }
  return diffData.diff_files || []
}
