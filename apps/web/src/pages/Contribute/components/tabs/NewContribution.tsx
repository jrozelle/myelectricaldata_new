import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, FileJson, X } from 'lucide-react'
import { energyApi, type EnergyProvider, type ContributionData } from '@/api/energy'
import { toast } from '@/stores/notificationStore'
import PowerVariantForm from '../forms/PowerVariantForm'
import { type PowerVariant } from '../../types'
import { formatPrice } from '../../utils'

interface NewContributionProps {
  editingContributionId: string | null
  setEditingContributionId: (id: string | null) => void
  formState: {
    contributionType: 'NEW_PROVIDER' | 'NEW_OFFER'
    providerName: string
    providerWebsite: string
    selectedProviderId: string
    offerName: string
    offerType: string
    description: string
    powerVariants: PowerVariant[]
    priceSheetUrl: string
    screenshotUrl: string
  }
  onFormStateChange: (key: string, value: unknown) => void
}

export default function NewContribution({ 
  editingContributionId, 
  setEditingContributionId,
  formState,
  onFormStateChange 
}: NewContributionProps) {
  const queryClient = useQueryClient()
  const [showJsonImport, setShowJsonImport] = useState(false)
  const [jsonImportData, setJsonImportData] = useState('')
  const [importProgress, setImportProgress] = useState<{current: number, total: number, errors: string[]} | null>(null)

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

  // Submit mutation (create new contribution)
  const submitMutation = useMutation({
    mutationFn: async (data: ContributionData) => {
      return await energyApi.submitContribution(data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-contributions'] })
      toast.success('Contribution soumise avec succès ! Les administrateurs vont la vérifier.')
      resetForm()
    },
    onError: (error: unknown) => {
      const errorMessage = (error as Error)?.message || 'Une erreur est survenue'
      toast.error(`Erreur: ${errorMessage}`)
    },
  })

  // Update mutation (edit existing contribution)
  const updateMutation = useMutation({
    mutationFn: async ({ contributionId, data }: { contributionId: string; data: ContributionData }) => {
      return await energyApi.updateContribution(contributionId, data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-contributions'] })
      toast.success('Contribution mise à jour avec succès !')
      resetForm()
      setEditingContributionId(null)
    },
    onError: (error: unknown) => {
      const errorMessage = (error as Error)?.message || 'Une erreur est survenue'
      toast.error(`Erreur: ${errorMessage}`)
    },
  })

  const resetForm = () => {
    onFormStateChange('offerName', '')
    onFormStateChange('offerType', 'BASE')
    onFormStateChange('description', '')
    onFormStateChange('powerVariants', [])
    onFormStateChange('priceSheetUrl', '')
    onFormStateChange('screenshotUrl', '')
    onFormStateChange('providerName', '')
    onFormStateChange('providerWebsite', '')
    onFormStateChange('selectedProviderId', '')
    setEditingContributionId(null)
  }

  const handleAddPowerVariant = (variant: PowerVariant) => {
    onFormStateChange('powerVariants', [...formState.powerVariants, variant])
  }

  const handleRemovePowerVariant = (index: number) => {
    onFormStateChange('powerVariants', formState.powerVariants.filter((_, i) => i !== index))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    // Validation : au moins une variante de puissance
    if (formState.powerVariants.length === 0) {
      toast.error('Veuillez ajouter au moins une variante de puissance')
      return
    }

    const contributionData: ContributionData = {
      contribution_type: formState.contributionType,
      offer_name: formState.offerName,
      offer_type: formState.offerType,
      description: formState.description || undefined,
      power_variants: formState.powerVariants,
      price_sheet_url: formState.priceSheetUrl,
      screenshot_url: formState.screenshotUrl || undefined,
      valid_from: new Date().toISOString().split('T')[0], // Date du jour (YYYY-MM-DD)
    }

    if (formState.contributionType === 'NEW_PROVIDER') {
      contributionData.provider_name = formState.providerName
      contributionData.provider_website = formState.providerWebsite || undefined
    } else {
      contributionData.existing_provider_id = formState.selectedProviderId
    }

    // If editing an existing contribution, update it. Otherwise, create a new one.
    if (editingContributionId) {
      updateMutation.mutate({ contributionId: editingContributionId, data: contributionData })
    } else {
      submitMutation.mutate(contributionData)
    }
  }

  const handleJsonImport = async () => {
    try {
      const data = JSON.parse(jsonImportData)
      const contributions = Array.isArray(data) ? data : [data]

      setImportProgress({ current: 0, total: contributions.length, errors: [] })
      const errors: string[] = []

      for (let i = 0; i < contributions.length; i++) {
        try {
          await energyApi.submitContribution(contributions[i])
          setImportProgress({ current: i + 1, total: contributions.length, errors })
        } catch (error: unknown) {
          const offerName = contributions[i].offer_name || 'Inconnue'
          const errorMessage = (error as Error)?.message || 'Erreur inconnue'
          const errorMsg = `Offre ${i + 1} (${offerName}): ${errorMessage}`
          errors.push(errorMsg)
          setImportProgress({ current: i + 1, total: contributions.length, errors })
        }
      }

      if (errors.length === 0) {
        toast.success(`${contributions.length} contribution(s) importée(s) avec succès !`)
      } else {
        toast.error(`Import terminé avec ${errors.length} erreur(s). Vérifiez les détails ci-dessous.`)
      }

      queryClient.invalidateQueries({ queryKey: ['my-contributions'] })

      if (errors.length === 0) {
        setJsonImportData('')
        setShowJsonImport(false)
      }
    } catch (error: unknown) {
      const errorMessage = (error as Error)?.message || 'Format JSON invalide'
      toast.error(`Erreur de parsing JSON: ${errorMessage}`)
    }
  }

  return (
    <div id="contribution-form" className="card">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Plus className="text-primary-600 dark:text-primary-400" size={20} />
          {editingContributionId ? 'Modifier la contribution' : 'Nouvelle contribution'}
        </h2>
        <div className="flex items-center gap-4">
          {editingContributionId && (
            <button
              type="button"
              onClick={() => {
                setEditingContributionId(null)
                resetForm()
              }}
              className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            >
              Annuler l'édition
            </button>
          )}
          <button
            type="button"
            onClick={() => setShowJsonImport(!showJsonImport)}
            className={`btn flex items-center gap-2 text-sm ${showJsonImport ? 'btn-primary' : 'btn-secondary'}`}
          >
            <FileJson size={16} />
            {showJsonImport ? 'Formulaire' : 'Import JSON'}
          </button>
        </div>
      </div>

      {/* JSON Import Section */}
      {showJsonImport ? (
        <div className="space-y-4">
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 p-4 rounded-lg">
            <h3 className="font-semibold mb-2 text-blue-900 dark:text-blue-100">📋 Structure du fichier JSON</h3>
            <p className="text-sm text-blue-800 dark:text-blue-200 mb-3">
              Vous pouvez importer une ou plusieurs offres en utilisant un tableau JSON.
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Collez votre JSON ici :</label>
            <textarea
              value={jsonImportData}
              onChange={(e) => setJsonImportData(e.target.value)}
              className="input font-mono text-xs"
              rows={15}
              placeholder='[{"contribution_type": "NEW_OFFER", ...}]'
            />
          </div>

          {importProgress && (
            <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded">
              <div className="mb-2">
                <div className="flex justify-between text-sm mb-1">
                  <span>Progression : {importProgress.current} / {importProgress.total}</span>
                  <span>{Math.round((importProgress.current / importProgress.total) * 100)}%</span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                  <div
                    className="bg-primary-600 h-2 rounded-full transition-all"
                    style={{ width: `${(importProgress.current / importProgress.total) * 100}%` }}
                  ></div>
                </div>
              </div>
              {importProgress.errors.length > 0 && (
                <div className="mt-3">
                  <p className="text-sm font-medium text-red-600 dark:text-red-400 mb-2">Erreurs :</p>
                  <ul className="text-xs space-y-1 text-red-600 dark:text-red-400">
                    {importProgress.errors.map((error, i) => (
                      <li key={i}>• {error}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          <div className="flex gap-3">
            <button
              type="button"
              onClick={handleJsonImport}
              className="btn btn-primary"
              disabled={!jsonImportData || importProgress !== null}
            >
              Importer les offres
            </button>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Contribution Type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Type de contribution</label>
            <div className="flex gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  value="NEW_OFFER"
                  checked={formState.contributionType === 'NEW_OFFER'}
                  onChange={(e) => onFormStateChange('contributionType', e.target.value as 'NEW_OFFER')}
                  className="cursor-pointer"
                />
                <span>Nouvelle offre (fournisseur existant)</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  value="NEW_PROVIDER"
                  checked={formState.contributionType === 'NEW_PROVIDER'}
                  onChange={(e) => onFormStateChange('contributionType', e.target.value as 'NEW_PROVIDER')}
                  className="cursor-pointer"
                />
                <span>Nouveau fournisseur + offre</span>
              </label>
            </div>
          </div>

          {/* Provider Selection or Creation */}
          {formState.contributionType === 'NEW_PROVIDER' ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Nom du fournisseur <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={formState.providerName}
                  onChange={(e) => onFormStateChange('providerName', e.target.value)}
                  className="input"
                  required
                  placeholder="Ex: EDF, Engie, Total Energies..."
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Site web (optionnel)</label>
                <input
                  type="url"
                  value={formState.providerWebsite}
                  onChange={(e) => onFormStateChange('providerWebsite', e.target.value)}
                  className="input"
                  placeholder="https://..."
                />
              </div>
            </div>
          ) : (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Fournisseur <span className="text-red-500">*</span>
              </label>
              <select
                value={formState.selectedProviderId}
                onChange={(e) => onFormStateChange('selectedProviderId', e.target.value)}
                className="input"
                required
              >
                <option value="">Sélectionnez un fournisseur</option>
                {Array.isArray(providersData) && providersData.map((provider) => (
                  <option key={provider.id} value={provider.id}>
                    {provider.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Offer Details */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Nom de l'offre <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={formState.offerName}
                onChange={(e) => onFormStateChange('offerName', e.target.value)}
                className="input"
                required
                placeholder="Ex: Tarif Bleu, Heures Creuses..."
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Type d'offre <span className="text-red-500">*</span>
              </label>
              <select
                value={formState.offerType}
                onChange={(e) => onFormStateChange('offerType', e.target.value)}
                className="input"
                required
              >
                <option value="BASE">BASE</option>
                <option value="BASE_WEEKEND">BASE Week-end (tarif unique + week-end réduit)</option>
                <option value="HC_HP">Heures Creuses / Heures Pleines</option>
                <option value="HC_NUIT_WEEKEND">HC Nuit & Week-end (23h-6h + week-end)</option>
                <option value="HC_WEEKEND">HC Week-end (HC PDL + week-end)</option>
                <option value="SEASONAL">SEASONAL (Tarifs saisonniers hiver/été)</option>
                <option value="ZEN_FLEX">ZEN FLEX (Éco + Sobriété)</option>
                <option value="TEMPO">TEMPO</option>
                <option value="EJP">EJP</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Description (optionnelle)</label>
            <textarea
              value={formState.description}
              onChange={(e) => onFormStateChange('description', e.target.value)}
              className="input"
              rows={3}
              placeholder="Décrivez brièvement cette offre..."
            />
          </div>

          {/* Power Variants */}
          <div className="border-t pt-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Variantes de puissance</h3>
              <span className="text-xs font-semibold px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded-full">
                ⚠️ PRIX TTC UNIQUEMENT
              </span>
            </div>

            <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg mb-4">
              <p className="text-sm text-blue-800 dark:text-blue-200">
                💡 Ajoutez une ou plusieurs puissances avec leurs prix d'abonnement et prix kWh respectifs.
              </p>
            </div>

            <PowerVariantForm
              offerType={formState.offerType}
              onAddVariant={handleAddPowerVariant}
              existingPowers={formState.powerVariants.map(v => v.power_kva)}
            />

            {formState.powerVariants.length > 0 && (
              <div className="mt-6 space-y-3">
                <h4 className="font-semibold text-sm text-gray-900 dark:text-white">Variantes ajoutées ({formState.powerVariants.length})</h4>
                {formState.powerVariants.map((variant, index) => (
                  <div key={index} className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <span className="font-semibold text-primary-600 dark:text-primary-400">{variant.power_kva} kVA</span>
                        <span className="text-sm text-gray-600 dark:text-gray-400">•</span>
                        <span className="text-sm">Abo: {variant.subscription_price}€/mois</span>
                      </div>
                      {variant.pricing_data && (
                        <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-gray-600 dark:text-gray-400">
                          {variant.pricing_data.base_price && <span>Base: {formatPrice(variant.pricing_data.base_price)}</span>}
                          {variant.pricing_data.hc_price && <span>HC: {formatPrice(variant.pricing_data.hc_price)}</span>}
                          {variant.pricing_data.hp_price && <span>HP: {formatPrice(variant.pricing_data.hp_price)}</span>}
                          {variant.pricing_data.tempo_blue_hc && (
                            <span className="text-blue-600 dark:text-blue-400">
                              Bleu: {formatPrice(variant.pricing_data.tempo_blue_hc)}/{formatPrice(variant.pricing_data.tempo_blue_hp!)}
                            </span>
                          )}
                          {variant.pricing_data.tempo_white_hc && (
                            <span>
                              Blanc: {formatPrice(variant.pricing_data.tempo_white_hc)}/{formatPrice(variant.pricing_data.tempo_white_hp!)}
                            </span>
                          )}
                          {variant.pricing_data.tempo_red_hc && (
                            <span className="text-red-600 dark:text-red-400">
                              Rouge: {formatPrice(variant.pricing_data.tempo_red_hc)}/{formatPrice(variant.pricing_data.tempo_red_hp!)}
                            </span>
                          )}
                          {variant.pricing_data.ejp_normal && <span>Normal: {formatPrice(variant.pricing_data.ejp_normal)}</span>}
                          {variant.pricing_data.ejp_peak && <span className="text-orange-600 dark:text-orange-400">Pointe: {formatPrice(variant.pricing_data.ejp_peak)}</span>}
                        </div>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={() => handleRemovePowerVariant(index)}
                      className="ml-4 p-2 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
                      title="Supprimer"
                    >
                      <X size={18} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Documentation (Required) */}
          <div className="border-t pt-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Documentation <span className="text-red-500">*</span></h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              Pour valider votre contribution, nous avons besoin d'une source officielle du fournisseur.
            </p>

            <div className="grid grid-cols-1 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Lien vers la fiche des prix <span className="text-red-500">*</span>
                </label>
                <input
                  type="url"
                  value={formState.priceSheetUrl}
                  onChange={(e) => onFormStateChange('priceSheetUrl', e.target.value)}
                  className="input"
                  required
                  placeholder="https://particulier.edf.fr/tarif-bleu/..."
                />
                <p className="text-xs text-gray-500 mt-1">URL officielle du fournisseur présentant les tarifs</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Screenshot ou PDF (optionnel)
                </label>
                <input
                  type="url"
                  value={formState.screenshotUrl}
                  onChange={(e) => onFormStateChange('screenshotUrl', e.target.value)}
                  className="input"
                  placeholder="https://imgur.com/... ou lien direct vers un screenshot"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Hébergez votre capture d'écran sur Imgur, Dropbox, Google Drive, ou tout autre service et collez le lien direct
                </p>
              </div>
            </div>
          </div>

          {/* Submit */}
          <div className="flex justify-end gap-4">
            <button
              type="button"
              onClick={resetForm}
              className="btn"
              disabled={submitMutation.isPending}
            >
              Réinitialiser
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={submitMutation.isPending || updateMutation.isPending}
            >
              {(submitMutation.isPending || updateMutation.isPending)
                ? 'Envoi en cours...'
                : editingContributionId
                  ? 'Mettre à jour la contribution'
                  : 'Soumettre la contribution'
              }
            </button>
          </div>
        </form>
      )}
    </div>
  )
}
