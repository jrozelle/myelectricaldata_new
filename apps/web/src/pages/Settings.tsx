import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { authApi } from '@/api/auth'
import { useAuth } from '@/hooks/useAuth'
import { Trash2, TrendingUp, Copy, RefreshCw, Key } from 'lucide-react'

export default function Settings() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [deleteConfirmText, setDeleteConfirmText] = useState('')
  const [showRegenerateConfirm, setShowRegenerateConfirm] = useState(false)
  const [newSecret, setNewSecret] = useState<string | null>(null)
  const [copiedNewSecret, setCopiedNewSecret] = useState(false)
  const [copiedClientId, setCopiedClientId] = useState(false)
  const [notification, setNotification] = useState<{type: 'success' | 'error', message: string} | null>(null)

  const { data: credentialsResponse } = useQuery({
    queryKey: ['credentials'],
    queryFn: () => authApi.getCredentials(),
  })

  const { data: usageStatsResponse } = useQuery({
    queryKey: ['usage-stats'],
    queryFn: () => authApi.getUsageStats(),
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  const credentials = credentialsResponse?.success ? credentialsResponse.data : null
  const usageStats = usageStatsResponse?.success ? usageStatsResponse.data as any : null

  const regenerateSecretMutation = useMutation({
    mutationFn: () => authApi.regenerateSecret(),
    onSuccess: (response) => {
      if (response.success && response.data) {
        setNewSecret(response.data.client_secret)
        setNotification({
          type: 'success',
          message: 'Nouveau client_secret généré avec succès ! Copiez-le maintenant, il ne sera plus affiché.'
        })
        setShowRegenerateConfirm(false)
        queryClient.invalidateQueries({ queryKey: ['credentials'] })
        setTimeout(() => {
          setNotification(null)
          setNewSecret(null)
        }, 60000)
      }
    },
    onError: (error: any) => {
      setNotification({
        type: 'error',
        message: error?.message || 'Erreur lors de la régénération du secret'
      })
      setShowRegenerateConfirm(false)
      setTimeout(() => setNotification(null), 10000)
    }
  })

  const deleteAccountMutation = useMutation({
    mutationFn: () => authApi.deleteAccount(),
    onSuccess: () => {
      logout()
      navigate('/')
    },
  })

  const handleRegenerateSecret = () => {
    regenerateSecretMutation.mutate()
  }

  const handleDeleteAccount = () => {
    if (deleteConfirmText === 'SUPPRIMER') {
      deleteAccountMutation.mutate()
    }
  }

  const copyNewSecret = () => {
    if (newSecret) {
      navigator.clipboard.writeText(newSecret)
      setCopiedNewSecret(true)
      setTimeout(() => setCopiedNewSecret(false), 2000)
    }
  }

  const copyClientId = () => {
    if (credentials?.client_id) {
      navigator.clipboard.writeText(credentials.client_id)
      setCopiedClientId(true)
      setTimeout(() => setCopiedClientId(false), 2000)
    }
  }

  return (
    <div className="space-y-8 w-full">
      {/* Notification Toast */}
      {notification && (
        <div className={`p-4 rounded-lg flex items-start gap-3 ${
          notification.type === 'success'
            ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800'
            : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800'
        }`}>
          <div className="flex-1">
            <p className={notification.type === 'success'
              ? 'text-green-800 dark:text-green-200 font-medium'
              : 'text-red-800 dark:text-red-200 font-medium'
            }>
              {notification.message}
            </p>
          </div>
          <button
            onClick={() => setNotification(null)}
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            ✕
          </button>
        </div>
      )}

      <div>
        <h1 className="text-3xl font-bold mb-2">Mon compte</h1>
        <p className="text-gray-600 dark:text-gray-400">
          Gérez votre compte et vos préférences
        </p>
      </div>

      {/* Account Info */}
      <div className="card">
        <h2 className="text-xl font-semibold mb-4">Informations du compte</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">Email</label>
            <div className="input bg-gray-50 dark:bg-gray-900">
              {user?.email}
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">ID utilisateur</label>
            <div className="input bg-gray-50 dark:bg-gray-900 font-mono text-sm">
              {user?.id}
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Statut</label>
            <div className="inline-flex items-center px-3 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded-full text-sm">
              ● Actif
            </div>
          </div>
        </div>
      </div>

      {/* API Credentials */}
      <div className="card border-primary-200 dark:border-primary-800">
        <div className="flex items-center gap-2 mb-4">
          <Key className="text-primary-600 dark:text-primary-400" size={24} />
          <h2 className="text-xl font-semibold">Identifiants API</h2>
        </div>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">Client ID</label>
            <div className="flex gap-2">
              <div className="input bg-gray-50 dark:bg-gray-900 font-mono text-sm break-all flex-1">
                {credentials?.client_id || 'Chargement...'}
              </div>
              <button
                onClick={copyClientId}
                className="btn btn-secondary flex-shrink-0"
                title="Copier le client_id"
                disabled={!credentials?.client_id}
              >
                {copiedClientId ? '✓' : <Copy size={20} />}
              </button>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Client Secret</label>
            <div className="space-y-3">
              {newSecret ? (
                <div className="space-y-3">
                  <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
                    <p className="text-green-800 dark:text-green-200 font-medium mb-2">
                      ✅ Nouveau client_secret généré !
                    </p>
                    <p className="text-sm text-green-700 dark:text-green-300 mb-3">
                      Copiez-le maintenant, il ne sera plus jamais affiché.
                    </p>
                    <div className="flex gap-2">
                      <div className="input bg-white dark:bg-gray-900 font-mono text-sm flex-1 break-all">
                        {newSecret}
                      </div>
                      <button
                        onClick={copyNewSecret}
                        className="btn btn-secondary flex-shrink-0"
                        title="Copier"
                      >
                        {copiedNewSecret ? '✓' : <Copy size={20} />}
                      </button>
                    </div>
                  </div>
                </div>
              ) : (
                <>
                  {!showRegenerateConfirm ? (
                    <div className="flex flex-col sm:flex-row gap-3">
                      <div className="flex-1 p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg flex items-center">
                        <p className="text-sm text-yellow-800 dark:text-yellow-200">
                          ⚠️ Le client_secret n'est jamais stocké ni affiché. Vous l'avez reçu lors de la création de votre compte.
                        </p>
                      </div>
                      <button
                        onClick={() => setShowRegenerateConfirm(true)}
                        className="btn bg-yellow-600 hover:bg-yellow-700 text-white flex items-center gap-2 justify-center whitespace-nowrap"
                      >
                        <RefreshCw size={18} />
                        Régénérer le client_secret
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                        <p className="text-red-800 dark:text-red-200 font-medium mb-2">
                          ⚠️ Attention : Cette action est irréversible
                        </p>
                        <p className="text-sm text-red-700 dark:text-red-300">
                          La régénération du client_secret va :
                        </p>
                        <ul className="text-sm text-red-700 dark:text-red-300 list-disc list-inside mt-2">
                          <li>Invalider votre ancien client_secret</li>
                          <li>Supprimer toutes vos données en cache</li>
                        </ul>
                        <p className="text-sm text-red-700 dark:text-red-300 mt-2 font-medium">
                          Le nouveau client_secret sera affiché une seule fois. Copiez-le immédiatement !
                        </p>
                      </div>

                      <div className="flex gap-3">
                        <button
                          onClick={handleRegenerateSecret}
                          disabled={regenerateSecretMutation.isPending}
                          className="btn bg-red-600 hover:bg-red-700 text-white disabled:opacity-50"
                        >
                          {regenerateSecretMutation.isPending ? 'Régénération...' : 'Confirmer la régénération'}
                        </button>
                        <button
                          onClick={() => setShowRegenerateConfirm(false)}
                          className="btn btn-secondary"
                        >
                          Annuler
                        </button>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Usage Stats */}
      <div className="card border-blue-200 dark:border-blue-800">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp className="text-blue-600 dark:text-blue-400" size={24} />
          <h2 className="text-xl font-semibold">Utilisation de l'API</h2>
        </div>
        {usageStats ? (
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                <p className="text-sm text-blue-600 dark:text-blue-400 font-medium mb-1">Avec cache</p>
                <p className="text-2xl font-bold">
                  {usageStats.cached_requests} / {usageStats.cached_limit}
                </p>
                <div className="mt-2 w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full"
                    style={{
                      width: `${Math.min((usageStats.cached_requests / usageStats.cached_limit) * 100, 100)}%`
                    }}
                  ></div>
                </div>
              </div>
              <div className="p-4 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg">
                <p className="text-sm text-orange-600 dark:text-orange-400 font-medium mb-1">Sans cache</p>
                <p className="text-2xl font-bold">
                  {usageStats.no_cache_requests} / {usageStats.no_cache_limit}
                </p>
                <div className="mt-2 w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                  <div
                    className="bg-orange-600 h-2 rounded-full"
                    style={{
                      width: `${Math.min((usageStats.no_cache_requests / usageStats.no_cache_limit) * 100, 100)}%`
                    }}
                  ></div>
                </div>
              </div>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Compteurs quotidiens • Réinitialisés à minuit UTC • Date : {usageStats.date}
            </p>
          </div>
        ) : (
          <p className="text-gray-500">Chargement des statistiques...</p>
        )}
      </div>

      {/* Danger Zone */}
      <div className="card border-red-200 dark:border-red-800">
        <h2 className="text-xl font-semibold mb-4 text-red-600 dark:text-red-400">
          Zone dangereuse
        </h2>

        {!showDeleteConfirm ? (
          <div>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              La suppression de votre compte est irréversible. Toutes vos données, PDL et cache seront définitivement supprimés.
            </p>
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="btn bg-red-600 hover:bg-red-700 text-white flex items-center gap-2"
            >
              <Trash2 size={20} />
              Supprimer mon compte
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
              <p className="text-red-800 dark:text-red-200 font-medium mb-2">
                ⚠️ Attention : Cette action est irréversible
              </p>
              <p className="text-sm text-red-700 dark:text-red-300">
                Toutes vos données seront définitivement supprimées :
              </p>
              <ul className="text-sm text-red-700 dark:text-red-300 list-disc list-inside mt-2">
                <li>Votre compte et vos identifiants API</li>
                <li>Tous vos points de livraison (PDL)</li>
                <li>Tous les tokens OAuth Enedis</li>
                <li>Toutes les données en cache</li>
              </ul>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">
                Tapez <span className="font-mono bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">SUPPRIMER</span> pour confirmer
              </label>
              <input
                type="text"
                value={deleteConfirmText}
                onChange={(e) => setDeleteConfirmText(e.target.value)}
                placeholder="SUPPRIMER"
                className="input mb-4"
              />
            </div>

            <div className="flex gap-3">
              <button
                onClick={handleDeleteAccount}
                disabled={deleteConfirmText !== 'SUPPRIMER' || deleteAccountMutation.isPending}
                className="btn bg-red-600 hover:bg-red-700 text-white disabled:opacity-50"
              >
                {deleteAccountMutation.isPending ? 'Suppression...' : 'Confirmer la suppression'}
              </button>
              <button
                onClick={() => {
                  setShowDeleteConfirm(false)
                  setDeleteConfirmText('')
                }}
                className="btn btn-secondary"
              >
                Annuler
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
