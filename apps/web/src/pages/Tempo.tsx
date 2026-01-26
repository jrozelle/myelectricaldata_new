import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { RefreshCw, Clock, TrendingUp, Info, ChevronDown, ChevronUp } from 'lucide-react'
import { tempoApi, type TempoDay, type TempoForecastDay } from '../api/tempo'
import { syncApi } from '../api/sync'
import { useAppMode } from '../hooks/useAppMode'
import { usePermissions } from '../hooks/usePermissions'
import { toast } from '../stores/notificationStore'

// Composant pour afficher la barre de probabilité d'une prévision
function ForecastProbabilityBar({ forecast }: { forecast: TempoForecastDay }) {
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    const dayNames = ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam']
    return {
      day: dayNames[date.getDay()],
      date: date.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' }),
    }
  }

  const { day, date } = formatDate(forecast.date)

  const getConfidenceBadge = (confidence: string) => {
    switch (confidence) {
      case 'high':
        return (
          <span className="text-xs px-1.5 py-0.5 rounded bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300">
            Fiable
          </span>
        )
      case 'medium':
        return (
          <span className="text-xs px-1.5 py-0.5 rounded bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300">
            Modéré
          </span>
        )
      default:
        return (
          <span className="text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400">
            Estimé
          </span>
        )
    }
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
      {/* Header : Date et confiance */}
      <div className="flex items-center justify-between mb-3">
        <div>
          <span className="font-semibold text-gray-900 dark:text-white">{day}</span>
          <span className="text-sm text-gray-500 dark:text-gray-400 ml-2">{date}</span>
        </div>
        {getConfidenceBadge(forecast.confidence)}
      </div>

      {/* Barre de probabilité */}
      <div className="relative h-8 rounded-lg overflow-hidden flex">
        {/* Bleu */}
        <div
          className="bg-blue-500 flex items-center justify-center transition-all duration-300"
          style={{ width: `${forecast.probability_blue}%` }}
          title={`Bleu: ${forecast.probability_blue}%`}
        >
          {forecast.probability_blue >= 15 && (
            <span className="text-xs font-medium text-white">
              {Math.round(forecast.probability_blue)}%
            </span>
          )}
        </div>
        {/* Blanc */}
        <div
          className="bg-gray-300 dark:bg-gray-400 flex items-center justify-center transition-all duration-300"
          style={{ width: `${forecast.probability_white}%` }}
          title={`Blanc: ${forecast.probability_white}%`}
        >
          {forecast.probability_white >= 15 && (
            <span className="text-xs font-medium text-gray-800">
              {Math.round(forecast.probability_white)}%
            </span>
          )}
        </div>
        {/* Rouge */}
        <div
          className="bg-red-500 flex items-center justify-center transition-all duration-300"
          style={{ width: `${forecast.probability_red}%` }}
          title={`Rouge: ${forecast.probability_red}%`}
        >
          {forecast.probability_red >= 15 && (
            <span className="text-xs font-medium text-white">
              {Math.round(forecast.probability_red)}%
            </span>
          )}
        </div>
      </div>

      {/* Couleur la plus probable */}
      <div className="mt-2 flex items-center gap-2 text-sm">
        <span className="text-gray-500 dark:text-gray-400">Prévision :</span>
        <span
          className={`font-medium ${
            forecast.most_likely === 'BLUE'
              ? 'text-blue-600 dark:text-blue-400'
              : forecast.most_likely === 'WHITE'
              ? 'text-gray-700 dark:text-gray-300'
              : 'text-red-600 dark:text-red-400'
          }`}
        >
          {forecast.most_likely === 'BLUE'
            ? 'Jour Bleu'
            : forecast.most_likely === 'WHITE'
            ? 'Jour Blanc'
            : 'Jour Rouge'}
        </span>
      </div>
    </div>
  )
}

