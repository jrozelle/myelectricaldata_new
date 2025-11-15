import { useState, useEffect } from 'react'
import { Activity, ChevronDown, ChevronUp } from 'lucide-react'

interface LoadingProgressProps {
  isLoadingDetailed: boolean
  dailyLoadingComplete: boolean
  loadingProgress: {current: number, total: number, currentRange: string}
  allLoadingComplete: boolean
  dateRange: any
  isLoadingProduction: boolean
  productionResponse: any
  hasYesterdayDataInCache: boolean
}

export function LoadingProgress({
  isLoadingDetailed,
  dailyLoadingComplete,
  loadingProgress,
  allLoadingComplete,
  dateRange,
  isLoadingProduction,
  productionResponse,
  hasYesterdayDataInCache
}: LoadingProgressProps) {
  const [isProgressExpanded, setIsProgressExpanded] = useState(false)
  const [wasManuallyExpanded, setWasManuallyExpanded] = useState(false)

  useEffect(() => {
    if (allLoadingComplete && isProgressExpanded && !wasManuallyExpanded) {
      const timer = setTimeout(() => {
        setIsProgressExpanded(false)
      }, 2000)
      return () => clearTimeout(timer)
    }
  }, [allLoadingComplete, isProgressExpanded, wasManuallyExpanded])

  const hasAnyActivity = dateRange || isLoadingProduction || isLoadingDetailed || allLoadingComplete || hasYesterdayDataInCache

  if (!hasAnyActivity) {
    return null
  }

  const tasks = [
    { name: 'Quotidien', complete: dailyLoadingComplete, loading: isLoadingProduction, error: productionResponse?.success === false },
    { name: 'Détaillé', complete: loadingProgress.total === 0 || (loadingProgress.total > 0 && loadingProgress.current === loadingProgress.total), loading: isLoadingDetailed && loadingProgress.total > 0, progress: loadingProgress.total > 0 ? `${loadingProgress.current}/${loadingProgress.total}` : null },
  ]

  return (
    <div className="mt-6">
      <div
        onClick={() => {
          const willExpand = !isProgressExpanded
          setIsProgressExpanded(willExpand)
          if (willExpand) {
            setWasManuallyExpanded(true)
          }
        }}
        className="flex items-center justify-between cursor-pointer hover:opacity-70 transition-opacity"
      >
        <div className="flex items-center gap-2">
          <Activity className="text-primary-600 dark:text-primary-400" size={20} />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Progression du chargement
          </h3>
        </div>

        {!isProgressExpanded && (
          <div className="flex items-center gap-3 text-xs">
            {tasks.map((task, idx) => (
              <div key={idx} className="flex items-center gap-1">
                {task.complete ? (
                  <svg className="h-4 w-4 text-green-600 dark:text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                ) : task.error ? (
                  <svg className="h-4 w-4 text-red-600 dark:text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                ) : task.loading ? (
                  <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-primary-600"></div>
                ) : (
                  <div className="h-4 w-4 rounded-full border-2 border-gray-300 dark:border-gray-600"></div>
                )}
                <span className={`font-medium ${
                  task.complete ? 'text-green-600 dark:text-green-400' :
                  task.error ? 'text-red-600 dark:text-red-400' :
                  task.loading ? 'text-primary-600 dark:text-primary-400' :
                  'text-gray-500 dark:text-gray-400'
                }`}>
                  {task.name}
                  {task.progress && ` (${task.progress})`}
                </span>
              </div>
            ))}
          </div>
        )}

        <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
          {isProgressExpanded ? (
            <span className="text-sm">Réduire</span>
          ) : (
            <span className="text-sm">Développer</span>
          )}
          {isProgressExpanded ? (
            <ChevronUp size={20} className="text-gray-500" />
          ) : (
            <ChevronDown size={20} className="text-gray-500" />
          )}
        </div>
      </div>

      {isProgressExpanded && (
        <div className="animate-in fade-in slide-in-from-top-2 duration-300 mt-4">
          <div className="bg-gray-50 dark:bg-gray-900/30 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex flex-col gap-6">
              <div className="text-sm text-gray-600 dark:text-gray-400">
                {dailyLoadingComplete ? 'Chargement terminé !' : 'Chargement en cours...'}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
