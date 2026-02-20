"""Enedis-like router for Client Mode

This router provides the same endpoints as the server mode's enedis router,
but uses a "local-first" strategy:
1. Check PostgreSQL for cached data
2. Identify missing date ranges
3. Only fetch missing data from MyElectricalData gateway
4. Combine and return results

This dramatically reduces API calls to the gateway while ensuring
the frontend can use the same API calls in both modes.
"""

import logging
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..adapters.myelectricaldata import get_med_adapter
from ..middleware import get_current_user
from ..models import PDL, User
from ..models.database import get_db
from ..schemas import APIResponse, ErrorDetail
from ..services.local_data import (
    LocalDataService,
    format_daily_response,
    format_detail_response,
)

logger = logging.getLogger(__name__)

# Lightweight in-process caches to avoid hammering remote gateway
_POWER_CACHE_TTL = timedelta(hours=6)
_DETAIL_CHUNK_BACKOFF_TTL = timedelta(hours=12)
_power_cache: dict[str, tuple[datetime, dict]] = {}
_detail_chunk_backoff: dict[str, datetime] = {}

router = APIRouter(
    prefix="/enedis",
    tags=["Enedis Data (via Gateway)"],
    responses={
        401: {"description": "Unauthorized - Invalid or missing authentication"},
        403: {"description": "Forbidden - PDL does not belong to user"},
    },
)


async def verify_pdl_ownership(usage_point_id: str, user: User, db: AsyncSession) -> bool:
    """Verify that the PDL belongs to the current user and is active"""
    result = await db.execute(
        select(PDL).where(
            PDL.user_id == user.id,
            PDL.usage_point_id == usage_point_id,
            PDL.is_active == True  # noqa: E712
        )
    )
    pdl = result.scalar_one_or_none()
    return pdl is not None


def extract_gateway_data(response: dict) -> dict:
    """Extract data from gateway response.

    The gateway returns {"success": true, "data": {...}, ...}
    We need to extract just the inner "data" part to avoid double wrapping.
    """
    if isinstance(response, dict) and "data" in response:
        return response["data"]
    return response


def parse_date(date_str: str) -> date:
    """Parse date string to date object."""
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def extract_readings_from_response(response: dict) -> list[dict]:
    """Extract interval_reading from gateway response."""
    if not response:
        return []

    # Try different response structures
    meter_reading = response.get("meter_reading", {})
    if not meter_reading and "data" in response:
        data = response.get("data")
        if isinstance(data, dict):
            meter_reading = data.get("meter_reading", {})

    if not isinstance(meter_reading, dict):
        return []

    interval_reading = meter_reading.get("interval_reading", [])
    return interval_reading if isinstance(interval_reading, list) else []


def _extract_day(date_str: str) -> str:
    """Extract YYYY-MM-DD from reading date string."""
    if not date_str:
        return ""
    if "T" in date_str:
        return date_str.split("T", 1)[0][:10]
    if " " in date_str:
        return date_str.split(" ", 1)[0][:10]
    return date_str[:10]


def _merge_daily_readings(readings: list[dict]) -> list[dict]:
    """Deduplicate daily readings by date (keep highest value)."""
    by_day: dict[str, dict] = {}
    for reading in readings:
        day = _extract_day(str(reading.get("date", "")))
        if not day:
            continue
        try:
            value = int(float(reading.get("value", 0)))
        except (TypeError, ValueError):
            value = 0

        current = by_day.get(day)
        if current is None or value >= int(float(current.get("value", 0))):
            by_day[day] = {"date": day, "value": value}

    return [by_day[d] for d in sorted(by_day.keys())]


def _extract_day_and_time(date_str: str) -> tuple[str, str]:
    """Extract YYYY-MM-DD and HH:MM from a reading date string."""
    if not date_str:
        return "", "00:00"

    if "T" in date_str:
        day_part, time_part = date_str.split("T", 1)
    elif " " in date_str:
        day_part, time_part = date_str.split(" ", 1)
    else:
        return date_str[:10], "00:00"

    # Keep only HH:MM and ignore seconds/timezone suffixes.
    hhmm = time_part[:5] if len(time_part) >= 5 else "00:00"
    return day_part[:10], hhmm


