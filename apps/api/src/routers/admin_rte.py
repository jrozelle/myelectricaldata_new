"""
Administration des API RTE

Ce module fournit des endpoints pour tester et monitorer les 4 API RTE :
- Tempo Calendar : Calendrier des jours Tempo
- EcoWatt : Signaux de tension du réseau
- Consumption : Prévisions de consommation nationale
- Generation Forecast : Prévisions de production (solaire, éolien)
"""

from datetime import datetime, date, timedelta, UTC
from typing import Any
import logging
import httpx

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User
from ..models.database import get_db
from ..middleware import require_permission
from ..schemas import APIResponse, ErrorDetail
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/rte", tags=["Admin - RTE APIs"])

# Configuration des API RTE
RTE_APIS = {
    "tempo": {
        "name": "Tempo Calendar",
        "description": "Calendrier des jours Tempo EDF (Bleu, Blanc, Rouge)",
        "endpoint": "/open_api/tempo_like_supply_contract/v1/tempo_like_calendars",
        "doc_url": "https://data.rte-france.com/catalog/-/api/consumption/Tempo-Like-Supply-Contract/v1.1",
    },
    "ecowatt": {
        "name": "EcoWatt Signals",
        "description": "Signaux de tension du réseau électrique français",
        "endpoint": "/open_api/ecowatt/v5/signals",
        "doc_url": "https://data.rte-france.com/catalog/-/api/consumption/Ecowatt/v5.0",
    },
    "consumption": {
        "name": "Consumption Forecast",
        "description": "Prévisions de consommation électrique nationale",
        "endpoint": "/open_api/consumption/v1/short_term",
        "doc_url": "https://data.rte-france.com/catalog/-/api/consumption/Consumption/v1.2",
    },
    "generation": {
        "name": "Generation Forecast",
        "description": "Prévisions de production (solaire, éolien)",
        "endpoint": "/open_api/generation_forecast/v3/forecasts",
        "doc_url": "https://data.rte-france.com/catalog/-/api/generation/Generation-Forecast/v3.0",
    },
}


async def _get_rte_token() -> str | None:
    """Obtenir un token OAuth2 pour les API RTE"""
    import base64

    if not settings.RTE_CLIENT_ID or not settings.RTE_CLIENT_SECRET:
        return None

    credentials = f"{settings.RTE_CLIENT_ID}:{settings.RTE_CLIENT_SECRET}"
    encoded = base64.b64encode(credentials.encode()).decode()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.RTE_BASE_URL}/token/oauth/",
            headers={
                "Authorization": f"Basic {encoded}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials"},
        )

        if response.status_code == 200:
            return response.json().get("access_token")
        return None


