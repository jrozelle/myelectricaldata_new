// Fonctions utilitaires partagées pour la page Contribuer

/**
 * Retourne le label français pour un type d'offre
 */
export const getOfferTypeLabel = (type: string): string => {
  const labels: Record<string, string> = {
    'BASE': 'Base',
    'HC_HP': 'Heures Creuses / Heures Pleines',
    'TEMPO': 'Tempo',
    'EJP': 'EJP',
    'BASE_WEEKEND': 'Base + Weekend',
    'HC_WEEKEND': 'HC/HP + Weekend',
    'HC_NUIT_WEEKEND': 'HC Nuit + Weekend',
    'SEASONAL': 'Saisonnier',
    'ZEN_FLEX': 'Zen Flex',
  }
  return labels[type] || type
}

/**
 * Formate un prix en €/kWh avec 4 décimales
 */
export const formatPrice = (price: number | undefined): string => {
  if (price === undefined || price === null) return '-'
  return `${Number(price).toFixed(4)} €/kWh`
}
