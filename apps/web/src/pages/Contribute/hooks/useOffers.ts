import { useQuery } from '@tanstack/react-query'
import { energyApi, type EnergyOffer } from '@/api/energy'

/**
 * Hook pour récupérer toutes les offres d'énergie
 */
export function useOffers() {
  const { data: offers, isLoading, error } = useQuery({
    queryKey: ['energy-offers'],
    queryFn: async () => {
      const response = await energyApi.getOffers()
      if (response.success && Array.isArray(response.data)) {
        return response.data as EnergyOffer[]
      }
      return []
    },
  })

  return {
    offers: offers || [],
    isLoading,
    error,
  }
}
