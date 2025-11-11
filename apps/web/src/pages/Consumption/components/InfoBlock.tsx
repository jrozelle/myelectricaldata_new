export function InfoBlock() {
  return (
    <div className="mt-6 rounded-xl shadow-md border bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-700 transition-colors duration-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
        ℹ️ Informations importantes
      </h3>

      <div className="space-y-4">
        {/* Cache Information */}
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
          <p className="text-sm text-yellow-800 dark:text-yellow-200">
            <strong>💾 Cache automatique :</strong> L'utilisation de la page de consommation active automatiquement le cache. Vos données de consommation seront stockées temporairement pour améliorer les performances et éviter de solliciter excessivement l'API Enedis. Les données en cache expirent automatiquement après <strong>24 heures</strong>.
          </p>
        </div>

        {/* Data Source Information */}
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <div className="text-sm text-blue-800 dark:text-blue-200 space-y-2">
            <p>
              <strong>📊 Source des données :</strong>
            </p>
            <ul className="list-disc list-inside space-y-1 ml-2">
              <li>Les données sont récupérées depuis l'API <strong>Enedis Data Connect</strong></li>
              <li>Endpoint utilisé : <code className="bg-blue-100 dark:bg-blue-900/40 px-1 rounded">consumption/daily</code> (relevés quotidiens)</li>
              <li>Récupération automatique de <strong>1095 jours d'historique</strong> (limite maximale Enedis)</li>
              <li>Les données Enedis ne sont disponibles qu'en <strong>J-1</strong> (hier)</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
