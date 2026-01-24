# Intégration Jeedom

## Vue d'ensemble

L'intégration Jeedom permet d'exporter vos données vers votre installation Jeedom via l'API JSON RPC. Idéal pour les utilisateurs de la solution domotique française.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        INTÉGRATION JEEDOM                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  MyElectricalData Client          Jeedom                                    │
│  ━━━━━━━━━━━━━━━━━━━━━━           ━━━━━━                                    │
│                                                                             │
│  ┌─────────────┐                  ┌─────────────────────────┐               │
│  │ PostgreSQL  │                  │  Plugin Virtuel         │               │
│  │             │                  │                         │               │
│  │ consumption │───────────────▶  │  [Conso] 15.2 kWh       │               │
│  │ production  │  JSON RPC        │  [Prod] 8.5 kWh         │               │
│  │ tempo       │                  │  [Tempo] BLEU           │               │
│  │ ecowatt     │                  │  [EcoWatt] Niveau 1     │               │
│  └─────────────┘                  └─────────────────────────┘               │
│                                          │                                  │
│                                          ▼                                  │
│                                   ┌─────────────┐                           │
│                                   │ Scénarios   │                           │
│                                   │ Widgets     │                           │
│                                   └─────────────┘                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Prérequis

1. Jeedom 4.0 ou supérieur
2. Plugin **Virtuel** installé et activé
3. Clé API Jeedom

### Récupérer la clé API

1. Aller dans **Réglages** > **Système** > **Configuration**
2. Onglet **API**
3. Copier la clé API (ou activer l'API si désactivée)

---

## Configuration

### Via l'interface web

1. Aller dans **Exporter** > **Jeedom**
2. Renseigner :
   - **URL** : `http://jeedom.local` (ou IP)
   - **Clé API** : La clé copiée précédemment
3. Cliquer sur **Tester la connexion**
4. Si OK, activer l'export et **Sauvegarder**

### Via variables d'environnement

```bash
# .env.client
JEEDOM_URL=http://192.168.1.50
JEEDOM_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
JEEDOM_ENABLED=true
```

---

## Équipements créés

L'exportateur crée automatiquement un équipement virtuel par PDL :

### Structure

```
📁 Objet "MyElectricalData"
└── 📦 Équipement "PDL 12345678901234"
    ├── 📊 Consommation journalière (kWh)
    ├── 📊 Consommation hier (kWh)
    ├── 📊 Consommation mensuelle (kWh)
    ├── ⚡ Production journalière (kWh)
    ├── 🎨 Tempo couleur
    ├── 🎨 Tempo demain
    └── 🟢 EcoWatt niveau
```

### Commandes créées

| Commande | Type | Sous-type | Unité |
|----------|------|-----------|-------|
| Conso journalière | Info | Numérique | kWh |
| Conso hier | Info | Numérique | kWh |
| Conso mensuelle | Info | Numérique | kWh |
| Prod journalière | Info | Numérique | kWh |
| Tempo couleur | Info | Autre | - |
| Tempo demain | Info | Autre | - |
| EcoWatt niveau | Info | Numérique | - |

---

## Première configuration Jeedom

### Créer l'objet parent

1. Aller dans **Outils** > **Objets**
2. Cliquer sur **Ajouter**
3. Nommer l'objet "MyElectricalData"
4. **Sauvegarder**

### Activer le plugin Virtuel

1. Aller dans **Plugins** > **Gestion des plugins**
2. Chercher "Virtuel"
3. Cliquer sur **Installer**
4. **Activer** le plugin

L'exportateur créera automatiquement les équipements virtuels.

---

## Scénarios Jeedom

### Alerte Tempo Rouge

```
# Scénario "Alerte Tempo Rouge"

# Déclencheur
- Programmé : tous les jours à 11h30

# Condition
- #[MyElectricalData][PDL xxx][Tempo demain]# == "ROUGE"

# Actions
- Envoyer notification : "⚠️ Demain est un jour Tempo Rouge !"
- Exécuter commande : #[Chauffage][Planificateur][Mode Éco]#
```

### Coupure EcoWatt

```
# Scénario "Alerte EcoWatt"

# Déclencheur
- Sur changement de : #[MyElectricalData][PDL xxx][EcoWatt niveau]#

# Condition
- #[MyElectricalData][PDL xxx][EcoWatt niveau]# >= 2

# Actions SI
- Envoyer notification : "⚡ Alerte EcoWatt niveau #{cmdVar}# !"
- Exécuter commande : #[Prises][Veille TV][Off]#

# Actions SINON
- Exécuter commande : #[Prises][Veille TV][On]#
```

---

## Widgets

### Widget Tempo coloré

Créer un widget personnalisé pour afficher la couleur Tempo :

```html
<!-- Widget cmd.info.string.tempo -->
<div class="cmd cmd-widget" data-cmd_id="#id#">
  <div class="tempo-widget"
       style="background-color: #value# == 'BLEU' ? '#3B82F6' :
              (#value# == 'BLANC' ? '#F3F4F6' : '#EF4444')">
    <span class="value">#value#</span>
  </div>
</div>

<style>
.tempo-widget {
  padding: 10px 20px;
  border-radius: 8px;
  text-align: center;
  font-weight: bold;
}
</style>
```

### Widget EcoWatt

```html
<!-- Widget cmd.info.numeric.ecowatt -->
<div class="cmd cmd-widget" data-cmd_id="#id#">
  <div class="ecowatt-widget level-#value#">
    <span class="icon">
      {% if #value# == 1 %}🟢
      {% elif #value# == 2 %}🟠
      {% else %}🔴{% endif %}
    </span>
    <span class="label">
      {% if #value# == 1 %}Normal
      {% elif #value# == 2 %}Tendu
      {% else %}Critique{% endif %}
    </span>
  </div>
</div>
```

---

## API utilisée

L'exportateur utilise l'API JSON RPC de Jeedom :

### Endpoint

```
POST http://jeedom.local/core/api/jeeApi.php
```

### Exemple de requête

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "cmd::execCmd",
  "params": {
    "apikey": "xxx",
    "id": "123",
    "value": "15.2"
  }
}
```

### Création d'équipement virtuel

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "eqLogic::save",
  "params": {
    "apikey": "xxx",
    "eqLogic": {
      "name": "PDL 12345678901234",
      "eqType_name": "virtual",
      "object_id": "1",
      "isEnable": 1,
      "isVisible": 1
    }
  }
}
```

