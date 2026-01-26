import { apiClient } from './client'

export interface TempoDay {
  date: string
  color: 'BLUE' | 'WHITE' | 'RED'
  updated_at?: string
  rte_updated_date?: string
}

export interface TempoForecastDay {
  date: string
  day_in_season: number
  probability_blue: number
  probability_white: number
  probability_red: number
  most_likely: 'BLUE' | 'WHITE' | 'RED'
  confidence: 'high' | 'medium' | 'low'
  threshold_white_red: number
  threshold_red: number
  normalized_consumption: number | null
  forecast_type: string
  factors: {
    is_winter: boolean
    is_weekend: boolean
    days_remaining_in_season: number
    blue_remaining: number
    white_remaining: number
    red_remaining: number
    has_rte_data: boolean
  }
}

export interface TempoForecastResponse {
  season: string
  season_stats: {
    blue_used: number
    blue_remaining: number
    white_used: number
    white_remaining: number
    red_used: number
    red_remaining: number
  }
  forecasts: TempoForecastDay[]
  algorithm_info: {
    description: string
    params_blanc_rouge: { A: number; B: number; C: number }
    params_rouge: { A: number; B: number; C: number }
    formula_blanc_rouge: string
    formula_rouge: string
  }
}

export const tempoApi = {
  // Get today's TEMPO color
  getToday: async () => {
    return apiClient.get<TempoDay>('tempo/today')
  },

  // Get next 7 days
  getWeek: async () => {
    return apiClient.get<TempoDay[]>('tempo/week')
  },

  // Get custom date range
  getDays: async (startDate?: string, endDate?: string) => {
    const params: Record<string, string> = {}
    if (startDate) params.start_date = startDate
    if (endDate) params.end_date = endDate
    return apiClient.get<TempoDay[]>('tempo/days', params)
  },

  // Manually refresh cache (authenticated)
  // RTE API limitation: only today + tomorrow (after 6am)
  refreshCache: async () => {
    return apiClient.post('tempo/refresh', {})
  },

  // Clear old data (admin only)
  clearOldData: async (daysToKeep: number = 30) => {
    return apiClient.delete(`tempo/clear-old?days_to_keep=${daysToKeep}`)
  },

  // Clear ALL cache (admin only)
  clearAllCache: async () => {
    return apiClient.delete('tempo/clear-all')
  },

  // Get forecast for next N days (1-8)
  getForecast: async (days: number = 8, forceRefresh: boolean = false) => {
    const params = new URLSearchParams({ days: days.toString() })
    if (forceRefresh) {
      params.append('force_refresh', 'true')
    }
    return apiClient.get<TempoForecastResponse>(`tempo/forecast?${params.toString()}`)
  },
}
