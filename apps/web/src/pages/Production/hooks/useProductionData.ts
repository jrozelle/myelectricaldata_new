import { useQuery, useQueryClient } from '@tanstack/react-query'
import { pdlApi } from '@/api/pdl'
import { enedisApi } from '@/api/enedis'
import type { PDL } from '@/types/api'
import type { DateRange } from '../types/production.types'

export function useProductionData(selectedPDL: string, dateRange: DateRange | null, detailDateRange: DateRange | null, selectedPDLDetails: PDL | undefined) {
  const queryClient = useQueryClient()

  // Fetch PDLs
  const { data: pdlsData } = useQuery({
    queryKey: ['pdls'],
    queryFn: async () => {
      const response = await pdlApi.list()
      if (response.success && Array.isArray(response.data)) {
        return response.data as PDL[]
      }
      return []
    },
  })

  const pdls = Array.isArray(pdlsData) ? pdlsData : []

  // Filter only active PDLs that have production enabled
  const activePdls = pdls.filter(p => p.is_active !== false && p.has_production === true)

  // Fetch production data with React Query
  const { data: productionResponse, isLoading: isLoadingProduction } = useQuery({
    queryKey: ['production', selectedPDL, dateRange?.start, dateRange?.end],
    queryFn: async () => {
      if (!selectedPDL || !dateRange) return null

      // Calculate the total date range in days
      const startDate = new Date(dateRange.start + 'T00:00:00Z')
      const endDate = new Date(dateRange.end + 'T00:00:00Z')
      const totalDays = Math.ceil((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24))

      // If the range is <= 365 days, make a single call
      if (totalDays <= 365) {
        return enedisApi.getProductionDaily(selectedPDL, {
          start: dateRange.start,
          end: dateRange.end,
          use_cache: true,
        })
      }

      // Split into yearly chunks (max 365 days per call)
      const yearlyChunks: { start: string; end: string }[] = []
      let currentStart = new Date(startDate)

      while (currentStart <= endDate) {
        let currentEnd = new Date(currentStart)
        currentEnd.setUTCFullYear(currentEnd.getUTCFullYear() + 1)
        currentEnd.setUTCDate(currentEnd.getUTCDate() - 1)

        if (currentEnd > endDate) {
          currentEnd = new Date(endDate)
        }

        const chunkStart = currentStart.getUTCFullYear() + '-' +
                          String(currentStart.getUTCMonth() + 1).padStart(2, '0') + '-' +
                          String(currentStart.getUTCDate()).padStart(2, '0')
        const chunkEnd = currentEnd.getUTCFullYear() + '-' +
                        String(currentEnd.getUTCMonth() + 1).padStart(2, '0') + '-' +
                        String(currentEnd.getUTCDate()).padStart(2, '0')

        yearlyChunks.push({ start: chunkStart, end: chunkEnd })

        currentStart = new Date(currentEnd)
        currentStart.setUTCDate(currentStart.getUTCDate() + 1)
      }

      // Fetch all chunks in parallel
      const chunkPromises = yearlyChunks.map(chunk =>
        enedisApi.getProductionDaily(selectedPDL, {
          start: chunk.start,
          end: chunk.end,
          use_cache: true,
        })
      )

      const chunkResults = await Promise.all(chunkPromises)

      // Merge all chunks into a single response
      const firstSuccess = chunkResults.find(r => r?.success)
      if (!firstSuccess) {
        return chunkResults[0]
      }

      // Combine all interval_reading arrays
      const allReadings: any[] = []
      for (const result of chunkResults) {
        if (result?.success && (result as any)?.data?.meter_reading?.interval_reading) {
          allReadings.push(...(result as any).data.meter_reading.interval_reading)
        }
      }

      return {
        ...firstSuccess,
        data: {
          ...(firstSuccess.data as any),
          meter_reading: {
            ...(firstSuccess.data as any)?.meter_reading,
            interval_reading: allReadings
          }
        }
      }
    },
    enabled: !!selectedPDL && !!dateRange,
    staleTime: 1000 * 60 * 60, // 1 hour - data is considered fresh
    gcTime: 1000 * 60 * 60 * 24, // 24 hours - keep in cache
  })

  // Production doesn't have max power data - skip this query

  // Fetch detailed production data (load curve)
  const shouldFetchDetail = !!selectedPDL &&
                           !!detailDateRange &&
                           selectedPDLDetails?.is_active &&
                           selectedPDLDetails?.has_production

  const { data: detailResponse, isLoading: isLoadingDetail } = useQuery({
    queryKey: ['productionDetail', selectedPDL, detailDateRange?.start, detailDateRange?.end],
    queryFn: async () => {
      if (!selectedPDL || !detailDateRange) return null

      try {
        // Get all days in the range from cache (day by day)
        const startDate = new Date(detailDateRange.start + 'T00:00:00Z')
        const endDate = new Date(detailDateRange.end + 'T00:00:00Z')
        const allPoints: any[] = []

        // Iterate through each day in the range
        const currentDate = new Date(startDate)
        while (currentDate <= endDate) {
          const dateStr = currentDate.getUTCFullYear() + '-' +
                         String(currentDate.getUTCMonth() + 1).padStart(2, '0') + '-' +
                         String(currentDate.getUTCDate()).padStart(2, '0')

          // Try to get this day's data from cache
          const dayData = queryClient.getQueryData(['productionDetail', selectedPDL, dateStr, dateStr]) as any

          if (dayData?.data?.meter_reading?.interval_reading) {
            allPoints.push(...dayData.data.meter_reading.interval_reading)
          }

          // Move to next day
          currentDate.setUTCDate(currentDate.getUTCDate() + 1)
        }

        // Return combined data in the same format as API response
        return allPoints.length > 0 ? {
          success: true,
          data: {
            meter_reading: {
              interval_reading: allPoints
            }
          }
        } : null
      } catch (error) {
        console.error('Error in detailResponse queryFn:', error)
        return null
      }
    },
    enabled: shouldFetchDetail,
    staleTime: 1000 * 60 * 60, // 1 hour
    gcTime: 1000 * 60 * 60 * 24, // 24 hours
  })

  const productionData = (productionResponse as any)?.success ? (productionResponse as any).data : null
  const detailData = (detailResponse as any)?.success ? (detailResponse as any).data : null
  const isLoading = isLoadingProduction || isLoadingDetail

  return {
    pdls,
    activePdls,
    productionData,
    detailData,
    isLoading,
    isLoadingProduction,
    isLoadingDetail,
    queryClient
  }
}
