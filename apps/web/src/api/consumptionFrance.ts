import { apiClient } from './client'
import type { APIResponse } from '@/types/api'

// Types pour la consommation nationale
export interface ConsumptionFranceValue {
  start_date: string
  end_date: string
  value: number // MW
  updated_date: string | null
}

export interface ConsumptionFranceData {
  type: string // REALISED, ID, D-1, D-2
  values: ConsumptionFranceValue[]
}

export interface ConsumptionFranceResponse {
  short_term: ConsumptionFranceData[]
  period: {
    start: string
    end: string
  }
}

export interface ConsumptionFranceCurrent {
  start_date: string
  end_date: string
  value: number
  unit: string
  updated_date: string | null
}

export const consumptionFranceApi = {
  /**
   * Récupérer les données de consommation nationale
   */
  getConsumption: async (params?: {
    type?: string
    start_date?: string
    end_date?: string
  }): Promise<APIResponse<ConsumptionFranceResponse>> => {
    return apiClient.get<ConsumptionFranceResponse>('consumption-france', params)
  },

  /**
   * Récupérer la consommation actuelle (dernière valeur réalisée)
   */
  getCurrent: async (): Promise<APIResponse<ConsumptionFranceCurrent>> => {
    return apiClient.get<ConsumptionFranceCurrent>('consumption-france/current')
  },

  /**
   * Récupérer les prévisions de consommation
   */
  getForecast: async (days: number = 2): Promise<APIResponse<ConsumptionFranceResponse>> => {
    return apiClient.get<ConsumptionFranceResponse>('consumption-france/forecast', { days })
  },

  /**
   * Actualiser le cache (admin)
   */
  refresh: async (): Promise<APIResponse<{ message: string; updated_count: number }>> => {
    return apiClient.post<{ message: string; updated_count: number }>('consumption-france/refresh')
  },
}
