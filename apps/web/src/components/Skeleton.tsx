/**
 * Skeleton loading components for better loading states
 */

interface SkeletonProps {
  className?: string
}

export function Skeleton({ className = '' }: SkeletonProps) {
  return (
    <div
      className={`animate-pulse bg-gray-200 dark:bg-gray-700 rounded ${className}`}
      aria-hidden="true"
    />
  )
}

export function SkeletonText({ className = '' }: SkeletonProps) {
  return <Skeleton className={`h-4 ${className}`} />
}

export function SkeletonTitle({ className = '' }: SkeletonProps) {
  return <Skeleton className={`h-6 ${className}`} />
}

export function SkeletonCircle({ className = '' }: SkeletonProps) {
  return <Skeleton className={`rounded-full ${className}`} />
}

export function SkeletonButton({ className = '' }: SkeletonProps) {
  return <Skeleton className={`h-10 ${className}`} />
}

/**
 * Skeleton loader for PDL Card
 */
export function PDLCardSkeleton() {
  return (
    <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 space-y-4">
      {/* Header */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 flex-1">
            <SkeletonTitle className="w-48" />
            <Skeleton className="w-20 h-5" />
          </div>
          <div className="flex gap-2">
            <SkeletonButton className="w-20" />
            <SkeletonButton className="w-20" />
            <SkeletonButton className="w-20" />
            <SkeletonButton className="w-20" />
          </div>
        </div>

        {/* PDL number and dates */}
        <div className="flex items-center justify-between">
          <SkeletonText className="w-40" />
          <div className="flex items-center gap-3">
            <SkeletonText className="w-32" />
            <SkeletonText className="w-32" />
          </div>
        </div>
      </div>

      {/* Contract Info */}
      <div className="space-y-3 pt-3 border-t border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <SkeletonText className="w-32" />
          <SkeletonText className="w-20" />
        </div>
        <div className="flex items-center justify-between pl-7">
          <SkeletonText className="w-40" />
          <Skeleton className="w-32 h-8" />
        </div>
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <SkeletonText className="w-32" />
          </div>
          <div className="flex items-center justify-between gap-2">
            <SkeletonText className="w-24" />
            <div className="flex-1 flex items-center gap-2">
              <Skeleton className="w-16 h-8" />
              <SkeletonText className="w-4" />
              <Skeleton className="w-16 h-8" />
              <SkeletonText className="w-8" />
              <Skeleton className="w-16 h-8" />
              <SkeletonText className="w-4" />
              <Skeleton className="w-16 h-8" />
            </div>
            <Skeleton className="w-16 h-8" />
          </div>
        </div>
        <div className="flex items-center justify-between">
          <SkeletonText className="w-28" />
          <SkeletonText className="w-20" />
        </div>
      </div>
    </div>
  )
}

/**
 * Skeleton loader for notification toast
 */
export function NotificationSkeleton() {
  return (
    <div className="p-4 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 flex items-start gap-3">
      <SkeletonCircle className="w-6 h-6" />
      <div className="flex-1 space-y-2">
        <SkeletonTitle className="w-48" />
        <SkeletonText className="w-64" />
      </div>
    </div>
  )
}
