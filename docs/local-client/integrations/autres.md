# Autres intégrations

## Intégrations planifiées

Les intégrations suivantes sont prévues pour de futures versions :

| Destination | Statut | Description |
|-------------|--------|-------------|
| InfluxDB | 🔜 Planifié | Base time-series alternative |
| Domoticz | 🔜 Planifié | Solution domotique open-source |
| OpenHAB | 🔜 Planifié | Plateforme domotique Java |
| Prometheus | 🔜 Planifié | Scraping metrics (pull) |
| Webhook | 🔜 Planifié | Appels HTTP personnalisés |

---

## Créer une intégration personnalisée

### Structure d'un exportateur

Chaque exportateur hérite de la classe de base :

```python
# apps/api/src/services/exporters/base.py

from abc import ABC, abstractmethod
from typing import Any

class BaseExporter(ABC):
    """Classe de base pour tous les exportateurs"""

    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    async def test_connection(self) -> ConnectionTestResult:
        """Teste la connexion à la destination"""
        pass

    @abstractmethod
    async def export_consumption(self, data: ConsumptionData) -> ExportResult:
        """Exporte les données de consommation"""
        pass

    @abstractmethod
    async def export_production(self, data: ProductionData) -> ExportResult:
        """Exporte les données de production"""
        pass

    @abstractmethod
    async def export_tempo(self, data: TempoData) -> ExportResult:
        """Exporte les données Tempo"""
        pass

    @abstractmethod
    async def export_ecowatt(self, data: EcowattData) -> ExportResult:
        """Exporte les données EcoWatt"""
        pass
```

### Exemple : Exportateur Webhook

```python
# apps/api/src/services/exporters/webhook.py

from .base import BaseExporter
import aiohttp

class WebhookExporter(BaseExporter):
    """Exportateur générique vers un webhook HTTP"""

    def __init__(self, config: dict):
        super().__init__(config)
        self.url = config["url"]
        self.headers = config.get("headers", {})
        self.method = config.get("method", "POST")

    async def test_connection(self) -> ConnectionTestResult:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    "HEAD", self.url, headers=self.headers, timeout=10
                ) as resp:
                    return ConnectionTestResult(
                        success=resp.status < 400,
                        message=f"HTTP {resp.status}"
                    )
        except Exception as e:
            return ConnectionTestResult(success=False, error=str(e))

    async def export_consumption(self, data: ConsumptionData) -> ExportResult:
        payload = {
            "type": "consumption",
            "pdl": data.pdl,
            "date": data.date.isoformat(),
            "value_kwh": data.value_wh / 1000,
            "timestamp": datetime.now().isoformat(),
        }
        return await self._send(payload)

    async def _send(self, payload: dict) -> ExportResult:
        async with aiohttp.ClientSession() as session:
            async with session.request(
                self.method,
                self.url,
                json=payload,
                headers=self.headers,
            ) as resp:
                return ExportResult(
                    success=resp.status < 400,
                    records_exported=1,
                    error=None if resp.status < 400 else await resp.text(),
                )
```

### Enregistrer l'exportateur

```python
# apps/api/src/services/exporter.py

from .exporters.webhook import WebhookExporter

class ExporterService:
    exporters = {
        'home_assistant': HomeAssistantExporter,
        'mqtt': MQTTExporter,
        'victoriametrics': VictoriaMetricsExporter,
        'jeedom': JeedomExporter,
        'webhook': WebhookExporter,  # Nouveau
    }
```

---

## Utiliser les données via API

Si aucune intégration ne correspond à votre besoin, vous pouvez utiliser l'API REST du backend :

### Endpoints disponibles

```bash
# Consommation
GET /api/consumption/daily/{pdl}?start=2024-01-01&end=2024-01-31

# Production
GET /api/production/daily/{pdl}?start=2024-01-01&end=2024-01-31

# Tempo
GET /api/tempo?start=2024-01-01&end=2024-01-31

# EcoWatt
GET /api/ecowatt?date=2024-01-15
```

### Exemple avec curl

```bash
# Récupérer la consommation
curl "http://localhost:8181/api/consumption/daily/12345678901234?start=2024-01-01&end=2024-01-31"
```

### Exemple avec Python

```python
import requests
from datetime import date, timedelta

# Configuration
API_URL = "http://localhost:8181/api"
PDL = "12345678901234"

# Récupérer la consommation du mois
end = date.today()
start = end - timedelta(days=30)

response = requests.get(
    f"{API_URL}/consumption/daily/{PDL}",
    params={"start": start.isoformat(), "end": end.isoformat()}
)

data = response.json()
for reading in data["data"]:
    print(f"{reading['date']}: {reading['value_wh'] / 1000:.2f} kWh")
```

---

## Intégration CSV/Excel

Pour une export ponctuel vers CSV ou Excel :

### Export CSV

```bash
# Via API
curl "http://localhost:8181/api/consumption/daily/12345678901234?start=2024-01-01&end=2024-12-31&format=csv" \
  -o consumption_2024.csv
```

### Export via interface

1. Aller dans **Consommation** ou **Production**
2. Sélectionner la période
3. Cliquer sur le bouton **Exporter** (icône téléchargement)
4. Choisir le format (CSV ou Excel)

---

## Contribution

Pour proposer une nouvelle intégration :

1. Forker le dépôt
2. Créer l'exportateur dans `apps/api/src/services/exporters/`
3. Ajouter les tests dans `apps/api/tests/exporters/`
4. Documenter dans `docs/local-client/integrations/`
5. Soumettre une Pull Request

### Guidelines

- Suivre le pattern des exportateurs existants
- Implémenter toutes les méthodes de `BaseExporter`
- Ajouter une gestion d'erreurs robuste
- Documenter la configuration requise
- Fournir des exemples de test
