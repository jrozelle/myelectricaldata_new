export interface DateRange {
  start: string
  end: string
}

export interface LoadingProgress {
  current: number
  total: number
  currentRange: string
}

export interface ProductionAPIResponse {
  meter_reading: {
    interval_reading: Array<{
      date: string
      value: string | number
    }>
    reading_type?: {
      unit?: string
      interval_length?: string
    }
  }
}

export interface MaxPowerAPIResponse {
  meter_reading: {
    interval_reading: Array<{
      date: string
      value: string | number
    }>
    reading_type?: {
      unit?: string
      interval_length?: string
    }
  }
}

export interface DetailAPIResponse {
  meter_reading: {
    interval_reading: Array<{
      date: string
      value: string | number
    }>
    reading_type?: {
      unit?: string
      interval_length?: string
    }
  }
}
