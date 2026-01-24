import { useState } from 'react'
import { type PowerVariant } from '../types'

/**
 * Hook pour gérer l'état du formulaire de contribution
 */
export function useContributionForm() {
  const [formState, setFormState] = useState({
    contributionType: 'NEW_OFFER' as 'NEW_PROVIDER' | 'NEW_OFFER',
    providerName: '',
    providerWebsite: '',
    selectedProviderId: '',
    offerName: '',
    offerType: 'BASE',
    description: '',
    powerVariants: [] as PowerVariant[],
    priceSheetUrl: '',
    screenshotUrl: '',
  })

  const handleFormStateChange = (key: string, value: unknown) => {
    setFormState(prev => ({ ...prev, [key]: value }))
  }

  const resetForm = () => {
    setFormState({
      contributionType: 'NEW_OFFER',
      providerName: '',
      providerWebsite: '',
      selectedProviderId: '',
      offerName: '',
      offerType: 'BASE',
      description: '',
      powerVariants: [],
      priceSheetUrl: '',
      screenshotUrl: '',
    })
  }

  return {
    formState,
    setFormState,
    handleFormStateChange,
    resetForm,
  }
}