export default function Tempo() {
  const { isClientMode } = useAppMode()
  const { isAdmin } = usePermissions()
  const queryClient = useQueryClient()
  const [syncing, setSyncing] = useState(false)
  const [refreshingForecast, setRefreshingForecast] = useState(false)
  const [showAlgorithmInfo, setShowAlgorithmInfo] = useState(false)

  // Fetch sync status (last sync time) - only in client mode
  const { data: syncStatus } = useQuery({
    queryKey: ['tempo-sync-status'],
    queryFn: () => syncApi.getTempoStatus(),
    enabled: isClientMode,
    refetchInterval: 60000, // Refresh every minute
  })

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

  const handleSync = async () => {
    setSyncing(true)
    const loadingId = toast.loading('Synchronisation des données Tempo...')
    try {
      const response = await syncApi.syncTempoNow()
      toast.dismiss(loadingId)
      // Response structure: { success: boolean, data: { created, updated, errors }, message }
      if (response.success && response.data) {
        const { created, updated, errors } = response.data
        if (errors && errors.length > 0) {
          const firstError = errors[0]
          if (firstError.includes('404')) {
            toast.error('L\'API Tempo n\'est pas encore disponible sur la passerelle distante')
          } else {
            toast.warning(`Synchronisation partielle : ${created} créés, ${updated} mis à jour, ${errors.length} erreur(s)`)
          }
        } else if (created > 0 || updated > 0) {
          toast.success(`Synchronisation réussie : ${created} créés, ${updated} mis à jour`)
          queryClient.invalidateQueries({ queryKey: ['tempo-all'] })
          queryClient.invalidateQueries({ queryKey: ['tempo-sync-status'] })
        } else {
          toast.info('Aucune nouvelle donnée Tempo à synchroniser')
        }
      } else {
        toast.error('Échec de la synchronisation')
      }
    } catch (err) {
      toast.dismiss(loadingId)
      const errorMessage = err instanceof Error ? err.message : 'Erreur inconnue'
      toast.error(`Échec de la synchronisation : ${errorMessage}`)
    } finally {
      setSyncing(false)
    }
  }

  const handleRefreshForecast = async () => {
    setRefreshingForecast(true)
    const loadingId = toast.loading('Rafraîchissement des prévisions Tempo...')
    try {
      // Forcer le rafraîchissement côté backend
      const response = await tempoApi.getForecast(6, true)
      toast.dismiss(loadingId)
      if (response.success) {
        toast.success('Prévisions mises à jour depuis les API RTE')
        // Invalider le cache React Query pour forcer le re-render
        queryClient.invalidateQueries({ queryKey: ['tempo-forecast'] })
      } else {
        toast.error('Échec du rafraîchissement des prévisions')
      }
    } catch (err) {
      toast.dismiss(loadingId)
      const errorMessage = err instanceof Error ? err.message : 'Erreur inconnue'
      toast.error(`Échec du rafraîchissement : ${errorMessage}`)
    } finally {
      setRefreshingForecast(false)
    }
  }

  const { data: tempoData, isLoading } = useQuery({
    queryKey: ['tempo-all'],
    queryFn: () => tempoApi.getDays(),
  })

  // Fetch forecast data
  // Note: Le backend a un cache de 4h, donc on peut rafraîchir plus souvent côté frontend
  const { data: forecastData, isLoading: forecastLoading } = useQuery({
    queryKey: ['tempo-forecast'],
    queryFn: () => tempoApi.getForecast(6),
    staleTime: 1000 * 60 * 5, // Cache 5 minutes (le backend gère le cache long)
    refetchInterval: 1000 * 60 * 15, // Refetch every 15 minutes
  })

  if (isLoading) {
    return (
      <div className="w-full">
        <div className="flex items-center justify-center py-12">
          <p className="text-gray-600 dark:text-gray-400">Chargement des données...</p>
        </div>
      </div>
    )
  }

  // Ensure data is always an array
  const allDays: TempoDay[] = Array.isArray(tempoData?.data) ? tempoData.data : []

  // Get today's and tomorrow's colors
  const today = new Date().toISOString().split('T')[0] // YYYY-MM-DD
  const tomorrow = new Date(Date.now() + 86400000).toISOString().split('T')[0]
  const todayData = allDays.find(d => d.date === today)
  const tomorrowData = allDays.find(d => d.date === tomorrow)

  const getColorInfo = (color: string | undefined) => {
    switch (color) {
      case 'BLUE':
        return {
          label: 'Jour Bleu',
          bgClass: 'bg-blue-500',
          textClass: 'text-white',
          borderClass: 'border-blue-600',
          description: 'Tarif le plus avantageux'
        }
      case 'WHITE':
        return {
          label: 'Jour Blanc',
          bgClass: 'bg-white dark:bg-gray-100',
          textClass: 'text-gray-900',
          borderClass: 'border-gray-400',
          description: 'Tarif intermédiaire'
        }
      case 'RED':
        return {
          label: 'Jour Rouge',
          bgClass: 'bg-red-500',
          textClass: 'text-white',
          borderClass: 'border-red-600',
          description: 'Tarif le plus élevé - Réduisez votre consommation'
        }
      default:
        return {
          label: 'Non disponible',
          bgClass: 'bg-gray-300 dark:bg-gray-600',
          textClass: 'text-gray-700 dark:text-gray-300',
          borderClass: 'border-gray-400',
          description: 'Couleur non encore déterminée'
        }
    }
  }

  if (!tempoData?.success || allDays.length === 0) {
    return (
      <div className="w-full">
        {/* Bouton de synchronisation (client mode uniquement) */}
        {isClientMode && (
          <div className="mb-6 flex justify-end">
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
        <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
          <p className="text-sm text-yellow-800 dark:text-yellow-200">
            Aucune donnée Tempo disponible.
            {isClientMode && ' Cliquez sur "Synchroniser" pour récupérer les données depuis la passerelle.'}
          </p>
        </div>
      </div>
    )
  }

  // Group days by TEMPO season (Sept 1 to Aug 31)
  // TEMPO season: Sept Year N to Aug Year N+1 = Season "N/N+1"
  const groupedBySeason: Record<string, Record<string, TempoDay[]>> = {}
  allDays.forEach((day) => {
    // Parse date as local date (YYYY-MM-DD) to avoid timezone issues
    const [year, month] = day.date.split('-').map(Number)
    const monthIndex = month - 1 // Convert to 0-based index (0=Jan, 8=Sept)

    // TEMPO season starts Sept 1 (month 8)
    const seasonStart = monthIndex >= 8 ? year : year - 1
    const seasonKey = `${seasonStart}/${seasonStart + 1}`

    if (!groupedBySeason[seasonKey]) {
      groupedBySeason[seasonKey] = {}
    }
    if (!groupedBySeason[seasonKey][monthIndex]) {
      groupedBySeason[seasonKey][monthIndex] = []
    }
    groupedBySeason[seasonKey][monthIndex].push(day)
  })

  const seasons = Object.keys(groupedBySeason).sort((a, b) => {
    const yearA = parseInt(a.split('/')[0])
    const yearB = parseInt(b.split('/')[0])
    return yearB - yearA // Most recent first
  })

  const getColorClasses = (color: string) => {
    switch (color) {
      case 'BLUE':
        return 'bg-blue-500 text-white'
      case 'WHITE':
        return 'bg-white dark:bg-white text-gray-900 dark:text-gray-900 border border-gray-400 dark:border-gray-500'
      case 'RED':
        return 'bg-red-500 text-white'
      default:
        return 'bg-gray-300 text-gray-700'
    }
  }

  const monthNames = [
    'Janvier',
    'Février',
    'Mars',
    'Avril',
    'Mai',
    'Juin',
    'Juillet',
    'Août',
    'Septembre',
    'Octobre',
    'Novembre',
    'Décembre',
  ]

  const renderMonth = (season: string, month: number) => {
    const days = groupedBySeason[season][month] || []
    if (days.length === 0) return null

    // Sort days by date (using string comparison for YYYY-MM-DD format)
    days.sort((a, b) => a.date.localeCompare(b.date))

    // Get actual year for this month (Sept-Dec uses first year, Jan-Aug uses second year)
    const [year1, year2] = season.split('/').map(Number)
    const actualYear = month >= 8 ? year1 : year2

    // Get first day of month to determine offset
    const firstDay = new Date(actualYear, month, 1)
    const firstDayOfWeek = firstDay.getDay() // 0 = Sunday, 1 = Monday, ...
    const offset = firstDayOfWeek === 0 ? 6 : firstDayOfWeek - 1 // Convert to Monday = 0

    // Get number of days in month
    const daysInMonth = new Date(actualYear, month + 1, 0).getDate()

    // Create array for all days in month
    const calendarDays: (TempoDay | null)[] = Array(daysInMonth).fill(null)
    days.forEach((day) => {
      // Extract day number from YYYY-MM-DD format (avoids timezone issues)
      const dayNum = parseInt(day.date.split('-')[2], 10)
      calendarDays[dayNum - 1] = day
    })

    return (
      <div key={`${season}-${month}`} className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
        <h3 className="font-semibold text-lg mb-3 text-center">{monthNames[month]} {actualYear}</h3>

        {/* Week day headers */}
        <div className="grid grid-cols-7 gap-1 mb-2">
          {['L', 'M', 'M', 'J', 'V', 'S', 'D'].map((day, idx) => (
            <div key={idx} className="text-center text-xs font-semibold text-gray-600 dark:text-gray-400">
              {day}
            </div>
          ))}
        </div>

        {/* Calendar grid */}
        <div className="grid grid-cols-7 gap-1">
          {/* Offset for first day of month */}
          {Array(offset)
            .fill(null)
            .map((_, idx) => (
              <div key={`offset-${idx}`} />
            ))}

          {/* Days */}
          {calendarDays.map((day, idx) => {
            const dayNum = idx + 1
            return (
              <div
                key={dayNum}
                className={`aspect-square flex items-center justify-center text-sm font-medium rounded ${
                  day ? getColorClasses(day.color) : 'bg-gray-100 dark:bg-gray-700 text-gray-400'
                }`}
                title={day ? `${dayNum} - ${day.color}` : `${dayNum}`}
              >
                {dayNum}
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  // Count colors by season
  const getSeasonStats = (season: string) => {
    const seasonData = groupedBySeason[season]
    const stats = { BLUE: 0, WHITE: 0, RED: 0 }

    Object.values(seasonData).forEach((monthDays) => {
      monthDays.forEach((day) => {
        if (day.color in stats) {
          stats[day.color as keyof typeof stats]++
        }
      })
    })

    return stats
  }

  // Get current season stats
  const getCurrentSeasonStats = () => {
    const today = new Date()
    const year = today.getFullYear()
    const month = today.getMonth()

    // Determine current season
    const currentSeasonStart = month >= 8 ? year : year - 1
    const currentSeasonKey = `${currentSeasonStart}/${currentSeasonStart + 1}`

    if (!groupedBySeason[currentSeasonKey]) {
      return null
    }

    const stats = getSeasonStats(currentSeasonKey)
    return {
      season: currentSeasonKey,
      blueUsed: stats.BLUE,
      whiteUsed: stats.WHITE,
      redUsed: stats.RED,
      blueRemaining: 300 - stats.BLUE,
      whiteRemaining: 43 - stats.WHITE,
      redRemaining: 22 - stats.RED,
    }
  }

  const currentSeasonStats = getCurrentSeasonStats()

  const todayInfo = getColorInfo(todayData?.color)
  const tomorrowInfo = getColorInfo(tomorrowData?.color)

  return (
    <div className="w-full space-y-6">
      {/* Current Season Summary */}
      {currentSeasonStats && (
        <div className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-gray-800 dark:to-gray-700 rounded-lg p-6 border border-blue-200 dark:border-gray-600">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold">Saison en cours : {currentSeasonStats.season}</h2>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                Du 1er septembre au 31 août
              </p>
            </div>
            {/* Bouton de synchronisation (client mode uniquement) */}
            {isClientMode && (
              <div className="flex items-center gap-3">
                <span className="text-sm text-gray-500 dark:text-gray-400 flex items-center gap-1">
                  <Clock className="w-4 h-4" />
                  {formatLastSync(syncStatus?.data?.last_sync_at)}
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
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Blue days */}
            <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border-l-4 border-blue-500">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-semibold text-gray-600 dark:text-gray-400">Jours Bleus Restants</span>
                <span className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                  {currentSeasonStats.blueRemaining}
                </span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-500 dark:text-gray-400">Utilisés : {currentSeasonStats.blueUsed}</span>
                <span className="text-gray-500 dark:text-gray-400">/ 300</span>
              </div>
              <div className="mt-2 bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-blue-500 h-full transition-all"
                  style={{ width: `${(currentSeasonStats.blueUsed / 300) * 100}%` }}
                />
              </div>
            </div>

            {/* White days */}
            <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border-l-4 border-gray-500">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-semibold text-gray-600 dark:text-gray-400">Jours Blancs Restants</span>
                <span className="text-2xl font-bold text-gray-700 dark:text-gray-300">
                  {currentSeasonStats.whiteRemaining}
                </span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-500 dark:text-gray-400">Utilisés : {currentSeasonStats.whiteUsed}</span>
                <span className="text-gray-500 dark:text-gray-400">/ 43</span>
              </div>
              <div className="mt-2 bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-gray-500 h-full transition-all"
                  style={{ width: `${(currentSeasonStats.whiteUsed / 43) * 100}%` }}
                />
              </div>
            </div>

            {/* Red days */}
            <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border-l-4 border-red-500">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-semibold text-gray-600 dark:text-gray-400">Jours Rouges Restants</span>
                <span className="text-2xl font-bold text-red-600 dark:text-red-400">
                  {currentSeasonStats.redRemaining}
                </span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-500 dark:text-gray-400">Utilisés : {currentSeasonStats.redUsed}</span>
                <span className="text-gray-500 dark:text-gray-400">/ 22</span>
              </div>
              <div className="mt-2 bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-red-500 h-full transition-all"
                  style={{ width: `${(currentSeasonStats.redUsed / 22) * 100}%` }}
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Today and Tomorrow Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Today */}
        <div className={`rounded-xl p-6 border-2 ${todayInfo.borderClass} ${todayInfo.bgClass} shadow-lg`}>
          <div>
            <p className={`text-sm font-medium ${todayInfo.textClass} opacity-80`}>Aujourd'hui</p>
            <p className={`text-3xl font-bold ${todayInfo.textClass}`}>{todayInfo.label}</p>
            <p className={`text-sm mt-1 ${todayInfo.textClass} opacity-80`}>{todayInfo.description}</p>
          </div>
        </div>

        {/* Tomorrow */}
        <div className={`rounded-xl p-6 border-2 ${tomorrowInfo.borderClass} ${tomorrowInfo.bgClass} shadow-lg`}>
          <div>
            <p className={`text-sm font-medium ${tomorrowInfo.textClass} opacity-80`}>Demain</p>
            <p className={`text-3xl font-bold ${tomorrowInfo.textClass}`}>{tomorrowInfo.label}</p>
            <p className={`text-sm mt-1 ${tomorrowInfo.textClass} opacity-80`}>{tomorrowInfo.description}</p>
          </div>
        </div>
      </div>

      {/* Forecast Section - 8 prochains jours */}
      <div className="bg-gradient-to-r from-purple-50 to-indigo-50 dark:from-gray-800 dark:to-gray-700 rounded-xl p-6 border border-purple-200 dark:border-gray-600">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <TrendingUp className="w-6 h-6 text-purple-600 dark:text-purple-400" />
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Prévisions des 6 prochains jours
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Estimation basée sur l'algorithme RTE officiel
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {/* Bouton rafraîchissement réservé aux admins en mode serveur uniquement */}
            {!isClientMode && isAdmin() && (
              <button
                onClick={handleRefreshForecast}
                disabled={refreshingForecast}
                className="flex items-center gap-2 px-3 py-1.5 bg-purple-600 hover:bg-purple-700 dark:bg-purple-500 dark:hover:bg-purple-600 text-white text-sm rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                title="Rafraîchir les prévisions depuis les API RTE (Admin)"
              >
                <RefreshCw className={`w-4 h-4 ${refreshingForecast ? 'animate-spin' : ''}`} />
                {refreshingForecast ? 'Rafraîchissement...' : 'Rafraîchir'}
              </button>
            )}
            <button
              onClick={() => setShowAlgorithmInfo(!showAlgorithmInfo)}
              className="flex items-center gap-1 text-sm text-purple-600 dark:text-purple-400 hover:underline"
            >
              <Info className="w-4 h-4" />
              {showAlgorithmInfo ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Info algorithme - avec fallback statique si données non disponibles */}
        {showAlgorithmInfo && (
          <div className="mb-4 p-4 bg-white/50 dark:bg-gray-900/30 rounded-lg text-sm">
            <p className="font-medium text-gray-700 dark:text-gray-300 mb-2">
              {forecastData?.data?.algorithm_info?.description || 'Algorithme basé sur les seuils RTE officiels'}
            </p>
            <div className="space-y-1 text-gray-600 dark:text-gray-400 font-mono text-xs">
              <p>• {forecastData?.data?.algorithm_info?.formula_blanc_rouge || 'Seuil = A - B × JourTempo - C × StockRestant(Blanc+Rouge)'}</p>
              <p>• {forecastData?.data?.algorithm_info?.formula_rouge || "Seuil = A' - B' × JourTempo - C' × StockRestant(Rouge)"}</p>
            </div>
            <p className="mt-2 text-gray-500 dark:text-gray-500 text-xs">
              La consommation nette normalisée est comparée à ces seuils pour déterminer la couleur.
            </p>
          </div>
        )}

        {/* Prévisions */}
        {forecastLoading ? (
          <div className="flex items-center justify-center py-8">
            <p className="text-gray-600 dark:text-gray-400">Chargement des prévisions...</p>
          </div>
        ) : forecastData?.success && forecastData.data?.forecasts ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {forecastData.data.forecasts.map((forecast) => (
              <ForecastProbabilityBar key={forecast.date} forecast={forecast} />
            ))}
          </div>
        ) : (
          <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
            <p className="text-sm text-yellow-800 dark:text-yellow-200">
              Les prévisions ne sont pas disponibles. Vérifiez que les APIs RTE Consumption et Generation sont activées.
            </p>
          </div>
        )}

        {/* Légende des niveaux de confiance */}
        <div className="mt-4 flex gap-4 flex-wrap text-xs text-gray-600 dark:text-gray-400">
          <span className="flex items-center gap-1">
            <span className="px-1.5 py-0.5 rounded bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300">
              Fiable
            </span>
            = Données RTE disponibles
          </span>
          <span className="flex items-center gap-1">
            <span className="px-1.5 py-0.5 rounded bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300">
              Modéré
            </span>
            = Estimation avec historique
          </span>
          <span className="flex items-center gap-1">
            <span className="px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400">
              Estimé
            </span>
            = Projection statistique
          </span>
        </div>
      </div>

      {/* Legend */}
      <div className="flex gap-6 flex-wrap">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 bg-blue-500 rounded"></div>
          <span className="text-sm">Jour Bleu (300 jours/an)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 bg-white dark:bg-gray-200 border border-gray-400 rounded"></div>
          <span className="text-sm">Jour Blanc (43 jours/an)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 bg-red-500 rounded"></div>
          <span className="text-sm">Jour Rouge (22 jours/an)</span>
        </div>
      </div>

      {seasons.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-600 dark:text-gray-400">Aucune donnée Tempo disponible</p>
        </div>
      ) : (
        <div className="space-y-12">
          {seasons.map((season) => {
            const stats = getSeasonStats(season)
            const months = Object.keys(groupedBySeason[season])
              .map(Number)
              .sort((a, b) => {
                // Sort months from most recent to oldest within a season
                // For a season (Sept N to Aug N+1):
                // - Jan-Aug (0-7) are more recent (year N+1)
                // - Sept-Dec (8-11) are older (year N)
                const orderA = a >= 8 ? a - 8 : a + 4
                const orderB = b >= 8 ? b - 8 : b + 4
                return orderB - orderA // Inverted for reverse order (most recent first)
              })

            return (
              <div key={season}>
                <div className="mb-4">
                  <h2 className="text-lg font-semibold">Saison Tempo {season}</h2>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                    Du 1er septembre au 31 août
                  </p>
                  <div className="flex gap-4 mt-2 text-sm">
                    <span className="text-blue-600 dark:text-blue-400">
                      {stats.BLUE} jours bleus
                    </span>
                    <span className="text-gray-700 dark:text-gray-300">
                      {stats.WHITE} jours blancs
                    </span>
                    <span className="text-red-600 dark:text-red-400">
                      {stats.RED} jours rouges
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                  {months.map((month) => renderMonth(season, month))}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