def _format_power_response(
    usage_point_id: str,
    start: str,
    end: str,
    readings: list[dict],
    from_cache: bool = False,
) -> dict:
    """Format max-power payload in Enedis-compatible shape."""
    return {
        "meter_reading": {
            "usage_point_id": usage_point_id,
            "start": start,
            "end": end,
            "reading_type": {
                "unit": "W",
                "measurement_kind": "power",
                "aggregate": "maximum",
            },
            "interval_reading": readings,
        },
        "_from_local_cache": from_cache,
    }


def _merge_power_interval_readings(readings: list[dict]) -> list[dict]:
    """Deduplicate power readings by day, keeping the highest daily value."""
    by_day: dict[str, tuple[int, str]] = {}

    for reading in readings:
        day, hhmm = _extract_day_and_time(str(reading.get("date", "")))
        if not day:
            continue

        try:
            value = int(float(reading.get("value", 0)))
        except (TypeError, ValueError):
            value = 0

        current = by_day.get(day)
        if current is None or value > current[0] or (value == current[0] and hhmm > current[1]):
            by_day[day] = (value, hhmm)

    merged: list[dict] = []
    for day in sorted(by_day.keys()):
        value, hhmm = by_day[day]
        merged.append(
            {
                "date": f"{day} {hhmm}:00",
                "value": value,
            }
        )
    return merged


async def _get_power_data_local_first(
    db: AsyncSession,
    usage_point_id: str,
    start: str,
    end: str,
    start_date: date,
    end_date: date,
    use_cache: bool,
) -> dict:
    """Get max power with local-first strategy on dedicated max_power_data cache."""
    cache_key = f"{usage_point_id}:{start}:{end}"
    now = datetime.now()

    if use_cache:
        cached = _power_cache.get(cache_key)
        if cached and cached[0] > now:
            return cached[1]

    if use_cache:
        local_service = LocalDataService(db)
        local_readings, missing_ranges = await local_service.get_consumption_max_power(
            usage_point_id=usage_point_id,
            start_date=start_date,
            end_date=end_date,
        )

        if not missing_ranges:
            payload = _format_power_response(
                usage_point_id=usage_point_id,
                start=start,
                end=end,
                readings=_merge_power_interval_readings(local_readings),
                from_cache=True,
            )
            _power_cache[cache_key] = (now + _POWER_CACHE_TTL, payload)
            return payload

        # Fill only missing day-ranges from gateway to limit remote calls.
        all_readings = list(local_readings)
        adapter = get_med_adapter()
        for range_start, range_end in missing_ranges:
            try:
                response = await adapter.get_consumption_max_power(
                    usage_point_id,
                    range_start.isoformat(),
                    range_end.isoformat(),
                )
                remote_data = extract_gateway_data(response)
                remote_readings = extract_readings_from_response(remote_data)
                all_readings.extend(remote_readings)
                await local_service.save_consumption_max_power(usage_point_id, remote_data)
            except Exception as exc:
                logger.warning(
                    f"[{usage_point_id}] Failed to fetch max power for missing range "
                    f"{range_start} -> {range_end}: {exc}"
                )

        # Rebuild from DB for canonical values after upsert.
        refreshed_local, _ = await local_service.get_consumption_max_power(
            usage_point_id=usage_point_id,
            start_date=start_date,
            end_date=end_date,
        )
        source_readings = refreshed_local if refreshed_local else all_readings
        merged = _merge_power_interval_readings(source_readings)
        combined = _format_power_response(
            usage_point_id=usage_point_id,
            start=start,
            end=end,
            readings=merged,
            from_cache=False,
        )
        _power_cache[cache_key] = (now + _POWER_CACHE_TTL, combined)
        return combined

    # Direct gateway fetch when cache/local strategy is disabled.
    adapter = get_med_adapter()
    response = await adapter.get_consumption_max_power(usage_point_id, start, end)
    data = extract_gateway_data(response)
    return data


# =========================================================================
# Contract & Address
# =========================================================================


