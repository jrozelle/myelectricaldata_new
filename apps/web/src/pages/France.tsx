import { useState, useEffect } from 'react'
import { Sun, Wind, Info, Leaf, Zap, TrendingUp, BarChart3, RefreshCw, Clock } from 'lucide-react'
import {
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import {
  consumptionFranceApi,
  type ConsumptionFranceResponse,
  type ConsumptionFranceCurrent,
} from '../api/consumptionFrance'
import {
  generationForecastApi,
  type RenewableMixResponse,
} from '../api/generationForecast'
import { syncApi } from '../api/sync'
import { useAppMode } from '../hooks/useAppMode'
import { toast } from '../stores/notificationStore'

// Formater la valeur en GW pour l'affichage
const formatMW = (value: number) => {
  if (value >= 1000) {
    return `${(value / 1000).toFixed(1)} GW`
  }
  return `${value.toFixed(0)} MW`
}

// Formater l'heure depuis une date ISO
const formatHour = (dateStr: string) => {
  const date = new Date(dateStr)
  return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
}

// Couleurs par type de données consommation
const TYPE_COLORS: Record<string, string> = {
  REALISED: '#10b981', // vert (réalisé)
  ID: '#f59e0b', // orange (intraday)
  'D-1': '#3b82f6', // bleu (prévision J-1)
  'D-2': '#8b5cf6', // violet (prévision J-2)
}

const TYPE_LABELS: Record<string, string> = {
  REALISED: 'Réalisé',
  ID: 'Intraday',
  'D-1': 'Prévision J-1',
  'D-2': 'Prévision J-2',
}

export default function France() {
  const { isClientMode } = useAppMode()

  // État consommation
  const [consumptionData, setConsumptionData] = useState<ConsumptionFranceResponse | null>(null)
  const [currentConsumption, setCurrentConsumption] = useState<ConsumptionFranceCurrent | null>(null)

  // État production
  const [mixData, setMixData] = useState<RenewableMixResponse | null>(null)

  // État commun
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // État synchronisation (mode client uniquement)
  const [syncing, setSyncing] = useState(false)
  const [lastSyncConsumption, setLastSyncConsumption] = useState<string | null>(null)
  const [lastSyncGeneration, setLastSyncGeneration] = useState<string | null>(null)

  // Formatter le temps écoulé depuis la dernière synchronisation
  const formatLastSync = (isoString: string | null | undefined) => {
    if (!isoString) return 'Jamais'
    const date = new Date(isoString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)

    if (diffMins < 1) return 'À l\'instant'
    if (diffMins < 60) return `Il y a ${diffMins} min`
    if (diffHours < 24) return `Il y a ${diffHours}h`
    return date.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
  }

  // Récupérer le statut de synchronisation (mode client uniquement)
  const fetchSyncStatus = async () => {
    if (!isClientMode) return
    try {
      const [consumptionStatus, generationStatus] = await Promise.all([
        syncApi.getConsumptionFranceStatus(),
        syncApi.getGenerationForecastStatus(),
      ])
      if (consumptionStatus.success && consumptionStatus.data) {
        setLastSyncConsumption(consumptionStatus.data.last_sync_at)
      }
      if (generationStatus.success && generationStatus.data) {
        setLastSyncGeneration(generationStatus.data.last_sync_at)
      }
    } catch (err) {
      console.error('Erreur lors de la récupération du statut de synchronisation', err)
    }
  }

  // Synchroniser les données depuis la passerelle (mode client uniquement)
  const handleSync = async () => {
    setSyncing(true)
    const loadingId = toast.loading('Synchronisation des données France...')
    try {
      const [consumptionResult, generationResult] = await Promise.all([
        syncApi.syncConsumptionFranceNow(),
        syncApi.syncGenerationForecastNow(),
      ])

      toast.dismiss(loadingId)

      const consumptionCreated = consumptionResult.data?.created || 0
      const consumptionUpdated = consumptionResult.data?.updated || 0
      const generationCreated = generationResult.data?.created || 0
      const generationUpdated = generationResult.data?.updated || 0

      const totalCreated = consumptionCreated + generationCreated
      const totalUpdated = consumptionUpdated + generationUpdated

      const hasErrors = (consumptionResult.data?.errors?.length || 0) > 0 ||
                        (generationResult.data?.errors?.length || 0) > 0

      if (hasErrors) {
        toast.warning(`Synchronisation partielle : ${totalCreated} créés, ${totalUpdated} mis à jour`)
      } else if (totalCreated > 0 || totalUpdated > 0) {
        toast.success(`Synchronisation réussie : ${totalCreated} créés, ${totalUpdated} mis à jour`)
        // Recharger les données après synchronisation
        await fetchData()
      } else {
        toast.info('Aucune nouvelle donnée à synchroniser')
      }

      // Mettre à jour le statut de synchronisation
      await fetchSyncStatus()
    } catch (err) {
      toast.dismiss(loadingId)
      const errorMessage = err instanceof Error ? err.message : 'Erreur inconnue'
      toast.error(`Échec de la synchronisation : ${errorMessage}`)
    } finally {
      setSyncing(false)
    }
  }

  useEffect(() => {
    fetchData()
    fetchSyncStatus()
  }, [])

  const fetchData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [consumptionResponse, currentResponse, mixResponse] = await Promise.all([
        consumptionFranceApi.getConsumption(),
        consumptionFranceApi.getCurrent(),
        generationForecastApi.getMix(),
      ])

      if (consumptionResponse.success && consumptionResponse.data) {
        setConsumptionData(consumptionResponse.data)
      }

      if (currentResponse.success && currentResponse.data) {
        setCurrentConsumption(currentResponse.data)
      }

      if (mixResponse.success && mixResponse.data) {
        setMixData(mixResponse.data)
      }
    } catch (err) {
      setError('Erreur lors du chargement des données')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  // Préparer les données pour le graphique consommation
  const prepareConsumptionChartData = () => {
    if (!consumptionData) return []

    const dataByTime: Record<string, Record<string, number>> = {}

    for (const typeData of consumptionData.short_term) {
      for (const value of typeData.values) {
        const time = value.start_date
        if (!dataByTime[time]) {
          dataByTime[time] = {}
        }
        dataByTime[time][typeData.type] = value.value
      }
    }

    return Object.entries(dataByTime)
      .map(([time, values]) => ({
        time,
        label: formatHour(time),
        ...values,
      }))
      .sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime())
      .slice(-96) // 24h de données à 15min
  }

  // Préparer les données pour le graphique production
  const prepareMixChartData = () => {
    if (!mixData) return []

    return mixData.mix.map((item) => ({
      time: item.start_date,
      label: formatHour(item.start_date),
      solar: item.solar,
      wind: item.wind,
      total: item.total_renewable,
    }))
  }

  // Calculer les totaux production actuels
  const getCurrentProductionTotals = () => {
    if (!mixData || mixData.mix.length === 0) return null

    const latest = mixData.mix[Math.floor(mixData.mix.length / 2)] || mixData.mix[0]
    return {
      solar: latest.solar,
      wind: latest.wind,
      total: latest.total_renewable,
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 dark:bg-red-900/20 border-l-4 border-red-500 rounded-lg">
        <p className="text-red-800 dark:text-red-200">{error}</p>
        <button
          onClick={fetchData}
          className="mt-2 text-sm text-red-600 dark:text-red-400 hover:underline"
        >
          Réessayer
        </button>
      </div>
    )
  }

  const consumptionChartData = prepareConsumptionChartData()
  const mixChartData = prepareMixChartData()
  const productionTotals = getCurrentProductionTotals()
  const availableConsumptionTypes = consumptionData?.short_term.map(d => d.type) || []

  // Calculer le dernier temps de synchronisation (le plus récent des deux)
  const getLastSyncTime = () => {
    if (!lastSyncConsumption && !lastSyncGeneration) return null
    if (!lastSyncConsumption) return lastSyncGeneration
    if (!lastSyncGeneration) return lastSyncConsumption
    return new Date(lastSyncConsumption) > new Date(lastSyncGeneration)
      ? lastSyncConsumption
      : lastSyncGeneration
  }

  return (
    <div className="pt-6 w-full">
      <div className="space-y-8">
        {/* Bouton de synchronisation (mode client uniquement) */}
        {isClientMode && (
          <div className="flex items-center justify-end gap-3">
            <span className="text-sm text-gray-500 dark:text-gray-400 flex items-center gap-1">
              <Clock className="w-4 h-4" />
              {formatLastSync(getLastSyncTime())}
            </span>
            <button
              onClick={handleSync}
              disabled={syncing}
              className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 dark:bg-primary-500 dark:hover:bg-primary-600 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
              {syncing ? 'Synchronisation...' : 'Synchroniser'}
            </button>
          </div>
        )}

        {/* ===== SECTION CONSOMMATION ===== */}

        {/* Cartes résumé : consommation actuelle + production renouvelable */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Consommation actuelle */}
          {currentConsumption && (
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-md border border-gray-300 dark:border-gray-700 p-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-green-100 dark:bg-green-900/30 rounded-lg">
                  <Zap className="text-green-600 dark:text-green-400" size={24} />
                </div>
                <div>
                  <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400">
                    Consommation
                  </h3>
                  <div className="text-2xl font-bold text-gray-900 dark:text-white">
                    {formatMW(currentConsumption.value)}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Production solaire */}
          {productionTotals && (
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-md border border-gray-300 dark:border-gray-700 p-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-yellow-100 dark:bg-yellow-900/30 rounded-lg">
                  <Sun className="text-yellow-600 dark:text-yellow-400" size={24} />
                </div>
                <div>
                  <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400">
                    Solaire
                  </h3>
                  <div className="text-2xl font-bold text-gray-900 dark:text-white">
                    {formatMW(productionTotals.solar)}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Production éolienne */}
          {productionTotals && (
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-md border border-gray-300 dark:border-gray-700 p-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                  <Wind className="text-blue-600 dark:text-blue-400" size={24} />
                </div>
                <div>
                  <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400">
                    Éolien
                  </h3>
                  <div className="text-2xl font-bold text-gray-900 dark:text-white">
                    {formatMW(productionTotals.wind)}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Total renouvelable */}
          {productionTotals && (
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-md border border-gray-300 dark:border-gray-700 p-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-green-100 dark:bg-green-900/30 rounded-lg">
                  <Leaf className="text-green-600 dark:text-green-400" size={24} />
                </div>
                <div>
                  <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400">
                    Renouvelable
                  </h3>
                  <div className="text-2xl font-bold text-gray-900 dark:text-white">
                    {formatMW(productionTotals.total)}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Graphique consommation */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-md border border-gray-300 dark:border-gray-700 p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2 text-gray-900 dark:text-white">
            <TrendingUp className="text-primary-600 dark:text-primary-400" size={20} />
            Consommation nationale
          </h2>

          {consumptionChartData.length > 0 ? (
            <div className="h-[350px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={consumptionChartData}>
                  <CartesianGrid strokeDasharray="3 3" className="dark:opacity-30" />
                  <XAxis
                    dataKey="label"
                    tick={{ fill: 'currentColor', fontSize: 12 }}
                    interval="preserveStartEnd"
                  />
                  <YAxis
                    tickFormatter={(value) => `${(value / 1000).toFixed(0)} GW`}
                    tick={{ fill: 'currentColor', fontSize: 12 }}
                    domain={['auto', 'auto']}
                  />
                  <Tooltip
                    formatter={(value: number, name: string) => [formatMW(value), TYPE_LABELS[name] || name]}
                    labelFormatter={(label) => `Heure : ${label}`}
                    contentStyle={{
                      backgroundColor: 'var(--tooltip-bg, #fff)',
                      border: '1px solid var(--tooltip-border, #e5e7eb)',
                      borderRadius: '0.5rem',
                    }}
                  />
                  <Legend
                    formatter={(value) => TYPE_LABELS[value] || value}
                  />
                  {availableConsumptionTypes.map((type) => (
                    <Line
                      key={type}
                      type="monotone"
                      dataKey={type}
                      stroke={TYPE_COLORS[type] || '#6b7280'}
                      strokeWidth={type === 'REALISED' ? 2 : 1}
                      dot={false}
                      name={type}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-[350px] text-center">
              <BarChart3 className="text-gray-400 dark:text-gray-500 mb-4" size={48} />
              <p className="text-gray-500 dark:text-gray-400">
                Aucune donnée disponible.
                {isClientMode
                  ? ' Cliquez sur "Synchroniser" pour récupérer les données depuis la passerelle.'
                  : ' Les données seront chargées automatiquement.'}
              </p>
            </div>
          )}
        </div>

        {/* ===== SECTION PRODUCTION ===== */}

        {/* Graphique du mix renouvelable */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-md border border-gray-300 dark:border-gray-700 p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2 text-gray-900 dark:text-white">
            <Leaf className="text-primary-600 dark:text-primary-400" size={20} />
            Production renouvelable
          </h2>

          {mixChartData.length > 0 ? (
            <div className="h-[350px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={mixChartData}>
                  <CartesianGrid strokeDasharray="3 3" className="dark:opacity-30" />
                  <XAxis
                    dataKey="label"
                    tick={{ fill: 'currentColor', fontSize: 12 }}
                    interval="preserveStartEnd"
                  />
                  <YAxis
                    tickFormatter={(value) => `${(value / 1000).toFixed(0)} GW`}
                    tick={{ fill: 'currentColor', fontSize: 12 }}
                    domain={[0, 'auto']}
                  />
                  <Tooltip
                    formatter={(value: number, name: string) => {
                      const labels: Record<string, string> = {
                        solar: 'Solaire',
                        wind: 'Éolien',
                        total: 'Total',
                      }
                      return [formatMW(value), labels[name] || name]
                    }}
                    labelFormatter={(label) => `Heure : ${label}`}
                    contentStyle={{
                      backgroundColor: 'var(--tooltip-bg, #fff)',
                      border: '1px solid var(--tooltip-border, #e5e7eb)',
                      borderRadius: '0.5rem',
                    }}
                  />
                  <Legend
                    formatter={(value) => {
                      const labels: Record<string, string> = {
                        solar: 'Solaire',
                        wind: 'Éolien',
                      }
                      return labels[value] || value
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="solar"
                    stackId="1"
                    stroke="#f59e0b"
                    fill="#fcd34d"
                    fillOpacity={0.6}
                  />
                  <Area
                    type="monotone"
                    dataKey="wind"
                    stackId="1"
                    stroke="#3b82f6"
                    fill="#93c5fd"
                    fillOpacity={0.6}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-[300px] text-center">
              <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-xl border border-yellow-200 dark:border-yellow-800 max-w-md">
                <p className="text-yellow-800 dark:text-yellow-200 font-medium mb-2">
                  Données non disponibles
                </p>
                <p className="text-yellow-700 dark:text-yellow-300 text-sm">
                  Les données de production renouvelable ne sont pas encore chargées.
                  {isClientMode
                    ? ' Cliquez sur "Synchroniser" pour récupérer les données depuis la passerelle.'
                    : ' Les données seront chargées automatiquement.'}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Info combinée */}
        <div className="bg-blue-50 dark:bg-blue-900/20 rounded-xl border border-blue-200 dark:border-blue-800 p-6">
          <div className="flex items-start gap-3">
            <Info className="text-blue-600 dark:text-blue-400 mt-1 flex-shrink-0" size={20} />
            <div>
              <h3 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">
                À propos des données
              </h3>
              <p className="text-blue-800 dark:text-blue-200 text-sm mb-3">
                Ces données proviennent de l'API RTE et sont mises à jour automatiquement.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div>
                  <h4 className="font-medium text-blue-900 dark:text-blue-100 mb-1">Consommation</h4>
                  <ul className="text-blue-800 dark:text-blue-200 list-disc list-inside space-y-0.5">
                    <li><strong>Réalisé</strong> : Mesure temps réel (15 min)</li>
                    <li><strong>Intraday</strong> : Prévision horaire</li>
                    <li><strong>D-1</strong> : Prévision de la veille</li>
                  </ul>
                </div>
                <div>
                  <h4 className="font-medium text-blue-900 dark:text-blue-100 mb-1">Production renouvelable</h4>
                  <ul className="text-blue-800 dark:text-blue-200 list-disc list-inside space-y-0.5">
                    <li>Solaire centralisé</li>
                    <li>Éolien (onshore + offshore)</li>
                    <li>Granularité : 1 heure</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