---

## Dépannage

### Erreur "API Key invalide"

- Vérifier la clé API dans Jeedom (Réglages > Système > Configuration > API)
- S'assurer que l'API est activée
- Essayer avec la clé API "Admin" si disponible

### Erreur "Plugin non trouvé"

- Installer et activer le plugin "Virtuel"
- Redémarrer Jeedom si nécessaire

### Équipements non créés

- Vérifier les logs Jeedom : Analyse > Logs
- S'assurer que l'objet parent existe
- Vérifier les droits de l'API

### Test de l'API

```bash
# Tester la connexion
curl -X POST "http://jeedom.local/core/api/jeeApi.php" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "version",
    "params": {
      "apikey": "VOTRE_CLE_API"
    }
  }'

# Réponse attendue
# {"jsonrpc":"2.0","id":"1","result":"4.4.0"}
```

### Logs Jeedom

1. Aller dans **Analyse** > **Logs**
2. Sélectionner "api" ou "scenario"
3. Chercher les erreurs liées à "MyElectricalData" ou "virtual"

---

## Limitations

| Aspect | Limitation |
|--------|------------|
| Fréquence | Max 1 requête/seconde |
| Équipements | Max 100 commandes/équipement |
| Historique | Géré par Jeedom (paramétrable) |

---

## Code source

L'exportateur Jeedom est implémenté dans :

```
apps/api/src/services/exporters/jeedom.py
```

### Exemple d'export

```python
class JeedomExporter:
    async def update_cmd(self, cmd_id: int, value: Any):
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid4()),
            "method": "cmd::execCmd",
            "params": {
                "apikey": self.api_key,
                "id": cmd_id,
                "value": str(value),
            }
        }

        async with self.session.post(
            f"{self.url}/core/api/jeeApi.php",
            json=payload,
        ) as resp:
            result = await resp.json()
            if "error" in result:
                raise ExportError(result["error"]["message"])
```