async def _test_rte_api(
    api_key: str,
    token: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Tester une API RTE spécifique

    Returns:
        Dict avec status, response_time, data ou error
    """
    api_config = RTE_APIS.get(api_key)
    if not api_config:
        return {"status": "error", "error": f"API inconnue: {api_key}"}

    url = f"{settings.RTE_BASE_URL}{api_config['endpoint']}"
    start_time = datetime.now(UTC)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                url,
                params=params,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
            )

        response_time = (datetime.now(UTC) - start_time).total_seconds() * 1000

        result: dict[str, Any] = {
            "api": api_key,
            "name": api_config["name"],
            "status_code": response.status_code,
            "response_time_ms": round(response_time, 2),
        }

        if response.status_code == 200:
            result["status"] = "ok"
            data = response.json()
            # Extraire un résumé des données selon l'API
            result["summary"] = _extract_api_summary(api_key, data)
            result["data"] = data
        elif response.status_code == 403:
            result["status"] = "forbidden"
            result["error"] = "API non activée dans votre compte RTE"
            result["help"] = f"Activez cette API sur {api_config['doc_url']}"
        elif response.status_code == 429:
            result["status"] = "rate_limited"
            result["error"] = "Trop de requêtes - rate limit atteint"
        elif response.status_code >= 500:
            result["status"] = "server_error"
            result["error"] = f"Erreur serveur RTE ({response.status_code})"
            try:
                error_data = response.json()
                result["error_details"] = error_data
            except Exception:
                result["error_details"] = response.text[:500]
        else:
            result["status"] = "error"
            result["error"] = f"Erreur HTTP {response.status_code}"
            try:
                result["error_details"] = response.json()
            except Exception:
                result["error_details"] = response.text[:500]

        return result

    except httpx.TimeoutException:
        return {
            "api": api_key,
            "name": api_config["name"],
            "status": "timeout",
            "error": "Timeout après 30 secondes",
        }
    except Exception as e:
        return {
            "api": api_key,
            "name": api_config["name"],
            "status": "error",
            "error": str(e),
        }


def _extract_api_summary(api_key: str, data: dict[str, Any]) -> dict[str, Any]:
    """Extraire un résumé des données selon l'API"""
    summary: dict[str, Any] = {}

    if api_key == "tempo":
        calendars = data.get("tempo_like_calendars", {})
        values = calendars.get("values", [])
        summary["total_days"] = len(values)
        if values:
            # Compter les couleurs
            colors = {"BLUE": 0, "WHITE": 0, "RED": 0}
            for day in values:
                color = day.get("value")
                if color in colors:
                    colors[color] += 1
            summary["colors"] = colors
            # Dernière date
            summary["latest_date"] = values[-1].get("start_date", "")[:10] if values else None

    elif api_key == "ecowatt":
        signals = data.get("signals", [])
        summary["total_signals"] = len(signals)
        if signals:
            summary["latest_date"] = signals[0].get("jour", "")[:10]
            summary["latest_dvalue"] = signals[0].get("dvalue")

    elif api_key == "consumption":
        short_term = data.get("short_term", [])
        summary["forecast_count"] = len(short_term)
        if short_term:
            values = short_term[0].get("values", [])
            summary["values_count"] = len(values)
            if values:
                # Calculer min/max consommation (en MW)
                consumptions = [v.get("value", 0) for v in values]
                summary["min_mw"] = min(consumptions)
                summary["max_mw"] = max(consumptions)
                summary["avg_mw"] = round(sum(consumptions) / len(consumptions))

    elif api_key == "generation":
        forecasts = data.get("forecasts", [])
        summary["forecast_count"] = len(forecasts)
        by_type: dict[str, int] = {}
        for f in forecasts:
            prod_type = f.get("production_type", "unknown")
            by_type[prod_type] = by_type.get(prod_type, 0) + 1
        summary["by_production_type"] = by_type

    return summary


@router.get("/status", response_model=APIResponse)
async def get_rte_status(
    current_user: User = Depends(require_permission("admin_dashboard")),
) -> APIResponse:
    """
    Obtenir le statut de la configuration RTE

    Vérifie si les credentials RTE sont configurés.
    """
    has_credentials = bool(settings.RTE_CLIENT_ID and settings.RTE_CLIENT_SECRET)

    return APIResponse(
        success=True,
        data={
            "has_credentials": has_credentials,
            "base_url": settings.RTE_BASE_URL,
            "client_id_configured": bool(settings.RTE_CLIENT_ID),
            "client_secret_configured": bool(settings.RTE_CLIENT_SECRET),
            "apis": {
                key: {
                    "name": api["name"],
                    "description": api["description"],
                    "doc_url": api["doc_url"],
                }
                for key, api in RTE_APIS.items()
            },
        },
    )


@router.get("/test", response_model=APIResponse)
async def test_all_rte_apis(
    current_user: User = Depends(require_permission("admin_dashboard")),
) -> APIResponse:
    """
    Tester toutes les API RTE

    Effectue un test de connexion à chaque API RTE et retourne le statut.
    """
    # Vérifier les credentials
    if not settings.RTE_CLIENT_ID or not settings.RTE_CLIENT_SECRET:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="NO_RTE_CREDENTIALS",
                message="Les credentials RTE ne sont pas configurés (RTE_CLIENT_ID, RTE_CLIENT_SECRET)",
            ),
        )

    # Obtenir le token
    token = await _get_rte_token()
    if not token:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="AUTH_FAILED",
                message="Impossible d'obtenir un token RTE. Vérifiez vos credentials.",
            ),
        )

    # Tester chaque API
    results: dict[str, Any] = {}
    today = date.today()
    tomorrow = today + timedelta(days=1)

    # Tempo - pas de paramètres nécessaires
    results["tempo"] = await _test_rte_api("tempo", token)

    # EcoWatt - pas de paramètres nécessaires
    results["ecowatt"] = await _test_rte_api("ecowatt", token)

    # Consumption - avec dates
    from zoneinfo import ZoneInfo
    paris_tz = ZoneInfo("Europe/Paris")
    start_dt = datetime.combine(tomorrow, datetime.min.time()).replace(tzinfo=paris_tz)
    end_dt = datetime.combine(tomorrow + timedelta(days=1), datetime.min.time()).replace(tzinfo=paris_tz)

    results["consumption"] = await _test_rte_api(
        "consumption",
        token,
        params={
            "type": "D-1",
            "start_date": start_dt.isoformat(),
            "end_date": end_dt.isoformat(),
        },
    )

    # Generation Forecast - Solar
    results["generation_solar"] = await _test_rte_api(
        "generation",
        token,
        params={
            "production_type": "SOLAR",
            "type": "D-1",
            "start_date": start_dt.isoformat(),
            "end_date": end_dt.isoformat(),
        },
    )

    # Generation Forecast - Wind (v3 utilise WIND_ONSHORE)
    results["generation_wind"] = await _test_rte_api(
        "generation",
        token,
        params={
            "production_type": "WIND_ONSHORE",
            "type": "D-1",
            "start_date": start_dt.isoformat(),
            "end_date": end_dt.isoformat(),
        },
    )

    # Calculer le résumé global
    ok_count = sum(1 for r in results.values() if r.get("status") == "ok")
    total_count = len(results)

    return APIResponse(
        success=True,
        data={
            "summary": {
                "total_apis": total_count,
                "apis_ok": ok_count,
                "apis_failed": total_count - ok_count,
                "all_ok": ok_count == total_count,
            },
            "results": results,
            "tested_at": datetime.now(UTC).isoformat(),
        },
    )