@router.get("/contract/{usage_point_id}", response_model=APIResponse)
async def get_contract(
    usage_point_id: str = Path(..., description="Point de livraison (14 chiffres)"),
    use_cache: bool = Query(True, description="Use cached data if available"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """Get contract data - local-first strategy.

    1. Check local PostgreSQL cache
    2. If not found or use_cache=False, fetch from gateway
    3. Save to local cache for future requests
    """
    # Verify PDL ownership
    if not await verify_pdl_ownership(usage_point_id, current_user, db):
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="ACCESS_DENIED",
                message="Access denied: PDL not found or does not belong to you.",
            ),
        )

    local_service = LocalDataService(db)

    # Try local cache first
    if use_cache:
        cached_data = await local_service.get_contract(usage_point_id)
        if cached_data:
            logger.info(f"[{usage_point_id}] Contract served from local cache")
            return APIResponse(success=True, data=cached_data)

    # Fetch from gateway
    try:
        adapter = get_med_adapter()
        response = await adapter.get_contract(usage_point_id)
        data = extract_gateway_data(response)

        # Save to local cache
        await local_service.save_contract(usage_point_id, data)
        logger.info(f"[{usage_point_id}] Contract fetched from gateway and cached")

        return APIResponse(success=True, data=data)
    except Exception as e:
        logger.error(f"[{usage_point_id}] Error fetching contract: {e}")
        return APIResponse(
            success=False,
            error=ErrorDetail(code="GATEWAY_ERROR", message=str(e)),
        )


@router.get("/address/{usage_point_id}", response_model=APIResponse)
async def get_address(
    usage_point_id: str = Path(..., description="Point de livraison (14 chiffres)"),
    use_cache: bool = Query(True, description="Use cached data if available"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """Get address data - local-first strategy.

    1. Check local PostgreSQL cache
    2. If not found or use_cache=False, fetch from gateway
    3. Save to local cache for future requests
    """
    # Verify PDL ownership
    if not await verify_pdl_ownership(usage_point_id, current_user, db):
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="ACCESS_DENIED",
                message="Access denied: PDL not found or does not belong to you.",
            ),
        )

    local_service = LocalDataService(db)

    # Try local cache first
    if use_cache:
        cached_data = await local_service.get_address(usage_point_id)
        if cached_data:
            logger.info(f"[{usage_point_id}] Address served from local cache")
            return APIResponse(success=True, data=cached_data)

    # Fetch from gateway
    try:
        adapter = get_med_adapter()
        response = await adapter.get_address(usage_point_id)
        data = extract_gateway_data(response)

        # Save to local cache
        await local_service.save_address(usage_point_id, data)
        logger.info(f"[{usage_point_id}] Address fetched from gateway and cached")

        return APIResponse(success=True, data=data)
    except Exception as e:
        logger.error(f"[{usage_point_id}] Error fetching address: {e}")
        return APIResponse(
            success=False,
            error=ErrorDetail(code="GATEWAY_ERROR", message=str(e)),
        )


# =========================================================================
# Consumption Data
# =========================================================================


@router.get("/consumption/daily/{usage_point_id}", response_model=APIResponse)
async def get_consumption_daily(
    usage_point_id: str = Path(..., description="Point de livraison (14 chiffres)"),
    start: str = Query(..., description="Date de début (YYYY-MM-DD)"),
    end: str = Query(..., description="Date de fin (YYYY-MM-DD)"),
    use_cache: bool = Query(True, description="Use local cache and only fetch missing data"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """Get daily consumption data - local-first strategy.

    1. Check local PostgreSQL for cached data in requested range
    2. Identify missing date ranges
    3. Only fetch missing data from gateway
    4. Combine and return all data
    """
    # Verify PDL ownership
    if not await verify_pdl_ownership(usage_point_id, current_user, db):
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="ACCESS_DENIED",
                message="Access denied: PDL not found or does not belong to you.",
            ),
        )

    try:
        start_date = parse_date(start)
        end_date = parse_date(end)
    except ValueError as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(code="INVALID_DATE", message=str(e)),
        )

    local_service = LocalDataService(db)
    all_readings: list[dict] = []

    if use_cache:
        # Get local data and find missing ranges
        local_data, missing_ranges = await local_service.get_consumption_daily(
            usage_point_id, start_date, end_date
        )
        all_readings.extend(local_data)

        # If no missing ranges, return local data only
        if not missing_ranges:
            merged_readings = _merge_daily_readings(all_readings)
            logger.info(
                f"[{usage_point_id}] Daily consumption fully served from local cache "
                f"({len(merged_readings)} records)"
            )
            return APIResponse(
                success=True,
                data=format_daily_response(usage_point_id, start, end, merged_readings, from_cache=True),
            )

        # Fetch only missing ranges from gateway
        adapter = get_med_adapter()
        for range_start, range_end in missing_ranges:
            try:
                response = await adapter.get_consumption_daily(
                    usage_point_id,
                    range_start.isoformat(),
                    range_end.isoformat(),
                )
                gateway_readings = extract_readings_from_response(response)
                all_readings.extend(gateway_readings)
                logger.info(
                    f"[{usage_point_id}] Fetched {len(gateway_readings)} records from gateway "
                    f"for range {range_start} to {range_end}"
                )
            except Exception as e:
                logger.warning(
                    f"[{usage_point_id}] Failed to fetch {range_start} to {range_end}: {e}"
                )

        # Sort + dedup by date
        all_readings = _merge_daily_readings(all_readings)

        return APIResponse(
            success=True,
            data=format_daily_response(usage_point_id, start, end, all_readings, from_cache=False),
        )

    else:
        # Force fetch from gateway (no cache)
        try:
            adapter = get_med_adapter()
            response = await adapter.get_consumption_daily(usage_point_id, start, end)
            data = extract_gateway_data(response)
            logger.info(f"[{usage_point_id}] Daily consumption fetched from gateway (cache disabled)")
            return APIResponse(success=True, data=data)
        except Exception as e:
            logger.error(f"[{usage_point_id}] Error fetching daily consumption: {e}")
            return APIResponse(
                success=False,
                error=ErrorDetail(code="GATEWAY_ERROR", message=str(e)),
            )


