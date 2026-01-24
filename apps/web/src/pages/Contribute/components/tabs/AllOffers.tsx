import { useState, useMemo, useEffect, useRef } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Package, Send, X, Link, AlertCircle, Plus, Trash2, Undo2, Eye, Pencil, Info } from 'lucide-react'
import { energyApi, type EnergyProvider, type ContributionData, type EnergyOffer } from '@/api/energy'
import { toast } from '@/stores/notificationStore'
import { LoadingOverlay } from '@/components/LoadingOverlay'
import { usePermissions } from '@/hooks/usePermissions'

export default function AllOffers() {
  const queryClient = useQueryClient()
  const { isAdmin, isModerator } = usePermissions()

  // Les admins et modérateurs n'ont pas besoin de fournir l'URL de la fiche tarifaire
  const isPrivilegedUser = isAdmin() || isModerator()

  // Mode lecture (par défaut) ou édition
  const [isEditMode, setIsEditMode] = useState(false)

  // Filter state
  const [filterProvider, setFilterProvider] = useState<string>('')
  const [filterOfferType, setFilterOfferType] = useState<string>('all')

  // State pour l'édition inline des offres
  const [editedOffers, setEditedOffers] = useState<Record<string, Record<string, string>>>({})
  const [submittingOffers, setSubmittingOffers] = useState(false)
  const [priceSheetUrl, setPriceSheetUrl] = useState('')
  const recapRef = useRef<HTMLDivElement>(null)

  // State pour les propositions d'ajout/suppression de puissances
  const [powersToRemove, setPowersToRemove] = useState<number[]>([])
  // Nouvelles puissances à ajouter avec leurs tarifs (liste)
  const [newPowersData, setNewPowersData] = useState<Array<{
    power: number
    fields: Record<string, string>
  }>>([])

  // Fetch providers
  const { data: providersData } = useQuery({
    queryKey: ['energy-providers'],
    queryFn: async () => {
      const response = await energyApi.getProviders()
      if (response.success && Array.isArray(response.data)) {
        return response.data as EnergyProvider[]
      }
      return []
    },
  })

  // Fetch all offers
  const { data: offersData } = useQuery({
    queryKey: ['energy-offers'],
    queryFn: async () => {
      const response = await energyApi.getOffers()
      if (response.success && Array.isArray(response.data)) {
        return response.data as EnergyOffer[]
      }
      return []
    },
  })

  // Normaliser offersData en tableau (protection contre les données corrompues du cache)
  const offersArray = useMemo(() => {
    return Array.isArray(offersData) ? offersData : []
  }, [offersData])

  // Trier les fournisseurs avec EDF en premier
  const sortedProviders = useMemo(() => {
    if (!Array.isArray(providersData)) return []
    return [...providersData].sort((a, b) => {
      if (a.name.toUpperCase() === 'EDF') return -1
      if (b.name.toUpperCase() === 'EDF') return 1
      return a.name.localeCompare(b.name)
    })
  }, [providersData])

  // Types d'offres disponibles pour le fournisseur sélectionné
  const availableOfferTypes = useMemo(() => {
    if (!filterProvider || offersArray.length === 0) return []
    const providerOffers = offersArray.filter(o => o.provider_id === filterProvider)
    const types = [...new Set(providerOffers.map(o => o.offer_type))]
    const typeOrder = ['BASE', 'HC_HP', 'TEMPO', 'EJP', 'ZEN_FLEX', 'ZEN_WEEK_END', 'ZEN_WEEK_END_HP_HC']
    return types.sort((a, b) => {
      const indexA = typeOrder.indexOf(a)
      const indexB = typeOrder.indexOf(b)
      if (indexA === -1 && indexB === -1) return a.localeCompare(b)
      if (indexA === -1) return 1
      if (indexB === -1) return -1
      return indexA - indexB
    })
  }, [filterProvider, offersArray])

  // Initialiser avec EDF par défaut
  useEffect(() => {
    if (sortedProviders.length > 0 && !filterProvider) {
      const edf = sortedProviders.find(p => p.name.toUpperCase() === 'EDF')
      if (edf) {
        setFilterProvider(edf.id)
      } else {
        setFilterProvider(sortedProviders[0].id)
      }
    }
  }, [sortedProviders, filterProvider])

  // Reset le filtre de type d'offre et les propositions de puissances quand on change de fournisseur
  useEffect(() => {
    if (!filterProvider || offersArray.length === 0) {
      setFilterOfferType('all')
      setPowersToRemove([])
      setNewPowersData([])
      return
    }
    const providerOffers = offersArray.filter(o => o.provider_id === filterProvider)
    const types = [...new Set(providerOffers.map(o => o.offer_type))]
    const typeOrder = ['BASE', 'HC_HP', 'TEMPO', 'EJP', 'ZEN_FLEX', 'ZEN_WEEK_END', 'ZEN_WEEK_END_HP_HC']
    const sortedTypes = types.sort((a, b) => {
      const indexA = typeOrder.indexOf(a)
      const indexB = typeOrder.indexOf(b)
      if (indexA === -1 && indexB === -1) return a.localeCompare(b)
      if (indexA === -1) return 1
      if (indexB === -1) return -1
      return indexA - indexB
    })
    if (sortedTypes.length > 0) {
      setFilterOfferType(sortedTypes[0])
    } else {
      setFilterOfferType('all')
    }
    // Reset les propositions de puissances
    setPowersToRemove([])
    setNewPowersData([])
  }, [filterProvider, offersArray])

  // Reset les propositions de puissances quand on change de type d'offre
  useEffect(() => {
    setPowersToRemove([])
    setNewPowersData([])
  }, [filterOfferType])


  // Helper pour vérifier si une offre a été modifiée
  const isOfferModified = (offer: EnergyOffer): boolean => {
    const edited = editedOffers[offer.id]
    if (!edited) return false
    return Object.entries(edited).some(([key, value]) => {
      const originalValue = (offer as unknown as Record<string, unknown>)[key]
      return String(originalValue ?? '') !== value
    })
  }

  // Helper pour mettre à jour un champ
  const updateField = (offerId: string, fieldKey: string, value: string) => {
    setEditedOffers(prev => ({
      ...prev,
      [offerId]: {
        ...prev[offerId],
        [fieldKey]: value
      }
    }))
  }

  // Helper pour formater la valeur
  const formatValue = (value: string | number | undefined): string => {
    if (value === undefined || value === null || value === '') return ''
    const num = typeof value === 'string' ? parseFloat(value) : value
    if (isNaN(num)) return ''
    return num.toString()
  }

  // Helper pour obtenir la couleur du label
  const getLabelColor = (label: string) => {
    if (label === 'HC') return 'text-blue-600 dark:text-blue-400'
    if (label === 'HP') return 'text-red-600 dark:text-red-400'
    return 'text-gray-600 dark:text-gray-400'
  }

  // Render un champ (éditable en mode édition, lecture seule sinon)
  const renderEditableField = (label: string, fieldKey: string, unit: string, offer: EnergyOffer) => {
    const editedValue = editedOffers[offer.id]?.[fieldKey]
    const originalValue = (offer as unknown as Record<string, unknown>)[fieldKey]
    const displayValue = editedValue !== undefined ? editedValue : formatValue(originalValue as string | number | undefined)
    const isModified = editedValue !== undefined && editedValue !== String(originalValue ?? '')

    // Mode lecture : affichage simple
    if (!isEditMode) {
      return (
        <div key={`${offer.id}-${fieldKey}`} className="flex items-center gap-2 w-[160px]">
          <span className={`text-sm font-semibold w-10 shrink-0 text-right ${getLabelColor(label)}`}>{label}</span>
          <span className="text-base font-bold text-gray-900 dark:text-white">
            {displayValue || '-'}
          </span>
          <span className="text-gray-500 dark:text-gray-400 text-xs shrink-0">{unit}</span>
        </div>
      )
    }

    // Mode édition : champ input
    return (
      <div key={`${offer.id}-${fieldKey}`} className="flex items-center gap-2 w-[200px]">
        <span className={`text-sm font-semibold w-10 shrink-0 text-right ${getLabelColor(label)}`}>{label}</span>
        <input
          type="number"
          step="0.0001"
          value={displayValue}
          onChange={(e) => updateField(offer.id, fieldKey, e.target.value)}
          className={`w-28 px-3 py-2 text-base font-bold border-2 rounded-lg bg-white dark:bg-gray-800 focus:ring-2 focus:ring-primary-500 focus:outline-none ${
            isModified
              ? 'border-amber-400 dark:border-amber-600 bg-amber-50 dark:bg-amber-900/20'
              : 'border-gray-300 dark:border-gray-600'
          }`}
        />
        <span className="text-gray-500 dark:text-gray-400 text-sm w-12 shrink-0">{unit}</span>
      </div>
    )
  }

  // Helper pour extraire et nettoyer le nom de l'offre
  const getCleanOfferName = (offerName: string): string => {
    let name = offerName.replace(/\s*\d+\s*kVA/gi, '')
    name = name.replace(/\s*-?\s*(BASE|HC[_\s]?HP|TEMPO|EJP)/gi, '')
    name = name.replace(/\s*-\s*-\s*/g, ' - ').replace(/\s+/g, ' ').trim()
    name = name.replace(/\s*-\s*$/, '').trim()
    return name || offerName
  }

  // Helper pour extraire la puissance
  const getPower = (offerName: string): string | null => {
    const match = offerName.match(/(\d+)\s*kVA/i)
    return match ? `${match[1]} kVA` : null
  }

  // Helper pour soumettre toutes les modifications
  const submitAllModifications = async () => {
    const currentProvider = sortedProviders.find(p => p.id === filterProvider)
    if (!currentProvider) return

    const providerOffers = offersArray.filter((offer) =>
      offer.provider_id === currentProvider.id && offer.offer_type === filterOfferType
    )

    // Récupérer le nom de base des offres existantes (sans la puissance)
    const existingBaseOfferName = providerOffers.length > 0
      ? getCleanOfferName(providerOffers[0].name)
      : `${currentProvider.name} - ${filterOfferType}`

    const modifiedOffers = providerOffers.filter(offer => isOfferModified(offer))
    const hasModifications = modifiedOffers.length > 0 || newPowersData.length > 0 || powersToRemove.length > 0

    if (!hasModifications) return

    setSubmittingOffers(true)
    let successCount = 0
    let errorCount = 0

    // Helper pour parser les valeurs numériques en évitant NaN
    const parsePrice = (editedValue: string | undefined, originalValue: number | undefined): number | undefined => {
      if (editedValue !== undefined && editedValue !== '') {
        const parsed = parseFloat(editedValue)
        return isNaN(parsed) ? originalValue : parsed
      }
      return originalValue
    }

    // Soumettre les modifications de tarifs existants
    for (const offer of modifiedOffers) {
      try {
        const edited = editedOffers[offer.id] || {}
        // Extraire la puissance de l'offre depuis son nom (ex: "Tarif Bleu - 6 kVA")
        const powerMatch = offer.name.match(/(\d+)\s*kVA/i)
        const powerKva = powerMatch ? parseInt(powerMatch[1]) : offer.power_kva || 6

        const contributionData: ContributionData = {
          contribution_type: 'UPDATE_OFFER',
          existing_provider_id: offer.provider_id,
          existing_offer_id: offer.id,
          provider_name: currentProvider.name,
          offer_name: offer.name,
          offer_type: offer.offer_type,
          power_kva: powerKva,
          pricing_data: {
            subscription_price: parsePrice(edited.subscription_price, offer.subscription_price),
            base_price: parsePrice(edited.base_price, offer.base_price),
            hc_price: parsePrice(edited.hc_price, offer.hc_price),
            hp_price: parsePrice(edited.hp_price, offer.hp_price),
            base_price_weekend: parsePrice(edited.base_price_weekend, offer.base_price_weekend),
            hc_price_weekend: parsePrice(edited.hc_price_weekend, offer.hc_price_weekend),
            hp_price_weekend: parsePrice(edited.hp_price_weekend, offer.hp_price_weekend),
            tempo_blue_hc: parsePrice(edited.tempo_blue_hc, offer.tempo_blue_hc),
            tempo_blue_hp: parsePrice(edited.tempo_blue_hp, offer.tempo_blue_hp),
            tempo_white_hc: parsePrice(edited.tempo_white_hc, offer.tempo_white_hc),
            tempo_white_hp: parsePrice(edited.tempo_white_hp, offer.tempo_white_hp),
            tempo_red_hc: parsePrice(edited.tempo_red_hc, offer.tempo_red_hc),
            tempo_red_hp: parsePrice(edited.tempo_red_hp, offer.tempo_red_hp),
            ejp_normal: parsePrice(edited.ejp_normal, offer.ejp_normal),
            ejp_peak: parsePrice(edited.ejp_peak, offer.ejp_peak),
            hc_price_winter: parsePrice(edited.hc_price_winter, offer.hc_price_winter),
            hp_price_winter: parsePrice(edited.hp_price_winter, offer.hp_price_winter),
            hc_price_summer: parsePrice(edited.hc_price_summer, offer.hc_price_summer),
            hp_price_summer: parsePrice(edited.hp_price_summer, offer.hp_price_summer),
          },
          price_sheet_url: priceSheetUrl,
          valid_from: offer.valid_from || new Date().toISOString().split('T')[0],
        }
        const response = await energyApi.submitContribution(contributionData)
        if (response.success) {
          successCount++
        } else {
          errorCount++
        }
      } catch {
        errorCount++
      }
    }

    // Soumettre les demandes de suppression de puissances (utilise UPDATE_OFFER avec description)
    for (const power of powersToRemove) {
      try {
        const contributionData: ContributionData = {
          contribution_type: 'UPDATE_OFFER',
          existing_provider_id: currentProvider.id,
          provider_name: currentProvider.name,
          offer_name: `[SUPPRESSION] ${currentProvider.name} - ${filterOfferType} - ${power} kVA`,
          offer_type: filterOfferType,
          description: `Demande de suppression de la puissance ${power} kVA pour ${currentProvider.name} (${filterOfferType})`,
          power_kva: power,
          price_sheet_url: priceSheetUrl,
          valid_from: new Date().toISOString().split('T')[0],
        }
        const response = await energyApi.submitContribution(contributionData)
        if (response.success) {
          successCount++
        } else {
          errorCount++
        }
      } catch {
        errorCount++
      }
    }

    // Soumettre les demandes d'ajout de puissances (utilise NEW_OFFER)
    for (const newPower of newPowersData) {
      try {
        const contributionData: ContributionData = {
          contribution_type: 'NEW_OFFER',
          existing_provider_id: currentProvider.id,
          provider_name: currentProvider.name,
          offer_name: `${existingBaseOfferName} - ${newPower.power} kVA`,
          offer_type: filterOfferType,
          description: `Ajout de la puissance ${newPower.power} kVA pour ${currentProvider.name} (${filterOfferType})`,
          power_kva: newPower.power,
          pricing_data: {
            subscription_price: parsePrice(newPower.fields.subscription_price, undefined),
            base_price: parsePrice(newPower.fields.base_price, undefined),
            hc_price: parsePrice(newPower.fields.hc_price, undefined),
            hp_price: parsePrice(newPower.fields.hp_price, undefined),
          },
          price_sheet_url: priceSheetUrl,
          valid_from: new Date().toISOString().split('T')[0],
        }
        const response = await energyApi.submitContribution(contributionData)
        if (response.success) {
          successCount++
        } else {
          errorCount++
        }
      } catch {
        errorCount++
      }
    }

    if (successCount > 0) {
      toast.success(`${successCount} contribution(s) soumise(s) avec succès !`)
      setEditedOffers({})
      setPriceSheetUrl('')
      setPowersToRemove([])
      setNewPowersData([])
      queryClient.invalidateQueries({ queryKey: ['my-contributions'] })
    }
    if (errorCount > 0) {
      toast.error(`${errorCount} erreur(s) lors de l'envoi`)
    }
    setSubmittingOffers(false)
  }

  // Labels pour les champs
  const fieldLabels: Record<string, string> = {
    subscription_price: 'Abonnement',
    base_price: 'Prix Base',
    hc_price: 'HC',
    hp_price: 'HP',
    tempo_blue_hc: 'Bleu HC',
    tempo_blue_hp: 'Bleu HP',
    tempo_white_hc: 'Blanc HC',
    tempo_white_hp: 'Blanc HP',
    tempo_red_hc: 'Rouge HC',
    tempo_red_hp: 'Rouge HP',
  }

  // Get provider offers filtered and sorted by power
  const providerOffers = offersArray
    .filter((offer) =>
      offer.provider_id === filterProvider && offer.offer_type === filterOfferType
    )
    .sort((a, b) => {
      const powerA = a.power_kva || parseInt(a.name.match(/(\d+)\s*kVA/i)?.[1] || '0')
      const powerB = b.power_kva || parseInt(b.name.match(/(\d+)\s*kVA/i)?.[1] || '0')
      return powerA - powerB
    })

  const modifiedOffers = providerOffers.filter(offer => isOfferModified(offer))

  // Calculer les puissances existantes pour ce fournisseur/type
  const existingPowers = useMemo(() => {
    return providerOffers.map(offer => {
      const powerMatch = offer.name.match(/(\d+)\s*kVA/i)
      return powerMatch ? parseInt(powerMatch[1]) : (offer.power_kva || 0)
    }).filter(p => p > 0)
  }, [providerOffers])

  // Vérifier si une puissance est déjà utilisée (existante ou dans les nouvelles puissances ajoutées)
  const isPowerAlreadyUsed = (power: number, currentIndex?: number): boolean => {
    // Vérifier dans les offres existantes (sauf celles marquées pour suppression)
    if (existingPowers.includes(power) && !powersToRemove.includes(power)) {
      return true
    }
    // Vérifier dans les nouvelles puissances ajoutées (sauf l'index courant)
    return newPowersData.some((p, i) => p.power === power && i !== currentIndex)
  }

  // Vérifier s'il y a des doublons dans les nouvelles puissances
  const hasDuplicatePowers = useMemo(() => {
    return newPowersData.some((newPower, index) => isPowerAlreadyUsed(newPower.power, index))
  }, [newPowersData, existingPowers, powersToRemove])

  // Vérifier si une nouvelle puissance a tous les champs obligatoires remplis
  const isNewPowerComplete = (newPower: { power: number; fields: Record<string, string> }): boolean => {
    // Puissance doit être > 0
    if (!newPower.power || newPower.power <= 0) return false
    // Abonnement obligatoire
    if (!newPower.fields.subscription_price || newPower.fields.subscription_price === '') return false
    // Prix kWh obligatoire selon le type d'offre
    if (filterOfferType === 'BASE') {
      if (!newPower.fields.base_price || newPower.fields.base_price === '') return false
    } else if (filterOfferType === 'HC_HP') {
      if (!newPower.fields.hc_price || newPower.fields.hc_price === '') return false
      if (!newPower.fields.hp_price || newPower.fields.hp_price === '') return false
    }
    // Pour les autres types (TEMPO, EJP, etc.), seul l'abonnement est requis
    return true
  }

  // Vérifier si toutes les nouvelles puissances sont complètes
  const hasIncompletePowers = useMemo(() => {
    return newPowersData.length > 0 && newPowersData.some(p => !isNewPowerComplete(p))
  }, [newPowersData, filterOfferType])

  // Afficher l'overlay de chargement pendant la soumission
  if (submittingOffers) {
    return (
      <LoadingOverlay
        message="Envoi des contributions"
        subMessage="Veuillez patienter pendant l'envoi de vos modifications..."
      />
    )
  }

  return (
    <div className="card">
      {/* Header avec bouton mode */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Package className="text-primary-600 dark:text-primary-400" size={20} />
            Offres disponibles
          </h2>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            {(() => {
              if (offersArray.length === 0) return '0 offre'
              const filteredCount = offersArray.filter((offer) => {
                if (filterProvider && offer.provider_id !== filterProvider) return false
                if (filterOfferType !== 'all' && offer.offer_type !== filterOfferType) return false
                return true
              }).length

              const selectedProvider = sortedProviders.find(p => p.id === filterProvider)
              const typeLabels: Record<string, string> = {
                'BASE': 'Base',
                'HC_HP': 'HC/HP',
                'TEMPO': 'Tempo',
                'EJP': 'EJP',
                'ZEN_FLEX': 'Zen Flex',
                'ZEN_WEEK_END': 'Zen Week-end',
                'ZEN_WEEK_END_HP_HC': 'Zen Week-end HC/HP',
              }
              const typeLabel = filterOfferType !== 'all' ? typeLabels[filterOfferType] || filterOfferType : ''
              return `${filteredCount} offre(s) ${selectedProvider ? `pour ${selectedProvider.name}` : ''}${typeLabel ? ` - ${typeLabel}` : ''}`
            })()}
          </p>
        </div>
        {/* Bouton mode lecture/édition */}
        <button
          onClick={() => {
            if (isEditMode) {
              // Quitter le mode édition : reset des modifications
              setEditedOffers({})
              setPriceSheetUrl('')
              setPowersToRemove([])
              setNewPowersData([])
            }
            setIsEditMode(!isEditMode)
          }}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
            isEditMode
              ? 'bg-primary-600 text-white hover:bg-primary-700'
              : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
          }`}
        >
          {isEditMode ? (
            <>
              <Eye size={16} />
              Mode lecture
            </>
          ) : (
            <>
              <Pencil size={16} />
              Proposer des modifications
            </>
          )}
        </button>
      </div>

      {/* Encadré d'information en mode édition */}
      {isEditMode && (
        <div className="mb-6 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
          <div className="flex items-start gap-3">
            <Info size={20} className="text-blue-600 dark:text-blue-400 shrink-0 mt-0.5" />
            <div className="text-sm text-blue-800 dark:text-blue-300">
              <p className="font-medium mb-2">Mode édition activé</p>
              <ul className="list-disc list-inside space-y-1">
                <li>Sélectionnez <strong>un fournisseur</strong> et <strong>un type d'offre</strong> pour proposer des modifications.</li>
                <li>Chaque soumission concerne <strong>un seul fournisseur</strong> et <strong>un seul type d'offre</strong> à la fois.</li>
                <li>Vos modifications seront <strong>vérifiées et validées</strong> par un administrateur ou modérateur avant publication.</li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="mb-6 space-y-4">
        {/* Fournisseurs - Boutons */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Sélectionner un fournisseur</label>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
            {sortedProviders.map((provider) => {
              const isSelected = filterProvider === provider.id
              const providerOffersCount = offersArray.filter(o => o.provider_id === provider.id).length
              return (
                <button
                  key={provider.id}
                  onClick={() => setFilterProvider(provider.id)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2 w-full ${
                    isSelected
                      ? 'bg-primary-600 text-white shadow-md'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                  }`}
                >
                  {provider.name}
                  <span className={`px-1.5 py-0.5 text-xs rounded-full ${
                    isSelected
                      ? 'bg-primary-500 text-white'
                      : 'bg-gray-200 dark:bg-gray-600 text-gray-600 dark:text-gray-400'
                  }`}>
                    {providerOffersCount}
                  </span>
                </button>
              )
            })}
          </div>
        </div>

        {/* Type d'offre - Boutons dynamiques */}
        {availableOfferTypes.length > 0 && (
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Type d'offre</label>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
              {availableOfferTypes.map((type) => {
                const isSelected = filterOfferType === type
                const typeCount = offersArray.filter(o => o.provider_id === filterProvider && o.offer_type === type).length
                const typeLabels: Record<string, string> = {
                  'BASE': 'Base',
                  'HC_HP': 'HC/HP',
                  'TEMPO': 'Tempo',
                  'EJP': 'EJP',
                  'ZEN_FLEX': 'Zen Flex',
                  'ZEN_WEEK_END': 'Zen Week-end',
                  'ZEN_WEEK_END_HP_HC': 'Zen Week-end HC/HP',
                }
                return (
                  <button
                    key={type}
                    onClick={() => setFilterOfferType(type)}
                    className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-1.5 w-full ${
                      isSelected
                        ? 'bg-primary-600 text-white shadow-md'
                        : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                    }`}
                  >
                    {typeLabels[type] || type}
                    <span className={`px-1.5 py-0.5 text-xs rounded-full ${
                      isSelected
                        ? 'bg-primary-500 text-white'
                        : 'bg-gray-200 dark:bg-gray-600 text-gray-600 dark:text-gray-400'
                    }`}>
                      {typeCount}
                    </span>
                  </button>
                )
              })}
            </div>
          </div>
        )}

      </div>

      {/* Message si pas de fournisseur ou type sélectionné */}
      {(!filterProvider || filterOfferType === 'all') ? (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-900 rounded-lg border border-dashed border-gray-300 dark:border-gray-700">
          <p className="text-lg mb-2">
            {!filterProvider
              ? 'Sélectionnez un fournisseur pour voir les offres disponibles'
              : 'Sélectionnez un type d\'offre pour afficher les tarifs'}
          </p>
          <p className="text-sm">
            Vous pourrez ensuite modifier les tarifs et soumettre vos contributions.
          </p>
        </div>
      ) : offersArray.length > 0 && providerOffers.length === 0 ? (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          Aucune offre ne correspond aux filtres sélectionnés.
        </div>
      ) : providerOffers.length > 0 ? (
        <div className="space-y-6">
          {/* Liste des offres éditables */}
          <div className="space-y-2">
            {providerOffers.map((offer) => {
              const modified = isOfferModified(offer)
              const cleanName = getCleanOfferName(offer.name)
              const power = getPower(offer.name)
              const powerNum = power ? parseInt(power) : null
              const isMarkedForRemoval = powerNum !== null && powersToRemove.includes(powerNum)

              return (
                <div
                  key={offer.id}
                  className={`bg-gray-50 dark:bg-gray-900 rounded-lg p-3 border transition-all ${
                    isMarkedForRemoval
                      ? 'border-red-400 dark:border-red-600 bg-red-50 dark:bg-red-900/20 opacity-60'
                      : modified
                        ? 'border-amber-400 dark:border-amber-600'
                        : 'border-gray-200 dark:border-gray-700'
                  }`}
                >
                  <div className="flex flex-wrap items-center gap-4">
                    {/* Nom de l'offre */}
                    <div className="w-64 shrink-0">
                      <div className="flex items-center gap-2">
                        <h4 className={`font-medium text-sm truncate ${isMarkedForRemoval ? 'text-red-600 dark:text-red-400 line-through' : 'text-gray-900 dark:text-white'}`} title={cleanName}>{cleanName}</h4>
                        {isMarkedForRemoval && (
                          <span className="text-xs text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-900/30 px-1.5 py-0.5 rounded shrink-0">À supprimer</span>
                        )}
                        {modified && !isMarkedForRemoval && (
                          <span className="text-xs text-amber-600 dark:text-amber-400 bg-amber-100 dark:bg-amber-900/30 px-1.5 py-0.5 rounded shrink-0">Modifié</span>
                        )}
                      </div>
                    </div>

                    {/* Puissance */}
                    <div className="w-16 text-center shrink-0">
                      <span className={`text-xs font-medium px-2 py-1 rounded ${isMarkedForRemoval ? 'text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-900/30' : 'text-gray-700 dark:text-gray-300 bg-gray-200 dark:bg-gray-700'}`}>
                        {power || '-'}
                      </span>
                    </div>

                    {/* Abonnement */}
                    <div className="shrink-0">
                      {renderEditableField('Abo.', 'subscription_price', '€/mois', offer)}
                    </div>

                    {/* Tarifs selon le type */}
                    <div className="flex flex-wrap gap-x-3 gap-y-1 justify-end pr-4 flex-1">
                      {offer.offer_type === 'BASE' && (
                        renderEditableField('Base', 'base_price', '€/kWh', offer)
                      )}

                      {offer.offer_type === 'BASE_WEEKEND' && (
                        <>
                          {renderEditableField('Base', 'base_price', '€/kWh', offer)}
                          <div className="w-full flex flex-wrap gap-x-3 gap-y-1 items-center justify-end">
                            <span className="text-sm font-semibold text-green-600 dark:text-green-400 w-14">Week-end</span>
                            {renderEditableField('Base', 'base_price_weekend', '€', offer)}
                          </div>
                        </>
                      )}

                      {offer.offer_type === 'HC_HP' && (
                        <>
                          {renderEditableField('HC', 'hc_price', '€/kWh', offer)}
                          {renderEditableField('HP', 'hp_price', '€/kWh', offer)}
                        </>
                      )}

                      {(offer.offer_type === 'HC_WEEKEND' || offer.offer_type === 'HC_NUIT_WEEKEND') && (
                        <>
                          {renderEditableField('HC', 'hc_price', '€/kWh', offer)}
                          {renderEditableField('HP', 'hp_price', '€/kWh', offer)}
                          <div className="w-full flex flex-wrap gap-x-3 gap-y-1 items-center justify-end">
                            <span className="text-sm font-semibold text-green-600 dark:text-green-400 w-14">Week-end</span>
                            {renderEditableField('HC', 'hc_price_weekend', '€', offer)}
                            {renderEditableField('HP', 'hp_price_weekend', '€', offer)}
                          </div>
                        </>
                      )}

                      {offer.offer_type === 'TEMPO' && (
                        <>
                          <div className="w-full flex flex-wrap gap-x-3 gap-y-1 items-center justify-end">
                            <span className="text-sm font-semibold text-blue-600 dark:text-blue-400 w-14">Bleus</span>
                            {renderEditableField('HC', 'tempo_blue_hc', '€', offer)}
                            {renderEditableField('HP', 'tempo_blue_hp', '€', offer)}
                          </div>
                          <div className="w-full flex flex-wrap gap-x-3 gap-y-1 items-center justify-end">
                            <span className="text-sm font-semibold text-gray-600 dark:text-gray-300 w-14">Blancs</span>
                            {renderEditableField('HC', 'tempo_white_hc', '€', offer)}
                            {renderEditableField('HP', 'tempo_white_hp', '€', offer)}
                          </div>
                          <div className="w-full flex flex-wrap gap-x-3 gap-y-1 items-center justify-end">
                            <span className="text-sm font-semibold text-red-600 dark:text-red-400 w-14">Rouges</span>
                            {renderEditableField('HC', 'tempo_red_hc', '€', offer)}
                            {renderEditableField('HP', 'tempo_red_hp', '€', offer)}
                          </div>
                        </>
                      )}

                      {offer.offer_type === 'ZEN_FLEX' && (
                        <>
                          <div className="w-full flex flex-wrap gap-x-3 gap-y-1 items-center justify-end">
                            <span className="text-sm font-semibold text-green-600 dark:text-green-400 w-20">Éco</span>
                            {renderEditableField('HC', 'hc_price_winter', '€', offer)}
                            {renderEditableField('HP', 'hp_price_winter', '€', offer)}
                          </div>
                          <div className="w-full flex flex-wrap gap-x-3 gap-y-1 items-center justify-end">
                            <span className="text-sm font-semibold text-red-600 dark:text-red-400 w-20">Sobriété</span>
                            {renderEditableField('HC', 'hc_price_summer', '€', offer)}
                            {renderEditableField('HP', 'hp_price_summer', '€', offer)}
                          </div>
                        </>
                      )}

                      {offer.offer_type === 'SEASONAL' && (
                        <>
                          <div className="w-full flex flex-wrap gap-x-3 gap-y-1 items-center justify-end">
                            <span className="text-sm font-semibold text-blue-600 dark:text-blue-400 w-14">Hiver</span>
                            {renderEditableField('HC', 'hc_price_winter', '€', offer)}
                            {renderEditableField('HP', 'hp_price_winter', '€', offer)}
                          </div>
                          <div className="w-full flex flex-wrap gap-x-3 gap-y-1 items-center justify-end">
                            <span className="text-sm font-semibold text-orange-600 dark:text-orange-400 w-14">Été</span>
                            {renderEditableField('HC', 'hc_price_summer', '€', offer)}
                            {renderEditableField('HP', 'hp_price_summer', '€', offer)}
                          </div>
                        </>
                      )}

                      {(offer.offer_type === 'ZEN_WEEK_END' || offer.offer_type === 'ZEN_WEEK_END_HP_HC') && (
                        <>
                          {renderEditableField('HC', 'hc_price', '€/kWh', offer)}
                          {renderEditableField('HP', 'hp_price', '€/kWh', offer)}
                          <div className="w-full flex flex-wrap gap-x-3 gap-y-1 items-center justify-end">
                            <span className="text-sm font-semibold text-green-600 dark:text-green-400 w-14">Week-end</span>
                            {renderEditableField('HC', 'hc_price_weekend', '€', offer)}
                            {renderEditableField('HP', 'hp_price_weekend', '€', offer)}
                          </div>
                        </>
                      )}

                      {offer.offer_type === 'EJP' && (
                        <>
                          {renderEditableField('Normal', 'ejp_normal', '€/kWh', offer)}
                          {renderEditableField('Pointe', 'ejp_peak', '€/kWh', offer)}
                        </>
                      )}
                    </div>

                    {/* Bouton supprimer la puissance (uniquement en mode édition) */}
                    {isEditMode && powerNum !== null && (
                      <div className="shrink-0">
                        {isMarkedForRemoval ? (
                          <button
                            onClick={() => setPowersToRemove(prev => prev.filter(p => p !== powerNum))}
                            className="p-1.5 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
                            title="Annuler la suppression"
                          >
                            <Undo2 size={16} />
                          </button>
                        ) : (
                          <button
                            onClick={() => {
                              if (!powersToRemove.includes(powerNum)) {
                                setPowersToRemove(prev => [...prev, powerNum])
                              }
                            }}
                            className="p-1.5 text-red-500 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
                            title="Proposer la suppression de cette puissance"
                          >
                            <Trash2 size={16} />
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>

          {/* Lignes des nouvelles puissances ajoutées (uniquement en mode édition) */}
          {isEditMode && newPowersData.map((newPower, index) => {
            const isDuplicate = isPowerAlreadyUsed(newPower.power, index)
            const isIncomplete = !isNewPowerComplete(newPower)
            const hasError = isDuplicate || isIncomplete
            return (
            <div
              key={`new-power-${index}`}
              className={`rounded-lg p-3 border transition-all ${
                isDuplicate
                  ? 'bg-red-50 dark:bg-red-900/20 border-red-400 dark:border-red-600'
                  : isIncomplete
                    ? 'bg-amber-50 dark:bg-amber-900/20 border-amber-400 dark:border-amber-600'
                    : 'bg-green-50 dark:bg-green-900/20 border-green-400 dark:border-green-600'
              }`}
            >
              <div className="flex flex-wrap items-center gap-4">
                {/* Nom de l'offre */}
                <div className="w-64 shrink-0">
                  <div className="flex items-center gap-2">
                    <Plus size={16} className={hasError ? (isDuplicate ? 'text-red-600 dark:text-red-400' : 'text-amber-600 dark:text-amber-400') : 'text-green-600 dark:text-green-400'} />
                    <h4 className={`font-medium text-sm ${hasError ? (isDuplicate ? 'text-red-700 dark:text-red-300' : 'text-amber-700 dark:text-amber-300') : 'text-green-700 dark:text-green-300'}`}>Nouvelle puissance</h4>
                    {isDuplicate ? (
                      <span className="text-xs text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-900/30 px-1.5 py-0.5 rounded shrink-0">Existe déjà</span>
                    ) : isIncomplete ? (
                      <span className="text-xs text-amber-600 dark:text-amber-400 bg-amber-100 dark:bg-amber-900/30 px-1.5 py-0.5 rounded shrink-0">Incomplet</span>
                    ) : (
                      <span className="text-xs text-green-600 dark:text-green-400 bg-green-100 dark:bg-green-900/30 px-1.5 py-0.5 rounded shrink-0">Nouveau</span>
                    )}
                  </div>
                </div>

                {/* Puissance */}
                <div className="w-16 text-center shrink-0">
                  <input
                    type="number"
                    min="1"
                    max="100"
                    value={newPower.power}
                    onChange={(e) => {
                      const power = e.target.value ? parseInt(e.target.value) : 0
                      setNewPowersData(prev => prev.map((p, i) => i === index ? { ...p, power } : p))
                    }}
                    className={`w-full px-2 py-1 text-xs font-medium text-center border rounded bg-white dark:bg-gray-800 focus:ring-2 focus:outline-none ${
                      isDuplicate || !newPower.power || newPower.power <= 0
                        ? 'border-red-400 dark:border-red-600 focus:ring-red-500'
                        : 'border-green-300 dark:border-green-600 focus:ring-green-500'
                    }`}
                  />
                </div>

                {/* Abonnement (obligatoire) */}
                <div className="shrink-0">
                  <div className="flex items-center gap-2 w-[200px]">
                    <span className="text-sm font-semibold w-10 shrink-0 text-right text-gray-600 dark:text-gray-400">Abo.<span className="text-red-500">*</span></span>
                    <input
                      type="number"
                      step="0.01"
                      value={newPower.fields.subscription_price ?? ''}
                      onChange={(e) => setNewPowersData(prev => prev.map((p, i) =>
                        i === index ? { ...p, fields: { ...p.fields, subscription_price: e.target.value } } : p
                      ))}
                      placeholder="0.00"
                      className={`w-28 px-3 py-2 text-base font-bold border-2 rounded-lg bg-white dark:bg-gray-800 focus:ring-2 focus:outline-none ${
                        !newPower.fields.subscription_price || newPower.fields.subscription_price === ''
                          ? 'border-amber-400 dark:border-amber-600 focus:ring-amber-500'
                          : 'border-green-300 dark:border-green-600 focus:ring-green-500'
                      }`}
                    />
                    <span className="text-gray-500 dark:text-gray-400 text-sm w-12 shrink-0">€/mois</span>
                  </div>
                </div>

                {/* Tarifs selon le type d'offre */}
                <div className="flex flex-wrap gap-x-3 gap-y-1 justify-end pr-4 flex-1">
                  {filterOfferType === 'BASE' && (
                    <div className="flex items-center gap-2 w-[200px]">
                      <span className="text-sm font-semibold w-10 shrink-0 text-right text-gray-600 dark:text-gray-400">Base<span className="text-red-500">*</span></span>
                      <input
                        type="number"
                        step="0.0001"
                        value={newPower.fields.base_price ?? ''}
                        onChange={(e) => setNewPowersData(prev => prev.map((p, i) =>
                          i === index ? { ...p, fields: { ...p.fields, base_price: e.target.value } } : p
                        ))}
                        placeholder="0.0000"
                        className={`w-28 px-3 py-2 text-base font-bold border-2 rounded-lg bg-white dark:bg-gray-800 focus:ring-2 focus:outline-none ${
                          !newPower.fields.base_price || newPower.fields.base_price === ''
                            ? 'border-amber-400 dark:border-amber-600 focus:ring-amber-500'
                            : 'border-green-300 dark:border-green-600 focus:ring-green-500'
                        }`}
                      />
                      <span className="text-gray-500 dark:text-gray-400 text-sm w-12 shrink-0">€/kWh</span>
                    </div>
                  )}

                  {filterOfferType === 'HC_HP' && (
                    <>
                      <div className="flex items-center gap-2 w-[200px]">
                        <span className="text-sm font-semibold w-10 shrink-0 text-right text-blue-600 dark:text-blue-400">HC<span className="text-red-500">*</span></span>
                        <input
                          type="number"
                          step="0.0001"
                          value={newPower.fields.hc_price ?? ''}
                          onChange={(e) => setNewPowersData(prev => prev.map((p, i) =>
                            i === index ? { ...p, fields: { ...p.fields, hc_price: e.target.value } } : p
                          ))}
                          placeholder="0.0000"
                          className={`w-28 px-3 py-2 text-base font-bold border-2 rounded-lg bg-white dark:bg-gray-800 focus:ring-2 focus:outline-none ${
                            !newPower.fields.hc_price || newPower.fields.hc_price === ''
                              ? 'border-amber-400 dark:border-amber-600 focus:ring-amber-500'
                              : 'border-green-300 dark:border-green-600 focus:ring-green-500'
                          }`}
                        />
                        <span className="text-gray-500 dark:text-gray-400 text-sm w-12 shrink-0">€/kWh</span>
                      </div>
                      <div className="flex items-center gap-2 w-[200px]">
                        <span className="text-sm font-semibold w-10 shrink-0 text-right text-red-600 dark:text-red-400">HP<span className="text-red-500">*</span></span>
                        <input
                          type="number"
                          step="0.0001"
                          value={newPower.fields.hp_price ?? ''}
                          onChange={(e) => setNewPowersData(prev => prev.map((p, i) =>
                            i === index ? { ...p, fields: { ...p.fields, hp_price: e.target.value } } : p
                          ))}
                          placeholder="0.0000"
                          className={`w-28 px-3 py-2 text-base font-bold border-2 rounded-lg bg-white dark:bg-gray-800 focus:ring-2 focus:outline-none ${
                            !newPower.fields.hp_price || newPower.fields.hp_price === ''
                              ? 'border-amber-400 dark:border-amber-600 focus:ring-amber-500'
                              : 'border-green-300 dark:border-green-600 focus:ring-green-500'
                          }`}
                        />
                        <span className="text-gray-500 dark:text-gray-400 text-sm w-12 shrink-0">€/kWh</span>
                      </div>
                    </>
                  )}

                  {filterOfferType === 'TEMPO' && (
                    <div className="text-sm text-gray-500 dark:text-gray-400 italic">
                      Tarifs Tempo à renseigner après validation
                    </div>
                  )}

                  {(filterOfferType === 'ZEN_WEEK_END' || filterOfferType === 'ZEN_WEEK_END_HP_HC' || filterOfferType === 'ZEN_FLEX' || filterOfferType === 'SEASONAL' || filterOfferType === 'EJP') && (
                    <div className="text-sm text-gray-500 dark:text-gray-400 italic">
                      Tarifs spécifiques à renseigner après validation
                    </div>
                  )}
                </div>

                {/* Bouton supprimer */}
                <div className="shrink-0">
                  <button
                    onClick={() => setNewPowersData(prev => prev.filter((_, i) => i !== index))}
                    className="p-1.5 text-red-500 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
                    title="Supprimer cette puissance"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            </div>
          )})}


          {/* Bouton pour ajouter une nouvelle puissance (uniquement en mode édition) */}
          {isEditMode && (
            <button
              onClick={() => setNewPowersData(prev => [...prev, { power: 0, fields: {} }])}
              className="w-full bg-green-50 dark:bg-green-900/20 rounded-lg p-3 border border-dashed border-green-300 dark:border-green-700 hover:border-green-400 dark:hover:border-green-600 hover:bg-green-100 dark:hover:bg-green-900/30 transition-all flex items-center justify-center gap-2"
            >
              <Plus size={18} className="text-green-600 dark:text-green-400" />
              <span className="font-medium text-sm text-green-700 dark:text-green-300">Ajouter une puissance</span>
            </button>
          )}

          {/* Récapitulatif dynamique des modifications (uniquement en mode édition) */}
          {isEditMode && (modifiedOffers.length > 0 || newPowersData.length > 0 || powersToRemove.length > 0) && (
            <div ref={recapRef} className="mt-6">
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-6">
                <h4 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                  <Send size={18} className="text-primary-600 dark:text-primary-400" />
                  Récapitulatif des modifications
                  {modifiedOffers.length > 0 && (
                    <span className="text-sm font-normal text-gray-500">
                      ({modifiedOffers.length} offre{modifiedOffers.length > 1 ? 's' : ''})
                    </span>
                  )}
                </h4>
                <div className="mb-4">
                  <div className="space-y-4">
                    {/* Modifications de tarifs */}
                    {modifiedOffers.map(offer => {
                      const edited = editedOffers[offer.id] || {}
                      const changes = Object.entries(edited).filter(([key, value]) => {
                        const originalValue = (offer as unknown as Record<string, unknown>)[key]
                        const origNum = Number(originalValue)
                        const newNum = Number(value)
                        if (isNaN(origNum) && isNaN(newNum)) return false
                        if (isNaN(origNum) || isNaN(newNum)) return true
                        return Math.abs(origNum - newNum) > 0.00001
                      })
                      if (changes.length === 0) return null
                      return (
                        <div key={offer.id} className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                          <div className="font-semibold text-gray-900 dark:text-white mb-3 pb-2 border-b border-gray-200 dark:border-gray-700">
                            {offer.name}
                          </div>
                          <div className="space-y-2">
                            {changes.map(([key, value]) => {
                              const originalValue = (offer as unknown as Record<string, unknown>)[key]
                              const origNum = Number(originalValue)
                              const newNum = Number(value)
                              const isSubscription = key === 'subscription_price'
                              return (
                                <div key={key} className="flex items-center justify-between bg-white dark:bg-gray-800 rounded px-3 py-2">
                                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                                    {fieldLabels[key] || key}
                                  </span>
                                  <div className="flex items-center gap-3">
                                    <span className="text-sm text-red-500 line-through font-mono">
                                      {isNaN(origNum) ? '-' : origNum.toFixed(isSubscription ? 2 : 4)}
                                    </span>
                                    <span className="text-gray-400">→</span>
                                    <span className="text-sm text-green-600 dark:text-green-400 font-bold font-mono">
                                      {isNaN(newNum) ? '-' : newNum.toFixed(isSubscription ? 2 : 4)}
                                    </span>
                                    <span className="text-xs text-gray-500">
                                      {isSubscription ? '€/mois' : '€/kWh'}
                                    </span>
                                  </div>
                                </div>
                              )
                            })}
                          </div>
                        </div>
                      )
                    })}

                    {/* Modifications de puissances */}
                    {(newPowersData.length > 0 || powersToRemove.length > 0) && (
                      <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                        <div className="font-semibold text-gray-900 dark:text-white mb-3 pb-2 border-b border-gray-200 dark:border-gray-700 flex items-center gap-2">
                          Modifications de puissances
                          {sortedProviders.find(p => p.id === filterProvider) && (
                            <span className="text-sm font-normal text-gray-500">
                              ({sortedProviders.find(p => p.id === filterProvider)?.name} - {filterOfferType})
                            </span>
                          )}
                        </div>
                        <div className="space-y-2">
                          {powersToRemove.sort((a, b) => a - b).map(power => (
                            <div key={`remove-${power}`} className="flex items-center justify-between bg-red-50 dark:bg-red-900/20 rounded px-3 py-2 border border-red-200 dark:border-red-800">
                              <span className="text-sm font-medium text-red-700 dark:text-red-300 flex items-center gap-2">
                                <Trash2 size={14} />
                                Supprimer la puissance
                              </span>
                              <span className="text-sm font-bold text-red-600 dark:text-red-400">
                                {power} kVA
                              </span>
                            </div>
                          ))}
                          {newPowersData.map((newPower, index) => (
                            <div key={`add-${index}`} className="bg-green-50 dark:bg-green-900/20 rounded px-3 py-2 border border-green-200 dark:border-green-800">
                              <div className="flex items-center justify-between">
                                <span className="text-sm font-medium text-green-700 dark:text-green-300 flex items-center gap-2">
                                  <Plus size={14} />
                                  Ajouter la puissance
                                </span>
                                <span className="text-sm font-bold text-green-600 dark:text-green-400">
                                  {newPower.power} kVA
                                </span>
                              </div>
                              {/* Afficher les tarifs saisis */}
                              <div className="mt-2 pt-2 border-t border-green-200 dark:border-green-700 space-y-1">
                                {newPower.fields.subscription_price && (
                                  <div className="flex items-center justify-between text-xs">
                                    <span className="text-green-600 dark:text-green-400">Abonnement :</span>
                                    <span className="font-semibold text-green-700 dark:text-green-300">{newPower.fields.subscription_price} €/mois</span>
                                  </div>
                                )}
                                {newPower.fields.base_price && (
                                  <div className="flex items-center justify-between text-xs">
                                    <span className="text-green-600 dark:text-green-400">Base :</span>
                                    <span className="font-semibold text-green-700 dark:text-green-300">{newPower.fields.base_price} €/kWh</span>
                                  </div>
                                )}
                                {newPower.fields.hc_price && (
                                  <div className="flex items-center justify-between text-xs">
                                    <span className="text-blue-600 dark:text-blue-400">HC :</span>
                                    <span className="font-semibold text-blue-700 dark:text-blue-300">{newPower.fields.hc_price} €/kWh</span>
                                  </div>
                                )}
                                {newPower.fields.hp_price && (
                                  <div className="flex items-center justify-between text-xs">
                                    <span className="text-red-600 dark:text-red-400">HP :</span>
                                    <span className="font-semibold text-red-700 dark:text-red-300">{newPower.fields.hp_price} €/kWh</span>
                                  </div>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Champ lien vers la fiche tarifaire (optionnel pour admin/modérateur) */}
                <div className="mb-4 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
                  <label className="flex items-center gap-2 text-sm font-medium text-amber-800 dark:text-amber-300 mb-2">
                    <Link size={16} />
                    Lien vers la fiche tarifaire officielle
                    {!isPrivilegedUser && <span className="text-red-500">*</span>}
                    {isPrivilegedUser && <span className="text-gray-500 text-xs font-normal">(optionnel)</span>}
                  </label>
                  <input
                    type="url"
                    value={priceSheetUrl}
                    onChange={(e) => setPriceSheetUrl(e.target.value)}
                    placeholder="https://www.edf.fr/grille-tarifaire.pdf"
                    className={`w-full px-4 py-2 rounded-lg border ${
                      priceSheetUrl && !priceSheetUrl.startsWith('http')
                        ? 'border-red-400 dark:border-red-600'
                        : 'border-gray-300 dark:border-gray-600'
                    } bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:outline-none`}
                  />
                  {!priceSheetUrl && !isPrivilegedUser && (
                    <p className="mt-2 text-xs text-amber-700 dark:text-amber-400 flex items-center gap-1">
                      <AlertCircle size={12} />
                      Ce champ est obligatoire pour valider vos modifications
                    </p>
                  )}
                </div>

                {/* Message d'erreur si des puissances en doublon */}
                {hasDuplicatePowers && (
                  <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                    <p className="text-sm text-red-700 dark:text-red-300 flex items-center gap-2">
                      <AlertCircle size={16} />
                      Certaines puissances que vous souhaitez ajouter existent déjà. Veuillez corriger les doublons avant de soumettre.
                    </p>
                  </div>
                )}

                {/* Message d'erreur si des puissances incomplètes */}
                {hasIncompletePowers && !hasDuplicatePowers && (
                  <div className="mb-4 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
                    <p className="text-sm text-amber-700 dark:text-amber-300 flex items-center gap-2">
                      <AlertCircle size={16} />
                      Veuillez renseigner tous les champs obligatoires (abonnement et tarifs kWh) pour les nouvelles puissances.
                    </p>
                  </div>
                )}

                <div className="flex gap-3">
                  <button
                    onClick={() => {
                      setEditedOffers({})
                      setPriceSheetUrl('')
                      setPowersToRemove([])
                      setNewPowersData([])
                    }}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg transition-colors"
                  >
                    <X size={18} />
                    Annuler les modifications
                  </button>
                  <button
                    onClick={submitAllModifications}
                    disabled={submittingOffers || (!isPrivilegedUser && !priceSheetUrl) || (priceSheetUrl.length > 0 && !priceSheetUrl.startsWith('http')) || hasDuplicatePowers || hasIncompletePowers}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 disabled:bg-primary-400 disabled:cursor-not-allowed rounded-lg transition-colors"
                  >
                    <Send size={18} />
                    {submittingOffers ? 'Envoi en cours...' : 'Soumettre les contributions'}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      ) : null}
    </div>
  )
}
