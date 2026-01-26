import { useQuery, useQueryClient } from '@tanstack/react-query'
import { energyApi, type Contribution } from '@/api/energy'

/**
 * Hook pour récupérer les contributions de l'utilisateur
 */
export function useContributions() {
  const queryClient = useQueryClient()

  const { data: contributions, isLoading, error } = useQuery({
    queryKey: ['my-contributions'],
    queryFn: async () => {
      const response = await energyApi.getMyContributions()
      if (response.success && Array.isArray(response.data)) {
        return response.data as Contribution[]
      }
      return []
    },
    refetchInterval: 10000, // Rafraîchit toutes les 10 secondes
  })

  const invalidateContributions = () => {
    queryClient.invalidateQueries({ queryKey: ['my-contributions'] })
  }

  return {
    contributions: contributions || [],
    isLoading,
    error,
    invalidateContributions,
  }
}