@router.get("/consumption/detail/{usage_point_id}", response_model=APIResponse)
async def get_consumption_detail(
    usage_point_id: str = Path(..., description="Point de livraison (14 chiffres)"),
    start: str = Query(..., description="Date de début (YYYY-MM-DD)"),
    end: str = Query(..., description="Date de fin (YYYY-MM-DD)"),
    use_cache: bool = Query(True, description="Use local cache and only fetch missing data"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """Get detailed consumption data (30-min intervals) - local-first strategy.

    1. Check local PostgreSQL for cached data in requested range
    2. Identify missing date ranges
    3. Only fetch missing data from gateway
    4. Combine and return all data
    """
    # Verify PDL ownership
    if not await verify_pdl_ownership(usage_point_id, current_user, db):
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="ACCESS_DENIED",
                message="Access denied: PDL not found or does not belong to you.",
            ),
        )

    try:
        start_date = parse_date(start)
        end_date = parse_date(end)
    except ValueError as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(code="INVALID_DATE", message=str(e)),
        )

    local_service = LocalDataService(db)
    all_readings: list[dict] = []

    if use_cache:
        # Get local data and find missing ranges
        local_data, missing_ranges = await local_service.get_consumption_detail(
            usage_point_id, start_date, end_date
        )
        all_readings.extend(local_data)

        # If no missing ranges, return local data only
        if not missing_ranges:
            logger.info(
                f"[{usage_point_id}] Detailed consumption fully served from local cache "
                f"({len(local_data)} records)"
            )
            return APIResponse(
                success=True,
                data=format_detail_response(usage_point_id, start, end, all_readings, from_cache=True),
            )

        # Fetch only missing ranges from gateway
        adapter = get_med_adapter()
        for range_start, range_end in missing_ranges:
            try:
                response = await adapter.get_consumption_detail(
                    usage_point_id,
                    range_start.isoformat(),
                    range_end.isoformat(),
                )
                gateway_readings = extract_readings_from_response(response)
                all_readings.extend(gateway_readings)
                logger.info(
                    f"[{usage_point_id}] Fetched {len(gateway_readings)} detail records from gateway "
                    f"for range {range_start} to {range_end}"
                )
            except Exception as e:
                logger.warning(
                    f"[{usage_point_id}] Failed to fetch detail {range_start} to {range_end}: {e}"
                )

        # Sort by date
        all_readings.sort(key=lambda x: x.get("date", ""))

        return APIResponse(
            success=True,
            data=format_detail_response(usage_point_id, start, end, all_readings, from_cache=False),
        )

    else:
        # Force fetch from gateway (no cache)
        try:
            adapter = get_med_adapter()
            response = await adapter.get_consumption_detail(usage_point_id, start, end)
            data = extract_gateway_data(response)
            logger.info(f"[{usage_point_id}] Detailed consumption fetched from gateway (cache disabled)")
            return APIResponse(success=True, data=data)
        except Exception as e:
            logger.error(f"[{usage_point_id}] Error fetching detailed consumption: {e}")
            return APIResponse(
                success=False,
                error=ErrorDetail(code="GATEWAY_ERROR", message=str(e)),
            )


