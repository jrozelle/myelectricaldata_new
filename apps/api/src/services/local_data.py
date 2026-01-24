"""Local Data Service for Client Mode

This service queries the local PostgreSQL database for cached energy data.
It implements a "local-first" strategy:
1. Check local database for requested data
2. Identify missing date ranges ("holes")
3. Only fetch missing data from gateway
4. Return combined results

This dramatically reduces API calls to the gateway.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.client_mode import (
    ConsumptionData,
    ProductionData,
    ContractData,
    AddressData,
    DataGranularity,
    SyncStatus,
)

logger = logging.getLogger(__name__)


class LocalDataService:
    """Service for querying locally cached energy data"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_consumption_daily(
        self,
        usage_point_id: str,
        start_date: date,
        end_date: date,
    ) -> tuple[list[dict[str, Any]], list[tuple[date, date]]]:
        """Get daily consumption from local database.

        Returns:
            Tuple of:
            - List of consumption records found locally
            - List of (start, end) date ranges missing locally
        """
        return await self._get_energy_data(
            model=ConsumptionData,
            usage_point_id=usage_point_id,
            start_date=start_date,
            end_date=end_date,
            granularity=DataGranularity.DAILY,
        )

    async def get_consumption_detail(
        self,
        usage_point_id: str,
        start_date: date,
        end_date: date,
    ) -> tuple[list[dict[str, Any]], list[tuple[date, date]]]:
        """Get detailed consumption (30-min intervals) from local database."""
        return await self._get_energy_data(
            model=ConsumptionData,
            usage_point_id=usage_point_id,
            start_date=start_date,
            end_date=end_date,
            granularity=DataGranularity.DETAILED,
        )

    async def get_production_daily(
        self,
        usage_point_id: str,
        start_date: date,
        end_date: date,
    ) -> tuple[list[dict[str, Any]], list[tuple[date, date]]]:
        """Get daily production from local database."""
        return await self._get_energy_data(
            model=ProductionData,
            usage_point_id=usage_point_id,
            start_date=start_date,
            end_date=end_date,
            granularity=DataGranularity.DAILY,
        )

    async def get_production_detail(
        self,
        usage_point_id: str,
        start_date: date,
        end_date: date,
    ) -> tuple[list[dict[str, Any]], list[tuple[date, date]]]:
        """Get detailed production (30-min intervals) from local database."""
        return await self._get_energy_data(
            model=ProductionData,
            usage_point_id=usage_point_id,
            start_date=start_date,
            end_date=end_date,
            granularity=DataGranularity.DETAILED,
        )

    async def get_contract(self, usage_point_id: str) -> dict[str, Any] | None:
        """Get contract data from local database."""
        result = await self.db.execute(
            select(ContractData).where(ContractData.usage_point_id == usage_point_id)
        )
        contract = result.scalar_one_or_none()

        if contract is None:
            return None

        # Return in gateway-compatible format
        return {
            "customer": {
                "usage_points": [
                    {
                        "usage_point": {"usage_point_id": usage_point_id},
                        "contracts": {
                            "subscribed_power": str(contract.subscribed_power) if contract.subscribed_power else None,
                            "offpeak_hours": contract.offpeak_hours,
                            "last_activation_date": None,
                            "distribution_tariff": contract.pricing_option,
                        }
                    }
                ]
            },
            "_cached": True,
            "_cached_at": contract.updated_at.isoformat() if contract.updated_at else None,
        }

    async def get_address(self, usage_point_id: str) -> dict[str, Any] | None:
        """Get address data from local database."""
        result = await self.db.execute(
            select(AddressData).where(AddressData.usage_point_id == usage_point_id)
        )
        address = result.scalar_one_or_none()

        if address is None:
            return None

        # Return in gateway-compatible format
        return {
            "customer": {
                "usage_points": [
                    {
                        "usage_point": {"usage_point_id": usage_point_id},
                        "usage_point_addresses": {
                            "street": address.street,
                            "postal_code": address.postal_code,
                            "city": address.city,
                            "country": address.country,
                            "insee_code": address.insee_code,
                            "geo_points": {
                                "latitude": str(address.latitude) if address.latitude else None,
                                "longitude": str(address.longitude) if address.longitude else None,
                            } if address.latitude and address.longitude else None,
                        }
                    }
                ]
            },
            "_cached": True,
            "_cached_at": address.updated_at.isoformat() if address.updated_at else None,
        }

    async def save_contract(self, usage_point_id: str, data: dict[str, Any]) -> None:
        """Save contract data to local database."""
        # Extract contract info from gateway response
        contract_info = self._extract_contract_from_response(data, usage_point_id)
        if not contract_info:
            return

        # Check if exists
        result = await self.db.execute(
            select(ContractData).where(ContractData.usage_point_id == usage_point_id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.subscribed_power = contract_info.get("subscribed_power")
            existing.pricing_option = contract_info.get("pricing_option")
            existing.offpeak_hours = contract_info.get("offpeak_hours")
            existing.raw_data = data
            existing.last_sync_at = datetime.now()
        else:
            contract = ContractData(
                usage_point_id=usage_point_id,
                subscribed_power=contract_info.get("subscribed_power"),
                pricing_option=contract_info.get("pricing_option"),
                offpeak_hours=contract_info.get("offpeak_hours"),
                raw_data=data,
                last_sync_at=datetime.now(),
            )
            self.db.add(contract)

        await self.db.commit()

    async def save_address(self, usage_point_id: str, data: dict[str, Any]) -> None:
        """Save address data to local database."""
        # Extract address info from gateway response
        address_info = self._extract_address_from_response(data, usage_point_id)
        if not address_info:
            return

        # Check if exists
        result = await self.db.execute(
            select(AddressData).where(AddressData.usage_point_id == usage_point_id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.street = address_info.get("street")
            existing.postal_code = address_info.get("postal_code")
            existing.city = address_info.get("city")
            existing.country = address_info.get("country")
            existing.insee_code = address_info.get("insee_code")
            existing.latitude = address_info.get("latitude")
            existing.longitude = address_info.get("longitude")
            existing.raw_data = data
            existing.last_sync_at = datetime.now()
        else:
            address = AddressData(
                usage_point_id=usage_point_id,
                street=address_info.get("street"),
                postal_code=address_info.get("postal_code"),
                city=address_info.get("city"),
                country=address_info.get("country"),
                insee_code=address_info.get("insee_code"),
                latitude=address_info.get("latitude"),
                longitude=address_info.get("longitude"),
                raw_data=data,
                last_sync_at=datetime.now(),
            )
            self.db.add(address)

        await self.db.commit()

    async def _get_energy_data(
        self,
        model: type[ConsumptionData | ProductionData],
        usage_point_id: str,
        start_date: date,
        end_date: date,
        granularity: DataGranularity,
    ) -> tuple[list[dict[str, Any]], list[tuple[date, date]]]:
        """Generic method to get energy data from local database.

        Returns:
            Tuple of:
            - List of records found locally (formatted for API response)
            - List of (start, end) date ranges that are missing
        """
        # Query local data
        result = await self.db.execute(
            select(model).where(
                and_(
                    model.usage_point_id == usage_point_id,
                    model.granularity == granularity,
                    model.date >= start_date,
                    model.date < end_date,  # end_date is exclusive
                )
            ).order_by(model.date, model.interval_start)
        )
        records = result.scalars().all()

        # Format records for API response
        if granularity == DataGranularity.DAILY:
            formatted = [
                {"date": rec.date.isoformat(), "value": rec.value}
                for rec in records
            ]
        else:  # DETAILED
            formatted = [
                {
                    "date": f"{rec.date.isoformat()} {rec.interval_start}:00" if rec.interval_start else rec.date.isoformat(),
                    "value": rec.value,
                }
                for rec in records
            ]

        # Find missing date ranges
        missing_ranges = await self._find_missing_ranges(
            model=model,
            usage_point_id=usage_point_id,
            start_date=start_date,
            end_date=end_date,
            granularity=granularity,
        )

        data_type = "consumption" if model == ConsumptionData else "production"
        if formatted:
            logger.info(
                f"[{usage_point_id}] Found {len(formatted)} local {data_type} records "
                f"({granularity.value}) from {start_date} to {end_date}"
            )
        if missing_ranges:
            logger.info(
                f"[{usage_point_id}] Missing {len(missing_ranges)} date ranges for {data_type} "
                f"({granularity.value}): {missing_ranges}"
            )

        return formatted, missing_ranges

    async def _find_missing_ranges(
        self,
        model: type[ConsumptionData | ProductionData],
        usage_point_id: str,
        start_date: date,
        end_date: date,
        granularity: DataGranularity,
    ) -> list[tuple[date, date]]:
        """Find date ranges that are missing from local database.

        For daily granularity, checks each day.
        For detailed granularity, checks if any data exists for each day.

        Returns list of (start, end) tuples representing missing ranges.
        """
        # Get distinct dates that have data
        result = await self.db.execute(
            select(func.distinct(model.date)).where(
                and_(
                    model.usage_point_id == usage_point_id,
                    model.granularity == granularity,
                    model.date >= start_date,
                    model.date < end_date,
                )
            )
        )
        existing_dates = {row[0] for row in result.fetchall()}

        # Generate all dates in range
        all_dates = set()
        current = start_date
        while current < end_date:
            all_dates.add(current)
            current += timedelta(days=1)

        # Find missing dates
        missing_dates = sorted(all_dates - existing_dates)

        if not missing_dates:
            return []

        # Group consecutive missing dates into ranges
        ranges: list[tuple[date, date]] = []
        range_start = missing_dates[0]
        range_end = missing_dates[0]

        for d in missing_dates[1:]:
            if d == range_end + timedelta(days=1):
                # Consecutive - extend range
                range_end = d
            else:
                # Gap - save current range and start new one
                # end is exclusive, so add 1 day
                ranges.append((range_start, range_end + timedelta(days=1)))
                range_start = d
                range_end = d

        # Don't forget the last range
        ranges.append((range_start, range_end + timedelta(days=1)))

        return ranges

    async def get_sync_status(
        self,
        usage_point_id: str,
        data_type: str,
        granularity: DataGranularity,
    ) -> SyncStatus | None:
        """Get sync status for a specific data type and granularity."""
        result = await self.db.execute(
            select(SyncStatus).where(
                and_(
                    SyncStatus.usage_point_id == usage_point_id,
                    SyncStatus.data_type == data_type,
                    SyncStatus.granularity == granularity,
                )
            )
        )
        return result.scalar_one_or_none()

    def _extract_contract_from_response(
        self, data: dict[str, Any], usage_point_id: str
    ) -> dict[str, Any] | None:
        """Extract contract info from gateway response."""
        try:
            # Navigate the nested structure
            customer = data.get("customer", data.get("data", {}).get("customer", {}))
            usage_points = customer.get("usage_points", [])

            for up in usage_points:
                if up.get("usage_point", {}).get("usage_point_id") == usage_point_id:
                    contracts = up.get("contracts", {})
                    power_str = contracts.get("subscribed_power", "0")
                    return {
                        "subscribed_power": int(power_str) if power_str else None,
                        "pricing_option": contracts.get("distribution_tariff"),
                        "offpeak_hours": contracts.get("offpeak_hours"),
                    }
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"Failed to extract contract: {e}")

        return None

    def _extract_address_from_response(
        self, data: dict[str, Any], usage_point_id: str
    ) -> dict[str, Any] | None:
        """Extract address info from gateway response."""
        try:
            # Navigate the nested structure
            customer = data.get("customer", data.get("data", {}).get("customer", {}))
            usage_points = customer.get("usage_points", [])

            for up in usage_points:
                if up.get("usage_point", {}).get("usage_point_id") == usage_point_id:
                    addr = up.get("usage_point_addresses", {})
                    geo = addr.get("geo_points", {})
                    lat = geo.get("latitude") if geo else None
                    lon = geo.get("longitude") if geo else None
                    return {
                        "street": addr.get("street"),
                        "postal_code": addr.get("postal_code"),
                        "city": addr.get("city"),
                        "country": addr.get("country"),
                        "insee_code": addr.get("insee_code"),
                        "latitude": float(lat) if lat else None,
                        "longitude": float(lon) if lon else None,
                    }
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"Failed to extract address: {e}")

        return None


def format_daily_response(
    usage_point_id: str,
    start: str,
    end: str,
    readings: list[dict[str, Any]],
    from_cache: bool = False,
) -> dict[str, Any]:
    """Format daily data in Enedis-like response format."""
    return {
        "meter_reading": {
            "usage_point_id": usage_point_id,
            "start": start,
            "end": end,
            "reading_type": {
                "unit": "Wh",
                "measurement_kind": "energy",
            },
            "interval_reading": readings,
        },
        "_from_local_cache": from_cache,
    }


def format_detail_response(
    usage_point_id: str,
    start: str,
    end: str,
    readings: list[dict[str, Any]],
    from_cache: bool = False,
) -> dict[str, Any]:
    """Format detailed data in Enedis-like response format."""
    return {
        "meter_reading": {
            "usage_point_id": usage_point_id,
            "start": start,
            "end": end,
            "reading_type": {
                "unit": "W",
                "measurement_kind": "power",
            },
            "interval_reading": readings,
        },
        "_from_local_cache": from_cache,
    }
