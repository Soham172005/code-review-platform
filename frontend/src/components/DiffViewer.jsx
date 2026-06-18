import { useState } from 'react'
import { ChevronDownIcon, ChevronRightIcon, PlusIcon } from '@heroicons/react/24/outline'
import Prism from 'prismjs'
import CommentThread from './CommentThread'
import { cn } from '../utils/classNames'

const LINE_BG = {
  added: 'bg-green-50 dark:bg-green-500/10',
  removed: 'bg-red-50 dark:bg-red-500/10',
  context: '',
}

const GUTTER_BG = {
  added: 'bg-green-100 dark:bg-green-500/20',
  removed: 'bg-red-100 dark:bg-red-500/20',
  context: 'bg-zinc-50 dark:bg-zinc-800/50',
}

const LINE_PREFIX = {
  added: '+',
  removed: '-',
  context: ' ',
}

const LINE_PREFIX_COLOR = {
  added: 'text-green-600 dark:text-green-400',
  removed: 'text-red-600 dark:text-red-400',
  context: 'text-zinc-300 dark:text-zinc-600',
}

function getFileExtension(path) {
  return path.split('.').pop()?.toLowerCase() || ''
}

function highlightCode(text) {
  try {
    return Prism.highlight(text, Prism.languages.clike, 'clike')
  } catch {
    return text
  }
}

