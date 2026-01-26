"""
Consumption France endpoints - Consommation électrique nationale

Supports both server mode (direct RTE API) and client mode (via gateway).
"""

import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..middleware import require_action
from ..models import User
from ..models.database import get_db
from ..schemas import APIResponse, ErrorDetail
from ..services.rte import rte_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/consumption-france", tags=["Consumption France"])


@router.get("", response_model=APIResponse)
@router.get("/", response_model=APIResponse, include_in_schema=False)
async def get_consumption_france(
    type: str | None = Query(
        None,
        description="Type de données (REALISED, ID, D-1, D-2)",
        openapi_examples={
            "realised": {"summary": "Consommation réalisée", "value": "REALISED"},
            "d-1": {"summary": "Prévision J-1", "value": "D-1"},
            "intraday": {"summary": "Prévision intraday", "value": "ID"},
        },
    ),
    start_date: str | None = Query(
        None,
        description="Date de début (YYYY-MM-DD ou ISO 8601)",
        openapi_examples={
            "today": {"summary": "Aujourd'hui", "value": "2024-01-15"},
        },
    ),
    end_date: str | None = Query(
        None,
        description="Date de fin (YYYY-MM-DD ou ISO 8601)",
        openapi_examples={
            "tomorrow": {"summary": "Demain", "value": "2024-01-16"},
        },
    ),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """
    Récupérer les données de consommation électrique nationale française.

    Types de données disponibles :
    - **REALISED** : Consommation réalisée (temps réel)
    - **ID** : Prévision intraday (mise à jour toutes les heures)
    - **D-1** : Prévision pour le lendemain (disponible vers 19h30)
    - **D-2** : Prévision pour J+2 (disponible vers 7h)

    Les données sont en MW et représentent la consommation totale France métropolitaine.
    """
    try:
        # Parser les dates si fournies
        start_dt = None
        end_dt = None

        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=UTC)

        if end_date:
            end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=UTC)

        # Par défaut : dernières 24h + prochaines 24h
        if not start_dt:
            start_dt = datetime.now(UTC) - timedelta(days=1)
        if not end_dt:
            end_dt = datetime.now(UTC) + timedelta(days=1)

        # Récupérer les données depuis le cache
        consumption_data = await rte_service.get_consumption_france(
            db,
            consumption_type=type,
            start_date=start_dt,
            end_date=end_dt,
        )

        # Grouper par type
        data_by_type: dict[str, list] = {}
        for record in consumption_data:
            if record.type not in data_by_type:
                data_by_type[record.type] = []
            data_by_type[record.type].append(
                {
                    "start_date": record.start_date.isoformat() if record.start_date else None,
                    "end_date": record.end_date.isoformat() if record.end_date else None,
                    "value": record.value,
                    "updated_date": record.updated_date.isoformat() if record.updated_date else None,
                }
            )

        return APIResponse(
            success=True,
            data={
                "short_term": [
                    {
                        "type": data_type,
                        "values": values,
                    }
                    for data_type, values in data_by_type.items()
                ],
                "period": {
                    "start": start_dt.isoformat(),
                    "end": end_dt.isoformat(),
                },
            },
        )

    except ValueError as e:
        return APIResponse(success=False, error=ErrorDetail(code="INVALID_DATE", message=f"Format de date invalide: {e}"))
    except Exception as e:
        logger.error(f"[CONSUMPTION FRANCE ERROR] {str(e)}")
        return APIResponse(success=False, error=ErrorDetail(code="SERVER_ERROR", message=str(e)))


