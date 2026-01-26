import { useQuery } from '@tanstack/react-query'
import { energyApi, type EnergyProvider } from '@/api/energy'

/**
 * Hook pour récupérer la liste des fournisseurs d'énergie
 */
export function useProviders() {
  const { data: providers, isLoading, error } = useQuery({
    queryKey: ['energy-providers'],
    queryFn: async () => {
      const response = await energyApi.getProviders()
      if (response.success && Array.isArray(response.data)) {
        return response.data as EnergyProvider[]
      }
      return []
    },
  })

  return {
    providers: providers || [],
    isLoading,
    error,
  }
}
