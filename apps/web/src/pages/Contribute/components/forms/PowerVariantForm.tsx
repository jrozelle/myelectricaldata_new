import { useState } from 'react'
import { type PowerVariant } from '../../types'

interface PowerVariantFormProps {
  offerType: string
  onAddVariant: (variant: PowerVariant) => void
  existingPowers: number[]
}

export default function PowerVariantForm({ offerType, onAddVariant, existingPowers }: PowerVariantFormProps) {
  const [power, setPower] = useState('')
  const [subscriptionPrice, setSubscriptionPrice] = useState('')

  // Prix kWh
  const [basePrice, setBasePrice] = useState('')
  const [hcPrice, setHcPrice] = useState('')
  const [hpPrice, setHpPrice] = useState('')
  const [tempoBlueHc, setTempoBlueHc] = useState('')
  const [tempoBlueHp, setTempoBlueHp] = useState('')
  const [tempoWhiteHc, setTempoWhiteHc] = useState('')
  const [tempoWhiteHp, setTempoWhiteHp] = useState('')
  const [tempoRedHc, setTempoRedHc] = useState('')
  const [tempoRedHp, setTempoRedHp] = useState('')
  const [ejpNormal, setEjpNormal] = useState('')
  const [ejpPeak, setEjpPeak] = useState('')
  const [hcPriceWinter, setHcPriceWinter] = useState('')
  const [hpPriceWinter, setHpPriceWinter] = useState('')
  const [hcPriceSummer, setHcPriceSummer] = useState('')
  const [hpPriceSummer, setHpPriceSummer] = useState('')
  const [peakDayPrice, setPeakDayPrice] = useState('')
  const [basePriceWeekend, setBasePriceWeekend] = useState('')

  const resetForm = () => {
    setPower('')
    setSubscriptionPrice('')
    setBasePrice('')
    setHcPrice('')
    setHpPrice('')
    setTempoBlueHc('')
    setTempoBlueHp('')
    setTempoWhiteHc('')
    setTempoWhiteHp('')
    setTempoRedHc('')
    setTempoRedHp('')
    setEjpNormal('')
    setEjpPeak('')
    setHcPriceWinter('')
    setHpPriceWinter('')
    setHcPriceSummer('')
    setHpPriceSummer('')
    setPeakDayPrice('')
    setBasePriceWeekend('')
  }

  const handleAdd = () => {
    if (!power || !subscriptionPrice) {
      return
    }

    const pricingData: PowerVariant['pricing_data'] = {}

    // Ajouter les prix selon le type d'offre
    if (offerType === 'BASE') {
      if (basePrice) pricingData.base_price = parseFloat(basePrice)
    } else if (offerType === 'BASE_WEEKEND') {
      if (basePrice) pricingData.base_price = parseFloat(basePrice)
      if (basePriceWeekend) pricingData.base_price_weekend = parseFloat(basePriceWeekend)
    } else if (offerType === 'HC_HP' || offerType === 'HC_NUIT_WEEKEND' || offerType === 'HC_WEEKEND') {
      if (hcPrice) pricingData.hc_price = parseFloat(hcPrice)
      if (hpPrice) pricingData.hp_price = parseFloat(hpPrice)
    } else if (offerType === 'SEASONAL') {
      if (hcPriceWinter) pricingData.hc_price_winter = parseFloat(hcPriceWinter)
      if (hpPriceWinter) pricingData.hp_price_winter = parseFloat(hpPriceWinter)
      if (hcPriceSummer) pricingData.hc_price_summer = parseFloat(hcPriceSummer)
      if (hpPriceSummer) pricingData.hp_price_summer = parseFloat(hpPriceSummer)
      if (peakDayPrice) pricingData.peak_day_price = parseFloat(peakDayPrice)
    } else if (offerType === 'TEMPO') {
      if (tempoBlueHc) pricingData.tempo_blue_hc = parseFloat(tempoBlueHc)
      if (tempoBlueHp) pricingData.tempo_blue_hp = parseFloat(tempoBlueHp)
      if (tempoWhiteHc) pricingData.tempo_white_hc = parseFloat(tempoWhiteHc)
      if (tempoWhiteHp) pricingData.tempo_white_hp = parseFloat(tempoWhiteHp)
      if (tempoRedHc) pricingData.tempo_red_hc = parseFloat(tempoRedHc)
      if (tempoRedHp) pricingData.tempo_red_hp = parseFloat(tempoRedHp)
    } else if (offerType === 'EJP') {
      if (ejpNormal) pricingData.ejp_normal = parseFloat(ejpNormal)
      if (ejpPeak) pricingData.ejp_peak = parseFloat(ejpPeak)
    } else if (offerType === 'ZEN_FLEX') {
      if (hcPriceWinter) pricingData.hc_price_winter = parseFloat(hcPriceWinter)
      if (hpPriceWinter) pricingData.hp_price_winter = parseFloat(hpPriceWinter)
      if (hcPriceSummer) pricingData.hc_price_summer = parseFloat(hcPriceSummer)
      if (hpPriceSummer) pricingData.hp_price_summer = parseFloat(hpPriceSummer)
    }

    const variant: PowerVariant = {
      power_kva: parseFloat(power),
      subscription_price: parseFloat(subscriptionPrice),
      pricing_data: Object.keys(pricingData).length > 0 ? pricingData : undefined
    }

    onAddVariant(variant)
    resetForm()
  }

  return (
    <div className="bg-gray-50 dark:bg-gray-900/30 border border-gray-300 dark:border-gray-700 rounded-lg p-4 space-y-4">
      {/* Puissance et abonnement */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium mb-1">Puissance (kVA) <span className="text-red-600">*</span></label>
          <select
            value={power}
            onChange={(e) => setPower(e.target.value)}
            className="input text-sm"
          >
            <option value="">Sélectionnez...</option>
            {[3, 6, 9, 12, 15, 18, 24, 30, 36].filter(p => !existingPowers.includes(p)).map(p => (
              <option key={p} value={p}>{p} kVA</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium mb-1">Prix abonnement (€/mois TTC) <span className="text-red-600">*</span></label>
          <input
            type="number"
            step="0.01"
            value={subscriptionPrice}
            onChange={(e) => setSubscriptionPrice(e.target.value)}
            className="input text-sm"
            placeholder="12.34"
          />
        </div>
      </div>

      {/* Prix kWh selon le type d'offre */}
      <div className="border-t border-gray-300 dark:border-gray-700 pt-3">
        <p className="text-xs font-medium mb-2 text-gray-600 dark:text-gray-400">Prix kWh pour cette puissance</p>

        {/* BASE */}
        {offerType === 'BASE' && (
          <div>
            <label className="block text-xs font-medium mb-1">Prix BASE (€/kWh TTC) <span className="text-red-600">*</span></label>
            <input
              type="number"
              step="0.00001"
              value={basePrice}
              onChange={(e) => setBasePrice(e.target.value)}
              className="input text-sm"
              placeholder="0.2516"
            />
          </div>
        )}

        {/* BASE_WEEKEND */}
        {offerType === 'BASE_WEEKEND' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1">Prix BASE semaine (€/kWh TTC) <span className="text-red-600">*</span></label>
              <input
                type="number"
                step="0.00001"
                value={basePrice}
                onChange={(e) => setBasePrice(e.target.value)}
                className="input text-sm"
                placeholder="0.2516"
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">Prix BASE week-end (€/kWh TTC)</label>
              <input
                type="number"
                step="0.00001"
                value={basePriceWeekend}
                onChange={(e) => setBasePriceWeekend(e.target.value)}
                className="input text-sm"
                placeholder="0.2000"
              />
            </div>
          </div>
        )}

        {/* HC_HP */}
        {(offerType === 'HC_HP' || offerType === 'HC_NUIT_WEEKEND' || offerType === 'HC_WEEKEND') && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1">Prix HC (€/kWh TTC) <span className="text-red-600">*</span></label>
              <input
                type="number"
                step="0.00001"
                value={hcPrice}
                onChange={(e) => setHcPrice(e.target.value)}
                className="input text-sm"
                placeholder="0.2068"
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">Prix HP (€/kWh TTC) <span className="text-red-600">*</span></label>
              <input
                type="number"
                step="0.00001"
                value={hpPrice}
                onChange={(e) => setHpPrice(e.target.value)}
                className="input text-sm"
                placeholder="0.2700"
              />
            </div>
          </div>
        )}

        {/* TEMPO */}
        {offerType === 'TEMPO' && (
          <div className="space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium mb-1">
                  <span className="text-blue-600 dark:text-blue-400">Bleu HC</span> (€/kWh TTC) <span className="text-red-600">*</span>
                </label>
                <input
                  type="number"
                  step="0.00001"
                  value={tempoBlueHc}
                  onChange={(e) => setTempoBlueHc(e.target.value)}
                  className="input text-sm"
                  placeholder="0.1296"
                />
              </div>
              <div>
                <label className="block text-xs font-medium mb-1">
                  <span className="text-blue-600 dark:text-blue-400">Bleu HP</span> (€/kWh TTC) <span className="text-red-600">*</span>
                </label>
                <input
                  type="number"
                  step="0.00001"
                  value={tempoBlueHp}
                  onChange={(e) => setTempoBlueHp(e.target.value)}
                  className="input text-sm"
                  placeholder="0.1609"
                />
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium mb-1">Blanc HC (€/kWh TTC) <span className="text-red-600">*</span></label>
                <input
                  type="number"
                  step="0.00001"
                  value={tempoWhiteHc}
                  onChange={(e) => setTempoWhiteHc(e.target.value)}
                  className="input text-sm"
                  placeholder="0.1486"
                />
              </div>
              <div>
                <label className="block text-xs font-medium mb-1">Blanc HP (€/kWh TTC) <span className="text-red-600">*</span></label>
                <input
                  type="number"
                  step="0.00001"
                  value={tempoWhiteHp}
                  onChange={(e) => setTempoWhiteHp(e.target.value)}
                  className="input text-sm"
                  placeholder="0.1894"
                />
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium mb-1">
                  <span className="text-red-600 dark:text-red-400">Rouge HC</span> (€/kWh TTC) <span className="text-red-600">*</span>
                </label>
                <input
                  type="number"
                  step="0.00001"
                  value={tempoRedHc}
                  onChange={(e) => setTempoRedHc(e.target.value)}
                  className="input text-sm"
                  placeholder="0.1568"
                />
              </div>
              <div>
                <label className="block text-xs font-medium mb-1">
                  <span className="text-red-600 dark:text-red-400">Rouge HP</span> (€/kWh TTC) <span className="text-red-600">*</span>
                </label>
                <input
                  type="number"
                  step="0.00001"
                  value={tempoRedHp}
                  onChange={(e) => setTempoRedHp(e.target.value)}
                  className="input text-sm"
                  placeholder="0.7562"
                />
              </div>
            </div>
          </div>
        )}

        {/* EJP */}
        {offerType === 'EJP' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1">Prix Normal (€/kWh TTC) <span className="text-red-600">*</span></label>
              <input
                type="number"
                step="0.00001"
                value={ejpNormal}
                onChange={(e) => setEjpNormal(e.target.value)}
                className="input text-sm"
                placeholder="0.1658"
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">
                <span className="text-orange-600 dark:text-orange-400">Prix Pointe</span> (€/kWh TTC) <span className="text-red-600">*</span>
              </label>
              <input
                type="number"
                step="0.00001"
                value={ejpPeak}
                onChange={(e) => setEjpPeak(e.target.value)}
                className="input text-sm"
                placeholder="0.8488"
              />
            </div>
          </div>
        )}

        {/* SEASONAL */}
        {offerType === 'SEASONAL' && (
          <div className="space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium mb-1">HC Hiver (€/kWh TTC) <span className="text-red-600">*</span></label>
                <input
                  type="number"
                  step="0.00001"
                  value={hcPriceWinter}
                  onChange={(e) => setHcPriceWinter(e.target.value)}
                  className="input text-sm"
                  placeholder="0.31128"
                />
              </div>
              <div>
                <label className="block text-xs font-medium mb-1">HP Hiver (€/kWh TTC) <span className="text-red-600">*</span></label>
                <input
                  type="number"
                  step="0.00001"
                  value={hpPriceWinter}
                  onChange={(e) => setHpPriceWinter(e.target.value)}
                  className="input text-sm"
                  placeholder="0.22942"
                />
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium mb-1">HC Été (€/kWh TTC) <span className="text-red-600">*</span></label>
                <input
                  type="number"
                  step="0.00001"
                  value={hcPriceSummer}
                  onChange={(e) => setHcPriceSummer(e.target.value)}
                  className="input text-sm"
                  placeholder="0.19397"
                />
              </div>
              <div>
                <label className="block text-xs font-medium mb-1">HP Été (€/kWh TTC) <span className="text-red-600">*</span></label>
                <input
                  type="number"
                  step="0.00001"
                  value={hpPriceSummer}
                  onChange={(e) => setHpPriceSummer(e.target.value)}
                  className="input text-sm"
                  placeholder="0.13166"
                />
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">Prix Jour de Pointe (€/kWh TTC)</label>
              <input
                type="number"
                step="0.00001"
                value={peakDayPrice}
                onChange={(e) => setPeakDayPrice(e.target.value)}
                className="input text-sm"
                placeholder="0.51928"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Optionnel - si l'offre propose une option "jours de pointe"
              </p>
            </div>
          </div>
        )}

        {/* ZEN_FLEX */}
        {offerType === 'ZEN_FLEX' && (
          <div className="space-y-3">
            <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
              <p className="text-xs text-blue-800 dark:text-blue-200">
                💡 <strong>Zen Flex</strong> : Jours Éco (345j/an) + Jours Sobriété (20j/an). HC de 22h à 6h.
              </p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium mb-1">HC Éco (€/kWh TTC) <span className="text-red-600">*</span></label>
                <input
                  type="number"
                  step="0.00001"
                  value={hcPriceWinter}
                  onChange={(e) => setHcPriceWinter(e.target.value)}
                  className="input text-sm"
                  placeholder="0.1546"
                />
              </div>
              <div>
                <label className="block text-xs font-medium mb-1">HP Éco (€/kWh TTC) <span className="text-red-600">*</span></label>
                <input
                  type="number"
                  step="0.00001"
                  value={hpPriceWinter}
                  onChange={(e) => setHpPriceWinter(e.target.value)}
                  className="input text-sm"
                  placeholder="0.2068"
                />
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium mb-1">HC Sobriété (€/kWh TTC) <span className="text-red-600">*</span></label>
                <input
                  type="number"
                  step="0.00001"
                  value={hcPriceSummer}
                  onChange={(e) => setHcPriceSummer(e.target.value)}
                  className="input text-sm"
                  placeholder="0.2068"
                />
              </div>
              <div>
                <label className="block text-xs font-medium mb-1">HP Sobriété (€/kWh TTC) <span className="text-red-600">*</span></label>
                <input
                  type="number"
                  step="0.00001"
                  value={hpPriceSummer}
                  onChange={(e) => setHpPriceSummer(e.target.value)}
                  className="input text-sm"
                  placeholder="0.7562"
                />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Bouton Ajouter */}
      <button
        type="button"
        onClick={handleAdd}
        disabled={!power || !subscriptionPrice}
        className="w-full btn-primary px-4 py-2 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
      >
        ➕ Ajouter cette variante de puissance
      </button>
    </div>
  )
}
