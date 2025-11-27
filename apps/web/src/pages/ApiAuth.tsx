import { useState } from 'react'
import { Copy, Check } from 'lucide-react'
import { useAuthStore } from '@/stores/authStore'
import { Link } from 'react-router-dom'

export default function ApiAuth() {
  const { user } = useAuthStore()
  const [copiedField, setCopiedField] = useState<string | null>(null)

  const copyToClipboard = (text: string, field: string) => {
    navigator.clipboard.writeText(text)
    setCopiedField(field)
    setTimeout(() => setCopiedField(null), 2000)
  }

  const clientId = user?.client_id || 'votre_client_id'
  const [clientSecret, setClientSecret] = useState('votre_client_secret')
  const [bearerToken, setBearerToken] = useState('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...')

  return (
    <div className="w-full h-full flex flex-col">
      <div className="space-y-6">
        {/* Introduction */}
        <div className="card">
          <h2 className="text-xl font-semibold mb-3">Introduction</h2>
          <p className="text-gray-700 dark:text-gray-300">
            L'API MyElectricalData utilise le protocole <strong>OAuth 2.0</strong> avec le flux <strong>Client Credentials</strong> pour l'authentification. Ce mécanisme permet d'échanger vos identifiants d'application (client_id et client_secret) contre un token JWT sécurisé.
          </p>
        </div>

        {/* Principe OAuth 2.0 */}
        <div className="card bg-purple-50 dark:bg-purple-900/20 border-l-4 border-purple-500">
          <h2 className="text-xl font-semibold text-purple-900 dark:text-purple-100 mb-3">
            📋 Principe OAuth 2.0 - Client Credentials
          </h2>
          <p className="text-purple-800 dark:text-purple-200 mb-3">
            Le flux Client Credentials est conçu pour l'authentification machine-to-machine. Le processus est le suivant :
          </p>
          <ol className="text-purple-800 dark:text-purple-200 space-y-2 list-decimal list-inside ml-2">
            <li>Obtenez votre <strong>client_id</strong> dans la section "Mon compte"</li>
            <li>Obtenez votre <strong>client_secret</strong> (fourni à la création du compte, ou réinitialisez-le dans "Mon compte")</li>
            <li>Envoyez ces identifiants au serveur d'autorisation</li>
            <li>Le serveur vérifie les identifiants et retourne un <strong>access_token</strong></li>
            <li>Ce token est ensuite utilisé pour accéder aux ressources protégées</li>
          </ol>
        </div>

        {/* Étape 1 : Obtenir un Access Token */}
        <div className="card bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-500">
          <h2 className="text-xl font-semibold text-blue-900 dark:text-blue-100 mb-3">
            Étape 1 : Obtenir un Access Token
          </h2>
          <div className="space-y-4 text-sm">
            <p className="text-blue-800 dark:text-blue-200">
              Endpoint OAuth 2.0 : <code className="bg-blue-100 dark:bg-blue-800 px-2 py-1 rounded font-mono">/api/accounts/token</code>
            </p>
            <p className="text-blue-800 dark:text-blue-200">
              Envoyez une requête POST avec le Content-Type <code className="bg-blue-100 dark:bg-blue-800 px-2 py-1 rounded">application/x-www-form-urlencoded</code> :
            </p>
            <pre className="bg-gray-900 text-gray-100 p-3 rounded-lg overflow-x-auto text-xs font-mono">
{`POST /api/accounts/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials&client_id=${clientId}&client_secret=votre_client_secret`}
            </pre>
            <p className="text-blue-800 dark:text-blue-200 mt-3">
              Réponse OAuth 2.0 (JSON) :
            </p>
            <pre className="bg-gray-900 text-gray-100 p-3 rounded-lg overflow-x-auto text-xs font-mono">
{`{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 2592000
}`}
            </pre>
            <p className="text-blue-800 dark:text-blue-200 mt-3">
              Le <code className="bg-blue-100 dark:bg-blue-800 px-2 py-1 rounded">token_type</code> est <strong>"bearer"</strong>, ce qui signifie que le token doit être inclus dans l'en-tête Authorization avec le préfixe "Bearer".
            </p>
          </div>
        </div>

        {/* Étape 2 : Utiliser le Bearer Token */}
        <div className="card bg-green-50 dark:bg-green-900/20 border-l-4 border-green-500">
          <h2 className="text-xl font-semibold text-green-900 dark:text-green-100 mb-3">
            Étape 2 : Utiliser le Bearer Token
          </h2>
          <div className="space-y-4 text-sm">
            <p className="text-green-800 dark:text-green-200">
              Une fois le token obtenu, ajoutez-le dans l'en-tête <code className="bg-green-100 dark:bg-green-800 px-2 py-1 rounded font-mono">Authorization</code> de toutes vos requêtes API :
            </p>
            <pre className="bg-gray-900 text-gray-100 p-3 rounded-lg overflow-x-auto text-xs font-mono">
{`GET /api/pdl/
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`}
            </pre>
            <p className="text-green-800 dark:text-green-200">
              Format complet : <code className="bg-green-100 dark:bg-green-800 px-2 py-1 rounded font-mono">Authorization: Bearer &lt;access_token&gt;</code>
            </p>
          </div>
        </div>

        {/* Sécurité et Bonnes Pratiques */}
        <div className="card bg-yellow-50 dark:bg-yellow-900/20 border-l-4 border-yellow-500">
          <h2 className="text-xl font-semibold text-yellow-900 dark:text-yellow-100 mb-3">
            ⚠️ Sécurité et Bonnes Pratiques
          </h2>
          <ul className="text-yellow-800 dark:text-yellow-200 space-y-2 list-disc list-inside ml-2">
            <li><strong>Expiration</strong> : Le token expire après 30 jours</li>
            <li><strong>Stockage</strong> : Conservez le token de manière sécurisée (ne pas l'exposer côté client)</li>
            <li><strong>Confidentialité</strong> : Ne partagez jamais votre token ou vos identifiants</li>
            <li><strong>HTTPS obligatoire</strong> : Utilisez toujours HTTPS en production pour éviter l'interception du token</li>
            <li><strong>Renouvellement</strong> : Prévoyez de gérer l'expiration et le renouvellement du token dans votre application</li>
          </ul>
        </div>

        {/* Vos identifiants OAuth 2.0 */}
        <div className="card bg-indigo-50 dark:bg-indigo-900/20 border-l-4 border-indigo-500">
          <h2 className="text-xl font-semibold text-indigo-900 dark:text-indigo-100 mb-3">
            🔑 Vos identifiants OAuth 2.0
          </h2>
          <div className="text-indigo-800 dark:text-indigo-200 space-y-4">
            <div>
              <p className="font-semibold mb-2">client_id :</p>
              <div className="flex items-center gap-2">
                <code className="bg-indigo-100 dark:bg-indigo-800 px-3 py-2 rounded font-mono text-sm flex-1">
                  {clientId}
                </code>
                <button
                  onClick={() => copyToClipboard(clientId, 'client_id')}
                  className="btn-secondary p-2 flex items-center gap-1"
                  title="Copier le client_id"
                >
                  {copiedField === 'client_id' ? (
                    <Check className="w-4 h-4 text-green-600 dark:text-green-400" />
                  ) : (
                    <Copy className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>
            <div>
              <p className="font-semibold mb-2">client_secret :</p>
              <ul className="list-disc list-inside ml-2 space-y-1 text-sm">
                <li>Fourni lors de la création de votre compte</li>
                <li>Peut être réinitialisé dans <Link to="/settings" className="underline font-semibold">"Mon compte"</Link></li>
                <li>⚠️ Conservez-le en lieu sûr</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Exemple complet avec cURL */}
        <div className="card bg-gray-50 dark:bg-gray-800/50 border-l-4 border-gray-400 dark:border-gray-600">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
            🔍 Exemple complet avec cURL
          </h2>

          {/* Client Secret Input */}
          <div className="mb-4 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
            <label className="block text-sm font-medium text-amber-900 dark:text-amber-100 mb-2">
              Renseignez votre client_secret pour personnaliser l'exemple :
            </label>
            <input
              type="password"
              value={clientSecret}
              onChange={(e) => setClientSecret(e.target.value)}
              placeholder="Entrez votre client_secret"
              className="input w-full text-sm font-mono"
            />
            <p className="text-xs text-amber-700 dark:text-amber-300 mt-2">
              💡 Votre client_secret est stocké uniquement dans votre navigateur et n'est jamais envoyé.
            </p>
          </div>

          <p className="text-gray-700 dark:text-gray-300 mb-3">
            1. Obtenir le token :
          </p>
          <div className="relative">
            <pre className="bg-gray-900 text-gray-100 p-3 rounded-lg overflow-x-auto text-xs font-mono mb-3">
{`curl -X POST https://myelectricaldata.fr/api/accounts/token \\
  -H "Content-Type: application/x-www-form-urlencoded" \\
  -d "grant_type=client_credentials&client_id=${clientId}&client_secret=${clientSecret}"`}
            </pre>
            <button
              onClick={() => copyToClipboard(
                `curl -X POST https://myelectricaldata.fr/api/accounts/token -H "Content-Type: application/x-www-form-urlencoded" -d "grant_type=client_credentials&client_id=${clientId}&client_secret=${clientSecret}"`,
                'curl_token'
              )}
              className="absolute top-2 right-2 btn-secondary p-2 flex items-center gap-1"
              title="Copier la commande"
            >
              {copiedField === 'curl_token' ? (
                <Check className="w-4 h-4 text-green-600 dark:text-green-400" />
              ) : (
                <Copy className="w-4 h-4" />
              )}
            </button>
          </div>

          {/* Bearer Token Input */}
          <div className="mb-4 p-3 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg">
            <label className="block text-sm font-medium text-emerald-900 dark:text-emerald-100 mb-2">
              Renseignez votre access_token pour personnaliser l'exemple :
            </label>
            <input
              type="password"
              value={bearerToken}
              onChange={(e) => setBearerToken(e.target.value)}
              placeholder="Entrez votre Bearer token"
              className="input w-full text-sm font-mono"
            />
            <p className="text-xs text-emerald-700 dark:text-emerald-300 mt-2">
              💡 Collez ici le token obtenu à l'étape précédente. Il est stocké uniquement dans votre navigateur.
            </p>
          </div>

          <p className="text-gray-700 dark:text-gray-300 mb-3">
            2. Utiliser le token pour accéder aux ressources (exemple : lister vos PDL) :
          </p>
          <div className="relative">
            <pre className="bg-gray-900 text-gray-100 p-3 rounded-lg overflow-x-auto text-xs font-mono mb-3">
{`curl -X GET https://myelectricaldata.fr/api/pdl/ \\
  -H "Authorization: Bearer ${bearerToken}"`}
            </pre>
            <button
              onClick={() => copyToClipboard(
                `curl -X GET https://myelectricaldata.fr/api/pdl/ -H "Authorization: Bearer ${bearerToken}"`,
                'curl_api'
              )}
              className="absolute top-2 right-2 btn-secondary p-2 flex items-center gap-1"
              title="Copier la commande"
            >
              {copiedField === 'curl_api' ? (
                <Check className="w-4 h-4 text-green-600 dark:text-green-400" />
              ) : (
                <Copy className="w-4 h-4" />
              )}
            </button>
          </div>
          <p className="text-gray-700 dark:text-gray-300 mb-2">
            Réponse JSON :
          </p>
          <div className="relative">
            <pre className="bg-gray-900 text-gray-100 p-3 rounded-lg overflow-x-auto text-xs font-mono">
{`{
  "success": true,
  "data": [
    {
      "id": "abc123",
      "usage_point_id": "12345678901234",
      "name": "Maison principale",
      "created_at": "2024-01-15T10:30:00Z",
      "subscribed_power": 6000
    }
  ],
  "timestamp": "2024-01-20T14:30:00Z"
}`}
            </pre>
            <button
              onClick={() => copyToClipboard(
                `{\n  "success": true,\n  "data": [\n    {\n      "id": "abc123",\n      "usage_point_id": "12345678901234",\n      "name": "Maison principale",\n      "created_at": "2024-01-15T10:30:00Z",\n      "subscribed_power": 6000\n    }\n  ],\n  "timestamp": "2024-01-20T14:30:00Z"\n}`,
                'response_json'
              )}
              className="absolute top-2 right-2 btn-secondary p-2 flex items-center gap-1"
              title="Copier la réponse"
            >
              {copiedField === 'response_json' ? (
                <Check className="w-4 h-4 text-green-600 dark:text-green-400" />
              ) : (
                <Copy className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
