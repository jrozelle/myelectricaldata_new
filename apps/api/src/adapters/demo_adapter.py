"""
Demo Adapter - Provides mock data for demo accounts

This adapter intercepts Enedis API calls for demo users and returns
pre-generated mock data from Redis cache instead of making real API calls.
"""
import logging
from typing import Any, Optional
from datetime import datetime
from ..services.cache import cache_service

logger = logging.getLogger(__name__)


class DemoAdapter:
    """Adapter that provides mock data for demo accounts"""

    DEMO_EMAIL = "demo@myelectricaldata.fr"

    def __init__(self):
        self.cache_service = cache_service

    async def is_demo_user(self, user_email: str) -> bool:
        """Check if user is a demo account"""
        return user_email == self.DEMO_EMAIL

    async def get_consumption_daily(
        self,
        usage_point_id: str,
        start: str,
        end: str,
        client_secret: str,
    ) -> dict[str, Any]:
        """
        Get mock daily consumption data from cache.

        Args:
            usage_point_id: PDL number
            start: Start date (YYYY-MM-DD)
            end: End date (YYYY-MM-DD)
            client_secret: User's client secret for decryption

        Returns:
            Mock consumption data in Enedis format
        """
        logger.info(f"[DEMO] Fetching mock consumption data for {usage_point_id} from {start} to {end}")

        cache_key = f"demo:consumption:daily:{usage_point_id}"
        cached_data = await self.cache_service.get(cache_key, client_secret)

        if not cached_data:
            logger.warning(f"[DEMO] No cached consumption data found for {usage_point_id}")
            return {
                "meter_reading": {
                    "usage_point_id": usage_point_id,
                    "start": start,
                    "end": end,
                    "reading_type": {"unit": "kWh", "measurement_kind": "energy", "aggregate": "sum"},
                    "interval_reading": []
                }
            }

        # Filter data by date range
        all_data = cached_data.get("data", [])
        filtered_data = [
            item for item in all_data
            if start <= item["date"] <= end
        ]

        # Convert to Enedis format
        interval_reading = [
            {
                "value": str(item["value"]),
                "date": item["date"],
                "interval_length": "PT1D",
                "measure_type": "B",
            }
            for item in filtered_data
        ]

        logger.info(f"[DEMO] Returning {len(interval_reading)} consumption records")

        return {
            "meter_reading": {
                "usage_point_id": usage_point_id,
                "start": start,
                "end": end,
                "quality": "CORRIGE",
                "reading_type": {
                    "unit": "kWh",
                    "measurement_kind": "energy",
                    "aggregate": "sum"
                },
                "interval_reading": interval_reading
            }
        }

    async def get_consumption_detail(
        self,
        usage_point_id: str,
        start: str,
        end: str,
        client_secret: str,
    ) -> dict[str, Any]:
        """
        Get mock detailed consumption data (30-minute intervals).

        For demo purposes, we generate 30-minute intervals from daily data.
        """
        logger.info(f"[DEMO] Fetching mock detailed consumption data for {usage_point_id}")

        # Get daily data first
        daily_data = await self.get_consumption_daily(usage_point_id, start, end, client_secret)

        # Convert daily to 30-minute intervals (simplified version)
        interval_reading = []
        for daily_record in daily_data.get("meter_reading", {}).get("interval_reading", []):
            date_str = daily_record["date"]
            daily_value = float(daily_record["value"])

            # Divide daily consumption into 48 intervals (30 minutes each)
            # Simple distribution: lower at night, higher during day
            for hour in range(24):
                for half in [0, 30]:
                    # Create consumption pattern: lower at night (0-6h), higher during day
                    if 0 <= hour < 6:
                        factor = 0.5
                    elif 6 <= hour < 9:
                        factor = 1.2
                    elif 9 <= hour < 18:
                        factor = 1.0
                    elif 18 <= hour < 22:
                        factor = 1.3
                    else:
                        factor = 0.7

                    interval_value = (daily_value / 48) * factor

                    timestamp = f"{date_str}T{hour:02d}:{half:02d}:00+01:00"
                    interval_reading.append({
                        "value": f"{interval_value:.3f}",
                        "date": timestamp,
                        "interval_length": "PT30M",
                        "measure_type": "B",
                    })

        return {
            "meter_reading": {
                "usage_point_id": usage_point_id,
                "start": start,
                "end": end,
                "quality": "CORRIGE",
                "reading_type": {
                    "unit": "kWh",
                    "measurement_kind": "energy",
                    "aggregate": "sum"
                },
                "interval_reading": interval_reading
            }
        }

    async def get_production_daily(
        self,
        usage_point_id: str,
        start: str,
        end: str,
        client_secret: str,
    ) -> dict[str, Any]:
        """Get mock daily production data from cache"""
        logger.info(f"[DEMO] Fetching mock production data for {usage_point_id} from {start} to {end}")

        cache_key = f"demo:production:daily:{usage_point_id}"
        cached_data = await self.cache_service.get(cache_key, client_secret)

        if not cached_data:
            logger.warning(f"[DEMO] No cached production data found for {usage_point_id}")
            return {
                "meter_reading": {
                    "usage_point_id": usage_point_id,
                    "start": start,
                    "end": end,
                    "reading_type": {"unit": "kWh", "measurement_kind": "energy", "aggregate": "sum"},
                    "interval_reading": []
                }
            }

        # Filter data by date range
        all_data = cached_data.get("data", [])
        filtered_data = [
            item for item in all_data
            if start <= item["date"] <= end
        ]

        # Convert to Enedis format
        interval_reading = [
            {
                "value": str(item["value"]),
                "date": item["date"],
                "interval_length": "PT1D",
                "measure_type": "B",
            }
            for item in filtered_data
        ]

        logger.info(f"[DEMO] Returning {len(interval_reading)} production records")

        return {
            "meter_reading": {
                "usage_point_id": usage_point_id,
                "start": start,
                "end": end,
                "quality": "CORRIGE",
                "reading_type": {
                    "unit": "kWh",
                    "measurement_kind": "energy",
                    "aggregate": "sum"
                },
                "interval_reading": interval_reading
            }
        }

    async def get_production_detail(
        self,
        usage_point_id: str,
        start: str,
        end: str,
        client_secret: str,
    ) -> dict[str, Any]:
        """Get mock detailed production data (30-minute intervals)"""
        logger.info(f"[DEMO] Fetching mock detailed production data for {usage_point_id}")

        # Get daily data first
        daily_data = await self.get_production_daily(usage_point_id, start, end, client_secret)

        # Convert daily to 30-minute intervals
        interval_reading = []
        for daily_record in daily_data.get("meter_reading", {}).get("interval_reading", []):
            date_str = daily_record["date"]
            daily_value = float(daily_record["value"])

            # Solar production pattern: 0 at night, peak at midday
            for hour in range(24):
                for half in [0, 30]:
                    # Solar production only during daylight (6h-20h)
                    if 6 <= hour < 20:
                        # Bell curve: peak at noon (12h)
                        distance_from_noon = abs(hour - 12)
                        factor = max(0, 1 - (distance_from_noon / 6))
                        interval_value = (daily_value / 28) * factor  # 28 intervals of daylight
                    else:
                        interval_value = 0.0

                    timestamp = f"{date_str}T{hour:02d}:{half:02d}:00+01:00"
                    interval_reading.append({
                        "value": f"{interval_value:.3f}",
                        "date": timestamp,
                        "interval_length": "PT30M",
                        "measure_type": "B",
                    })

        return {
            "meter_reading": {
                "usage_point_id": usage_point_id,
                "start": start,
                "end": end,
                "quality": "CORRIGE",
                "reading_type": {
                    "unit": "kWh",
                    "measurement_kind": "energy",
                    "aggregate": "sum"
                },
                "interval_reading": interval_reading
            }
        }

    async def get_contract(
        self,
        usage_point_id: str,
        client_secret: str,
    ) -> dict[str, Any]:
        """Get mock contract information"""
        logger.info(f"[DEMO] Fetching mock contract for {usage_point_id}")

        cache_key = f"demo:contract:{usage_point_id}"
        cached_data = await self.cache_service.get(cache_key, client_secret)

        if not cached_data:
            # Return default contract if not cached
            return {
                "customer": {
                    "usage_point_id": usage_point_id,
                    "usage_point_status": "com",
                    "meter_type": "AMM"
                }
            }

        return {
            "customer": {
                "usage_point_id": usage_point_id,
                "usage_point_status": "com",
                "meter_type": "AMM",
                "subscribed_power": str(cached_data.get("subscribed_power", "6")),
                "offpeak_hours": cached_data.get("offpeak_hours"),
                "last_activation_date": cached_data.get("activation_date"),
            }
        }

    async def get_address(
        self,
        usage_point_id: str,
        client_secret: str,
    ) -> dict[str, Any]:
        """Get mock address information"""
        logger.info(f"[DEMO] Fetching mock address for {usage_point_id}")

        cache_key = f"demo:address:{usage_point_id}"
        cached_data = await self.cache_service.get(cache_key, client_secret)

        if not cached_data:
            # Return default address
            return {
                "customer": {
                    "usage_point_id": usage_point_id,
                    "usage_point_addresses": {
                        "street": "123 Rue de la Démo",
                        "locality": "Paris",
                        "postal_code": "75001",
                        "insee_code": "75101",
                        "city": "Paris",
                        "country": "France"
                    }
                }
            }

        return {
            "customer": {
                "usage_point_id": usage_point_id,
                "usage_point_addresses": {
                    "street": cached_data.get("street", "123 Rue de la Démo"),
                    "locality": cached_data.get("city", "Paris"),
                    "postal_code": cached_data.get("postal_code", "75001"),
                    "insee_code": "75101",
                    "city": cached_data.get("city", "Paris"),
                    "country": "France"
                }
            }
        }

    async def get_customer(
        self,
        usage_point_id: str,
        client_secret: str,
    ) -> dict[str, Any]:
        """Get mock customer information"""
        logger.info(f"[DEMO] Fetching mock customer for {usage_point_id}")

        return {
            "customer": {
                "customer_id": "demo_customer_123",
                "usage_point_id": usage_point_id,
                "civil_title": "MR",
                "first_name": "Demo",
                "last_name": "User"
            }
        }

    async def get_contact(
        self,
        usage_point_id: str,
        client_secret: str,
    ) -> dict[str, Any]:
        """Get mock contact information"""
        logger.info(f"[DEMO] Fetching mock contact for {usage_point_id}")

        return {
            "customer": {
                "usage_point_id": usage_point_id,
                "email": "demo@myelectricaldata.fr",
                "phone_number": "+33123456789"
            }
        }


# Global instance
demo_adapter = DemoAdapter()
