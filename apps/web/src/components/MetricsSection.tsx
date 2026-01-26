/**
 * Metrics Section Component
 *
 * Displays export metrics directly in the page (not in a modal).
 * Used by HomeAssistant, MQTT, and VictoriaMetrics export pages.
 */

import { useState } from 'react'
import {
  RefreshCw,
  AlertCircle,
  CheckCircle,
  ChevronDown,
  ChevronRight,
  Eye,
  Code,
  List,
} from 'lucide-react'
import { ExportMetric, ExportMetricsData } from '@/api/export'

interface MetricsSectionProps {
  /** Metrics data from API */
  metricsData: ExportMetricsData | null
  /** Loading state */
  isLoading: boolean
  /** Callback to reload metrics */
  onRefresh: () => void
  /** Icon component to use for empty state */
  emptyIcon?: React.ReactNode
  /** Title for the section */
  title?: string
  /** Subtitle for the section */
  subtitle?: string
  /** Custom field to display as metric identifier (topic, entity, name) */
  metricIdField?: 'topic' | 'entity' | 'name'
  /** Format as Home Assistant entity_id (sensor.prefix_...) */
  formatAsHomeAssistant?: boolean
}

export default function MetricsSection({
  metricsData,
  isLoading,
  onRefresh,
  emptyIcon,
  title = 'Métriques',
  subtitle = 'Données exportées',
  metricIdField = 'topic',
  formatAsHomeAssistant = false,
}: MetricsSectionProps) {
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set())
  const [detailedMode, setDetailedMode] = useState(false)

  /**
   * Convertit un topic MQTT en entity_id Home Assistant
   * Format HA: sensor.{prefix}_{pdl}_{metric} ou sensor.{prefix}_{metric}
   * Ex: "myelectricaldata/01226049119129/consumption/monthly"
   *  -> "sensor.myelectricaldata_01226049119129_consumption_monthly"
   * Ex: "myelectricaldata/tempo/today"
   *  -> "sensor.myelectricaldata_tempo_today"
   */
  const formatAsEntityId = (topic: string): string => {
    // Remplacer les / par des _ et nettoyer
    const entityName = topic
      .replace(/\//g, '_')  // Remplacer les slashes par des underscores
      .toLowerCase()
      .replace(/-/g, '_')  // Remplacer les tirets par des underscores
      .replace(/[^a-z0-9_]/g, '')  // Garder uniquement alphanumériques et underscores
      .replace(/_+/g, '_')  // Éviter les underscores multiples
      .replace(/^_|_$/g, '')  // Supprimer underscores en début/fin

    return `sensor.${entityName}`
  }

  const toggleCategory = (category: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev)
      if (next.has(category)) {
        next.delete(category)
      } else {
        next.add(category)
      }
      return next
    })
  }

  // Group metrics by category
  const groupedMetrics = metricsData?.metrics.reduce(
    (acc, metric) => {
      const category = metric.category || 'Autre'
      if (!acc[category]) {
        acc[category] = []
      }
      acc[category].push(metric)
      return acc
    },
    {} as Record<string, ExportMetric[]>
  )

  // Get the metric identifier based on type
  const getMetricId = (metric: ExportMetric): string => {
    // Pour Home Assistant, formater le topic en entity_id
    if (formatAsHomeAssistant && metric.topic) {
      return formatAsEntityId(metric.topic)
    }

    if (metricIdField === 'entity' && metric.entity) return metric.entity
    if (metricIdField === 'name' && metric.name) return metric.name
    return metric.topic || metric.entity || metric.name || 'unknown'
  }

  // Get the metric value to display
  const getMetricValue = (metric: ExportMetric): string => {
    const value = metric.state ?? metric.value
    if (value === undefined || value === null) return ''
    if (typeof value === 'object') return JSON.stringify(value, null, 2)
    return String(value)
  }

  return (
    <div className="mt-6 bg-white dark:bg-gray-800 rounded-xl shadow-md border border-gray-300 dark:border-gray-700 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <Eye size={20} className="text-purple-500" />
          <div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">
              {title}
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {subtitle}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* Mode Toggle */}
          <button
            onClick={() => setDetailedMode(!detailedMode)}
            className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm transition-colors ${
              detailedMode
                ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
            }`}
            title={detailedMode ? 'Mode simplifié' : 'Mode détaillé (JSON)'}
          >
            {detailedMode ? <Code size={16} /> : <List size={16} />}
            {detailedMode ? 'Détaillé' : 'Simple'}
          </button>
          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors disabled:opacity-50"
          >
            <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
            Actualiser
          </button>
        </div>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-8">
          <RefreshCw size={24} className="animate-spin text-primary-600 dark:text-primary-400 mb-3" />
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Chargement des métriques...
          </p>
        </div>
      ) : metricsData ? (
        <>
          {/* Connection status */}
          <div className="mb-4 p-3 bg-gray-50 dark:bg-gray-900/30 rounded-lg">
            <div className="flex flex-wrap items-center gap-4 text-sm text-gray-600 dark:text-gray-400">
              {metricsData.success ? (
                <span className="flex items-center gap-1 text-green-600 dark:text-green-400">
                  <CheckCircle size={16} /> Connecté
                </span>
              ) : (
                <span className="flex items-center gap-1 text-red-600 dark:text-red-400">
                  <AlertCircle size={16} /> Erreur
                </span>
              )}
              {metricsData.broker && (
                <span>
                  <strong>Broker:</strong> {metricsData.broker}
                </span>
              )}
              {metricsData.url && (
                <span>
                  <strong>URL:</strong> {metricsData.url}
                </span>
              )}
              {metricsData.entity_prefix && (
                <span>
                  <strong>Préfixe:</strong> {metricsData.entity_prefix}
                </span>
              )}
              {metricsData.database && (
                <span>
                  <strong>Base:</strong> {metricsData.database}
                </span>
              )}
            </div>
            {metricsData.message && (
              <p className="mt-2 text-sm text-gray-500 dark:text-gray-500">
                {metricsData.message}
              </p>
            )}
          </div>

          {/* Errors */}
          {metricsData.errors && metricsData.errors.length > 0 && (
            <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
              <p className="text-sm font-medium text-red-800 dark:text-red-200 mb-1">
                Erreurs rencontrées:
              </p>
              <ul className="text-sm text-red-700 dark:text-red-300 list-disc list-inside">
                {metricsData.errors.map((err, i) => (
                  <li key={i}>{err}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Metrics list */}
          {metricsData.metrics.length === 0 ? (
            <div className="text-center py-8">
              {emptyIcon || <Eye size={40} className="mx-auto text-gray-400 dark:text-gray-500 mb-3" />}
              <p className="text-gray-600 dark:text-gray-400">Aucune métrique trouvée</p>
              <p className="text-sm text-gray-500 dark:text-gray-500 mt-1">
                Les données n'ont peut-être pas encore été exportées
              </p>
            </div>
          ) : (
            <div className="space-y-2 max-h-[500px] overflow-y-auto">
              {groupedMetrics &&
                Object.entries(groupedMetrics).map(([category, metrics]) => (
                  <div
                    key={category}
                    className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden"
                  >
                    <button
                      onClick={() => toggleCategory(category)}
                      className="w-full flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-900/30 hover:bg-gray-100 dark:hover:bg-gray-900/50 transition-colors"
                    >
                      <div className="flex items-center gap-2">
                        {expandedCategories.has(category) ? (
                          <ChevronDown size={18} className="text-gray-500" />
                        ) : (
                          <ChevronRight size={18} className="text-gray-500" />
                        )}
                        <span className="font-medium text-gray-900 dark:text-white">
                          {category}
                        </span>
                        <span className="text-xs px-2 py-0.5 bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-full">
                          {metrics.length}
                        </span>
                      </div>
                    </button>

                    {expandedCategories.has(category) && (
                      <div className="divide-y divide-gray-200 dark:divide-gray-700">
                        {metrics.map((metric, idx) => {
                          // Utiliser les propriétés directement depuis l'interface ExportMetric
                          const { msg_type: msgType, raw_config: rawConfig, name: metricName, unit, device_class: deviceClass, icon, device } = metric

                          return (
                            <div
                              key={idx}
                              className="p-3 hover:bg-gray-50 dark:hover:bg-gray-900/20 transition-colors"
                            >
                              <div className="space-y-2">
                                <div className="flex items-start justify-between gap-4">
                                  <div className="flex-1 min-w-0">
                                    {/* Type badge + Entity name */}
                                    <div className="flex items-center gap-2 mb-1">
                                      {msgType && (
                                        <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                                          msgType === 'config'
                                            ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                                            : msgType === 'state'
                                            ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
                                            : 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300'
                                        }`}>
                                          {msgType}
                                        </span>
                                      )}
                                      {metricName && (
                                        <span className="text-sm font-medium text-gray-900 dark:text-white">
                                          {metricName}
                                        </span>
                                      )}
                                    </div>
                                    {/* Entity ID */}
                                    <p className="text-sm font-mono text-gray-700 dark:text-gray-300 break-all">
                                      {getMetricId(metric)}
                                    </p>
                                    {/* Metadata row */}
                                    <div className="flex flex-wrap items-center gap-2 mt-1">
                                      {metric.pdl && (
                                        <span className="text-xs text-gray-500 dark:text-gray-500">
                                          PDL: {metric.pdl}
                                        </span>
                                      )}
                                      {unit && (
                                        <span className="text-xs px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded">
                                          {unit}
                                        </span>
                                      )}
                                      {deviceClass && (
                                        <span className="text-xs px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded">
                                          {deviceClass}
                                        </span>
                                      )}
                                      {icon && (
                                        <span className="text-xs text-gray-500 dark:text-gray-500">
                                          {icon}
                                        </span>
                                      )}
                                      {device && (
                                        <span className="text-xs text-gray-500 dark:text-gray-500">
                                          Device: {device}
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                  {metric.timestamp && (
                                    <span className="text-xs text-gray-500 dark:text-gray-500 whitespace-nowrap">
                                      {new Date(metric.timestamp).toLocaleString('fr-FR')}
                                    </span>
                                  )}
                                </div>

                                {/* State value (simplifié) */}
                                {!detailedMode && getMetricValue(metric) && (
                                  <div className="bg-gray-100 dark:bg-gray-900/50 rounded p-2 overflow-x-auto">
                                    <pre className="text-xs text-gray-800 dark:text-gray-200 whitespace-pre-wrap break-all">
                                      {getMetricValue(metric)}
                                    </pre>
                                  </div>
                                )}

                                {/* Mode détaillé : affiche tout le JSON */}
                                {detailedMode && (
                                  <div className="bg-gray-100 dark:bg-gray-900/50 rounded p-2 overflow-x-auto">
                                    <pre className="text-xs text-gray-800 dark:text-gray-200 whitespace-pre-wrap break-all">
                                      {JSON.stringify(
                                        rawConfig || metric,
                                        null,
                                        2
                                      )}
                                    </pre>
                                  </div>
                                )}

                                {/* Attributes (for Home Assistant) - seulement en mode simple */}
                                {!detailedMode && metric.attributes && Object.keys(metric.attributes).length > 0 && (
                                  <div className="mt-2">
                                    <p className="text-xs text-gray-500 dark:text-gray-500 mb-1">
                                      Attributs:
                                    </p>
                                    <div className="bg-gray-100 dark:bg-gray-900/50 rounded p-2">
                                      <pre className="text-xs text-gray-600 dark:text-gray-400 whitespace-pre-wrap break-all">
                                        {JSON.stringify(metric.attributes, null, 2)}
                                      </pre>
                                    </div>
                                  </div>
                                )}

                                {/* Tags (for VictoriaMetrics) */}
                                {!detailedMode && metric.tags && Object.keys(metric.tags).length > 0 && (
                                  <div className="flex flex-wrap gap-1">
                                    {Object.entries(metric.tags).map(([key, value]) => (
                                      <span
                                        key={key}
                                        className="text-xs px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded"
                                      >
                                        {key}={String(value)}
                                      </span>
                                    ))}
                                  </div>
                                )}
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    )}
                  </div>
                ))}
            </div>
          )}
        </>
      ) : (
        <div className="text-center py-8">
          <AlertCircle size={40} className="mx-auto text-gray-400 dark:text-gray-500 mb-3" />
          <p className="text-gray-600 dark:text-gray-400">
            Cliquez sur "Actualiser" pour charger les métriques
          </p>
        </div>
      )}
    </div>
  )
}