@router.get("/consumption/max_power/{usage_point_id}", response_model=APIResponse)
async def get_max_power(
    usage_point_id: str = Path(..., description="Point de livraison (14 chiffres)"),
    start: str = Query(..., description="Date de début (YYYY-MM-DD)"),
    end: str = Query(..., description="Date de fin (YYYY-MM-DD)"),
    use_cache: bool = Query(True, description="Use local cache and only fetch missing data"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """Get daily maximum power data via MyElectricalData gateway"""
    # Verify PDL ownership
    if not await verify_pdl_ownership(usage_point_id, current_user, db):
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="ACCESS_DENIED",
                message="Access denied: PDL not found or does not belong to you.",
            ),
        )

    try:
        start_date = parse_date(start)
        end_date = parse_date(end)
    except ValueError as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(code="INVALID_DATE", message=str(e)),
        )

    try:
        data = await _get_power_data_local_first(
            db=db,
            usage_point_id=usage_point_id,
            start=start,
            end=end,
            start_date=start_date,
            end_date=end_date,
            use_cache=use_cache,
        )
        return APIResponse(success=True, data=data)
    except Exception as e:
        logger.error(f"[{usage_point_id}] Error fetching max power: {e}")
        return APIResponse(
            success=False,
            error=ErrorDetail(code="GATEWAY_ERROR", message=str(e)),
        )


# =========================================================================
# Production Data
# =========================================================================


@router.get("/production/daily/{usage_point_id}", response_model=APIResponse)
async def get_production_daily(
    usage_point_id: str = Path(..., description="Point de livraison (14 chiffres)"),
    start: str = Query(..., description="Date de début (YYYY-MM-DD)"),
    end: str = Query(..., description="Date de fin (YYYY-MM-DD)"),
    use_cache: bool = Query(True, description="Use local cache and only fetch missing data"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """Get daily production data - local-first strategy.

    1. Check local PostgreSQL for cached data in requested range
    2. Identify missing date ranges
    3. Only fetch missing data from gateway
    4. Combine and return all data
    """
    # Verify PDL ownership
    if not await verify_pdl_ownership(usage_point_id, current_user, db):
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="ACCESS_DENIED",
                message="Access denied: PDL not found or does not belong to you.",
            ),
        )

    try:
        start_date = parse_date(start)
        end_date = parse_date(end)
    except ValueError as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(code="INVALID_DATE", message=str(e)),
        )

    local_service = LocalDataService(db)
    all_readings: list[dict] = []

    if use_cache:
        # Get local data and find missing ranges
        local_data, missing_ranges = await local_service.get_production_daily(
            usage_point_id, start_date, end_date
        )
        all_readings.extend(local_data)

        # If no missing ranges, return local data only
        if not missing_ranges:
            merged_readings = _merge_daily_readings(all_readings)
            logger.info(
                f"[{usage_point_id}] Daily production fully served from local cache "
                f"({len(merged_readings)} records)"
            )
            return APIResponse(
                success=True,
                data=format_daily_response(usage_point_id, start, end, merged_readings, from_cache=True),
            )

        # Fetch only missing ranges from gateway
        adapter = get_med_adapter()
        for range_start, range_end in missing_ranges:
            try:
                response = await adapter.get_production_daily(
                    usage_point_id,
                    range_start.isoformat(),
                    range_end.isoformat(),
                )
                gateway_readings = extract_readings_from_response(response)
                all_readings.extend(gateway_readings)
                logger.info(
                    f"[{usage_point_id}] Fetched {len(gateway_readings)} production records from gateway "
                    f"for range {range_start} to {range_end}"
                )
            except Exception as e:
                logger.warning(
                    f"[{usage_point_id}] Failed to fetch production {range_start} to {range_end}: {e}"
                )

        # Sort + dedup by date
        all_readings = _merge_daily_readings(all_readings)

        return APIResponse(
            success=True,
            data=format_daily_response(usage_point_id, start, end, all_readings, from_cache=False),
        )

    else:
        # Force fetch from gateway (no cache)
        try:
            adapter = get_med_adapter()
            response = await adapter.get_production_daily(usage_point_id, start, end)
            data = extract_gateway_data(response)
            logger.info(f"[{usage_point_id}] Daily production fetched from gateway (cache disabled)")
            return APIResponse(success=True, data=data)
        except Exception as e:
            logger.error(f"[{usage_point_id}] Error fetching daily production: {e}")
            return APIResponse(
                success=False,
                error=ErrorDetail(code="GATEWAY_ERROR", message=str(e)),
            )


