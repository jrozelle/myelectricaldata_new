import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  RefreshCw,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  ExternalLink,
  Zap,
  Sun,
  Wind,
  Activity,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'
import { rteApi, type RTEApiTestResult } from '@/api/rte'
import { toast } from '@/stores/notificationStore'

// Interface pour les props du composant
interface ApiStatusCardProps {
  result: RTEApiTestResult
  expanded: boolean
  onToggle: () => void
}

// Composant pour afficher le statut d'une API
function ApiStatusCard({ result, expanded, onToggle }: ApiStatusCardProps) {
  const getStatusIcon = () => {
    switch (result.status) {
      case 'ok':
        return <CheckCircle2 className="text-green-500" size={24} />
      case 'forbidden':
        return <XCircle className="text-red-500" size={24} />
      case 'server_error':
        return <AlertTriangle className="text-orange-500" size={24} />
      case 'timeout':
        return <Clock className="text-yellow-500" size={24} />
      case 'rate_limited':
        return <AlertTriangle className="text-yellow-500" size={24} />
      default:
        return <XCircle className="text-red-500" size={24} />
    }
  }

  const getStatusBadge = () => {
    const baseClasses = 'px-2 py-1 rounded-full text-xs font-medium'
    switch (result.status) {
      case 'ok':
        return (
          <span className={`${baseClasses} bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300`}>
            OK
          </span>
        )
      case 'forbidden':
        return (
          <span className={`${baseClasses} bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300`}>
            Non activée
          </span>
        )
      case 'server_error':
        return (
          <span className={`${baseClasses} bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300`}>
            Erreur serveur
          </span>
        )
      case 'timeout':
        return (
          <span className={`${baseClasses} bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300`}>
            Timeout
          </span>
        )
      case 'rate_limited':
        return (
          <span className={`${baseClasses} bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300`}>
            Rate limit
          </span>
        )
      default:
        return (
          <span className={`${baseClasses} bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300`}>
            Erreur
          </span>
        )
    }
  }

  const getApiIcon = () => {
    if (result.api === 'tempo') return <Zap className="text-blue-500" size={20} />
    if (result.api === 'ecowatt') return <Activity className="text-green-500" size={20} />
    if (result.api === 'consumption') return <Activity className="text-purple-500" size={20} />
    if (result.api.includes('solar')) return <Sun className="text-yellow-500" size={20} />
    if (result.api.includes('wind')) return <Wind className="text-cyan-500" size={20} />
    return <Activity className="text-gray-500" size={20} />
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      {/* Header */}
      <button
        onClick={onToggle}
        className="w-full p-4 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          {getStatusIcon()}
          <div className="flex items-center gap-2">
            {getApiIcon()}
            <div className="text-left">
              <h3 className="font-semibold text-gray-900 dark:text-white">{result.name}</h3>
              {result.response_time_ms && (
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {result.response_time_ms.toFixed(0)} ms
                </p>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {getStatusBadge()}
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </button>

      {/* Details */}
      {expanded && (
        <div className="px-4 pb-4 border-t border-gray-100 dark:border-gray-700">
          <div className="mt-4 space-y-3">
            {/* Error message */}
            {result.error && (
              <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
                <p className="text-sm text-red-700 dark:text-red-300">{result.error}</p>
                {result.help && (
                  <a
                    href={result.help}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-2 inline-flex items-center gap-1 text-xs text-red-600 dark:text-red-400 hover:underline"
                  >
                    Activer l'API <ExternalLink size={12} />
                  </a>
                )}
              </div>
            )}

            {/* Summary for successful APIs */}
            {result.status === 'ok' && result.summary && (
              <div className="space-y-2">
                {/* Tempo summary */}
                {result.summary.colors && (
                  <div className="grid grid-cols-3 gap-2">
                    <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded text-center">
                      <div className="text-lg font-bold text-blue-600 dark:text-blue-400">
                        {result.summary.colors.BLUE}
                      </div>
                      <div className="text-xs text-blue-700 dark:text-blue-300">Bleu</div>
                    </div>
                    <div className="p-2 bg-gray-50 dark:bg-gray-700 rounded text-center">
                      <div className="text-lg font-bold text-gray-600 dark:text-gray-300">
                        {result.summary.colors.WHITE}
                      </div>
                      <div className="text-xs text-gray-700 dark:text-gray-400">Blanc</div>
                    </div>
                    <div className="p-2 bg-red-50 dark:bg-red-900/20 rounded text-center">
                      <div className="text-lg font-bold text-red-600 dark:text-red-400">
                        {result.summary.colors.RED}
                      </div>
                      <div className="text-xs text-red-700 dark:text-red-300">Rouge</div>
                    </div>
                  </div>
                )}

                {/* EcoWatt summary */}
                {result.summary.total_signals !== undefined && (
                  <div className="flex items-center gap-4 text-sm">
                    <span className="text-gray-600 dark:text-gray-400">
                      {result.summary.total_signals} signaux
                    </span>
                    {result.summary.latest_date && (
                      <span className="text-gray-500 dark:text-gray-500">
                        Dernier : {result.summary.latest_date}
                      </span>
                    )}
                  </div>
                )}

                {/* Consumption summary */}
                {result.summary.values_count !== undefined && (
                  <div className="grid grid-cols-3 gap-2 text-sm">
                    <div className="p-2 bg-purple-50 dark:bg-purple-900/20 rounded text-center">
                      <div className="font-semibold text-purple-600 dark:text-purple-400">
                        {result.summary.min_mw?.toLocaleString()} MW
                      </div>
                      <div className="text-xs text-purple-700 dark:text-purple-300">Min</div>
                    </div>
                    <div className="p-2 bg-purple-50 dark:bg-purple-900/20 rounded text-center">
                      <div className="font-semibold text-purple-600 dark:text-purple-400">
                        {result.summary.avg_mw?.toLocaleString()} MW
                      </div>
                      <div className="text-xs text-purple-700 dark:text-purple-300">Moyenne</div>
                    </div>
                    <div className="p-2 bg-purple-50 dark:bg-purple-900/20 rounded text-center">
                      <div className="font-semibold text-purple-600 dark:text-purple-400">
                        {result.summary.max_mw?.toLocaleString()} MW
                      </div>
                      <div className="text-xs text-purple-700 dark:text-purple-300">Max</div>
                    </div>
                  </div>
                )}

                {/* Generation summary */}
                {result.summary.forecast_count !== undefined && !result.summary.values_count && (
                  <div className="text-sm text-gray-600 dark:text-gray-400">
                    {result.summary.forecast_count} prévisions
                  </div>
                )}

                {/* Latest date */}
                {result.summary.latest_date && !result.summary.total_signals && (
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    Dernière date : {result.summary.latest_date}
                  </div>
                )}
              </div>
            )}

            {/* Error details */}
            {result.error_details !== undefined && result.error_details !== null && (
              <details className="text-xs">
                <summary className="cursor-pointer text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300">
                  Détails techniques
                </summary>
                <pre className="mt-2 p-2 bg-gray-100 dark:bg-gray-900 rounded overflow-x-auto text-gray-600 dark:text-gray-400">
                  {typeof result.error_details === 'string'
                    ? result.error_details
                    : JSON.stringify(result.error_details, null, 2)}
                </pre>
              </details>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default function RTE() {
  const queryClient = useQueryClient()
  const [expandedApis, setExpandedApis] = useState<Set<string>>(new Set())

  // Query pour le statut RTE
  const {
    data: statusData,
    isLoading: statusLoading,
  } = useQuery({
    queryKey: ['rte-status'],
    queryFn: () => rteApi.getStatus(),
  })

  // Query pour les tests (manuel)
  const {
    data: testData,
    isLoading: testLoading,
    refetch: runTests,
    isFetching: testFetching,
  } = useQuery({
    queryKey: ['rte-test'],
    queryFn: () => rteApi.testAll(),
    enabled: false, // Ne pas exécuter automatiquement
  })

  // Mutation pour rafraîchir Tempo
  const refreshTempoMutation = useMutation({
    mutationFn: () => rteApi.refreshTempo(),
    onSuccess: (response) => {
      if (response.success) {
        toast.success(response.data?.message || 'Cache Tempo mis à jour')
        queryClient.invalidateQueries({ queryKey: ['tempo'] })
      } else {
        toast.error(response.error?.message || 'Erreur lors du rafraîchissement')
      }
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Erreur lors du rafraîchissement Tempo')
    },
  })

  // Mutation pour rafraîchir EcoWatt
  const refreshEcowattMutation = useMutation({
    mutationFn: () => rteApi.refreshEcowatt(),
    onSuccess: (response) => {
      if (response.success) {
        toast.success(response.data?.message || 'Cache EcoWatt mis à jour')
        queryClient.invalidateQueries({ queryKey: ['ecowatt'] })
      } else {
        toast.error(response.error?.message || 'Erreur lors du rafraîchissement')
      }
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Erreur lors du rafraîchissement EcoWatt')
    },
  })

  const toggleExpanded = (api: string) => {
    setExpandedApis((prev) => {
      const next = new Set(prev)
      if (next.has(api)) {
        next.delete(api)
      } else {
        next.add(api)
      }
      return next
    })
  }

  const handleRunTests = () => {
    runTests()
    // Expand all APIs to show results
    if (testData?.data?.results) {
      setExpandedApis(new Set(Object.keys(testData.data.results)))
    }
  }

  if (statusLoading) {
    return (
      <div className="pt-6 w-full">
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="animate-spin text-primary-600" size={32} />
        </div>
      </div>
    )
  }

  const hasCredentials = statusData?.data?.has_credentials

  return (
    <div className="pt-6 w-full">
      {/* Configuration Status */}
      <div className="mb-6 p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {hasCredentials ? (
              <CheckCircle2 className="text-green-500" size={24} />
            ) : (
              <XCircle className="text-red-500" size={24} />
            )}
            <div>
              <h2 className="font-semibold text-gray-900 dark:text-white">Configuration RTE</h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {hasCredentials
                  ? 'Credentials configurés correctement'
                  : 'Variables RTE_CLIENT_ID et RTE_CLIENT_SECRET non configurées'}
              </p>
            </div>
          </div>
          <a
            href="https://data.rte-france.com"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-sm text-primary-600 dark:text-primary-400 hover:underline"
          >
            Portail RTE <ExternalLink size={14} />
          </a>
        </div>
      </div>

      {/* Actions */}
      <div className="mb-6 flex flex-wrap gap-3">
        <button
          onClick={handleRunTests}
          disabled={!hasCredentials || testLoading || testFetching}
          className="px-4 py-2 bg-primary-600 hover:bg-primary-700 dark:bg-primary-500 dark:hover:bg-primary-600 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          <RefreshCw size={16} className={testFetching ? 'animate-spin' : ''} />
          {testFetching ? 'Test en cours...' : 'Tester toutes les API'}
        </button>

        <button
          onClick={() => refreshTempoMutation.mutate()}
          disabled={!hasCredentials || refreshTempoMutation.isPending}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          <Zap size={16} />
          {refreshTempoMutation.isPending ? 'Rafraîchissement...' : 'Rafraîchir Tempo'}
        </button>

        <button
          onClick={() => refreshEcowattMutation.mutate()}
          disabled={!hasCredentials || refreshEcowattMutation.isPending}
          className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          <Activity size={16} />
          {refreshEcowattMutation.isPending ? 'Rafraîchissement...' : 'Rafraîchir EcoWatt'}
        </button>
      </div>

      {/* Test Results Summary */}
      {testData?.data?.summary && (
        <div className="mb-6 p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div
                className={`p-3 rounded-full ${
                  testData.data.summary.all_ok
                    ? 'bg-green-100 dark:bg-green-900/30'
                    : 'bg-yellow-100 dark:bg-yellow-900/30'
                }`}
              >
                {testData.data.summary.all_ok ? (
                  <CheckCircle2 className="text-green-600 dark:text-green-400" size={28} />
                ) : (
                  <AlertTriangle className="text-yellow-600 dark:text-yellow-400" size={28} />
                )}
              </div>
              <div>
                <h2 className="font-semibold text-gray-900 dark:text-white">
                  Résultat des tests
                </h2>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {testData.data.summary.apis_ok} / {testData.data.summary.total_apis} API(s)
                  fonctionnelle(s)
                </p>
              </div>
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400">
              {testData.data.tested_at &&
                new Date(testData.data.tested_at).toLocaleString('fr-FR')}
            </div>
          </div>
        </div>
      )}

      {/* API Cards */}
      {testData?.data?.results && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Détail des API
          </h2>

          <div className="grid gap-4">
            {(Object.entries(testData.data.results) as [string, RTEApiTestResult][]).map(([key, result]) => (
              <ApiStatusCard
                key={key}
                result={result}
                expanded={expandedApis.has(key)}
                onToggle={() => toggleExpanded(key)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Help Section */}
      <div className="mt-8 p-6 bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-gray-200 dark:border-gray-700">
        <h3 className="font-semibold text-gray-900 dark:text-white mb-3">
          À propos des API RTE
        </h3>
        <div className="grid md:grid-cols-2 gap-4 text-sm text-gray-600 dark:text-gray-400">
          <div>
            <h4 className="font-medium text-gray-800 dark:text-gray-200 flex items-center gap-2">
              <Zap size={16} className="text-blue-500" /> Tempo Calendar
            </h4>
            <p>Calendrier des jours Tempo EDF (Bleu, Blanc, Rouge) pour la saison en cours.</p>
          </div>
          <div>
            <h4 className="font-medium text-gray-800 dark:text-gray-200 flex items-center gap-2">
              <Activity size={16} className="text-green-500" /> EcoWatt
            </h4>
            <p>Signaux de tension du réseau électrique pour anticiper les pics de consommation.</p>
          </div>
          <div>
            <h4 className="font-medium text-gray-800 dark:text-gray-200 flex items-center gap-2">
              <Activity size={16} className="text-purple-500" /> Consumption
            </h4>
            <p>Prévisions de consommation électrique nationale (utilisé pour les prévisions Tempo).</p>
          </div>
          <div>
            <h4 className="font-medium text-gray-800 dark:text-gray-200 flex items-center gap-2">
              <Sun size={16} className="text-yellow-500" /> <Wind size={16} className="text-cyan-500" /> Generation Forecast
            </h4>
            <p>Prévisions de production solaire et éolienne (pour calculer la consommation nette).</p>
          </div>
        </div>

        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            <strong>Note :</strong> Chaque API doit être activée individuellement sur le{' '}
            <a
              href="https://data.rte-france.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary-600 dark:text-primary-400 hover:underline"
            >
              portail RTE
            </a>
            . Les prévisions Tempo avancées nécessitent les API Consumption et Generation Forecast.
          </p>
        </div>
      </div>
    </div>
  )
}
