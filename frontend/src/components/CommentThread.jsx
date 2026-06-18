import { useState } from 'react'
import { CheckCircleIcon } from '@heroicons/react/24/outline'
import { CheckCircleIcon as CheckCircleSolid } from '@heroicons/react/24/solid'
import { relativeTime } from '../utils/dates'

function Avatar({ username }) {
  const initials = (username || 'U').slice(0, 2).toUpperCase()
  return (
    <div className="h-7 w-7 rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-white text-[10px] font-semibold flex-shrink-0">
      {initials}
    </div>
  )
}

export default function CommentThread({ comments = [], linePosition, onSubmit, onResolve }) {
  const [body, setBody] = useState('')
  const [replyTo, setReplyTo] = useState(null)

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!body.trim()) return
    onSubmit?.({
      body: body.trim(),
      line_position: linePosition,
      parent: replyTo,
    })
    setBody('')
    setReplyTo(null)
  }

  return (
    <div className="space-y-2" data-testid="comment-thread">
      {comments.map((comment) => {
        const author = comment.author?.username || comment.reviewer?.username || 'User'
        const isResolved = comment.is_resolved

        return (
          <div
            key={comment.id}
            className={`rounded-lg border transition-colors ${
              isResolved
                ? 'bg-green-50/50 dark:bg-green-500/5 border-green-200 dark:border-green-800/30 opacity-75'
                : 'bg-white dark:bg-zinc-800/50 border-zinc-200 dark:border-zinc-700/50'
            } ${comment.parent ? 'ml-6 border-l-2 border-l-indigo-300 dark:border-l-indigo-500/40' : ''}`}
          >
            <div className="px-3 py-2.5">
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2">
                  <Avatar username={author} />
                  <span className="text-[13px] font-medium text-zinc-900 dark:text-zinc-100">
                    {author}
                  </span>
                  <span className="text-[11px] text-zinc-400 dark:text-zinc-500">
                    {comment.created_at ? relativeTime(comment.created_at) : ''}
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  {onResolve && (
                    <button
                      onClick={() => onResolve(comment.id)}
                      className={`p-1 rounded transition-colors ${
                        isResolved
                          ? 'text-green-500 hover:text-green-600'
                          : 'text-zinc-300 dark:text-zinc-600 hover:text-green-500'
                      }`}
                      title={isResolved ? 'Unresolve' : 'Resolve'}
                    >
                      {isResolved
                        ? <CheckCircleSolid className="h-4 w-4" />
                        : <CheckCircleIcon className="h-4 w-4" />
                      }
                    </button>
                  )}
                  <button
                    onClick={() => setReplyTo(comment.id)}
                    className="text-[11px] text-zinc-400 dark:text-zinc-500 hover:text-indigo-500 dark:hover:text-indigo-400 transition-colors px-1.5 py-0.5 rounded hover:bg-zinc-100 dark:hover:bg-zinc-700/50"
                  >
                    Reply
                  </button>
                </div>
              </div>
              <p className="text-[13px] text-zinc-700 dark:text-zinc-300 whitespace-pre-wrap leading-relaxed">
                {comment.body}
              </p>
            </div>
          </div>
        )
      })}

      <form onSubmit={handleSubmit} className="flex gap-2 pt-1">
        <input
          type="text"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder={replyTo ? 'Write a reply...' : 'Add a comment...'}
          className="flex-1 text-[13px] border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-800/50 rounded-lg px-3 py-2 text-zinc-900 dark:text-zinc-100 placeholder-zinc-400 dark:placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-colors"
        />
        <button
          type="submit"
          className="text-[13px] font-medium px-3.5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors"
        >
          {replyTo ? 'Reply' : 'Comment'}
        </button>
        {replyTo && (
          <button
            type="button"
            onClick={() => setReplyTo(null)}
            className="text-[13px] px-2 py-2 text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 transition-colors"
          >
            Cancel
          </button>
        )}
      </form>
    </div>
  )
}
