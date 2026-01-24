# Intégrations

Le mode client de MyElectricalData supporte l'export vers plusieurs plateformes domotiques et de monitoring.

## Destinations disponibles

| Destination | Type | Description |
|-------------|------|-------------|
| [Home Assistant](./home-assistant.md) | Domotique | Plateforme domotique open-source |
| [MQTT](./mqtt.md) | Protocole | Broker de messages IoT |
| [VictoriaMetrics](./victoriametrics.md) | Time-series DB | Base de données métriques |
| [Jeedom](./jeedom.md) | Domotique | Solution domotique française |

## Architecture commune

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        FLUX D'EXPORT                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────────┐               │
│  │ PostgreSQL  │────▶│ Exporter    │────▶│ Destination     │               │
│  │ (données)   │     │ Service     │     │ (HA/MQTT/VM/JD) │               │
│  └─────────────┘     └─────────────┘     └─────────────────┘               │
│                            │                                                │
│                            ▼                                                │
│                      ┌─────────────┐                                        │
│                      │ Export Logs │                                        │
│                      └─────────────┘                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Données exportables

| Donnée | Format | Fréquence |
|--------|--------|-----------|
| Consommation journalière | Wh / kWh | Quotidien |
| Consommation mensuelle | Wh / kWh | Quotidien |
| Production journalière | Wh / kWh | Quotidien |
| Tempo couleur | BLEU/BLANC/ROUGE | Quotidien |
| Tempo J+1 | BLEU/BLANC/ROUGE | Quotidien (après 11h) |
| EcoWatt niveau | 1/2/3 | Horaire |

## Configuration commune

Toutes les intégrations partagent les paramètres suivants :

```bash
# Activer/désactiver l'export automatique
{DESTINATION}_ENABLED=true

# Intervalle d'export en minutes (défaut: 60)
{DESTINATION}_INTERVAL=60

# Données à exporter (liste séparée par virgules)
{DESTINATION}_EXPORT_DATA=consumption_daily,production_daily,tempo,ecowatt
```

## Test de connexion

Chaque intégration peut être testée avant activation :

```bash
# Via API
curl -X POST http://localhost:8181/api/export/configs/{destination}/test

# Via CLI
docker compose -f docker-compose.client.yml exec backend-client \
  python -m scripts.test_export --destination home_assistant
```

## Logs et debugging

```bash
# Voir les logs d'export
docker compose -f docker-compose.client.yml logs backend-client | grep export

# Historique des exports en base
docker compose -f docker-compose.client.yml exec postgres-client \
  psql -U client -c "SELECT * FROM export_logs ORDER BY started_at DESC LIMIT 10;"
```