@router.get("/production/detail/{usage_point_id}", response_model=APIResponse)
async def get_production_detail(
    usage_point_id: str = Path(..., description="Point de livraison (14 chiffres)"),
    start: str = Query(..., description="Date de début (YYYY-MM-DD)"),
    end: str = Query(..., description="Date de fin (YYYY-MM-DD)"),
    use_cache: bool = Query(True, description="Use local cache and only fetch missing data"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """Get detailed production data (30-min intervals) - local-first strategy.

    1. Check local PostgreSQL for cached data in requested range
    2. Identify missing date ranges
    3. Only fetch missing data from gateway
    4. Combine and return all data
    """
    # Verify PDL ownership
    if not await verify_pdl_ownership(usage_point_id, current_user, db):
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="ACCESS_DENIED",
                message="Access denied: PDL not found or does not belong to you.",
            ),
        )

    try:
        start_date = parse_date(start)
        end_date = parse_date(end)
    except ValueError as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(code="INVALID_DATE", message=str(e)),
        )

    local_service = LocalDataService(db)
    all_readings: list[dict] = []

    if use_cache:
        # Get local data and find missing ranges
        local_data, missing_ranges = await local_service.get_production_detail(
            usage_point_id, start_date, end_date
        )
        all_readings.extend(local_data)

        # If no missing ranges, return local data only
        if not missing_ranges:
            logger.info(
                f"[{usage_point_id}] Detailed production fully served from local cache "
                f"({len(local_data)} records)"
            )
            return APIResponse(
                success=True,
                data=format_detail_response(usage_point_id, start, end, all_readings, from_cache=True),
            )

        # Fetch only missing ranges from gateway
        adapter = get_med_adapter()
        for range_start, range_end in missing_ranges:
            try:
                response = await adapter.get_production_detail(
                    usage_point_id,
                    range_start.isoformat(),
                    range_end.isoformat(),
                )
                gateway_readings = extract_readings_from_response(response)
                all_readings.extend(gateway_readings)
                logger.info(
                    f"[{usage_point_id}] Fetched {len(gateway_readings)} production detail records "
                    f"from gateway for range {range_start} to {range_end}"
                )
            except Exception as e:
                logger.warning(
                    f"[{usage_point_id}] Failed to fetch production detail {range_start} to {range_end}: {e}"
                )

        # Sort by date
        all_readings.sort(key=lambda x: x.get("date", ""))

        return APIResponse(
            success=True,
            data=format_detail_response(usage_point_id, start, end, all_readings, from_cache=False),
        )

    else:
        # Force fetch from gateway (no cache)
        try:
            adapter = get_med_adapter()
            response = await adapter.get_production_detail(usage_point_id, start, end)
            data = extract_gateway_data(response)
            logger.info(f"[{usage_point_id}] Detailed production fetched from gateway (cache disabled)")
            return APIResponse(success=True, data=data)
        except Exception as e:
            logger.error(f"[{usage_point_id}] Error fetching detailed production: {e}")
            return APIResponse(
                success=False,
                error=ErrorDetail(code="GATEWAY_ERROR", message=str(e)),
            )


# =========================================================================
# Power (Max Power) - Alias for frontend compatibility
# =========================================================================


@router.get("/power/{usage_point_id}", response_model=APIResponse)
async def get_power(
    usage_point_id: str = Path(..., description="Point de livraison (14 chiffres)"),
    start: str = Query(..., description="Date de début (YYYY-MM-DD)"),
    end: str = Query(..., description="Date de fin (YYYY-MM-DD)"),
    use_cache: bool = Query(True, description="Use local cache and only fetch missing data"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """Get daily maximum power data via MyElectricalData gateway"""
    # Verify PDL ownership
    if not await verify_pdl_ownership(usage_point_id, current_user, db):
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="ACCESS_DENIED",
                message="Access denied: PDL not found or does not belong to you.",
            ),
        )

    try:
        start_date = parse_date(start)
        end_date = parse_date(end)
    except ValueError as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(code="INVALID_DATE", message=str(e)),
        )

    try:
        data = await _get_power_data_local_first(
            db=db,
            usage_point_id=usage_point_id,
            start=start,
            end=end,
            start_date=start_date,
            end_date=end_date,
            use_cache=use_cache,
        )
        return APIResponse(success=True, data=data)
    except Exception as e:
        logger.error(f"[{usage_point_id}] Error fetching max power: {e}")
        return APIResponse(
            success=False,
            error=ErrorDetail(code="GATEWAY_ERROR", message=str(e)),
        )


