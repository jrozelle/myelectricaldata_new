"""Tempo Calendar endpoints"""

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

router = APIRouter(prefix="/tempo", tags=["Tempo Calendar"])


@router.get("", response_model=APIResponse)
@router.get("/", response_model=APIResponse, include_in_schema=False)
async def get_tempo_calendar(
    start: str | None = Query(
        None,
        description="Start date (YYYY-MM-DD)",
        openapi_examples={
            "season_start": {"summary": "Start of season", "value": "2024-09-01"},
        },
    ),
    end: str | None = Query(
        None,
        description="End date (YYYY-MM-DD)",
        openapi_examples={
            "season_end": {"summary": "End of season", "value": "2025-08-31"},
        },
    ),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """
    Get Tempo Calendar (public endpoint for client mode sync)

    Returns all Tempo days, optionally filtered by date range.
    Used by client mode to sync tempo data from the server.
    """
    try:
        # Parse dates if provided
        start_dt = None
        end_dt = None

        if start:
            start_dt = datetime.fromisoformat(start).replace(tzinfo=UTC)
        if end:
            end_dt = datetime.fromisoformat(end).replace(tzinfo=UTC)

        # Get data from cache
        tempo_days = await rte_service.get_tempo_days(db, start_dt, end_dt)

        return APIResponse(
            success=True,
            data=[
                {
                    "date": day.id,
                    "color": day.color.value,
                    "updated_at": day.updated_at.isoformat() if day.updated_at else None,
                }
                for day in tempo_days
            ],
        )

    except ValueError as e:
        return APIResponse(success=False, error=ErrorDetail(code="INVALID_DATE", message=f"Invalid date format: {e}"))
    except Exception as e:
        logger.error(f"[TEMPO ERROR] {str(e)}")
        return APIResponse(success=False, error=ErrorDetail(code="SERVER_ERROR", message=str(e)))


@router.get("/days", response_model=APIResponse)
async def get_tempo_days(
    start_date: str | None = Query(
        None,
        description="Start date (YYYY-MM-DD)",
        openapi_examples={
            "current_year": {"summary": "Start of 2024", "value": "2024-01-01"},
            "current_month": {"summary": "Start of October", "value": "2024-10-01"},
        },
    ),
    end_date: str | None = Query(
        None,
        description="End date (YYYY-MM-DD)",
        openapi_examples={
            "current_year": {"summary": "End of 2024", "value": "2024-12-31"},
            "current_month": {"summary": "End of October", "value": "2024-10-31"},
        },
    ),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """
    Get Tempo Calendar days from cache (public endpoint)

    Args:
        start_date: Optional start date (YYYY-MM-DD)
        end_date: Optional end date (YYYY-MM-DD)
    """
    try:
        # Parse dates if provided
        start_dt = None
        end_dt = None

        if start_date:
            start_dt = datetime.fromisoformat(start_date).replace(tzinfo=UTC)
        if end_date:
            end_dt = datetime.fromisoformat(end_date).replace(tzinfo=UTC)

        # Get data from cache
        tempo_days = await rte_service.get_tempo_days(db, start_dt, end_dt)

        return APIResponse(
            success=True,
            data=[
                {
                    "date": day.id,  # Use id (YYYY-MM-DD format) instead of date timestamp
                    "color": day.color.value,
                    "updated_at": day.updated_at.isoformat() if day.updated_at else None,
                    "rte_updated_date": day.rte_updated_date.isoformat() if day.rte_updated_date else None,
                }
                for day in tempo_days
            ],
        )

    except ValueError as e:
        return APIResponse(success=False, error=ErrorDetail(code="INVALID_DATE", message=f"Invalid date format: {e}"))
    except Exception as e:
        logger.error(f"[TEMPO ERROR] {str(e)}")
        return APIResponse(success=False, error=ErrorDetail(code="SERVER_ERROR", message=str(e)))


@router.get("/today", response_model=APIResponse)
async def get_today_tempo(db: AsyncSession = Depends(get_db)) -> APIResponse:
    """Get today's TEMPO color (public endpoint)"""
    try:
        today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        tempo_day = await rte_service.get_tempo_day(db, today)

        if not tempo_day:
            return APIResponse(
                success=False, error=ErrorDetail(code="NOT_FOUND", message="TEMPO data not available for today")
            )

        return APIResponse(
            success=True,
            data={
                "date": tempo_day.id,  # Use id (YYYY-MM-DD format) instead of date timestamp
                "color": tempo_day.color.value,
                "updated_at": tempo_day.updated_at.isoformat() if tempo_day.updated_at else None,
                "rte_updated_date": tempo_day.rte_updated_date.isoformat() if tempo_day.rte_updated_date else None,
            },
        )

    except Exception as e:
        logger.error(f"[TEMPO ERROR] {str(e)}")
        return APIResponse(success=False, error=ErrorDetail(code="SERVER_ERROR", message=str(e)))


@router.get("/week", response_model=APIResponse)
async def get_week_tempo(db: AsyncSession = Depends(get_db)) -> APIResponse:
    """Get last 7 days + tomorrow TEMPO colors from cache (public endpoint)"""
    try:
        # Get last 7 days + tomorrow (including today and historical data)
        today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = today - timedelta(days=6)  # 6 days ago + today = 7 days
        end_date = today + timedelta(days=1)  # Include tomorrow if available

        tempo_days = await rte_service.get_tempo_days(db, start_date, end_date)

        return APIResponse(
            success=True,
            data=[
                {
                    "date": day.id,  # Use id (YYYY-MM-DD format) instead of date timestamp
                    "color": day.color.value,
                    "updated_at": day.updated_at.isoformat() if day.updated_at else None,
                    "rte_updated_date": day.rte_updated_date.isoformat() if day.rte_updated_date else None,
                }
                for day in tempo_days
            ],
        )

    except Exception as e:
        logger.error(f"[TEMPO ERROR] {str(e)}")
        return APIResponse(success=False, error=ErrorDetail(code="SERVER_ERROR", message=str(e)))


@router.post("/refresh", response_model=APIResponse)
async def refresh_tempo_cache(
    current_user: User = Depends(require_action("tempo", "refresh")), db: AsyncSession = Depends(get_db)
) -> APIResponse:
    """
    Manually refresh TEMPO cache

    In server mode: fetches from RTE API
    In client mode: fetches from MyElectricalData gateway

    Required permission: admin.tempo.refresh
    """
    try:
        logger.info(f"[TEMPO] Refreshing cache (user: {current_user.email}, mode: {'CLIENT' if settings.CLIENT_MODE else 'SERVER'})")

        if settings.CLIENT_MODE:
            # Client mode: sync from gateway
            from ..services.sync import SyncService
            sync_service = SyncService(db)
            result = await sync_service.sync_tempo()
            updated_count = result.get("synced", 0)
        else:
            # Server mode: fetch from RTE API
            updated_count = await rte_service.update_tempo_cache(db)

        return APIResponse(
            success=True,
            data={"message": f"Successfully refreshed {updated_count} TEMPO days", "updated_count": updated_count},
        )

    except Exception as e:
        error_msg = str(e)
        logger.error(f"[TEMPO REFRESH ERROR] {error_msg}")
        import traceback

        traceback.print_exc()

        # Provide user-friendly error message for RTE API errors (server mode only)
        if not settings.CLIENT_MODE:
            if "400 Bad Request" in error_msg and "end_date" in error_msg:
                error_msg = "Les données TEMPO ne sont pas disponibles pour ces dates. L'API RTE ne fournit que des données historiques et quelques jours futurs."
            elif "400 Bad Request" in error_msg:
                error_msg = "Erreur lors de la récupération des données RTE. Veuillez réessayer plus tard."

        return APIResponse(success=False, error=ErrorDetail(code="RTE_API_ERROR", message=error_msg))


@router.delete("/clear-all", response_model=APIResponse)
async def clear_all_tempo_data(
    current_user: User = Depends(require_action("tempo", "clear")),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """
    Clear ALL TEMPO data from cache

    Required permission: admin.tempo.clear
    This will delete all TEMPO records and force a full refresh from RTE
    """
    try:
        logger.info(f"[TEMPO] Clearing ALL cache data (admin: {current_user.email})")

        # Import here to avoid circular dependency
        from sqlalchemy import delete
        from ..models import TempoDay

        result = await db.execute(delete(TempoDay))
        deleted_count = result.rowcount
        await db.commit()

        return APIResponse(
            success=True,
            data={"message": f"Successfully deleted all {deleted_count} TEMPO records", "count": deleted_count},
        )

    except Exception as e:
        logger.error(f"[TEMPO CLEAR ALL ERROR] {str(e)}")
        await db.rollback()
        return APIResponse(success=False, error=ErrorDetail(code="SERVER_ERROR", message=str(e)))


@router.get("/forecast", response_model=APIResponse)
async def get_tempo_forecast(
    days: int = Query(
        6,
        ge=1,
        le=6,
        description="Number of days to forecast (1-6)",
        openapi_examples={
            "default": {"summary": "6 days forecast", "value": 6},
            "short": {"summary": "3 days forecast", "value": 3},
        },
    ),
    force_refresh: bool = Query(
        False,
        description="Force refresh from RTE API (ignore cache)",
    ),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """
    Get Tempo forecast for the next N days (public endpoint)

    Returns probability estimates for each color based on:
    - RTE algorithm with calibrated thresholds
    - Historical season data (quotas used/remaining)
    - Consumption forecasts from RTE API (when available)

    The forecast uses the official RTE algorithm:
    - Seuil_Blanc+Rouge = 4 - 0.015 × JourTempo - 0.026 × StockRestant(Blanc+Rouge)
    - Seuil_Rouge = 3.15 - 0.01 × JourTempo - 0.031 × StockRestant(Rouge)

    Note: Results are cached for 4 hours to minimize RTE API calls.

    In client mode, forecasts are fetched from the MyElectricalData gateway
    which has access to RTE APIs.

    Args:
        days: Number of days to forecast (1-6, default: 6)
        force_refresh: If True, bypass cache and fetch fresh data from RTE
    """
    from datetime import date

    # Durée du cache : 4 heures (RTE met à jour les prévisions vers 11h et 19h30)
    CACHE_TTL_SECONDS = 4 * 3600  # 4 heures

    try:
        import json
        from ..services.cache import cache_service

        # Clé de cache basée sur le nombre de jours et la date
        current_date = date.today()
        cache_key = f"tempo:forecast:{current_date.isoformat()}:{days}"

        # Vérifier le cache local (sauf si force_refresh)
        if not force_refresh:
            cached_data = await cache_service.get_raw(cache_key)
            if cached_data:
                logger.info(f"[TEMPO FORECAST] Returning cached data for {days} days")
                return APIResponse(success=True, data=json.loads(cached_data))

        # ══════════════════════════════════════════════════════════════════════
        # MODE CLIENT : Récupérer les prévisions depuis la passerelle
        # La passerelle a accès aux APIs RTE et calcule les prévisions
        # ══════════════════════════════════════════════════════════════════════
        if settings.CLIENT_MODE:
            logger.info(f"[TEMPO FORECAST] Client mode - fetching from gateway (force={force_refresh})")

            from ..adapters.myelectricaldata import get_med_adapter
            adapter = get_med_adapter()

            try:
                response = await adapter.get_tempo_forecast(days=days, force_refresh=force_refresh)

                # La passerelle retourne directement les données au format APIResponse
                if response.get("success") and response.get("data"):
                    response_data = response["data"]

                    # Mettre en cache local pour éviter des appels répétés à la passerelle
                    await cache_service.set_raw(cache_key, json.dumps(response_data), ttl=CACHE_TTL_SECONDS)
                    logger.info(f"[TEMPO FORECAST] Cached gateway forecast for {days} days")

                    return APIResponse(success=True, data=response_data)
                else:
                    error_msg = response.get("error", {}).get("message", "Erreur inconnue de la passerelle")
                    return APIResponse(
                        success=False,
                        error=ErrorDetail(code="GATEWAY_ERROR", message=error_msg)
                    )

            except Exception as e:
                logger.error(f"[TEMPO FORECAST] Gateway error: {e}")
                return APIResponse(
                    success=False,
                    error=ErrorDetail(
                        code="GATEWAY_UNAVAILABLE",
                        message=f"Impossible de récupérer les prévisions depuis la passerelle : {e}"
                    )
                )

        # ══════════════════════════════════════════════════════════════════════
        # MODE SERVEUR : Calculer les prévisions localement avec les APIs RTE
        # ══════════════════════════════════════════════════════════════════════
        from ..services.tempo_forecast import tempo_forecast_service

        logger.info(f"[TEMPO FORECAST] Server mode - fetching from RTE API (force={force_refresh})")

        # Récupérer les statistiques de la saison en cours
        today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

        # Déterminer la saison en cours
        if current_date.month >= 9:
            season_start = datetime(current_date.year, 9, 1, tzinfo=UTC)
        else:
            season_start = datetime(current_date.year - 1, 9, 1, tzinfo=UTC)

        # Récupérer les jours Tempo de la saison
        tempo_days = await rte_service.get_tempo_days(db, season_start, today)

        # Compter les jours par couleur
        blue_used = sum(1 for d in tempo_days if d.color.value == "BLUE")
        white_used = sum(1 for d in tempo_days if d.color.value == "WHITE")
        red_used = sum(1 for d in tempo_days if d.color.value == "RED")

        logger.info(
            f"[TEMPO FORECAST] Season stats - Blue: {blue_used}/300, "
            f"White: {white_used}/43, Red: {red_used}/22"
        )

        # Générer les prévisions
        forecasts = await tempo_forecast_service.get_forecasts(
            days_ahead=days,
            blue_used=blue_used,
            white_used=white_used,
            red_used=red_used,
            reference_date=current_date,
        )

        # Construire les données de réponse
        response_data = {
            "season": f"{season_start.year}/{season_start.year + 1}",
            "season_stats": {
                "blue_used": blue_used,
                "blue_remaining": 300 - blue_used,
                "white_used": white_used,
                "white_remaining": 43 - white_used,
                "red_used": red_used,
                "red_remaining": 22 - red_used,
            },
            "forecasts": [
                {
                    "date": f.date,
                    "day_in_season": f.day_in_season,
                    "probability_blue": f.probability_blue,
                    "probability_white": f.probability_white,
                    "probability_red": f.probability_red,
                    "most_likely": f.most_likely,
                    "confidence": f.confidence,
                    "threshold_white_red": f.threshold_white_red,
                    "threshold_red": f.threshold_red,
                    "normalized_consumption": f.normalized_consumption,
                    "forecast_type": f.forecast_type,
                    "factors": f.factors,
                }
                for f in forecasts
            ],
            "algorithm_info": {
                "description": "Algorithme basé sur les seuils RTE officiels",
                "params_blanc_rouge": {"A": 4.0, "B": 0.015, "C": 0.026},
                "params_rouge": {"A": 3.15, "B": 0.01, "C": 0.031},
                "formula_blanc_rouge": "Seuil = A - B × JourTempo - C × StockRestant(Blanc+Rouge)",
                "formula_rouge": "Seuil = A' - B' × JourTempo - C' × StockRestant(Rouge)",
            },
            "cached_at": datetime.now(UTC).isoformat(),
            "cache_ttl_hours": CACHE_TTL_SECONDS // 3600,
        }

        # Sauvegarder dans le cache
        await cache_service.set_raw(cache_key, json.dumps(response_data), ttl=CACHE_TTL_SECONDS)
        logger.info(f"[TEMPO FORECAST] Cached forecast for {days} days (TTL: {CACHE_TTL_SECONDS // 3600}h)")

        return APIResponse(success=True, data=response_data)

    except Exception as e:
        logger.error(f"[TEMPO FORECAST ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return APIResponse(success=False, error=ErrorDetail(code="FORECAST_ERROR", message=str(e)))


@router.delete("/clear-old", response_model=APIResponse)
async def clear_old_tempo_data(
    days_to_keep: int = Query(
        30,
        ge=7,
        description="Number of days to keep (minimum 7)",
        openapi_examples={
            "default": {"summary": "Keep 30 days", "value": 30},
            "minimum": {"summary": "Keep 7 days (minimum)", "value": 7},
            "extended": {"summary": "Keep 90 days", "value": 90},
        },
    ),
    current_user: User = Depends(require_action("tempo", "clear")),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """
    Clear old TEMPO data from cache

    Required permission: admin.tempo.clear
    Args:
        days_to_keep: Keep data from last N days (default: 30, min: 7)
    """

    # Minimum 7 days
    days_to_keep = max(days_to_keep, 7)

    try:
        logger.info(f"[TEMPO] Clearing data older than {days_to_keep} days (admin: {current_user.email})")
        deleted_count = await rte_service.clear_old_data(db, days_to_keep)

        return APIResponse(
            success=True,
            data={"message": f"Successfully deleted {deleted_count} old TEMPO records", "count": deleted_count},
        )

    except Exception as e:
        logger.error(f"[TEMPO CLEAR ERROR] {str(e)}")
        return APIResponse(success=False, error=ErrorDetail(code="SERVER_ERROR", message=str(e)))
