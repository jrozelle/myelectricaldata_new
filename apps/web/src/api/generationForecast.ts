import { apiClient } from './client'
import type { APIResponse } from '@/types/api'

// Types pour les prévisions de production
export interface GenerationForecastValue {
  start_date: string
  end_date: string
  value: number // MW
  updated_date: string | null
}

export interface GenerationForecastData {
  production_type: string // SOLAR, WIND
  forecast_type: string // D-3, D-2, D-1, ID, CURRENT
  values: GenerationForecastValue[]
}

export interface GenerationForecastResponse {
  forecasts: GenerationForecastData[]
  period: {
    start: string
    end: string
  }
}

export interface SolarForecastResponse {
  production_type: 'SOLAR'
  forecasts: {
    forecast_type: string
    values: GenerationForecastValue[]
  }[]
  period: {
    start: string
    end: string
  }
}

export interface WindForecastResponse {
  production_type: 'WIND'
  forecasts: {
    forecast_type: string
    values: GenerationForecastValue[]
  }[]
  period: {
    start: string
    end: string
  }
}

export interface RenewableMixValue {
  start_date: string
  solar: number
  wind: number
  total_renewable: number
}

export interface RenewableMixResponse {
  forecast_type: string
  mix: RenewableMixValue[]
  period: {
    start: string
    end: string
  }
}

export const generationForecastApi = {
  /**
   * Récupérer les prévisions de production
   */
  getForecasts: async (params?: {
    production_type?: string
    forecast_type?: string
    start_date?: string
    end_date?: string
  }): Promise<APIResponse<GenerationForecastResponse>> => {
    return apiClient.get<GenerationForecastResponse>('generation-forecast', params)
  },

  /**
   * Récupérer les prévisions solaires
   */
  getSolar: async (days: number = 3): Promise<APIResponse<SolarForecastResponse>> => {
    return apiClient.get<SolarForecastResponse>('generation-forecast/solar', { days })
  },

  /**
   * Récupérer les prévisions éoliennes
   */
  getWind: async (days: number = 3): Promise<APIResponse<WindForecastResponse>> => {
    return apiClient.get<WindForecastResponse>('generation-forecast/wind', { days })
  },

  /**
   * Récupérer le mix renouvelable prévu
   */
  getMix: async (): Promise<APIResponse<RenewableMixResponse>> => {
    return apiClient.get<RenewableMixResponse>('generation-forecast/mix')
  },

  /**
   * Actualiser le cache (admin)
   */
  refresh: async (productionType?: string): Promise<APIResponse<{ message: string; updated_count: number; production_type: string }>> => {
    return apiClient.post<{ message: string; updated_count: number; production_type: string }>(
      'generation-forecast/refresh',
      undefined,
      productionType ? { production_type: productionType } : undefined
    )
  },
}
