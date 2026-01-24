import { apiClient } from './client'

// Types pour l'API RTE Admin

export interface RTEApiInfo {
  name: string
  description: string
  doc_url: string
}

export interface RTEStatusResponse {
  has_credentials: boolean
  base_url: string
  client_id_configured: boolean
  client_secret_configured: boolean
  apis: Record<string, RTEApiInfo>
}

export interface RTEApiTestResult {
  api: string
  name: string
  status: 'ok' | 'forbidden' | 'rate_limited' | 'server_error' | 'timeout' | 'error'
  status_code?: number
  response_time_ms?: number
  summary?: {
    total_days?: number
    colors?: { BLUE: number; WHITE: number; RED: number }
    latest_date?: string
    total_signals?: number
    latest_dvalue?: number
    forecast_count?: number
    values_count?: number
    min_mw?: number
    max_mw?: number
    avg_mw?: number
    by_production_type?: Record<string, number>
  }
  data?: unknown
  error?: string
  error_details?: unknown
  help?: string
}

export interface RTETestAllResponse {
  summary: {
    total_apis: number
    apis_ok: number
    apis_failed: number
    all_ok: boolean
  }
  results: Record<string, RTEApiTestResult>
  tested_at: string
}

export interface RTERefreshResponse {
  message: string
  updated_count: number
}

export const rteApi = {
  // Obtenir le statut de la configuration RTE
  getStatus: async () => {
    return apiClient.get<RTEStatusResponse>('admin/rte/status')
  },

  // Tester toutes les API RTE
  testAll: async () => {
    return apiClient.get<RTETestAllResponse>('admin/rte/test')
  },

  // Tester une API RTE spécifique
  testSingle: async (apiKey: string) => {
    return apiClient.get<RTEApiTestResult>(`admin/rte/test/${apiKey}`)
  },

  // Rafraîchir le cache Tempo
  refreshTempo: async () => {
    return apiClient.post<RTERefreshResponse>('admin/rte/refresh/tempo')
  },

  // Rafraîchir le cache EcoWatt
  refreshEcowatt: async () => {
    return apiClient.post<RTERefreshResponse>('admin/rte/refresh/ecowatt')
  },
}
