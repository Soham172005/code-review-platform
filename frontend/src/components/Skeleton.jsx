import { cn } from '../utils/classNames'

export function Skeleton({ className }) {
  return <div className={cn('animate-pulse rounded-md bg-zinc-200 dark:bg-zinc-800', className)} />
}

export function SkeletonCard() {
  return (
    <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-5 space-y-3">
      <Skeleton className="h-4 w-2/3" />
      <Skeleton className="h-3 w-1/3" />
      <Skeleton className="h-3 w-1/2" />
    </div>
  )
}

export function SkeletonRow() {
  return (
    <div className="flex items-center gap-4 px-5 py-3.5 border-b border-zinc-100 dark:border-zinc-800/50">
      <Skeleton className="h-2.5 w-2.5 rounded-full" />
      <Skeleton className="h-4 w-1/2" />
      <div className="flex-1" />
      <Skeleton className="h-5 w-16 rounded-full" />
    </div>
  )
}