@router.get("/current", response_model=APIResponse)
async def get_current_consumption(
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """
    Récupérer la consommation actuelle (dernière valeur réalisée).

    Retourne la dernière valeur de consommation réalisée disponible.
    """
    try:
        # Récupérer les données réalisées des dernières 2 heures
        now = datetime.now(UTC)
        start_dt = now - timedelta(hours=2)

        consumption_data = await rte_service.get_consumption_france(
            db,
            consumption_type="REALISED",
            start_date=start_dt,
            end_date=now,
        )

        if not consumption_data:
            return APIResponse(
                success=False,
                error=ErrorDetail(code="NOT_FOUND", message="Aucune donnée de consommation disponible"),
            )

        # Prendre la dernière valeur
        latest = consumption_data[-1]

        return APIResponse(
            success=True,
            data={
                "start_date": latest.start_date.isoformat() if latest.start_date else None,
                "end_date": latest.end_date.isoformat() if latest.end_date else None,
                "value": latest.value,
                "unit": "MW",
                "updated_date": latest.updated_date.isoformat() if latest.updated_date else None,
            },
        )

    except Exception as e:
        logger.error(f"[CONSUMPTION FRANCE CURRENT ERROR] {str(e)}")
        return APIResponse(success=False, error=ErrorDetail(code="SERVER_ERROR", message=str(e)))


@router.get("/forecast", response_model=APIResponse)
async def get_consumption_forecast(
    days: int = Query(
        2,
        ge=1,
        le=7,
        description="Nombre de jours de prévision (1-7)",
    ),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """
    Récupérer les prévisions de consommation nationale.

    Retourne les prévisions D-1 et D-2 pour les prochains jours.
    """
    try:
        now = datetime.now(UTC)
        end_dt = now + timedelta(days=days)

        # Récupérer les prévisions
        forecast_data = await rte_service.get_consumption_france(
            db,
            start_date=now,
            end_date=end_dt,
        )

        # Filtrer pour ne garder que les prévisions (pas REALISED)
        forecasts = [r for r in forecast_data if r.type != "REALISED"]

        # Grouper par type
        data_by_type: dict[str, list] = {}
        for record in forecasts:
            if record.type not in data_by_type:
                data_by_type[record.type] = []
            data_by_type[record.type].append(
                {
                    "start_date": record.start_date.isoformat() if record.start_date else None,
                    "end_date": record.end_date.isoformat() if record.end_date else None,
                    "value": record.value,
                    "updated_date": record.updated_date.isoformat() if record.updated_date else None,
                }
            )

        return APIResponse(
            success=True,
            data={
                "forecasts": [
                    {
                        "type": data_type,
                        "values": values,
                    }
                    for data_type, values in data_by_type.items()
                ],
                "period": {
                    "start": now.isoformat(),
                    "end": end_dt.isoformat(),
                },
            },
        )

    except Exception as e:
        logger.error(f"[CONSUMPTION FRANCE FORECAST ERROR] {str(e)}")
        return APIResponse(success=False, error=ErrorDetail(code="SERVER_ERROR", message=str(e)))


@router.post("/refresh", response_model=APIResponse)
async def refresh_consumption_cache(
    current_user: User = Depends(require_action("consumption_france", "refresh")),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """
    Actualiser manuellement le cache de consommation nationale.

    In server mode: fetches from RTE API
    In client mode: fetches from MyElectricalData gateway

    Permission requise : admin.consumption_france.refresh
    """
    try:
        logger.info(f"[CONSUMPTION FRANCE] Refreshing cache (user: {current_user.email}, mode: {'CLIENT' if settings.CLIENT_MODE else 'SERVER'})")

        if settings.CLIENT_MODE:
            # Client mode: sync from gateway
            from ..services.sync import SyncService
            sync_service = SyncService(db)
            result = await sync_service.sync_consumption_france()
            updated_count = result.get("created", 0) + result.get("updated", 0)
        else:
            # Server mode: fetch from RTE API
            updated_count = await rte_service.update_consumption_france_cache(db)

        return APIResponse(
            success=True,
            data={
                "message": f"Cache actualisé avec succès : {updated_count} enregistrements",
                "updated_count": updated_count,
            },
        )

    except Exception as e:
        error_msg = str(e)
        logger.error(f"[CONSUMPTION FRANCE REFRESH ERROR] {error_msg}")
        return APIResponse(success=False, error=ErrorDetail(code="RTE_API_ERROR", message=error_msg))