# =========================================================================
# Batch Endpoints - Fetch data in chunks (7 days for detailed data)
# =========================================================================


@router.get("/consumption/detail/batch/{usage_point_id}", response_model=APIResponse)
async def get_consumption_detail_batch(
    usage_point_id: str = Path(..., description="Point de livraison (14 chiffres)"),
    start: str = Query(..., description="Date de début (YYYY-MM-DD)"),
    end: str = Query(..., description="Date de fin (YYYY-MM-DD)"),
    use_cache: bool = Query(True, description="Utiliser le cache local et ne fetcher que les données manquantes"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """Get detailed consumption data in batch (handles long date ranges)

    Stratégie local-first : consulte la base locale, identifie les trous,
    et ne fetch que les plages manquantes depuis la passerelle.
    """
    # Verify PDL ownership
    if not await verify_pdl_ownership(usage_point_id, current_user, db):
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="ACCESS_DENIED",
                message="Access denied: PDL not found or does not belong to you.",
            ),
        )

    try:
        start_date = parse_date(start)
        end_date = parse_date(end)
    except ValueError as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(code="INVALID_DATE", message=str(e)),
        )

    try:
        local_service = LocalDataService(db)
        all_readings: list[dict] = []

        if use_cache:
            # Récupérer les données locales et les plages manquantes
            local_data, missing_ranges = await local_service.get_consumption_detail(
                usage_point_id, start_date, end_date
            )
            all_readings.extend(local_data)

            if not missing_ranges:
                logger.info(
                    f"[{usage_point_id}] Batch detail consumption servi depuis le cache local "
                    f"({len(local_data)} enregistrements)"
                )
                return APIResponse(
                    success=True,
                    data=format_detail_response(usage_point_id, start, end, all_readings, from_cache=True),
                )

            # Fetcher uniquement les plages manquantes en chunks de 7 jours
            adapter = get_med_adapter()
            for range_start, range_end in missing_ranges:
                current_start = range_start
                while current_start < range_end:
                    chunk_end = min(current_start + timedelta(days=7), range_end)
                    backoff_key = f"consumption:{usage_point_id}:{current_start.isoformat()}:{chunk_end.isoformat()}"
                    backoff_until = _detail_chunk_backoff.get(backoff_key)
                    if backoff_until and backoff_until > datetime.now():
                        current_start = chunk_end
                        continue
                    try:
                        response = await adapter.get_consumption_detail(
                            usage_point_id,
                            current_start.isoformat(),
                            chunk_end.isoformat(),
                        )
                        gateway_readings = extract_readings_from_response(response)
                        if not gateway_readings:
                            _detail_chunk_backoff[backoff_key] = datetime.now() + _DETAIL_CHUNK_BACKOFF_TTL
                        all_readings.extend(gateway_readings)
                    except Exception as chunk_error:
                        _detail_chunk_backoff[backoff_key] = datetime.now() + _DETAIL_CHUNK_BACKOFF_TTL
                        logger.warning(
                            f"[{usage_point_id}] Chunk {current_start} - {chunk_end} échoué: {chunk_error}"
                        )
                    current_start = chunk_end

            logger.info(
                f"[{usage_point_id}] Batch detail consumption: {len(local_data)} local + "
                f"{len(all_readings) - len(local_data)} gateway ({len(missing_ranges)} plages manquantes)"
            )

        else:
            # Force fetch sans cache
            adapter = get_med_adapter()
            current_start = start_date
            while current_start < end_date:
                chunk_end = min(current_start + timedelta(days=7), end_date)
                try:
                    response = await adapter.get_consumption_detail(
                        usage_point_id,
                        current_start.isoformat(),
                        chunk_end.isoformat(),
                    )
                    gateway_readings = extract_readings_from_response(response)
                    all_readings.extend(gateway_readings)
                except Exception as chunk_error:
                    logger.warning(
                        f"[{usage_point_id}] Chunk {current_start} - {chunk_end} échoué: {chunk_error}"
                    )
                current_start = chunk_end

        # Trier par date
        all_readings.sort(key=lambda x: x.get("date", ""))

        return APIResponse(
            success=True,
            data=format_detail_response(usage_point_id, start, end, all_readings, from_cache=False),
        )

    except Exception as e:
        logger.error(f"[{usage_point_id}] Erreur batch consumption detail: {e}")
        return APIResponse(
            success=False,
            error=ErrorDetail(code="GATEWAY_ERROR", message=str(e)),
        )