export default function DiffViewer({ diffFiles = [], comments = [], onLineClick, onCommentSubmit, onResolveComment }) {
  const [collapsed, setCollapsed] = useState({})
  const [viewMode] = useState('unified')

  const toggleFile = (idx) => {
    setCollapsed((prev) => ({ ...prev, [idx]: !prev[idx] }))
  }

  const getCommentsForLine = (fileId, linePos) => {
    return comments.filter(
      (c) => c.diff_file === fileId && c.line_position === linePos
    )
  }

  return (
    <div className="space-y-3" data-testid="diff-viewer">
      {diffFiles.map((file, fileIdx) => (
        <div
          key={fileIdx}
          className="border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden bg-white dark:bg-zinc-950"
        >
          <button
            onClick={() => toggleFile(fileIdx)}
            className="w-full flex items-center gap-2.5 px-4 py-2.5 bg-zinc-50 dark:bg-zinc-900 hover:bg-zinc-100 dark:hover:bg-zinc-800/70 text-sm font-mono text-left transition-colors border-b border-zinc-200 dark:border-zinc-800"
          >
            {collapsed[fileIdx] ? (
              <ChevronRightIcon className="h-4 w-4 text-zinc-400 flex-shrink-0" />
            ) : (
              <ChevronDownIcon className="h-4 w-4 text-zinc-400 flex-shrink-0" />
            )}
            <span className="text-xs px-1.5 py-0.5 rounded bg-zinc-200 dark:bg-zinc-700 text-zinc-500 dark:text-zinc-400 font-mono flex-shrink-0">
              {getFileExtension(file.file_path)}
            </span>
            <span className={cn(
              'text-[13px] truncate',
              file.change_type === 'added' && 'text-green-600 dark:text-green-400',
              file.change_type === 'deleted' && 'text-red-600 dark:text-red-400',
              file.change_type !== 'added' && file.change_type !== 'deleted' && 'text-zinc-700 dark:text-zinc-300'
            )}>
              {file.file_path}
            </span>
            <span className={cn(
              'text-[11px] ml-auto flex-shrink-0 px-1.5 py-0.5 rounded',
              file.change_type === 'added' && 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-500/10',
              file.change_type === 'deleted' && 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-500/10',
              file.change_type !== 'added' && file.change_type !== 'deleted' && 'text-zinc-400 dark:text-zinc-500'
            )}>
              {file.change_type}
            </span>
          </button>

          {!collapsed[fileIdx] && (
            <div className="overflow-x-auto">
              <table className="w-full text-[13px] font-mono border-collapse">
                <tbody>
                  {(file.patch?.hunks || file.hunks || []).map((hunk, hunkIdx) => (
                    <HunkRows
                      key={hunkIdx}
                      hunk={hunk}
                      fileIdx={fileIdx}
                      fileId={file.id}
                      showAddButton={!!(onLineClick || onCommentSubmit)}
                      onLineClick={onLineClick}
                      getCommentsForLine={getCommentsForLine}
                      onCommentSubmit={onCommentSubmit}
                      onResolveComment={onResolveComment}
                      viewMode={viewMode}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

function HunkRows({ hunk, fileIdx, fileId, showAddButton, onLineClick, getCommentsForLine, onCommentSubmit, onResolveComment }) {
  const [activeCommentLine, setActiveCommentLine] = useState(null)

  return (
    <>
      <tr className="bg-indigo-50/50 dark:bg-indigo-500/5">
        <td colSpan={4} className="px-4 py-1.5 text-xs text-indigo-600 dark:text-indigo-400 select-none">
          @@ -{hunk.old_start},{hunk.old_lines} +{hunk.new_start},{hunk.new_lines} @@
        </td>
      </tr>
      {hunk.lines.map((line, lineIdx) => {
        const linePos = line.new_lineno || line.old_lineno
        const lineComments = fileId ? getCommentsForLine(fileId, linePos) : []
        return (
          <DiffLine
            key={lineIdx}
            line={line}
            linePos={linePos}
            fileIdx={fileIdx}
            showAddButton={showAddButton}
            lineComments={lineComments}
            activeCommentLine={activeCommentLine}
            setActiveCommentLine={setActiveCommentLine}
            onLineClick={onLineClick}
            onCommentSubmit={onCommentSubmit}
            onResolveComment={onResolveComment}
          />
        )
      })}
    </>
  )
}

function DiffLine({ line, linePos, fileIdx, showAddButton, lineComments, activeCommentLine, setActiveCommentLine, onLineClick, onCommentSubmit, onResolveComment }) {
  const handleClick = () => {
    if (onLineClick) {
      onLineClick(fileIdx, linePos)
    }
    setActiveCommentLine(linePos === activeCommentLine ? null : linePos)
  }

  return (
    <>
      <tr
        data-testid={`diff-line-${line.line_type}`}
        className={cn(
          LINE_BG[line.line_type],
          'group/line hover:brightness-95 dark:hover:brightness-110 cursor-pointer transition-[filter]'
        )}
        onClick={handleClick}
      >
        <td className={cn(
          GUTTER_BG[line.line_type],
          'w-[1px] px-1 text-center select-none border-r border-zinc-200 dark:border-zinc-800/50'
        )}>
          {showAddButton && (
            <span className="opacity-0 group-hover/line:opacity-100 transition-opacity">
              <span className="inline-flex items-center justify-center h-[18px] w-[18px] rounded bg-indigo-500 text-white">
                <PlusIcon className="h-3 w-3" />
              </span>
            </span>
          )}
        </td>
        <td className={cn(
          GUTTER_BG[line.line_type],
          'w-12 px-2 text-right text-xs text-zinc-400 dark:text-zinc-500 select-none border-r border-zinc-200 dark:border-zinc-800/50 tabular-nums'
        )}>
          {line.old_lineno || ''}
        </td>
        <td className={cn(
          GUTTER_BG[line.line_type],
          'w-12 px-2 text-right text-xs text-zinc-400 dark:text-zinc-500 select-none border-r border-zinc-200 dark:border-zinc-800/50 tabular-nums'
        )}>
          {line.new_lineno || ''}
        </td>
        <td className="px-4 py-0.5 whitespace-pre-wrap">
          <span className={cn('mr-2 select-none', LINE_PREFIX_COLOR[line.line_type])}>
            {LINE_PREFIX[line.line_type]}
          </span>
          <span dangerouslySetInnerHTML={{ __html: highlightCode(line.content || '') }} />
        </td>
      </tr>
      {(lineComments.length > 0 || activeCommentLine === linePos) && (
        <tr>
          <td colSpan={4} className="bg-zinc-50 dark:bg-zinc-900/50 px-4 py-3 border-y border-zinc-200 dark:border-zinc-800/50">
            <CommentThread
              comments={lineComments}
              linePosition={linePos}
              onSubmit={onCommentSubmit}
              onResolve={onResolveComment}
            />
          </td>
        </tr>
      )}
    </>
  )
}
