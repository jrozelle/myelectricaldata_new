"""RTE API Service for Tempo Calendar and EcoWatt data"""

import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any, Dict, List, Optional, cast
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models import TempoColor, TempoDay
from ..models.ecowatt import EcoWatt
from ..models.consumption_france import ConsumptionFrance
from ..models.generation_forecast import GenerationForecast

logger = logging.getLogger(__name__)


class RTEService:
    """Service to fetch and cache Tempo Calendar and EcoWatt data from RTE API"""

    def __init__(self) -> None:
        self.base_url = settings.RTE_BASE_URL
        self.client_id = settings.RTE_CLIENT_ID
        self.client_secret = settings.RTE_CLIENT_SECRET
        self.token_url = f"{self.base_url}/token/oauth/"
        self.tempo_url = f"{self.base_url}/open_api/tempo_like_supply_contract/v1/tempo_like_calendars"
        self.ecowatt_url = f"{self.base_url}/open_api/ecowatt/v5/signals"
        self.consumption_url = f"{self.base_url}/open_api/consumption/v1/short_term"
        self.generation_forecast_url = f"{self.base_url}/open_api/generation_forecast/v3/forecasts"
        self._access_token: str | None = None
        self._token_expires_at: datetime | None = None
        self._last_ecowatt_fetch: datetime | None = None
        self._ecowatt_fetch_min_interval = timedelta(minutes=15)  # Min 15 minutes between API calls

    async def _get_access_token(self) -> str:
        """Get OAuth2 access token for RTE API"""
        # Return cached token if still valid
        if self._access_token and self._token_expires_at:
            if datetime.now(UTC) < self._token_expires_at:
                return self._access_token

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data={
                    "grant_type": "client_credentials",
                },
                auth=(self.client_id, self.client_secret),
            )
            response.raise_for_status()
            data = response.json()

            self._access_token = data["access_token"]
            # Token expires in 'expires_in' seconds, refresh 5 minutes before
            expires_in = data.get("expires_in", 3600)
            self._token_expires_at = datetime.now(UTC) + timedelta(seconds=expires_in - 300)

            return self._access_token

    async def fetch_tempo_calendar(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """
        Fetch Tempo Calendar from RTE API

        Args:
            start_date: Start date (timezone aware)
            end_date: End date (timezone aware)

        Returns:
            List of tempo day dictionaries with date, color, and update info
        """
        token = await self._get_access_token()

        # Convert to Paris timezone for RTE API (required format: YYYY-MM-DDThh:mm:ss+zz:zz)
        paris_tz = ZoneInfo("Europe/Paris")
        start_paris = start_date.astimezone(paris_tz)
        end_paris = end_date.astimezone(paris_tz)

        # Format dates in ISO 8601 with timezone (e.g., 2015-06-08T00:00:00+02:00)
        start_str = start_paris.isoformat()
        end_str = end_paris.isoformat()

        logger.debug(f"[RTE API] Requesting TEMPO data from {start_str} to {end_str}")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.tempo_url,
                params={"start_date": start_str, "end_date": end_str},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
            )
            logger.debug(f"[RTE API] Response status: {response.status_code}")

            if response.status_code != 200:
                logger.error(f"[RTE API] Error response body: {response.text}")

            response.raise_for_status()
            data = response.json()

            logger.debug(f"[RTE API] Raw response: {data}")
            logger.info(f"[RTE API] Received {len(data.get('tempo_like_calendars', {}).get('values', []))} TEMPO days")
            return cast(list[dict[str, Any]], data.get("tempo_like_calendars", {}).get("values", []))

    async def _get_missing_tempo_ranges(self, db: AsyncSession, start_date: datetime, end_date: datetime) -> List[tuple[datetime, datetime]]:
        """
        Identify missing date ranges in TEMPO cache

        Args:
            db: Database session
            start_date: Start date to check (timezone aware)
            end_date: End date to check (timezone aware)

        Returns:
            List of (start, end) tuples representing missing ranges
        """
        # Get all existing dates in range (dates are stored as datetime with timezone)
        result = await db.execute(
            select(TempoDay.date)
            .where(TempoDay.date >= start_date, TempoDay.date < end_date)
            .order_by(TempoDay.date)
        )

        # Normalize existing dates to midnight UTC for comparison
        # Database stores dates like "2015-11-25 23:00:00+00:00" (Paris time converted to UTC)
        # We need to extract just the date part and normalize to UTC midnight
        existing_dates = set()
        for row in result.all():
            db_date = row[0]
            # Convert to Paris timezone to get the actual day, then back to UTC midnight
            paris_tz = ZoneInfo("Europe/Paris")
            paris_date = db_date.astimezone(paris_tz)
            normalized_date = paris_date.replace(hour=0, minute=0, second=0, microsecond=0)
            # Store as date string for comparison (date-only, no time)
            existing_dates.add(normalized_date.date())

        # Generate all expected dates (date-only)
        current = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_normalized = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        all_dates = []
        while current < end_normalized:
            all_dates.append(current.date())
            current += timedelta(days=1)

        # Find missing ranges
        missing_ranges = []
        range_start = None

        for date_only in all_dates:
            if date_only not in existing_dates:
                if range_start is None:
                    range_start = date_only
            else:
                if range_start is not None:
                    # Convert date back to datetime with Paris timezone
                    paris_tz = ZoneInfo("Europe/Paris")
                    range_start_dt = datetime.combine(range_start, datetime.min.time()).replace(tzinfo=paris_tz)
                    range_end_dt = datetime.combine(date_only, datetime.min.time()).replace(tzinfo=paris_tz)
                    missing_ranges.append((range_start_dt, range_end_dt))
                    range_start = None

        # Close last range if needed
        if range_start is not None:
            paris_tz = ZoneInfo("Europe/Paris")
            range_start_dt = datetime.combine(range_start, datetime.min.time()).replace(tzinfo=paris_tz)
            range_end_dt = datetime.combine(end_normalized.date(), datetime.min.time()).replace(tzinfo=paris_tz)
            missing_ranges.append((range_start_dt, range_end_dt))

        return missing_ranges

    async def update_tempo_cache(self, db: AsyncSession, days: int = 7) -> int:
        """
        Update Tempo Calendar cache in database (optimized to only fetch missing data)

        Args:
            db: Database session
            days: Number of days to fetch (ignored - RTE API limitation)

        Returns:
            Number of days updated
        """
        # Fetch data from RTE API - use Paris timezone
        paris_tz = ZoneInfo("Europe/Paris")
        now_paris = datetime.now(paris_tz)

        updated_count = 0

        # 1. Always fetch today and tomorrow (volatile data that changes during the day)
        start_date = now_paris.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        if now_paris.hour >= 7:
            end_date = now_paris.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=2)
        else:
            end_date = now_paris.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)

        logger.info("[RTE] Fetching today/tomorrow data (always refresh)...")
        tempo_values = await self.fetch_tempo_calendar(start_date, end_date)
        updated_count += await self._process_tempo_values(db, tempo_values)

        # 2. Check historical data (last 10 years) and only fetch missing ranges
        logger.info("[RTE] Checking historical data (last 10 years)...")
        years_to_check = 10

        # Define full historical range
        historical_end = now_paris.replace(hour=0, minute=0, second=0, microsecond=0)
        historical_start = historical_end - timedelta(days=366 * years_to_check)

        # Identify missing ranges
        missing_ranges = await self._get_missing_tempo_ranges(db, historical_start, historical_end)

        # Filter out very small ranges (1-2 days) that might be timezone artifacts or future dates
        significant_missing = [
            (start, end) for start, end in missing_ranges
            if (end - start).days > 2
        ]

        if not significant_missing:
            logger.info("[RTE] All historical TEMPO data already in cache, skipping API calls")
            if missing_ranges and len(missing_ranges) != len(significant_missing):
                logger.debug(f"[RTE] Ignored {len(missing_ranges)} minor gaps (≤2 days) likely due to timezone or future dates")
        else:
            logger.info(f"[RTE] Found {len(significant_missing)} significant missing date ranges to fetch")

            for idx, (range_start, range_end) in enumerate(significant_missing, 1):
                try:
                    days_count = (range_end - range_start).days
                    logger.info(
                        f"[RTE] Fetching missing range {idx}/{len(significant_missing)}: "
                        f"{range_start.date()} to {range_end.date()} ({days_count} days)"
                    )

                    # Split large ranges into chunks of 366 days (RTE API limitation)
                    chunk_start = range_start
                    while chunk_start < range_end:
                        chunk_end = min(chunk_start + timedelta(days=366), range_end)

                        historical_values = await self.fetch_tempo_calendar(chunk_start, chunk_end)
                        logger.info(f"[RTE] Received {len(historical_values)} values for chunk")
                        count = await self._process_tempo_values(db, historical_values)
                        await db.commit()  # Commit after each chunk to avoid losing data
                        updated_count += count

                        chunk_start = chunk_end

                    logger.info(f"[RTE] Missing range {idx}/{len(significant_missing)}: completed")

                except Exception as e:
                    logger.warning(f"[RTE] Warning: Could not fetch missing range {idx}: {e}")
                    import traceback
                    traceback.print_exc()

        logger.info(f"[RTE] Total updated: {updated_count} days")
        return updated_count

    async def _process_tempo_values(self, db: AsyncSession, tempo_values: List[Dict[str, Any]]) -> int:
        """Process and store tempo values in database"""
        updated_count = 0
        for value in tempo_values:
            try:
                # Parse dates from RTE response
                # RTE API: start_date represents the day the color applies to
                # Example: start_date=2025-11-19 00:00 + end_date=2025-11-20 00:00 means color for Nov 19
                day_start = datetime.fromisoformat(value["start_date"])
                color_str = value["value"]
                updated_date_str = value.get("updated_date")

                # Use start_date as the reference date (this is the actual day the color applies to)
                date_id = day_start.strftime("%Y-%m-%d")

                # Parse RTE update date if provided
                rte_updated = None
                if updated_date_str:
                    rte_updated = datetime.fromisoformat(updated_date_str)

                # Check if day already exists
                result = await db.execute(select(TempoDay).where(TempoDay.id == date_id))
                existing = result.scalar_one_or_none()

                if existing:
                    # Update existing record
                    existing.color = TempoColor(color_str)  # type: ignore[assignment]
                    existing.rte_updated_date = rte_updated  # type: ignore[assignment]
                    existing.updated_at = datetime.now(UTC)  # type: ignore[assignment]
                else:
                    # Create new record (use start_date as the actual day)
                    tempo_day = TempoDay(
                        id=date_id,
                        date=day_start,
                        color=TempoColor(color_str),
                        rte_updated_date=rte_updated,
                    )
                    db.add(tempo_day)

                updated_count += 1

            except Exception as e:
                logger.error(f"Error processing TEMPO day {value}: {e}")
                continue

        return updated_count

    async def get_tempo_days(
        self, db: AsyncSession, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> List[TempoDay]:
        """
        Get TEMPO days from database cache

        Args:
            db: Database session
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of TempoDay objects
        """
        query = select(TempoDay).order_by(TempoDay.date)

        if start_date:
            query = query.where(TempoDay.date >= start_date)
        if end_date:
            query = query.where(TempoDay.date <= end_date)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_tempo_day(self, db: AsyncSession, date: datetime) -> TempoDay | None:
        """
        Get TEMPO color for a specific date

        Args:
            db: Database session
            date: Date to query

        Returns:
            TempoDay object or None
        """
        date_id = date.strftime("%Y-%m-%d")
        result = await db.execute(select(TempoDay).where(TempoDay.id == date_id))
        return result.scalar_one_or_none()

    async def clear_old_data(self, db: AsyncSession, days_to_keep: int = 30) -> int:
        """
        Remove old TEMPO data from cache

        Args:
            db: Database session
            days_to_keep: Keep data from last N days (default: 30)

        Returns:
            Number of records deleted
        """
        cutoff_date = datetime.now(UTC) - timedelta(days=days_to_keep)
        result = await db.execute(delete(TempoDay).where(TempoDay.date < cutoff_date))
        await db.commit()
        return result.rowcount

    # ========== EcoWatt Methods ==========

    async def fetch_ecowatt_signals(self) -> Dict[str, Any]:
        """
        Fetch EcoWatt signals from RTE API

        Returns:
            Dictionary containing EcoWatt signals
        """
        token = await self._get_access_token()

        logger.debug("[RTE API] Requesting EcoWatt data...")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.ecowatt_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
            )
            logger.debug(f"[RTE API] EcoWatt response status: {response.status_code}")

            if response.status_code != 200:
                logger.error(f"[RTE API] EcoWatt error response: {response.text}")

            response.raise_for_status()
            data = response.json()

            logger.info("[RTE API] Received EcoWatt signals")
            return cast(dict[str, Any], data)

    async def update_ecowatt_cache(self, db: AsyncSession) -> int:
        """
        Update EcoWatt signals cache in database

        Args:
            db: Database session

        Returns:
            Number of signals updated
        """
        try:
            # Check if we need to wait before making another API call (rate limiting)
            now = datetime.now(UTC)
            if self._last_ecowatt_fetch:
                time_since_last_fetch = now - self._last_ecowatt_fetch
                if time_since_last_fetch < self._ecowatt_fetch_min_interval:
                    remaining = self._ecowatt_fetch_min_interval - time_since_last_fetch
                    logger.warning(
                        f"[RTE] EcoWatt API rate limit: last fetch was {time_since_last_fetch.total_seconds():.0f}s ago, need to wait {remaining.total_seconds():.0f}s more"
                    )
                    return 0

            # Fetch EcoWatt data from RTE API
            ecowatt_data = await self.fetch_ecowatt_signals()

            # Update last fetch timestamp
            self._last_ecowatt_fetch = now

            if not ecowatt_data or "signals" not in ecowatt_data:
                logger.info("[RTE] No EcoWatt signals received")
                return 0

            signals = ecowatt_data["signals"]
            updated_count = 0

            for signal in signals:
                try:
                    # Extract signal data and convert to UTC naive datetime
                    generation_datetime = (
                        datetime.fromisoformat(signal["GenerationFichier"]).astimezone(UTC).replace(tzinfo=None)
                    )
                    periode = datetime.fromisoformat(signal["jour"]).astimezone(UTC).replace(tzinfo=None)

                    # Extract hourly values and map them to hours (pas = hour)
                    # Initialize with 24 hours, default value 0
                    hourly_values = [0] * 24
                    for hour_data in signal.get("values", []):
                        pas = hour_data["pas"]  # pas 0 = minuit, pas 1 = 1h, etc.
                        hvalue = hour_data["hvalue"]
                        if 0 <= pas <= 23:
                            hourly_values[pas] = hvalue

                    # Determine hdebut and hfin from actual data
                    signal_values = signal.get("values", [])
                    hdebut = min((v["pas"] for v in signal_values), default=0)
                    hfin = max((v["pas"] for v in signal_values), default=23)

                    # Prepare data for database
                    ecowatt_create = {
                        "generation_datetime": generation_datetime,
                        "periode": periode,
                        "hdebut": hdebut,
                        "hfin": hfin,
                        "pas": 60,  # Always 60 minutes (1 hour step)
                        "dvalue": signal["dvalue"],
                        "message": signal.get("message", ""),
                        "values": hourly_values,  # Array of 24 values indexed by hour
                    }

                    # Check if signal for this day already exists
                    result = await db.execute(select(EcoWatt).where(EcoWatt.periode == periode))
                    existing = result.scalar_one_or_none()

                    if existing:
                        # Update existing record
                        for key, value in ecowatt_create.items():
                            setattr(existing, key, value)
                        existing.updated_at = datetime.now(UTC).replace(tzinfo=None)  # type: ignore[assignment]
                    else:
                        # Create new record
                        ecowatt = EcoWatt(**ecowatt_create)
                        db.add(ecowatt)

                    updated_count += 1

                except Exception as e:
                    logger.error(f"Error processing EcoWatt signal {signal}: {e}")
                    continue

            await db.commit()
            logger.info(f"[RTE] Updated {updated_count} EcoWatt signals")
            return updated_count

        except Exception as e:
            await db.rollback()
            logger.error(f"[RTE] Error updating EcoWatt cache: {e}")
            import traceback

            traceback.print_exc()
            return 0

    async def get_ecowatt_signals(
        self, db: AsyncSession, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> List[EcoWatt]:
        """
        Get EcoWatt signals from database cache

        Args:
            db: Database session
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of EcoWatt objects
        """
        query = select(EcoWatt).order_by(EcoWatt.periode)

        if start_date:
            query = query.where(EcoWatt.periode >= start_date)
        if end_date:
            query = query.where(EcoWatt.periode <= end_date)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_ecowatt_signal(self, db: AsyncSession, target_date: date) -> Optional[EcoWatt]:
        """
        Get EcoWatt signal for a specific date

        Args:
            db: Database session
            target_date: Date to query

        Returns:
            EcoWatt object or None
        """
        # Convert date to datetime for comparison
        target_datetime = datetime.combine(target_date, datetime.min.time())

        result = await db.execute(
            select(EcoWatt).where(
                EcoWatt.periode >= target_datetime, EcoWatt.periode < target_datetime + timedelta(days=1)
            )
        )
        return result.scalar_one_or_none()


    # ========== Consumption France Methods ==========

    async def fetch_consumption_france(
        self,
        consumption_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> Dict[str, Any]:
        """
        Fetch French national consumption data from RTE API

        Args:
            consumption_type: Type of data (REALISED, ID, D-1, D-2)
            start_date: Start date (timezone aware)
            end_date: End date (timezone aware)

        Returns:
            Dictionary containing consumption data
        """
        token = await self._get_access_token()
        paris_tz = ZoneInfo("Europe/Paris")

        params: Dict[str, str] = {}
        if consumption_type:
            params["type"] = consumption_type
        if start_date:
            params["start_date"] = start_date.astimezone(paris_tz).isoformat()
        if end_date:
            params["end_date"] = end_date.astimezone(paris_tz).isoformat()

        logger.debug(f"[RTE API] Requesting Consumption data with params: {params}")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.consumption_url,
                params=params,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
            )
            logger.debug(f"[RTE API] Consumption response status: {response.status_code}")

            if response.status_code != 200:
                logger.error(f"[RTE API] Consumption error response: {response.text}")

            response.raise_for_status()
            data = response.json()

            logger.info("[RTE API] Received Consumption data")
            return cast(dict[str, Any], data)

    async def update_consumption_france_cache(
        self,
        db: AsyncSession,
        consumption_type: str | None = None,
    ) -> int:
        """
        Update French national consumption cache in database

        Args:
            db: Database session
            consumption_type: Optional type filter (REALISED, ID, D-1, D-2)

        Returns:
            Number of records updated
        """
        try:
            paris_tz = ZoneInfo("Europe/Paris")
            now = datetime.now(paris_tz)

            # Définir la période : 2 jours avant à 2 jours après
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=2)
            end_date = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=2)

            # Récupérer les données depuis l'API RTE
            consumption_data = await self.fetch_consumption_france(
                consumption_type=consumption_type,
                start_date=start_date,
                end_date=end_date,
            )

            if not consumption_data or "short_term" not in consumption_data:
                logger.info("[RTE] No consumption data received")
                return 0

            updated_count = 0
            for short_term in consumption_data["short_term"]:
                data_type = short_term["type"]
                for value in short_term.get("values", []):
                    try:
                        value_start = datetime.fromisoformat(value["start_date"]).astimezone(UTC).replace(tzinfo=None)
                        value_end = datetime.fromisoformat(value["end_date"]).astimezone(UTC).replace(tzinfo=None)
                        value_mw = value["value"]
                        updated_date_str = value.get("updated_date")
                        updated_date = (
                            datetime.fromisoformat(updated_date_str).astimezone(UTC).replace(tzinfo=None)
                            if updated_date_str
                            else None
                        )

                        # Vérifier si l'entrée existe déjà
                        result = await db.execute(
                            select(ConsumptionFrance).where(
                                ConsumptionFrance.type == data_type,
                                ConsumptionFrance.start_date == value_start,
                            )
                        )
                        existing = result.scalar_one_or_none()

                        if existing:
                            existing.value = value_mw  # type: ignore[assignment]
                            existing.end_date = value_end  # type: ignore[assignment]
                            existing.updated_date = updated_date  # type: ignore[assignment]
                            existing.updated_at = datetime.now(UTC).replace(tzinfo=None)  # type: ignore[assignment]
                        else:
                            record = ConsumptionFrance(
                                type=data_type,
                                start_date=value_start,
                                end_date=value_end,
                                value=value_mw,
                                updated_date=updated_date,
                            )
                            db.add(record)

                        updated_count += 1

                    except Exception as e:
                        logger.error(f"Error processing consumption value: {e}")
                        continue

            await db.commit()
            logger.info(f"[RTE] Updated {updated_count} consumption records")
            return updated_count

        except Exception as e:
            await db.rollback()
            logger.error(f"[RTE] Error updating consumption cache: {e}")
            import traceback

            traceback.print_exc()
            return 0

    async def get_consumption_france(
        self,
        db: AsyncSession,
        consumption_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> List[ConsumptionFrance]:
        """
        Get French national consumption data from database cache

        Args:
            db: Database session
            consumption_type: Optional type filter
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of ConsumptionFrance objects
        """
        query = select(ConsumptionFrance).order_by(ConsumptionFrance.start_date)

        if consumption_type:
            query = query.where(ConsumptionFrance.type == consumption_type)
        if start_date:
            # Retirer la timezone pour comparaison avec DateTime naive en DB
            start_naive = start_date.replace(tzinfo=None) if start_date.tzinfo else start_date
            query = query.where(ConsumptionFrance.start_date >= start_naive)
        if end_date:
            end_naive = end_date.replace(tzinfo=None) if end_date.tzinfo else end_date
            query = query.where(ConsumptionFrance.start_date <= end_naive)

        result = await db.execute(query)
        return list(result.scalars().all())

    # ========== Generation Forecast Methods ==========

    async def fetch_generation_forecast(
        self,
        production_type: str | None = None,
        forecast_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> Dict[str, Any]:
        """
        Fetch French generation forecast data from RTE API

        Args:
            production_type: Type of production (SOLAR, WIND, AGGREGATED_PROGRAMMABLE_FRANCE)
            forecast_type: Type of forecast (D-3, D-2, D-1, ID, CURRENT)
            start_date: Start date (timezone aware)
            end_date: End date (timezone aware)

        Returns:
            Dictionary containing forecast data
        """
        token = await self._get_access_token()
        paris_tz = ZoneInfo("Europe/Paris")

        params: Dict[str, str] = {}
        if production_type:
            params["production_type"] = production_type
        if forecast_type:
            params["type"] = forecast_type
        if start_date:
            params["start_date"] = start_date.astimezone(paris_tz).isoformat()
        if end_date:
            params["end_date"] = end_date.astimezone(paris_tz).isoformat()

        logger.debug(f"[RTE API] Requesting Generation Forecast with params: {params}")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.generation_forecast_url,
                params=params,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
            )
            logger.debug(f"[RTE API] Generation Forecast response status: {response.status_code}")

            if response.status_code != 200:
                logger.error(f"[RTE API] Generation Forecast error response: {response.text}")

            response.raise_for_status()
            data = response.json()

            logger.info("[RTE API] Received Generation Forecast data")
            return cast(dict[str, Any], data)

    async def update_generation_forecast_cache(
        self,
        db: AsyncSession,
        production_type: str | None = None,
    ) -> int:
        """
        Update French generation forecast cache in database (API v3)

        L'API v3 Generation Forecast requiert :
        - Un type de prévision (D-1, D-2, D-3) obligatoire
        - Des types de production spécifiques (SOLAR, WIND_ONSHORE, WIND_OFFSHORE)
        - Une période correspondant exactement au type (D-1 = demain uniquement)

        Args:
            db: Database session
            production_type: Optional production type filter

        Returns:
            Number of records updated
        """
        from datetime import time

        try:
            paris_tz = ZoneInfo("Europe/Paris")
            token = await self._get_access_token()
            today = date.today()

            # Types de production (API v3 sépare WIND en ONSHORE et OFFSHORE)
            prod_types = (
                [production_type]
                if production_type
                else ["SOLAR", "WIND_ONSHORE", "WIND_OFFSHORE"]
            )

            updated_count = 0

            # Stratégie de récupération :
            # - ID (intraday) : aujourd'hui et demain (mis à jour chaque heure)
            # - D-1 : aujourd'hui (prévisions faites hier pour aujourd'hui)
            # Les prévisions D-2, D-3 ne sont pas encore disponibles pour les jours futurs
            forecast_configs = [
                # (days_offset, forecast_type) - days_offset = 0 pour aujourd'hui
                (0, "ID"),    # Intraday pour aujourd'hui
                (1, "ID"),    # Intraday pour demain (si disponible)
                (0, "D-1"),   # Prévision D-1 pour aujourd'hui (faite hier)
            ]

            for days_offset, fc_type in forecast_configs:
                target_date = today + timedelta(days=days_offset)
                start_dt = datetime.combine(target_date, time(0, 0, 0)).replace(tzinfo=paris_tz)
                end_dt = datetime.combine(target_date + timedelta(days=1), time(0, 0, 0)).replace(tzinfo=paris_tz)

                for prod_type in prod_types:
                    try:
                        async with httpx.AsyncClient(timeout=30.0) as client:
                            response = await client.get(
                                self.generation_forecast_url,
                                params={
                                    "start_date": start_dt.isoformat(),
                                    "end_date": end_dt.isoformat(),
                                    "production_type": prod_type,
                                    "type": fc_type,  # Obligatoire en v3
                                },
                                headers={
                                    "Authorization": f"Bearer {token}",
                                    "Accept": "application/json",
                                },
                            )

                            if response.status_code == 400:
                                # 400 = données non disponibles pour ce type/période
                                continue

                            if response.status_code != 200:
                                logger.warning(
                                    f"[RTE] Generation forecast error for {prod_type} ({fc_type}): "
                                    f"{response.status_code}"
                                )
                                continue

                            data = response.json()
                            forecasts = data.get("forecasts", [])

                            for forecast in forecasts:
                                forecast_prod_type = forecast.get("production_type", prod_type)
                                forecast_type = forecast.get("type", fc_type)

                                for value in forecast.get("values", []):
                                    try:
                                        value_start = (
                                            datetime.fromisoformat(value["start_date"])
                                            .astimezone(UTC)
                                            .replace(tzinfo=None)
                                        )
                                        value_end = (
                                            datetime.fromisoformat(value["end_date"])
                                            .astimezone(UTC)
                                            .replace(tzinfo=None)
                                        )
                                        value_mw = value["value"]
                                        updated_date_str = value.get("updated_date")
                                        updated_date = (
                                            datetime.fromisoformat(updated_date_str)
                                            .astimezone(UTC)
                                            .replace(tzinfo=None)
                                            if updated_date_str
                                            else None
                                        )

                                        # Normaliser le type de production (WIND_ONSHORE/OFFSHORE -> WIND)
                                        normalized_prod_type = (
                                            "WIND" if "WIND" in forecast_prod_type else forecast_prod_type
                                        )

                                        # Vérifier si l'entrée existe déjà
                                        result = await db.execute(
                                            select(GenerationForecast).where(
                                                GenerationForecast.production_type == normalized_prod_type,
                                                GenerationForecast.forecast_type == forecast_type,
                                                GenerationForecast.start_date == value_start,
                                            )
                                        )
                                        existing = result.scalar_one_or_none()

                                        if existing:
                                            # Accumuler les valeurs WIND si déjà présent
                                            if "WIND" in forecast_prod_type and existing.value:
                                                existing.value = existing.value + value_mw  # type: ignore[assignment]
                                            else:
                                                existing.value = value_mw  # type: ignore[assignment]
                                            existing.end_date = value_end  # type: ignore[assignment]
                                            existing.updated_date = updated_date  # type: ignore[assignment]
                                            existing.updated_at = datetime.now(UTC).replace(tzinfo=None)  # type: ignore[assignment]
                                        else:
                                            record = GenerationForecast(
                                                production_type=normalized_prod_type,
                                                forecast_type=forecast_type,
                                                start_date=value_start,
                                                end_date=value_end,
                                                value=value_mw,
                                                updated_date=updated_date,
                                            )
                                            db.add(record)

                                        updated_count += 1

                                    except Exception as e:
                                        logger.error(f"Error processing forecast value: {e}")
                                        continue

                    except Exception as e:
                        logger.warning(f"[RTE] Could not fetch forecast for {prod_type} ({fc_type}): {e}")
                        continue

            await db.commit()
            logger.info(f"[RTE] Updated {updated_count} generation forecast records")
            return updated_count

        except Exception as e:
            await db.rollback()
            logger.error(f"[RTE] Error updating generation forecast cache: {e}")
            import traceback

            traceback.print_exc()
            return 0

    async def get_generation_forecast(
        self,
        db: AsyncSession,
        production_type: str | None = None,
        forecast_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> List[GenerationForecast]:
        """
        Get French generation forecast data from database cache

        Args:
            db: Database session
            production_type: Optional production type filter
            forecast_type: Optional forecast type filter
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of GenerationForecast objects
        """
        query = select(GenerationForecast).order_by(GenerationForecast.start_date)

        if production_type:
            query = query.where(GenerationForecast.production_type == production_type)
        if forecast_type:
            query = query.where(GenerationForecast.forecast_type == forecast_type)
        if start_date:
            # Retirer la timezone pour comparaison avec DateTime naive en DB
            start_naive = start_date.replace(tzinfo=None) if start_date.tzinfo else start_date
            query = query.where(GenerationForecast.start_date >= start_naive)
        if end_date:
            end_naive = end_date.replace(tzinfo=None) if end_date.tzinfo else end_date
            query = query.where(GenerationForecast.start_date <= end_naive)

        result = await db.execute(query)
        return list(result.scalars().all())


# Singleton instance
rte_service = RTEService()