@router.get("/test/{api_key}", response_model=APIResponse)
async def test_single_rte_api(
    api_key: str,
    current_user: User = Depends(require_permission("admin_dashboard")),
) -> APIResponse:
    """
    Tester une API RTE spécifique

    Args:
        api_key: Identifiant de l'API (tempo, ecowatt, consumption, generation)
    """
    if api_key not in RTE_APIS and api_key not in ["generation_solar", "generation_wind"]:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="INVALID_API",
                message=f"API inconnue: {api_key}. APIs disponibles: {', '.join(RTE_APIS.keys())}",
            ),
        )

    # Vérifier les credentials
    if not settings.RTE_CLIENT_ID or not settings.RTE_CLIENT_SECRET:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="NO_RTE_CREDENTIALS",
                message="Les credentials RTE ne sont pas configurés",
            ),
        )

    # Obtenir le token
    token = await _get_rte_token()
    if not token:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="AUTH_FAILED",
                message="Impossible d'obtenir un token RTE",
            ),
        )

    # Préparer les paramètres selon l'API
    params = None
    actual_api_key = api_key

    if api_key in ["consumption", "generation", "generation_solar", "generation_wind"]:
        from zoneinfo import ZoneInfo
        paris_tz = ZoneInfo("Europe/Paris")
        today = date.today()
        tomorrow = today + timedelta(days=1)
        start_dt = datetime.combine(tomorrow, datetime.min.time()).replace(tzinfo=paris_tz)
        end_dt = datetime.combine(tomorrow + timedelta(days=1), datetime.min.time()).replace(tzinfo=paris_tz)

        if api_key == "consumption":
            params = {
                "type": "D-1",
                "start_date": start_dt.isoformat(),
                "end_date": end_dt.isoformat(),
            }
        elif api_key in ["generation", "generation_solar"]:
            actual_api_key = "generation"
            params = {
                "production_type": "SOLAR",
                "type": "D-1",
                "start_date": start_dt.isoformat(),
                "end_date": end_dt.isoformat(),
            }
        elif api_key == "generation_wind":
            actual_api_key = "generation"
            params = {
                "production_type": "WIND_ONSHORE",
                "type": "D-1",
                "start_date": start_dt.isoformat(),
                "end_date": end_dt.isoformat(),
            }

    result = await _test_rte_api(actual_api_key, token, params)

    return APIResponse(
        success=result.get("status") == "ok",
        data=result if result.get("status") == "ok" else None,
        error=ErrorDetail(
            code=result.get("status", "error").upper(),
            message=result.get("error", "Erreur inconnue"),
        ) if result.get("status") != "ok" else None,
    )


@router.post("/refresh/tempo", response_model=APIResponse)
async def refresh_tempo_cache(
    current_user: User = Depends(require_permission("admin.tempo.refresh")),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """
    Rafraîchir le cache Tempo depuis l'API RTE

    Récupère les derniers jours Tempo et met à jour la base de données.
    """
    from ..services.rte import rte_service

    try:
        updated_count = await rte_service.update_tempo_cache(db)

        return APIResponse(
            success=True,
            data={
                "message": f"Cache Tempo mis à jour avec {updated_count} jours",
                "updated_count": updated_count,
            },
        )
    except Exception as e:
        logger.error(f"[RTE ADMIN] Erreur refresh Tempo: {e}")
        return APIResponse(
            success=False,
            error=ErrorDetail(code="REFRESH_ERROR", message=str(e)),
        )


@router.post("/refresh/ecowatt", response_model=APIResponse)
async def refresh_ecowatt_cache(
    current_user: User = Depends(require_permission("admin.ecowatt.refresh")),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """
    Rafraîchir le cache EcoWatt depuis l'API RTE

    Récupère les derniers signaux EcoWatt et met à jour la base de données.
    """
    from ..services.rte import rte_service

    try:
        updated_count = await rte_service.update_ecowatt_cache(db)

        return APIResponse(
            success=True,
            data={
                "message": f"Cache EcoWatt mis à jour avec {updated_count} signaux",
                "updated_count": updated_count,
            },
        )
    except Exception as e:
        logger.error(f"[RTE ADMIN] Erreur refresh EcoWatt: {e}")
        return APIResponse(
            success=False,
            error=ErrorDetail(code="REFRESH_ERROR", message=str(e)),
        )