@router.get("/production/detail/batch/{usage_point_id}", response_model=APIResponse)
async def get_production_detail_batch(
    usage_point_id: str = Path(..., description="Point de livraison (14 chiffres)"),
    start: str = Query(..., description="Date de début (YYYY-MM-DD)"),
    end: str = Query(..., description="Date de fin (YYYY-MM-DD)"),
    use_cache: bool = Query(True, description="Utiliser le cache local et ne fetcher que les données manquantes"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """Get detailed production data in batch (handles long date ranges)

    Stratégie local-first : consulte la base locale, identifie les trous,
    et ne fetch que les plages manquantes depuis la passerelle.
    """
    # Verify PDL ownership
    if not await verify_pdl_ownership(usage_point_id, current_user, db):
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="ACCESS_DENIED",
                message="Access denied: PDL not found or does not belong to you.",
            ),
        )

    try:
        start_date = parse_date(start)
        end_date = parse_date(end)
    except ValueError as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(code="INVALID_DATE", message=str(e)),
        )

    try:
        local_service = LocalDataService(db)
        all_readings: list[dict] = []

        if use_cache:
            # Récupérer les données locales et les plages manquantes
            local_data, missing_ranges = await local_service.get_production_detail(
                usage_point_id, start_date, end_date
            )
            all_readings.extend(local_data)

            if not missing_ranges:
                logger.info(
                    f"[{usage_point_id}] Batch detail production servi depuis le cache local "
                    f"({len(local_data)} enregistrements)"
                )
                return APIResponse(
                    success=True,
                    data=format_detail_response(usage_point_id, start, end, all_readings, from_cache=True),
                )

            # Fetcher uniquement les plages manquantes en chunks de 7 jours
            adapter = get_med_adapter()
            for range_start, range_end in missing_ranges:
                current_start = range_start
                while current_start < range_end:
                    chunk_end = min(current_start + timedelta(days=7), range_end)
                    backoff_key = f"production:{usage_point_id}:{current_start.isoformat()}:{chunk_end.isoformat()}"
                    backoff_until = _detail_chunk_backoff.get(backoff_key)
                    if backoff_until and backoff_until > datetime.now():
                        current_start = chunk_end
                        continue
                    try:
                        response = await adapter.get_production_detail(
                            usage_point_id,
                            current_start.isoformat(),
                            chunk_end.isoformat(),
                        )
                        gateway_readings = extract_readings_from_response(response)
                        if not gateway_readings:
                            _detail_chunk_backoff[backoff_key] = datetime.now() + _DETAIL_CHUNK_BACKOFF_TTL
                        all_readings.extend(gateway_readings)
                    except Exception as chunk_error:
                        _detail_chunk_backoff[backoff_key] = datetime.now() + _DETAIL_CHUNK_BACKOFF_TTL
                        logger.warning(
                            f"[{usage_point_id}] Chunk {current_start} - {chunk_end} échoué: {chunk_error}"
                        )
                    current_start = chunk_end

            logger.info(
                f"[{usage_point_id}] Batch detail production: {len(local_data)} local + "
                f"{len(all_readings) - len(local_data)} gateway ({len(missing_ranges)} plages manquantes)"
            )

        else:
            # Force fetch sans cache
            adapter = get_med_adapter()
            current_start = start_date
            while current_start < end_date:
                chunk_end = min(current_start + timedelta(days=7), end_date)
                try:
                    response = await adapter.get_production_detail(
                        usage_point_id,
                        current_start.isoformat(),
                        chunk_end.isoformat(),
                    )
                    gateway_readings = extract_readings_from_response(response)
                    all_readings.extend(gateway_readings)
                except Exception as chunk_error:
                    logger.warning(
                        f"[{usage_point_id}] Chunk {current_start} - {chunk_end} échoué: {chunk_error}"
                    )
                current_start = chunk_end

        # Trier par date
        all_readings.sort(key=lambda x: x.get("date", ""))

        return APIResponse(
            success=True,
            data=format_detail_response(usage_point_id, start, end, all_readings, from_cache=False),
        )

    except Exception as e:
        logger.error(f"[{usage_point_id}] Erreur batch production detail: {e}")
        return APIResponse(
            success=False,
            error=ErrorDetail(code="GATEWAY_ERROR", message=str(e)),
        )
