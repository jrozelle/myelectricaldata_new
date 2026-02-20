"""Home Assistant Exporter via MQTT Discovery

Full-featured Home Assistant exporter using MQTT Discovery for proper entity registration.
This allows entities to have unique_id, device grouping, and full HA UI management.

Compatible with the original MyElectricalData entity structure:
- Topics: myelectricaldata_rte/, myelectricaldata_edf/, myelectricaldata_consumption/, etc.
- Devices: RTE Tempo, EDF Tempo, RTE EcoWatt, Linky {pdl}

Entities created:
- RTE Tempo device:
  - sensor.myelectricaldata_tempo_today (today's color)
  - sensor.myelectricaldata_tempo_tomorrow (tomorrow's color)
- EDF Tempo device:
  - sensor.myelectricaldata_tempo_info (contract info)
  - sensor.myelectricaldata_tempo_days_{blue,white,red} (days count per color)
  - sensor.myelectricaldata_tempo_price_{blue_hp,blue_hc,white_hp,white_hc,red_hp,red_hc}
- RTE EcoWatt device:
  - sensor.myelectricaldata_ecowatt_j0 (today)
  - sensor.myelectricaldata_ecowatt_j1 (tomorrow)
  - sensor.myelectricaldata_ecowatt_j2 (day after tomorrow)
- Linky {pdl} device:
  - sensor.myelectricaldata_linky_{pdl}_consumption
  - sensor.myelectricaldata_linky_{pdl}_production
  - sensor.myelectricaldata_linky_{pdl}_consumption_history (31 last days as attributes)
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import ssl
from datetime import date, datetime, timedelta
from typing import Any

import aiomqtt
import websockets
from sqlalchemy import String, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseExporter

logger = logging.getLogger(__name__)

# Tempo quotas per season (EDF contract limits)
TEMPO_QUOTAS = {
    "BLUE": 300,   # 300 jours/an
    "WHITE": 43,   # 43 jours/an
    "RED": 22,     # 22 jours/an
}

# EDF Tempo prices (EUR/kWh) - Tarifs réglementés 2024
# Format: {color}_{period} where period is HP (heures pleines) or HC (heures creuses)
TEMPO_PRICES = {
    "blue_hc": 0.1296,   # Jour Bleu HC
    "blue_hp": 0.1609,   # Jour Bleu HP
    "white_hc": 0.1486,  # Jour Blanc HC
    "white_hp": 0.1894,  # Jour Blanc HP
    "red_hc": 0.1568,    # Jour Rouge HC
    "red_hp": 0.7562,    # Jour Rouge HP
}

# Tempo price display names
TEMPO_PRICE_NAMES = {
    "blue_hc": "Blue HC",
    "blue_hp": "Blue HP",
    "white_hc": "White HC",
    "white_hp": "White HP",
    "red_hc": "Red HC",
    "red_hp": "Red HP",
}

# Software version for device info
SOFTWARE_VERSION = "1.8.0"


class HomeAssistantExporter(BaseExporter):
    """Home Assistant exporter using MQTT Discovery

    Configuration:
        mqtt_broker: MQTT broker hostname
        mqtt_port: MQTT broker port (default: 1883)
        mqtt_username: MQTT username (optional)
        mqtt_password: MQTT password (optional)
        mqtt_use_tls: Use TLS for MQTT connection (default: False)
        entity_prefix: Entity ID prefix (default: myelectricaldata)
        discovery_prefix: HA discovery topic prefix (default: homeassistant)

    Creates entities with proper unique_id and device grouping under "MyElectricalData".
    """

    def _validate_config(self) -> None:
        """Validate Home Assistant MQTT configuration"""
        if not self.config.get("mqtt_broker"):
            raise ValueError("MQTT broker hostname is required")

        self.broker = self.config["mqtt_broker"]
        self.port = self.config.get("mqtt_port", 1883)
        self.username = self.config.get("mqtt_username")
        self.password = self.config.get("mqtt_password")
        self.use_tls = self.config.get("mqtt_use_tls", False)
        self.prefix = self.config.get("entity_prefix", "myelectricaldata")
        self.discovery_prefix = self.config.get("discovery_prefix", "homeassistant")

    def _get_device_rte_tempo(self) -> dict[str, Any]:
        """Get device info for RTE Tempo

        Original MyElectricalData device structure:
        - identifiers: "rte_tempo"
        - name: "RTE Tempo"
        - model: "RTE"
        """
        return {
            "identifiers": ["rte_tempo"],
            "name": "RTE Tempo",
            "manufacturer": "MyElectricalData",
            "model": "RTE",
            "sw_version": SOFTWARE_VERSION,
        }

    def _get_device_edf_tempo(self) -> dict[str, Any]:
        """Get device info for EDF Tempo (prices and days count)

        Original MyElectricalData device structure:
        - identifiers: "edf_tempo"
        - name: "EDF Tempo"
        - model: "EDF"
        """
        return {
            "identifiers": ["edf_tempo"],
            "name": "EDF Tempo",
            "manufacturer": "MyElectricalData",
            "model": "EDF",
            "sw_version": SOFTWARE_VERSION,
        }

    def _get_device_rte_ecowatt(self) -> dict[str, Any]:
        """Get device info for RTE EcoWatt

        Original MyElectricalData device structure:
        - identifiers: "rte_ecowatt"
        - name: "RTE EcoWatt"
        - model: "RTE"
        """
        return {
            "identifiers": ["rte_ecowatt"],
            "name": "RTE EcoWatt",
            "manufacturer": "MyElectricalData",
            "model": "RTE",
            "sw_version": SOFTWARE_VERSION,
        }

    def _get_device_linky(self, pdl: str) -> dict[str, Any]:
        """Get device info for a Linky meter (per PDL)

        Original MyElectricalData device structure:
        - identifiers: "{pdl}"
        - name: "Linky {pdl}"
        - model: "linky {pdl}"

        Args:
            pdl: The usage point ID (PDL number)
        """
        return {
            "identifiers": [pdl],
            "name": f"Linky {pdl}",
            "manufacturer": "MyElectricalData",
            "model": f"linky {pdl}",
            "sw_version": SOFTWARE_VERSION,
        }

    # Legacy compatibility
    def _get_device_info(self, pdl: str | None = None) -> dict[str, Any]:
        """Legacy method - use specific device methods instead"""
        if pdl:
            return self._get_device_linky(pdl)
        else:
            # Default to RTE Tempo for global sensors
            return self._get_device_rte_tempo()

    async def _get_mqtt_client(self) -> aiomqtt.Client:
        """Create and return an MQTT client

        Returns:
            Configured aiomqtt.Client instance
        """
        tls_context = None
        if self.use_tls:
            tls_context = ssl.create_default_context()

        return aiomqtt.Client(
            hostname=self.broker,
            port=self.port,
            username=self.username,
            password=self.password,
            tls_context=tls_context,
        )

    async def test_connection(self) -> bool:
        """Test connection to MQTT broker

        Returns:
            True if connection successful

        Raises:
            Exception if connection fails
        """
        async with await self._get_mqtt_client() as client:
            # Publish a test message
            await client.publish(
                f"{self.prefix}/status",
                payload="online",
                retain=True,
            )
            logger.info(f"[HA-MQTT] Connected to MQTT broker: {self.broker}:{self.port}")
            return True

    async def export_consumption(
        self,
        usage_point_id: str,
        data: list[dict[str, Any]],
        granularity: str,
    ) -> int:
        """Export consumption data to Home Assistant via MQTT Discovery

        Args:
            usage_point_id: PDL number
            data: List of consumption records
            granularity: 'daily' or 'detailed'

        Returns:
            Number of records exported
        """
        if not data:
            return 0

        total_kwh = sum(r.get("value", 0) for r in data) / 1000
        latest = data[-1] if data else None

        unique_id = f"{self.prefix}_{usage_point_id}_consumption_{granularity}"
        state_topic = f"{self.prefix}/{usage_point_id}/consumption/{granularity}"

        # Discovery config
        discovery_config = {
            "unique_id": unique_id,
            "object_id": unique_id,
            "name": f"Consommation {usage_point_id} ({granularity})",
            "state_topic": state_topic,
            "unit_of_measurement": "kWh",
            "device_class": "energy",
            "state_class": "total_increasing",
            "value_template": "{{ value_json.value }}",
            "json_attributes_topic": state_topic,
            "device": self._get_device_info(usage_point_id),
        }

        # State payload
        state_payload = {
            "value": round(total_kwh, 2),
            "usage_point_id": usage_point_id,
            "granularity": granularity,
            "records_count": len(data),
            "last_update": latest.get("date") if latest else None,
        }

        async with await self._get_mqtt_client() as client:
            # Publish discovery config
            # Format: homeassistant/sensor/{node_id}/{object_id}/config
            object_id = f"{usage_point_id}_consumption_{granularity}"
            await client.publish(
                f"{self.discovery_prefix}/sensor/{self.prefix}/{object_id}/config",
                payload=json.dumps(discovery_config),
                retain=True,
            )
            # Publish state
            await client.publish(
                state_topic,
                payload=json.dumps(state_payload),
                retain=True,
            )

        logger.info(f"[HA-MQTT] Exported consumption for {usage_point_id}: {len(data)} records, {total_kwh:.2f} kWh")
        return len(data)

    async def export_production(
        self,
        usage_point_id: str,
        data: list[dict[str, Any]],
        granularity: str,
    ) -> int:
        """Export production data to Home Assistant via MQTT Discovery

        Args:
            usage_point_id: PDL number
            data: List of production records
            granularity: 'daily' or 'detailed'

        Returns:
            Number of records exported
        """
        if not data:
            return 0

        total_kwh = sum(r.get("value", 0) for r in data) / 1000
        latest = data[-1] if data else None

        unique_id = f"{self.prefix}_{usage_point_id}_production_{granularity}"
        state_topic = f"{self.prefix}/{usage_point_id}/production/{granularity}"

        discovery_config = {
            "unique_id": unique_id,
            "object_id": unique_id,
            "name": f"Production {usage_point_id} ({granularity})",
            "state_topic": state_topic,
            "unit_of_measurement": "kWh",
            "device_class": "energy",
            "state_class": "total_increasing",
            "value_template": "{{ value_json.value }}",
            "json_attributes_topic": state_topic,
            "device": self._get_device_info(usage_point_id),
        }

        state_payload = {
            "value": round(total_kwh, 2),
            "usage_point_id": usage_point_id,
            "granularity": granularity,
            "records_count": len(data),
            "last_update": latest.get("date") if latest else None,
        }

        async with await self._get_mqtt_client() as client:
            # Format: homeassistant/sensor/{node_id}/{object_id}/config
            object_id = f"{usage_point_id}_production_{granularity}"
            await client.publish(
                f"{self.discovery_prefix}/sensor/{self.prefix}/{object_id}/config",
                payload=json.dumps(discovery_config),
                retain=True,
            )
            await client.publish(
                state_topic,
                payload=json.dumps(state_payload),
                retain=True,
            )

        logger.info(f"[HA-MQTT] Exported production for {usage_point_id}: {len(data)} records, {total_kwh:.2f} kWh")
        return len(data)

    # =========================================================================
    # FULL EXPORT METHOD
    # =========================================================================

    async def run_full_export(self, db: AsyncSession, usage_point_ids: list[str]) -> dict[str, Any]:
        """Run full Home Assistant export via MQTT Discovery

        This method exports comprehensive data:
        - Consumption/Production statistics (daily, monthly, yearly)
        - Tempo information (colors, remaining days)
        - EcoWatt signals

        All entities are created with unique_id and grouped under device "MyElectricalData".

        Args:
            db: Database session
            usage_point_ids: List of PDL numbers to export

        Returns:
            Export results summary
        """
        from ..statistics import StatisticsService
        stats = StatisticsService(db)

        results = {
            "consumption": 0,
            "production": 0,
            "tempo": 0,
            "ecowatt": 0,
            "errors": [],
        }

        async with await self._get_mqtt_client() as client:
            # Publish online status
            await client.publish(
                f"{self.prefix}/status",
                payload="online",
                retain=True,
            )

            # Global exports (not PDL-specific)
            try:
                count = await self._export_tempo(client, db, usage_point_ids)
                results["tempo"] = count
            except Exception as e:
                logger.error(f"[HA-MQTT] Tempo export failed: {e}")
                results["errors"].append(f"tempo: {str(e)}")

            try:
                count = await self._export_ecowatt(client, db)
                results["ecowatt"] = count
            except Exception as e:
                logger.error(f"[HA-MQTT] EcoWatt export failed: {e}")
                results["errors"].append(f"ecowatt: {str(e)}")

            # Per-PDL exports
            for pdl in usage_point_ids:
                try:
                    count = await self._export_consumption_stats(client, stats, pdl)
                    results["consumption"] += count

                    count = await self._export_production_stats(client, stats, pdl)
                    results["production"] += count

                except Exception as e:
                    logger.error(f"[HA-MQTT] Export failed for PDL {pdl}: {e}")
                    results["errors"].append(f"{pdl}: {str(e)}")

        logger.info(f"[HA-MQTT] Full export completed: {results}")
        return results

    async def _publish_sensor_old_format(
        self,
        client: aiomqtt.Client,
        topic: str,
        name: str,
        unique_id: str,
        device: dict[str, Any],
        state: Any,
        attributes: dict[str, Any] | None = None,
        unit: str | None = None,
        device_class: str | None = None,
        state_class: str | None = None,
        icon: str | None = None,
    ) -> None:
        """Publish a sensor via MQTT Discovery using old MyElectricalData format

        Original format from MyElectricalData:
        - Discovery config: {discovery_prefix}/sensor/{topic}/config
        - State topic: {discovery_prefix}/sensor/{topic}/state
        - Attributes topic: {discovery_prefix}/sensor/{topic}/attributes

        Args:
            client: MQTT client
            topic: Topic path (e.g., "myelectricaldata_rte/tempo_today")
            name: Display name for the entity
            unique_id: Unique ID for the entity (e.g., "myelectricaldata_tempo_today")
            device: Device info dict
            state: Current state value
            attributes: Additional attributes (optional)
            unit: Unit of measurement (optional)
            device_class: HA device class (optional)
            state_class: HA state class (optional)
            icon: MDI icon (optional)
        """
        # Base paths
        config_topic = f"{self.discovery_prefix}/sensor/{topic}/config"
        state_topic = f"{self.discovery_prefix}/sensor/{topic}/state"
        attributes_topic = f"{self.discovery_prefix}/sensor/{topic}/attributes"

        # Build discovery config
        discovery_config: dict[str, Any] = {
            "name": name,
            "uniq_id": unique_id,
            "obj_id": unique_id,
            "stat_t": state_topic,
            "json_attr_t": attributes_topic,
            "device": device,
        }

        if unit:
            discovery_config["unit_of_meas"] = unit
        if device_class:
            discovery_config["dev_cla"] = device_class
        if state_class:
            discovery_config["stat_cla"] = state_class
        if icon:
            discovery_config["ic"] = icon

        # Publish discovery config (retained)
        await client.publish(
            config_topic,
            payload=json.dumps(discovery_config),
            retain=True,
        )

        # Publish state (retained) - simple value, not JSON
        state_str = str(state) if state is not None else ""
        await client.publish(
            state_topic,
            payload=state_str,
            retain=True,
        )

        # Publish attributes (retained) - JSON object
        if attributes:
            await client.publish(
                attributes_topic,
                payload=json.dumps(attributes),
                retain=True,
            )

    # Keep the old method for compatibility but marked as deprecated
    async def _publish_sensor(
        self,
        client: aiomqtt.Client,
        unique_id: str,
        name: str,
        state_topic: str,
        state: Any,
        attributes: dict[str, Any],
        device: dict[str, Any],
        unit: str | None = None,
        device_class: str | None = None,
        state_class: str | None = None,
        icon: str | None = None,
        entity_category: str | None = None,
    ) -> None:
        """Publish a sensor via MQTT Discovery (legacy method, use _publish_sensor_old_format)"""
        # Build discovery config
        discovery_config: dict[str, Any] = {
            "unique_id": unique_id,
            "object_id": unique_id,
            "name": name,
            "state_topic": state_topic,
            "value_template": "{{ value_json.state }}",
            "json_attributes_topic": state_topic,
            "device": device,
        }

        if unit:
            discovery_config["unit_of_measurement"] = unit
        if device_class:
            discovery_config["device_class"] = device_class
        if state_class:
            discovery_config["state_class"] = state_class
        if icon:
            discovery_config["icon"] = icon
        if entity_category:
            discovery_config["entity_category"] = entity_category

        # Build state payload
        state_payload = {
            "state": state,
            **attributes,
        }

        # Publish discovery config (retained)
        object_id = unique_id.replace(f"{self.prefix}_", "", 1) if unique_id.startswith(f"{self.prefix}_") else unique_id
        await client.publish(
            f"{self.discovery_prefix}/sensor/{self.prefix}/{object_id}/config",
            payload=json.dumps(discovery_config),
            retain=True,
        )

        # Publish state (retained)
        await client.publish(
            state_topic,
            payload=json.dumps(state_payload),
            retain=True,
        )

    async def _publish_binary_sensor(
        self,
        client: aiomqtt.Client,
        unique_id: str,
        name: str,
        state_topic: str,
        is_on: bool,
        attributes: dict[str, Any],
        device: dict[str, Any],
        device_class: str | None = None,
        icon: str | None = None,
    ) -> None:
        """Publish a binary sensor via MQTT Discovery

        Args:
            client: MQTT client
            unique_id: Unique ID for the entity
            name: Display name
            state_topic: Topic for state updates
            is_on: Whether the binary sensor is on
            attributes: Additional attributes
            device: Device info dict
            device_class: HA device class (optional)
            icon: MDI icon (optional)
        """
        discovery_config: dict[str, Any] = {
            "unique_id": unique_id,
            "object_id": unique_id,
            "name": name,
            "state_topic": state_topic,
            "value_template": "{{ value_json.state }}",
            "payload_on": "ON",
            "payload_off": "OFF",
            "json_attributes_topic": state_topic,
            "device": device,
        }

        if device_class:
            discovery_config["device_class"] = device_class
        if icon:
            discovery_config["icon"] = icon

        state_payload = {
            "state": "ON" if is_on else "OFF",
            **attributes,
        }

        # Format: homeassistant/binary_sensor/{node_id}/{object_id}/config
        object_id = unique_id.replace(f"{self.prefix}_", "", 1) if unique_id.startswith(f"{self.prefix}_") else unique_id
        await client.publish(
            f"{self.discovery_prefix}/binary_sensor/{self.prefix}/{object_id}/config",
            payload=json.dumps(discovery_config),
            retain=True,
        )

        await client.publish(
            state_topic,
            payload=json.dumps(state_payload),
            retain=True,
        )

    # =========================================================================
    # CONSUMPTION/PRODUCTION STATISTICS
    # =========================================================================

    @staticmethod
    def _safe_evolution_percent(current_value: float, reference_value: float) -> float:
        """Return percentage evolution, guarded against division by zero."""
        if reference_value == 0:
            return 0.0
        return round(((current_value - reference_value) / reference_value) * 100, 2)

    @staticmethod
    def _normalize_offpeak_hours(offpeak_raw: Any) -> list[dict[str, str]]:
        """Normalize off-peak configuration to [{'start': 'HH:MM', 'end': 'HH:MM'}]."""
        normalized: list[dict[str, str]] = []

        def add_range(start: str, end: str) -> None:
            normalized.append({"start": start, "end": end})

        def parse_range_string(range_str: str) -> None:
            match = re.search(r"(\d{1,2})[h:](\d{2})\s*-\s*(\d{1,2})[h:](\d{2})", range_str)
            if not match:
                return
            add_range(
                f"{match.group(1).zfill(2)}:{match.group(2)}",
                f"{match.group(3).zfill(2)}:{match.group(4)}",
            )

        if isinstance(offpeak_raw, list):
            for item in offpeak_raw:
                if isinstance(item, dict):
                    start = item.get("start")
                    end = item.get("end")
                    if isinstance(start, str) and isinstance(end, str):
                        add_range(start, end)
                elif isinstance(item, str):
                    parse_range_string(item)
            return normalized

        if isinstance(offpeak_raw, dict):
            ranges = offpeak_raw.get("ranges")
            if isinstance(ranges, list):
                for item in ranges:
                    if isinstance(item, str):
                        parse_range_string(item)
                    elif isinstance(item, dict):
                        start = item.get("start")
                        end = item.get("end")
                        if isinstance(start, str) and isinstance(end, str):
                            add_range(start, end)
            for value in offpeak_raw.values():
                if isinstance(value, str):
                    parse_range_string(value)
                elif isinstance(value, list):
                    for sub_item in value:
                        if isinstance(sub_item, str):
                            parse_range_string(sub_item)
            return normalized

        return normalized

    def _is_offpeak_interval(self, interval_start: str | None, offpeak_hours: list[dict[str, str]]) -> bool:
        """Check if an interval start time is in off-peak period."""
        if not interval_start:
            return False

        # Default HC range when no contract schedule is available.
        periods = offpeak_hours or [{"start": "22:00", "end": "06:00"}]

        try:
            hour, minute = map(int, interval_start.split(":"))
            current_minutes = hour * 60 + minute
        except ValueError:
            return False

        for period in periods:
            try:
                start_h, start_m = map(int, period["start"].split(":"))
                end_h, end_m = map(int, period["end"].split(":"))
            except (KeyError, ValueError):
                continue

            start_minutes = start_h * 60 + start_m
            end_minutes = end_h * 60 + end_m

            # Overnight range (e.g. 22:00 -> 06:00)
            if start_minutes > end_minutes:
                if current_minutes >= start_minutes or current_minutes < end_minutes:
                    return True
            elif start_minutes <= current_minutes < end_minutes:
                return True

        return False

    @staticmethod
    def _detailed_value_to_wh(value: int, raw_data: dict[str, Any] | None) -> float:
        """Convert a detailed record value to Wh.

        Some MED payloads expose interval power values (W), others already provide Wh.
        We use interval_length when available to normalize.
        """
        if value is None:
            return 0.0

        if not raw_data:
            # Historical default used by the existing code path.
            return float(value) / 2

        interval_length = str(raw_data.get("interval_length", "PT30M"))
        match = re.match(r"PT(\d+)M", interval_length)
        if not match:
            # Daily/unknown payloads are already in Wh.
            return float(value)

        interval_minutes = int(match.group(1))
        if interval_minutes <= 0:
            return float(value)

        return float(value) / (60 / interval_minutes)

    async def _resolve_linky_pricing_context(
        self,
        db: AsyncSession,
        pdl: str,
    ) -> tuple[str, list[dict[str, str]], dict[str, float], int | None]:
        """Resolve pricing option, offpeak hours, prices and subscribed power for one PDL."""
        from ...models.client_mode import ContractData
        from ...models.energy_provider import EnergyOffer
        from ...models.pdl import PDL

        pricing_option = "BASE"
        offpeak_hours: list[dict[str, str]] = []
        subscribed_power: int | None = None

        # Default prices keep output deterministic (never NaN in card).
        prices: dict[str, float] = {
            "base": 0.0,
            "hc": 0.0,
            "hp": 0.0,
            **TEMPO_PRICES,
        }

        pdl_result = await db.execute(
            select(PDL).where(PDL.usage_point_id == pdl)
        )
        pdl_record = pdl_result.scalar_one_or_none()
        selected_offer_id = pdl_record.selected_offer_id if pdl_record else None

        if pdl_record and pdl_record.pricing_option:
            pricing_option = str(pdl_record.pricing_option).upper()
        if pdl_record and pdl_record.subscribed_power is not None:
            subscribed_power = int(pdl_record.subscribed_power)
        if pdl_record and pdl_record.offpeak_hours:
            offpeak_hours = self._normalize_offpeak_hours(pdl_record.offpeak_hours)

        contract_result = await db.execute(
            select(ContractData).where(ContractData.usage_point_id == pdl)
        )
        contract = contract_result.scalar_one_or_none()
        if contract and contract.pricing_option:
            pricing_option = str(contract.pricing_option).upper()
        if contract and contract.subscribed_power is not None:
            subscribed_power = int(contract.subscribed_power)
        if contract and contract.offpeak_hours:
            normalized = self._normalize_offpeak_hours(contract.offpeak_hours)
            if normalized:
                offpeak_hours = normalized

        if selected_offer_id:
            offer_result = await db.execute(
                select(EnergyOffer).where(EnergyOffer.id == selected_offer_id)
            )
            offer = offer_result.scalar_one_or_none()
            if offer:
                if offer.base_price is not None:
                    prices["base"] = float(offer.base_price)
                if offer.hc_price is not None:
                    prices["hc"] = float(offer.hc_price)
                if offer.hp_price is not None:
                    prices["hp"] = float(offer.hp_price)
                if offer.tempo_blue_hc is not None:
                    prices["blue_hc"] = float(offer.tempo_blue_hc)
                if offer.tempo_blue_hp is not None:
                    prices["blue_hp"] = float(offer.tempo_blue_hp)
                if offer.tempo_white_hc is not None:
                    prices["white_hc"] = float(offer.tempo_white_hc)
                if offer.tempo_white_hp is not None:
                    prices["white_hp"] = float(offer.tempo_white_hp)
                if offer.tempo_red_hc is not None:
                    prices["red_hc"] = float(offer.tempo_red_hc)
                if offer.tempo_red_hp is not None:
                    prices["red_hp"] = float(offer.tempo_red_hp)

        return pricing_option, offpeak_hours, prices, subscribed_power

    async def _get_day_hp_hc_kwh(
        self,
        db: AsyncSession,
        pdl: str,
        target_day: date,
        offpeak_hours: list[dict[str, str]],
    ) -> tuple[float, float, int]:
        """Return (HC_kWh, HP_kWh, interval_count) for one day from detailed data."""
        from ...models.client_mode import ConsumptionData, DataGranularity

        result = await db.execute(
            select(ConsumptionData.interval_start, ConsumptionData.value, ConsumptionData.raw_data)
            .where(ConsumptionData.usage_point_id == pdl)
            .where(ConsumptionData.granularity == DataGranularity.DETAILED)
            .where(ConsumptionData.date == target_day)
        )

        hc_wh = 0.0
        hp_wh = 0.0
        interval_count = 0
        for interval_start, value, raw_data in result.all():
            interval_count += 1
            value_wh = self._detailed_value_to_wh(int(value or 0), raw_data)
            if self._is_offpeak_interval(interval_start, offpeak_hours):
                hc_wh += value_wh
            else:
                hp_wh += value_wh

        return round(hc_wh / 1000, 3), round(hp_wh / 1000, 3), interval_count

    async def _get_day_max_power(
        self,
        db: AsyncSession,
        pdl: str,
        target_day: date,
    ) -> tuple[float, str]:
        """Return max power (kW) and time ISO string for one day from max_power_data."""
        from ...models.client_mode import MaxPowerData

        result = await db.execute(
            select(MaxPowerData.interval_start, MaxPowerData.value)
            .where(MaxPowerData.usage_point_id == pdl)
            .where(MaxPowerData.date == target_day)
            .limit(1)
        )
        row = result.first()
        if not row:
            return 0.0, f"{target_day.isoformat()}T00:00:00"

        interval_start, value = row
        hhmm = interval_start if interval_start else "00:00"
        kw = round(float(value or 0) / 1000.0, 2)
        return kw, f"{target_day.isoformat()}T{hhmm}:00"

    @staticmethod
    def _compute_day_costs(
        pricing_option: str,
        prices: dict[str, float],
        total_kwh: float,
        hc_kwh: float,
        hp_kwh: float,
        tempo_color: str | None,
    ) -> tuple[float, float, float]:
        """Return (total_cost, hc_cost, hp_cost) in EUR."""
        option = pricing_option.upper()
        color = (tempo_color or "BLUE").upper()

        if "TEMPO" in option:
            hc_price = prices.get(f"{color.lower()}_hc", 0.0)
            hp_price = prices.get(f"{color.lower()}_hp", 0.0)
            hc_cost = hc_kwh * hc_price
            hp_cost = hp_kwh * hp_price
            return round(hc_cost + hp_cost, 2), round(hc_cost, 2), round(hp_cost, 2)

        if option in ("HC/HP", "HCHP", "EJP", "HC_HP"):
            hc_cost = hc_kwh * prices.get("hc", 0.0)
            hp_cost = hp_kwh * prices.get("hp", 0.0)
            return round(hc_cost + hp_cost, 2), round(hc_cost, 2), round(hp_cost, 2)

        base_cost = total_kwh * prices.get("base", 0.0)
        return round(base_cost, 2), 0.0, 0.0

    @staticmethod
    def _choose_preferred_day_total_kwh(
        daily_total_kwh: float,
        hc_kwh: float,
        hp_kwh: float,
        detailed_interval_count: int = 0,
    ) -> float:
        """Choose a robust day total in kWh.

        Behavior:
        - Always trust DAILY total for the day when available.
        - If DAILY is missing/zero, fallback to HC+HP sum from detailed data
          so the card doesn't show 0 while HC/HP/cost have real values.
        """
        daily = round(float(daily_total_kwh), 2)
        if daily > 0:
            return daily
        detailed_sum = round(hc_kwh + hp_kwh, 2)
        if detailed_sum > 0 and detailed_interval_count >= 10:
            return detailed_sum
        return 0.0

    async def _build_linky_card_attributes(
        self,
        stats: Any,
        pdl: str,
        requested_date: date,
        data_wh: int,
        history: dict[str, float],
    ) -> dict[str, Any]:
        """Build legacy attributes expected by content-card-linky."""
        from ...models.tempo_day import TempoDay

        db: AsyncSession = stats.db
        # Derive today from the caller's requested_date (= yesterday) to avoid
        # date.today() returning a stale date if the export runs around midnight.
        today = requested_date + timedelta(days=1)
        yesterday = requested_date

        pricing_option, offpeak_hours, prices, subscribed_power = await self._resolve_linky_pricing_context(db, pdl)

        # Last 31 days in newest -> oldest order (matches legacy card expectations).
        days_desc = [today - timedelta(days=i) for i in range(1, 32)]
        week_days_desc = days_desc[:7]

        # Tempo colors for table (newest -> oldest).
        tempo_start = min(week_days_desc)
        tempo_end = max(week_days_desc)
        tempo_result = await db.execute(
            select(TempoDay.id, TempoDay.color)
            .where(cast(TempoDay.id, String) >= tempo_start.isoformat())
            .where(cast(TempoDay.id, String) <= tempo_end.isoformat())
        )
        tempo_by_day = {
            row.id: (row.color.value if hasattr(row.color, "value") else str(row.color))
            for row in tempo_result.all()
        }

        daily_values: list[float] = []
        dailyweek_dates: list[str] = []
        dailyweek_cost: list[float] = []
        dailyweek_cost_hc: list[float] = []
        dailyweek_cost_hp: list[float] = []
        dailyweek_hc: list[float] = []
        dailyweek_hp: list[float] = []
        dailyweek_tempo: list[str] = []
        dailyweek_mp: list[float] = []
        dailyweek_mp_over: list[str] = []
        dailyweek_mp_time: list[str] = []

        for target_day in days_desc:
            total_kwh = round(float(history.get(target_day.isoformat(), 0.0)), 2)
            day_total_kwh = total_kwh

            if target_day in week_days_desc:
                day_key = target_day.isoformat()
                dailyweek_dates.append(day_key)

                hc_kwh, hp_kwh, detailed_interval_count = await self._get_day_hp_hc_kwh(
                    db, pdl, target_day, offpeak_hours
                )
                dailyweek_hc.append(round(hc_kwh, 2))
                dailyweek_hp.append(round(hp_kwh, 2))
                day_total_kwh = self._choose_preferred_day_total_kwh(
                    total_kwh,
                    hc_kwh,
                    hp_kwh,
                    detailed_interval_count=detailed_interval_count,
                )

                tempo_color = tempo_by_day.get(day_key)
                dailyweek_tempo.append(tempo_color if tempo_color else "-1")

                total_cost, hc_cost, hp_cost = self._compute_day_costs(
                    pricing_option=pricing_option,
                    prices=prices,
                    total_kwh=day_total_kwh,
                    hc_kwh=hc_kwh,
                    hp_kwh=hp_kwh,
                    tempo_color=tempo_color,
                )
                dailyweek_cost.append(total_cost)
                dailyweek_cost_hc.append(hc_cost)
                dailyweek_cost_hp.append(hp_cost)

                max_power_kw, max_power_time = await self._get_day_max_power(db, pdl, target_day)
                dailyweek_mp.append(max_power_kw)
                is_over = bool(subscribed_power is not None and max_power_kw > float(subscribed_power))
                dailyweek_mp_over.append("true" if is_over else "false")
                dailyweek_mp_time.append(max_power_time)

            daily_values.append(day_total_kwh)

        yesterday_hc = 0.0
        yesterday_hp = 0.0
        if week_days_desc:
            # week_days_desc[0] is J-1
            yesterday_hc = dailyweek_hc[0] if len(dailyweek_hc) > 0 else 0.0
            yesterday_hp = dailyweek_hp[0] if len(dailyweek_hp) > 0 else 0.0

        yesterday_total = daily_values[0] if daily_values else round(data_wh / 1000, 2)
        day_2_total = daily_values[1] if len(daily_values) > 1 else 0.0

        current_year = round(await stats.get_year_total(pdl, today.year, "consumption") / 1000, 2)
        current_year_last_year = round(await stats.get_year_total(pdl, today.year - 1, "consumption") / 1000, 2)

        prev_month_date = today.replace(day=1) - timedelta(days=1)
        last_month = round(
            await stats.get_month_total(pdl, prev_month_date.year, prev_month_date.month, "consumption") / 1000,
            2,
        )
        last_month_last_year = round(
            await stats.get_month_total(pdl, prev_month_date.year - 1, prev_month_date.month, "consumption") / 1000,
            2,
        )
        current_month = round(await stats.get_month_total(pdl, today.year, today.month, "consumption") / 1000, 2)
        current_month_last_year = round(
            await stats.get_month_total(pdl, today.year - 1, today.month, "consumption") / 1000,
            2,
        )

        current_iso_year, current_iso_week, _ = today.isocalendar()
        current_week = round(await stats.get_week_total(pdl, current_iso_year, current_iso_week, "consumption") / 1000, 2)
        previous_week_date = today - timedelta(days=7)
        previous_iso_year, previous_iso_week, _ = previous_week_date.isocalendar()
        last_week = round(
            await stats.get_week_total(pdl, previous_iso_year, previous_iso_week, "consumption") / 1000,
            2,
        )

        peak_offpeak_percent = 0.0
        if (yesterday_hp + yesterday_hc) > 0:
            peak_offpeak_percent = round((yesterday_hp / (yesterday_hp + yesterday_hc)) * 100, 2)

        return {
            # Existing metadata
            "pdl": pdl,
            "date": yesterday.isoformat(),
            "value_wh": data_wh,
            "data_date": yesterday.isoformat(),
            "data_source": "requested_day",
            "history": history,
            "last_updated": datetime.now().isoformat(),
            # Legacy card attributes
            "unit_of_measurement": "kWh",
            "daily": daily_values,
            "dailyweek": dailyweek_dates,
            "dailyweek_cost": dailyweek_cost,
            "dailyweek_costHC": dailyweek_cost_hc,
            "dailyweek_costHP": dailyweek_cost_hp,
            "dailyweek_HC": dailyweek_hc,
            "dailyweek_HP": dailyweek_hp,
            "dailyweek_MP": dailyweek_mp,
            "dailyweek_MP_over": dailyweek_mp_over,
            "dailyweek_MP_time": dailyweek_mp_time,
            "dailyweek_Tempo": dailyweek_tempo,
            "yesterday": yesterday_total,
            "day_2": day_2_total,
            "yesterday_HC": round(yesterday_hc, 2),
            "yesterday_HP": round(yesterday_hp, 2),
            "daily_cost": dailyweek_cost[0] if dailyweek_cost else 0.0,
            "peak_offpeak_percent": peak_offpeak_percent,
            "current_year": current_year,
            "current_year_last_year": current_year_last_year,
            "yearly_evolution": self._safe_evolution_percent(current_year, current_year_last_year),
            "last_month": last_month,
            "last_month_last_year": last_month_last_year,
            "monthly_evolution": self._safe_evolution_percent(last_month, last_month_last_year),
            "current_month": current_month,
            "current_month_last_year": current_month_last_year,
            "current_month_evolution": self._safe_evolution_percent(current_month, current_month_last_year),
            "current_week": current_week,
            "last_week": last_week,
            "current_week_evolution": self._safe_evolution_percent(current_week, last_week),
            "yesterday_evolution": self._safe_evolution_percent(yesterday_total, day_2_total),
            # Keep optional legacy fields explicit to avoid undefined in card templates.
            "errorLastCall": "",
            "serviceEnedis": "myElectricalData",
            "versionUpdateAvailable": False,
            "versionGit": SOFTWARE_VERSION,
        }

    async def _export_consumption_stats(
        self,
        client: aiomqtt.Client,
        stats: Any,
        pdl: str,
    ) -> int:
        """Export consumption statistics for a PDL via MQTT Discovery (old format)

        Creates entities under Linky {pdl} device:
        - sensor.myelectricaldata_linky_{pdl}_consumption (daily value with history in attributes)
        - sensor.myelectricaldata_linky_{pdl}_consumption_last7day (last 7 days total)
        - sensor.myelectricaldata_linky_{pdl}_consumption_last14day (last 14 days total)
        - sensor.myelectricaldata_linky_{pdl}_consumption_last30day (last 30 days total)
        """
        today = date.today()
        yesterday = today - timedelta(days=1)
        count = 0
        device = self._get_device_linky(pdl)

        # Strict behavior: only publish J-1 daily value.
        # If J-1 is missing, keep 0.
        requested_date = yesterday
        data_wh = await stats.get_day_total(pdl, requested_date, "consumption")
        data_kwh = round(data_wh / 1000, 2)

        _, offpeak_hours, _, _ = await self._resolve_linky_pricing_context(stats.db, pdl)

        # Get last N days history for attributes
        history = {}
        for i in range(1, 32):  # Last 31 days
            day = today - timedelta(days=i)
            day_wh = await stats.get_day_total(pdl, day, "consumption")
            daily_kwh = round(day_wh / 1000, 2)
            hc_kwh, hp_kwh, detailed_interval_count = await self._get_day_hp_hc_kwh(
                stats.db, pdl, day, offpeak_hours
            )
            history[day.isoformat()] = self._choose_preferred_day_total_kwh(
                daily_total_kwh=daily_kwh,
                hc_kwh=hc_kwh,
                hp_kwh=hp_kwh,
                detailed_interval_count=detailed_interval_count,
            )

        attributes = await self._build_linky_card_attributes(
            stats=stats,
            pdl=pdl,
            requested_date=requested_date,
            data_wh=data_wh,
            history=history,
        )

        # Main consumption sensor with history in attributes
        await self._publish_sensor_old_format(
            client,
            topic=f"{self.prefix}_consumption/{pdl}",
            name="consumption",
            unique_id=f"{self.prefix}_linky_{pdl}_consumption",
            device=device,
            state=attributes.get("yesterday", data_kwh),
            attributes=attributes,
            unit="kWh",
            device_class="energy",
            state_class="total",
            icon="mdi:lightning-bolt",
        )
        count += 1

        # Last N days aggregates
        for days_count in [7, 14, 30]:
            total_kwh = 0.0
            for i in range(1, days_count + 1):
                day = today - timedelta(days=i)
                total_kwh += float(history.get(day.isoformat(), 0.0))

            await self._publish_sensor_old_format(
                client,
                topic=f"{self.prefix}_consumption_last_{days_count}_day/{pdl}",
                name=f"consumption last{days_count}day",
                unique_id=f"{self.prefix}_linky_{pdl}_consumption_last{days_count}day",
                device=device,
                state=round(total_kwh, 2),
                attributes={
                    "pdl": pdl,
                    "days": days_count,
                    "start_date": (today - timedelta(days=days_count)).isoformat(),
                    "end_date": yesterday.isoformat(),
                },
                unit="kWh",
                device_class="energy",
                state_class="total",
                icon="mdi:chart-line",
            )
            count += 1

        logger.debug(f"[HA-MQTT] Exported consumption stats for {pdl}: {count} sensors")
        return count

    async def _export_production_stats(
        self,
        client: aiomqtt.Client,
        stats: Any,
        pdl: str,
    ) -> int:
        """Export production statistics for a PDL via MQTT Discovery (old format)

        Creates entities under Linky {pdl} device:
        - sensor.myelectricaldata_linky_{pdl}_production (daily value with history in attributes)
        - sensor.myelectricaldata_linky_{pdl}_production_last7day (last 7 days total)
        - sensor.myelectricaldata_linky_{pdl}_production_last14day (last 14 days total)
        - sensor.myelectricaldata_linky_{pdl}_production_last30day (last 30 days total)
        """
        today = date.today()
        yesterday = today - timedelta(days=1)
        count = 0
        device = self._get_device_linky(pdl)

        # Check if PDL has production data
        from ...models.pdl import PDL
        result = await stats.db.execute(
            select(PDL.has_production).where(PDL.usage_point_id == pdl)
        )
        has_production = result.scalar_one_or_none()

        if not has_production:
            logger.debug(f"[HA-MQTT] PDL {pdl} has no production, skipping")
            return 0

        # Strict behavior: only publish J-1 daily value.
        # If J-1 is missing, keep 0.
        requested_date = yesterday
        data_wh = await stats.get_day_total(pdl, requested_date, "production")
        data_kwh = round(data_wh / 1000, 2)

        # Get last N days history for attributes
        history = {}
        for i in range(1, 32):  # Last 31 days
            day = today - timedelta(days=i)
            day_wh = await stats.get_day_total(pdl, day, "production")
            history[day.isoformat()] = round(day_wh / 1000, 2)

        # Main production sensor with history in attributes
        await self._publish_sensor_old_format(
            client,
            topic=f"{self.prefix}_production/{pdl}",
            name="production",
            unique_id=f"{self.prefix}_linky_{pdl}_production",
            device=device,
            state=data_kwh,
            attributes={
                "pdl": pdl,
                "date": requested_date.isoformat(),
                "value_wh": data_wh,
                "data_date": requested_date.isoformat(),
                "data_source": "requested_day",
                "history": history,
                "last_updated": datetime.now().isoformat(),
            },
            unit="kWh",
            device_class="energy",
            state_class="total",
            icon="mdi:solar-power",
        )
        count += 1

        # Last N days aggregates
        for days_count in [7, 14, 30]:
            total_kwh = 0.0
            for i in range(1, days_count + 1):
                day = today - timedelta(days=i)
                day_wh = await stats.get_day_total(pdl, day, "production")
                total_kwh += day_wh / 1000

            await self._publish_sensor_old_format(
                client,
                topic=f"{self.prefix}_production_last_{days_count}_day/{pdl}",
                name=f"production last{days_count}day",
                unique_id=f"{self.prefix}_linky_{pdl}_production_last{days_count}day",
                device=device,
                state=round(total_kwh, 2),
                attributes={
                    "pdl": pdl,
                    "days": days_count,
                    "start_date": (today - timedelta(days=days_count)).isoformat(),
                    "end_date": yesterday.isoformat(),
                },
                unit="kWh",
                device_class="energy",
                state_class="total",
                icon="mdi:solar-power-variant",
            )
            count += 1

        logger.debug(f"[HA-MQTT] Exported production stats for {pdl}: {count} sensors")
        return count

    # =========================================================================
    # TEMPO EXPORT (Old MyElectricalData format)
    # =========================================================================

    async def _get_tempo_prices_for_export(
        self,
        db: AsyncSession,
        usage_point_ids: list[str],
    ) -> tuple[dict[str, float], dict[str, Any]]:
        """Resolve Tempo prices for HA MQTT export.

        Priority:
        1. Selected TEMPO offer on one of the exported PDLs.
        2. Built-in fallback constants (TEMPO_PRICES).
        """
        from ...models.energy_provider import EnergyOffer
        from ...models.pdl import PDL

        if not usage_point_ids:
            return dict(TEMPO_PRICES), {"source": "fallback_defaults", "reason": "no_usage_point_ids"}

        pdl_result = await db.execute(
            select(PDL).where(PDL.usage_point_id.in_(usage_point_ids))
        )
        pdls = pdl_result.scalars().all()

        for pdl in pdls:
            if not pdl.selected_offer_id:
                continue

            offer_result = await db.execute(
                select(EnergyOffer).where(EnergyOffer.id == pdl.selected_offer_id)
            )
            offer = offer_result.scalar_one_or_none()

            if not offer or offer.offer_type != "TEMPO":
                continue

            price_map: dict[str, float] = {}
            if offer.tempo_blue_hc is not None:
                price_map["blue_hc"] = float(offer.tempo_blue_hc)
            if offer.tempo_blue_hp is not None:
                price_map["blue_hp"] = float(offer.tempo_blue_hp)
            if offer.tempo_white_hc is not None:
                price_map["white_hc"] = float(offer.tempo_white_hc)
            if offer.tempo_white_hp is not None:
                price_map["white_hp"] = float(offer.tempo_white_hp)
            if offer.tempo_red_hc is not None:
                price_map["red_hc"] = float(offer.tempo_red_hc)
            if offer.tempo_red_hp is not None:
                price_map["red_hp"] = float(offer.tempo_red_hp)

            if len(price_map) == len(TEMPO_PRICES):
                return price_map, {
                    "source": "selected_offer",
                    "usage_point_id": pdl.usage_point_id,
                    "offer_id": offer.id,
                    "offer_name": offer.name,
                    "price_updated_at": offer.price_updated_at.isoformat() if offer.price_updated_at else None,
                }

            logger.warning(
                "[HA-MQTT] Tempo offer '%s' for PDL %s is incomplete (%d/6 prices), using fallback constants",
                offer.name,
                pdl.usage_point_id,
                len(price_map),
            )

        return dict(TEMPO_PRICES), {"source": "fallback_defaults", "reason": "no_complete_tempo_offer"}

    async def _export_tempo(self, client: aiomqtt.Client, db: AsyncSession, usage_point_ids: list[str]) -> int:
        """Export Tempo information via MQTT Discovery (old MyElectricalData format)

        Creates entities under two devices:

        RTE Tempo device (myelectricaldata_rte/):
        - sensor.myelectricaldata_tempo_today
        - sensor.myelectricaldata_tempo_tomorrow

        EDF Tempo device (myelectricaldata_edf/):
        - sensor.myelectricaldata_tempo_info
        - sensor.myelectricaldata_tempo_days_blue
        - sensor.myelectricaldata_tempo_days_white
        - sensor.myelectricaldata_tempo_days_red
        - sensor.myelectricaldata_tempo_price_blue_hp
        - sensor.myelectricaldata_tempo_price_blue_hc
        - sensor.myelectricaldata_tempo_price_white_hp
        - sensor.myelectricaldata_tempo_price_white_hc
        - sensor.myelectricaldata_tempo_price_red_hp
        - sensor.myelectricaldata_tempo_price_red_hc
        """
        from ...models.tempo_day import TempoDay, TempoColor

        today = date.today()
        tomorrow = today + timedelta(days=1)
        count = 0

        device_rte = self._get_device_rte_tempo()
        device_edf = self._get_device_edf_tempo()

        today_str = today.isoformat()
        tomorrow_str = tomorrow.isoformat()

        # =====================================================================
        # RTE TEMPO: Today's and Tomorrow's color
        # =====================================================================

        # Today's color
        result = await db.execute(
            select(TempoDay).where(TempoDay.id == today_str)
        )
        today_tempo = result.scalar_one_or_none()
        today_color = today_tempo.color.value if today_tempo else "UNKNOWN"

        today_state = self._get_tempo_state(today_color)

        await self._publish_sensor_old_format(
            client,
            topic=f"{self.prefix}_rte/tempo_today",
            name="Today",
            unique_id=f"{self.prefix}_tempo_today",
            device=device_rte,
            state=today_state,
            attributes={
                "date": today_str,
                "color_fr": self._get_tempo_color_fr(today_color),
            },
            icon=self._get_tempo_icon(today_color),
        )
        count += 1

        # Tomorrow's color
        result = await db.execute(
            select(TempoDay).where(TempoDay.id == tomorrow_str)
        )
        tomorrow_tempo = result.scalar_one_or_none()
        tomorrow_color = tomorrow_tempo.color.value if tomorrow_tempo else "UNKNOWN"

        tomorrow_state = self._get_tempo_state(tomorrow_color)

        await self._publish_sensor_old_format(
            client,
            topic=f"{self.prefix}_rte/tempo_tomorrow",
            name="Tomorrow",
            unique_id=f"{self.prefix}_tempo_tomorrow",
            device=device_rte,
            state=tomorrow_state,
            attributes={
                "date": tomorrow_str,
                "color_fr": self._get_tempo_color_fr(tomorrow_color),
            },
            icon=self._get_tempo_icon(tomorrow_color),
        )
        count += 1

        # =====================================================================
        # EDF TEMPO: Days count per color
        # =====================================================================

        # Tempo season: Sept 1 to Aug 31
        if today.month >= 9:
            season_start = date(today.year, 9, 1)
            season_end = date(today.year + 1, 8, 31)
        else:
            season_start = date(today.year - 1, 9, 1)
            season_end = date(today.year, 8, 31)

        season_start_str = season_start.isoformat()
        season_end_str = season_end.isoformat()

        # Known colors for today/tomorrow should be deducted from remaining counters
        # (legacy behavior expected by existing dashboards/cards).
        # We rely on the two already-resolved states above to avoid enum-cast
        # inconsistencies across DB backends.
        known_future_counts: dict[str, int] = {c.value: 0 for c in TempoColor}
        if today_color in known_future_counts:
            known_future_counts[today_color] += 1
        if tomorrow_color in known_future_counts:
            known_future_counts[tomorrow_color] += 1

        # Days count per color (consumed + remaining)
        days_data: dict[str, dict[str, int]] = {}

        for color in TempoColor:
            color_name = color.value.lower()

            # Count used days this season (before today)
            result = await db.execute(
                select(func.count(TempoDay.id))
                .where(TempoDay.id >= season_start_str)
                .where(TempoDay.id < today_str)
                .where(cast(TempoDay.color, String) == color.value)
            )
            used = result.scalar() or 0

            quota = TEMPO_QUOTAS.get(color.value, 0)
            # Tempo "jours restants" is quota-based, not "future known rows in DB".
            # DB only contains known colors (historical + limited forecast), which can
            # wrongly produce tiny values like 1/0/1 if used directly.
            reserved_known = known_future_counts.get(color.value, 0)
            remaining = max(int(quota) - int(used) - int(reserved_known), 0)

            days_data[color_name] = {
                "used": used,
                "remaining": remaining,
                "reserved_known_days": reserved_known,
                "quota": quota,
            }

            # Publish days_{color} sensor
            await self._publish_sensor_old_format(
                client,
                topic=f"{self.prefix}_edf/tempo_days_{color_name}",
                name=f"Days {color.value.capitalize()}",
                unique_id=f"{self.prefix}_tempo_days_{color_name}",
                device=device_edf,
                state=remaining,
                attributes={
                    "used": used,
                    "remaining": remaining,
                    "reserved_known_days": reserved_known,
                    "quota": quota,
                    "season_start": season_start_str,
                    "season_end": season_end_str,
                },
                unit="jours",
                icon=self._get_tempo_icon(color.value),
            )
            count += 1

        # =====================================================================
        # EDF TEMPO: Info sensor (contract summary)
        # =====================================================================

        await self._publish_sensor_old_format(
            client,
            topic=f"{self.prefix}_edf/tempo_info",
            name="Tempo Info",
            unique_id=f"{self.prefix}_tempo_info",
            device=device_edf,
            state=today_color,
            attributes={
                "today": today_color,
                "tomorrow": tomorrow_color,
                "season_start": season_start_str,
                "season_end": season_end_str,
                "days_blue": f"{days_data['blue']['remaining']} / {days_data['blue']['quota']}",
                "days_white": f"{days_data['white']['remaining']} / {days_data['white']['quota']}",
                "days_red": f"{days_data['red']['remaining']} / {days_data['red']['quota']}",
                "days_blue_detail": days_data["blue"],
                "days_white_detail": days_data["white"],
                "days_red_detail": days_data["red"],
            },
            icon="mdi:information",
        )
        count += 1

        # =====================================================================
        # EDF TEMPO: Price sensors
        # =====================================================================

        tempo_prices, tempo_price_meta = await self._get_tempo_prices_for_export(db, usage_point_ids)

        for price_key, price_value in tempo_prices.items():
            price_name = TEMPO_PRICE_NAMES.get(price_key, price_key)

            await self._publish_sensor_old_format(
                client,
                topic=f"{self.prefix}_edf/tempo_price_{price_key}",
                name=f"Price {price_name}",
                unique_id=f"{self.prefix}_tempo_price_{price_key}",
                device=device_edf,
                state=price_value,
                attributes={
                    "price_type": price_key,
                    "name": price_name,
                    "source": tempo_price_meta.get("source"),
                    "offer_name": tempo_price_meta.get("offer_name"),
                    "usage_point_id": tempo_price_meta.get("usage_point_id"),
                    "price_updated_at": tempo_price_meta.get("price_updated_at"),
                },
                unit="EUR/kWh",
                icon="mdi:currency-eur",
            )
            count += 1

        logger.debug(f"[HA-MQTT] Exported Tempo: {count} sensors")
        return count

    def _get_tempo_color_fr(self, color: str) -> str:
        """Get French name for Tempo color"""
        names = {
            "BLUE": "Bleu",
            "WHITE": "Blanc",
            "RED": "Rouge",
            "UNKNOWN": "Inconnu",
        }
        return names.get(color, "Inconnu")

    def _get_tempo_state(self, color: str) -> str:
        """Normalize Tempo state value for MQTT (legacy compatibility)."""
        if (color or "").upper() == "UNKNOWN":
            return "Inconnu"
        return color

    def _get_tempo_icon(self, color: str) -> str:
        """Get MDI icon for Tempo color"""
        icons = {
            "BLUE": "mdi:calendar-check",
            "WHITE": "mdi:calendar-alert",
            "RED": "mdi:calendar-remove",
            "UNKNOWN": "mdi:calendar-question",
        }
        return icons.get(color, "mdi:calendar")

    # =========================================================================
    # ECOWATT EXPORT (Old MyElectricalData format)
    # =========================================================================

    async def _export_ecowatt(self, client: aiomqtt.Client, db: AsyncSession) -> int:
        """Export EcoWatt information via MQTT Discovery (old MyElectricalData format)

        Creates entities under RTE EcoWatt device:
        - sensor.myelectricaldata_ecowatt_j0 (today)
        - sensor.myelectricaldata_ecowatt_j1 (tomorrow)
        - sensor.myelectricaldata_ecowatt_j2 (day after tomorrow)
        """
        from ...models.ecowatt import EcoWatt

        today = date.today()
        now = datetime.now()
        current_hour = now.hour
        count = 0

        device = self._get_device_rte_ecowatt()

        # Day names for j0, j1, j2 (lowercase for consistency with entity_id convention)
        days = [
            ("j0", today, "Aujourd'hui"),
            ("j1", today + timedelta(days=1), "Demain"),
            ("j2", today + timedelta(days=2), "Après-demain"),
        ]

        for day_name, day_date, day_label in days:
            # Get EcoWatt data for this day
            result = await db.execute(
                select(EcoWatt)
                .where(func.date(EcoWatt.periode) == day_date)
                .order_by(EcoWatt.generation_datetime.desc())
                .limit(1)
            )
            ecowatt = result.scalar_one_or_none()

            if ecowatt:
                # Overall day value
                day_value = ecowatt.dvalue
                message = ecowatt.message or ""

                # For today, also include current hour value
                hour_values = ecowatt.values or []
                current_hour_value = None
                if day_name == "j0" and current_hour < len(hour_values):
                    current_hour_value = hour_values[current_hour]

                # Build attributes with hourly breakdown
                attributes = {
                    "date": day_date.isoformat(),
                    "day_label": day_label,
                    "message": message,
                    "level_name": self._get_ecowatt_level_name(day_value),
                    "hourly_values": hour_values,
                }
                if current_hour_value is not None:
                    attributes["current_hour"] = current_hour
                    attributes["current_hour_value"] = current_hour_value

                # Use day_value as state (1=Normal, 2=Tendu, 3=Critique)
                await self._publish_sensor_old_format(
                    client,
                    topic=f"{self.prefix}_rte/ecowatt_{day_name}",
                    name=day_name,
                    unique_id=f"{self.prefix}_ecowatt_{day_name}",
                    device=device,
                    state=day_value,
                    attributes=attributes,
                    icon=self._get_ecowatt_icon(day_value),
                )
                count += 1
            else:
                # No data available for this day
                await self._publish_sensor_old_format(
                    client,
                    topic=f"{self.prefix}_rte/ecowatt_{day_name}",
                    name=day_name,
                    unique_id=f"{self.prefix}_ecowatt_{day_name}",
                    device=device,
                    state="unknown",
                    attributes={
                        "date": day_date.isoformat(),
                        "day_label": day_label,
                        "message": "Données non disponibles",
                    },
                    icon="mdi:help-circle",
                )
                count += 1

        logger.debug(f"[HA-MQTT] Exported EcoWatt: {count} sensors")
        return count

    def _get_ecowatt_icon(self, level: int) -> str:
        """Get MDI icon for EcoWatt level"""
        icons = {
            1: "mdi:check-circle",
            2: "mdi:alert",
            3: "mdi:alert-octagon",
        }
        return icons.get(level, "mdi:help-circle")

    def _get_ecowatt_level_name(self, level: int) -> str:
        """Get human-readable name for EcoWatt level"""
        names = {
            1: "Normal",
            2: "Tendu",
            3: "Critique",
        }
        return names.get(level, "Inconnu")

    # =========================================================================
    # READ METRICS
    # =========================================================================

    async def read_metrics(self, usage_point_ids: list[str] | None = None) -> dict[str, Any]:
        """Read metrics from Home Assistant via MQTT retained messages

        Subscribes to the state topics and reads retained messages to get
        the current state of all exported entities.

        Args:
            usage_point_ids: Optional list of PDL numbers to filter

        Returns:
            Dict with metrics organized by entity type
        """
        import asyncio

        metrics: list[dict[str, Any]] = []
        errors: list[str] = []
        # Mapping topic_base → unique_id (rempli par les messages config)
        topic_to_unique_id: dict[str, str] = {}

        try:
            # Topics à lire - on s'abonne aux topics HA Discovery
            # Format: {discovery_prefix}/sensor/{topic_path}/state
            # Les topics publiés sont:
            #   - homeassistant/sensor/myelectricaldata_rte/tempo_today/state
            #   - homeassistant/sensor/myelectricaldata_edf/tempo_days_blue/state
            #   - homeassistant/sensor/myelectricaldata_consumption/{pdl}/state
            #   etc.
            topics_to_read = [
                f"{self.discovery_prefix}/sensor/{self.prefix}_rte/#",
                f"{self.discovery_prefix}/sensor/{self.prefix}_edf/#",
                f"{self.discovery_prefix}/sensor/{self.prefix}_consumption/#",
                f"{self.discovery_prefix}/sensor/{self.prefix}_consumption_last_7_day/#",
                f"{self.discovery_prefix}/sensor/{self.prefix}_consumption_last_14_day/#",
                f"{self.discovery_prefix}/sensor/{self.prefix}_consumption_last_30_day/#",
                f"{self.discovery_prefix}/sensor/{self.prefix}_production/#",
                f"{self.discovery_prefix}/sensor/{self.prefix}_production_last_7_day/#",
                f"{self.discovery_prefix}/sensor/{self.prefix}_production_last_14_day/#",
                f"{self.discovery_prefix}/sensor/{self.prefix}_production_last_30_day/#",
                # Legacy compatibility
                f"{self.discovery_prefix}/sensor/myelectricaldata_rte/#",
                f"{self.discovery_prefix}/sensor/myelectricaldata_edf/#",
                f"{self.discovery_prefix}/sensor/myelectricaldata_consumption/#",
                f"{self.discovery_prefix}/sensor/myelectricaldata_consumption_last_7_day/#",
                f"{self.discovery_prefix}/sensor/myelectricaldata_consumption_last_14_day/#",
                f"{self.discovery_prefix}/sensor/myelectricaldata_consumption_last_30_day/#",
                f"{self.discovery_prefix}/sensor/myelectricaldata_production/#",
                f"{self.discovery_prefix}/sensor/myelectricaldata_production_last_7_day/#",
                f"{self.discovery_prefix}/sensor/myelectricaldata_production_last_14_day/#",
                f"{self.discovery_prefix}/sensor/myelectricaldata_production_last_30_day/#",
                # Fallback pour le préfixe personnalisé
                f"{self.discovery_prefix}/sensor/{self.prefix}/#",
            ]

            # Compteur pour détecter quand on a fini de recevoir les messages retained
            last_message_time = asyncio.get_event_loop().time()
            idle_timeout = 0.5  # 500ms sans nouveau message = on a tout reçu

            # Collecter tous les messages bruts d'abord
            raw_messages: list[tuple[str, Any, str, str | None]] = []  # (topic, value, msg_type, pdl)

            async with await self._get_mqtt_client() as client:
                # S'abonner aux topics d'état
                for topic_pattern in topics_to_read:
                    await client.subscribe(topic_pattern)

                # Attendre les messages retenus avec un timeout global de 5 secondes
                try:
                    async with asyncio.timeout(5.0):
                        async for message in client.messages:
                            current_time = asyncio.get_event_loop().time()
                            last_message_time = current_time

                            topic = str(message.topic)
                            try:
                                payload = message.payload.decode("utf-8")
                                # Ignorer les payloads vides (messages de suppression)
                                if not payload:
                                    continue

                                # Déterminer le type de message (config, state, attributes)
                                topic_parts = topic.split("/")
                                msg_type = topic_parts[-1] if topic_parts else "unknown"

                                # Parser comme JSON si possible
                                try:
                                    value = json.loads(payload)
                                except json.JSONDecodeError:
                                    # Le state est souvent une valeur simple (pas JSON)
                                    value = payload

                                # Extraire le PDL du topic si présent
                                pdl = None
                                for part in topic_parts:
                                    if part.isdigit() and len(part) == 14:
                                        pdl = part
                                        break

                                # Filtrer par PDL si demandé
                                if usage_point_ids and pdl and pdl not in usage_point_ids:
                                    continue

                                raw_messages.append((topic, value, msg_type, pdl))

                            except Exception as e:
                                errors.append(f"Erreur parsing {topic}: {str(e)}")

                            # Vérifier si on est en idle (pas de nouveau message depuis idle_timeout)
                            await asyncio.sleep(0.01)  # Petit délai pour permettre d'autres messages
                            if asyncio.get_event_loop().time() - last_message_time > idle_timeout:
                                break

                except asyncio.TimeoutError:
                    # Timeout global atteint - c'est normal si le broker met du temps
                    pass

            # Phase 1 : Traiter les messages config pour construire le mapping topic_base → unique_id
            for topic, value, msg_type, pdl in raw_messages:
                if msg_type == "config" and isinstance(value, dict):
                    topic_parts = topic.split("/")
                    topic_base = "/".join(topic_parts[:-1]) if len(topic_parts) > 1 else topic
                    unique_id = value.get("uniq_id") or value.get("unique_id")
                    if unique_id:
                        topic_to_unique_id[topic_base] = unique_id

            # Phase 2 : Traiter tous les messages avec le mapping complet
            for topic, value, msg_type, pdl in raw_messages:
                topic_parts = topic.split("/")
                topic_base = "/".join(topic_parts[:-1]) if len(topic_parts) > 1 else topic

                # Construire le nom de l'entité à partir du topic (fallback)
                # Format: homeassistant/sensor/myelectricaldata_rte/tempo_today/state
                # On veut: myelectricaldata_rte_tempo_today (avec underscore, pas slash)
                entity_path = "_".join(topic_parts[2:-1]) if len(topic_parts) > 3 else topic.replace("/", "_")

                if msg_type == "config":
                    # Message de découverte - contient les métadonnées
                    if isinstance(value, dict):
                        entity_name = value.get("name", entity_path)
                        unique_id = value.get("uniq_id") or value.get("unique_id", entity_path)
                        unit = value.get("unit_of_meas") or value.get("unit_of_measurement")
                        device_class = value.get("dev_cla") or value.get("device_class")
                        icon = value.get("ic") or value.get("icon")
                        device = value.get("device", {})

                        category = self._categorize_ha_topic(topic)

                        metrics.append({
                            "entity": unique_id,
                            "name": entity_name,
                            "topic": topic,
                            "msg_type": "config",
                            "category": category,
                            "pdl": pdl,
                            "unit": unit,
                            "device_class": device_class,
                            "icon": icon,
                            "device": device.get("name") if device else None,
                            "raw_config": value,
                        })
                elif msg_type == "state":
                    # Message d'état - valeur actuelle
                    # Utiliser le unique_id si on l'a trouvé via le config
                    entity_id = topic_to_unique_id.get(topic_base, entity_path)
                    category = self._categorize_ha_topic(topic)

                    metrics.append({
                        "entity": entity_id,
                        "topic": topic,
                        "msg_type": "state",
                        "category": category,
                        "pdl": pdl,
                        "state": value,
                    })
                elif msg_type == "attributes":
                    # Attributs additionnels
                    # Utiliser le unique_id si on l'a trouvé via le config
                    entity_id = topic_to_unique_id.get(topic_base, entity_path)
                    category = self._categorize_ha_topic(topic)

                    metrics.append({
                        "entity": entity_id,
                        "topic": topic,
                        "msg_type": "attributes",
                        "category": category,
                        "pdl": pdl,
                        "attributes": value if isinstance(value, dict) else {"value": value},
                    })

            logger.info(f"[HA-MQTT] Read {len(metrics)} entity states")

            return {
                "success": True,
                "message": f"{len(metrics)} entités lues depuis Home Assistant",
                "metrics": metrics,
                "errors": errors,
                "broker": f"{self.broker}:{self.port}",
                "entity_prefix": self.prefix,
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[HA-MQTT] Failed to read metrics: {e}")

            # Message d'erreur plus explicite selon le type d'erreur
            if "timed out" in error_msg.lower() or "timeout" in error_msg.lower():
                user_message = (
                    f"Impossible de se connecter au broker MQTT ({self.broker}:{self.port}). "
                    "Vérifiez que le broker est accessible depuis le conteneur Docker."
                )
            elif "connection refused" in error_msg.lower():
                user_message = f"Connexion refusée par le broker MQTT ({self.broker}:{self.port})"
            elif "authentication" in error_msg.lower() or "not authorized" in error_msg.lower():
                user_message = "Authentification MQTT échouée. Vérifiez le nom d'utilisateur et le mot de passe."
            else:
                user_message = f"Erreur de lecture: {error_msg}"

            return {
                "success": False,
                "message": user_message,
                "metrics": [],
                "errors": [error_msg],
                "broker": f"{self.broker}:{self.port}",
                "entity_prefix": self.prefix,
            }

    def _categorize_ha_topic(self, topic: str) -> str:
        """Categorize a Home Assistant topic

        New format topics (old MyElectricalData structure):
        - {discovery_prefix}/sensor/myelectricaldata_rte/tempo_today/state
        - {discovery_prefix}/sensor/myelectricaldata_rte/tempo_tomorrow/state
        - {discovery_prefix}/sensor/myelectricaldata_rte/ecowatt_j0/state
        - {discovery_prefix}/sensor/myelectricaldata_edf/tempo_days_blue/state
        - {discovery_prefix}/sensor/myelectricaldata_edf/tempo_price_blue_hp/state
        - {discovery_prefix}/sensor/myelectricaldata_consumption/{pdl}/state
        - {discovery_prefix}/sensor/myelectricaldata_production/{pdl}/state
        """
        topic_lower = topic.lower()
        pref = self.prefix.lower()

        def _match(fragment: str) -> bool:
            return f"{pref}{fragment}" in topic_lower or f"myelectricaldata{fragment}" in topic_lower

        # RTE Tempo sensors
        if _match("_rte/tempo_today"):
            return "Tempo Aujourd'hui"
        elif _match("_rte/tempo_tomorrow"):
            return "Tempo Demain"

        # RTE EcoWatt sensors
        elif _match("_rte/ecowatt_j0"):
            return "EcoWatt Aujourd'hui"
        elif _match("_rte/ecowatt_j1"):
            return "EcoWatt Demain"
        elif _match("_rte/ecowatt_j2"):
            return "EcoWatt J+2"

        # EDF Tempo sensors
        elif _match("_edf/tempo_days_"):
            if "blue" in topic_lower:
                return "Tempo Jours Bleus"
            elif "white" in topic_lower:
                return "Tempo Jours Blancs"
            elif "red" in topic_lower:
                return "Tempo Jours Rouges"
            return "Tempo Jours"
        elif _match("_edf/tempo_price_"):
            return "Tempo Prix"
        elif _match("_edf/tempo_info"):
            return "Tempo Info"

        # Consumption sensors
        elif _match("_consumption_last_"):
            if "7" in topic_lower:
                return "Conso 7 derniers jours"
            elif "14" in topic_lower:
                return "Conso 14 derniers jours"
            elif "30" in topic_lower:
                return "Conso 30 derniers jours"
            return "Conso Période"
        elif _match("_consumption/"):
            return "Conso Journalière"

        # Production sensors
        elif _match("_production_last_"):
            if "7" in topic_lower:
                return "Prod 7 derniers jours"
            elif "14" in topic_lower:
                return "Prod 14 derniers jours"
            elif "30" in topic_lower:
                return "Prod 30 derniers jours"
            return "Prod Période"
        elif _match("_production/"):
            return "Prod Journalière"

        # Legacy format fallback
        parts = topic_lower.split("/")

        # Données globales Tempo (pas liées à un PDL)
        # Ex: myelectricaldata/tempo/today, myelectricaldata/tempo/tomorrow
        if "/tempo/" in topic_lower and not any(p.isdigit() and len(p) == 14 for p in parts):
            if "today" in topic_lower:
                return "Tempo Aujourd'hui"
            elif "tomorrow" in topic_lower:
                return "Tempo Demain"
            elif "remaining" in topic_lower or "days" in topic_lower:
                return "Tempo Jours Restants"
            elif "price" in topic_lower:
                return "Tempo Prix"
            else:
                return "Tempo"

        # Données globales EcoWatt
        if "/ecowatt/" in topic_lower:
            if "current" in topic_lower or "/j0/" in topic_lower:
                return "EcoWatt Aujourd'hui"
            elif "next" in topic_lower or "/j1/" in topic_lower:
                return "EcoWatt Demain"
            elif "/j2/" in topic_lower:
                return "EcoWatt J+2"
            elif "alert" in topic_lower:
                return "Alerte EcoWatt"
            else:
                return "EcoWatt"

        # Consommation par PDL
        if "/consumption/" in topic_lower:
            # Détecter le type de statistique
            if "/annual/" in topic_lower:
                # Sous-catégories par couleur Tempo ou base
                if "/tempo/" in topic_lower:
                    # Extraire la couleur du topic
                    if "blue" in topic_lower:
                        return "Conso Annuelle Tempo Bleu"
                    elif "white" in topic_lower:
                        return "Conso Annuelle Tempo Blanc"
                    elif "red" in topic_lower:
                        return "Conso Annuelle Tempo Rouge"
                    else:
                        return "Conso Annuelle Tempo"
                elif "/base/" in topic_lower or "/hc/" in topic_lower or "/hp/" in topic_lower:
                    return "Conso Annuelle Base"
                else:
                    return "Conso Annuelle"
            elif "/linear/" in topic_lower:
                if "/tempo/" in topic_lower:
                    if "blue" in topic_lower:
                        return "Conso Linéaire Tempo Bleu"
                    elif "white" in topic_lower:
                        return "Conso Linéaire Tempo Blanc"
                    elif "red" in topic_lower:
                        return "Conso Linéaire Tempo Rouge"
                    else:
                        return "Conso Linéaire Tempo"
                else:
                    return "Conso Linéaire"
            elif "/daily/" in topic_lower or "yesterday" in topic_lower:
                return "Conso Journalière"
            elif "/monthly/" in topic_lower:
                return "Conso Mensuelle"
            elif "/current/" in topic_lower or "/today/" in topic_lower:
                return "Conso Aujourd'hui"
            else:
                return "Consommation"

        # Production par PDL
        if "/production/" in topic_lower:
            if "/annual/" in topic_lower:
                return "Prod Annuelle"
            elif "/linear/" in topic_lower:
                return "Prod Linéaire"
            elif "/daily/" in topic_lower or "yesterday" in topic_lower:
                return "Prod Journalière"
            elif "/monthly/" in topic_lower:
                return "Prod Mensuelle"
            elif "/current/" in topic_lower or "/today/" in topic_lower:
                return "Prod Aujourd'hui"
            else:
                return "Production"

        # Statut du compteur
        if "/status" in topic_lower:
            return "Statut Compteur"

        # Contrat
        if "/contract" in topic_lower:
            return "Contrat"

        # Adresse
        if "/address" in topic_lower:
            return "Adresse"

        return "Autre"

    def _build_entity_name(self, topic: str) -> str:
        """Build a human-readable entity name from topic"""
        # Remove prefix and clean up
        parts = topic.replace(self.prefix, "").strip("/").split("/")

        # Build name from parts
        name_parts = []
        for part in parts:
            # Skip PDL in name (will be shown separately)
            if part.isdigit() and len(part) == 14:
                continue
            # Capitalize and replace underscores
            name_parts.append(part.replace("_", " ").title())

        return " - ".join(name_parts) if name_parts else topic

    # =========================================================================
    # HOME ASSISTANT WEBSOCKET API
    # =========================================================================

    def _has_websocket_config(self) -> bool:
        """Check if WebSocket configuration is available"""
        return bool(self.config.get("ha_url") and self.config.get("ha_token"))

    def _get_ws_url(self) -> str:
        """Get WebSocket URL from HA URL

        Converts http(s)://host:port to ws(s)://host:port/api/websocket
        """
        ha_url = self.config.get("ha_url", "").rstrip("/")
        if ha_url.startswith("https://"):
            return ha_url.replace("https://", "wss://") + "/api/websocket"
        else:
            return ha_url.replace("http://", "ws://") + "/api/websocket"

    async def _ws_send_and_receive(
        self,
        ws: websockets.WebSocketClientProtocol,
        message: dict[str, Any],
        msg_id: int,
    ) -> dict[str, Any]:
        """Send a WebSocket message and wait for response

        Args:
            ws: WebSocket connection
            message: Message to send (without id)
            msg_id: Message ID to use

        Returns:
            Response message
        """
        message["id"] = msg_id
        await ws.send(json.dumps(message))

        # Wait for response with matching ID
        while True:
            response = json.loads(await ws.recv())
            if response.get("id") == msg_id:
                return response

    async def _import_stats_in_chunks(
        self,
        ws: websockets.WebSocketClientProtocol,
        stats: list[dict[str, Any]],
        metadata: dict[str, Any],
        msg_id_start: int,
        chunk_size: int = 500,
        sync_delay_ms: int = 10000,
    ) -> tuple[int, int, list[str]]:
        """Import statistics in chunks to avoid WebSocket timeouts

        Args:
            ws: WebSocket connection
            stats: List of statistics to import (can be empty to just create the entity)
            metadata: Metadata for the statistic (has_mean, has_sum, statistic_id, name, source, unit)
            msg_id_start: Starting message ID
            chunk_size: Number of records per chunk (default 500 = ~20 days of hourly data)
            sync_delay_ms: Delay in milliseconds between chunks to let HA ingest data (default 10s)

        Returns:
            Tuple of (total_imported, next_msg_id, errors)
        """
        total_imported = 0
        errors: list[str] = []
        msg_id = msg_id_start

        # Si stats est vide, envoyer quand même pour créer l'entité dans HA
        if not stats:
            response = await self._ws_send_and_receive(
                ws,
                {
                    "type": "recorder/import_statistics",
                    "metadata": metadata,
                    "stats": [],
                },
                msg_id=msg_id,
            )
            msg_id += 1

            if response.get("success", True):
                logger.debug(f"[HA-WS] Created empty statistic for {metadata.get('statistic_id')}")
            else:
                error = response.get("error", {}).get("message", "Unknown error")
                errors.append(f"{metadata.get('statistic_id')} (empty): {error}")
                logger.warning(f"[HA-WS] Failed to create empty statistic: {error}")

            # Délai même pour les stats vides si demandé
            if sync_delay_ms > 0:
                await asyncio.sleep(sync_delay_ms / 1000)

            return 0, msg_id, errors

        # Split stats into chunks
        for i in range(0, len(stats), chunk_size):
            chunk = stats[i:i + chunk_size]

            response = await self._ws_send_and_receive(
                ws,
                {
                    "type": "recorder/import_statistics",
                    "metadata": metadata,
                    "stats": chunk,
                },
                msg_id=msg_id,
            )
            msg_id += 1

            if response.get("success", True):
                total_imported += len(chunk)
                logger.debug(
                    f"[HA-WS] Imported chunk {i//chunk_size + 1}: "
                    f"{len(chunk)} stats for {metadata.get('statistic_id')}"
                )
            else:
                error = response.get("error", {}).get("message", "Unknown error")
                errors.append(f"{metadata.get('statistic_id')} chunk {i//chunk_size + 1}: {error}")
                logger.warning(f"[HA-WS] Chunk import failed: {error}")

            # Délai entre les chunks pour laisser HA ingérer les données
            if sync_delay_ms > 0:
                await asyncio.sleep(sync_delay_ms / 1000)

        return total_imported, msg_id, errors

    async def list_statistics(self, prefix: str = "myelectricaldata") -> dict[str, Any]:
        """List all statistics IDs in Home Assistant matching prefix

        Uses WebSocket API: recorder/list_statistic_ids

        Args:
            prefix: Filter statistics by this prefix

        Returns:
            Dict with list of statistic_ids
        """
        if not self._has_websocket_config():
            return {
                "success": False,
                "message": "Configuration WebSocket manquante (ha_url, ha_token)",
                "statistic_ids": [],
            }

        ws_url = self._get_ws_url()
        token = self.config.get("ha_token")

        try:
            async with websockets.connect(ws_url) as ws:
                # Wait for auth_required
                auth_req = json.loads(await ws.recv())
                if auth_req.get("type") != "auth_required":
                    return {"success": False, "message": "Unexpected HA response", "statistic_ids": []}

                # Authenticate
                await ws.send(json.dumps({"type": "auth", "access_token": token}))
                auth_result = json.loads(await ws.recv())

                if auth_result.get("type") != "auth_ok":
                    return {
                        "success": False,
                        "message": f"Authentification échouée: {auth_result.get('message', 'Unknown error')}",
                        "statistic_ids": [],
                    }

                # List statistic IDs
                response = await self._ws_send_and_receive(
                    ws,
                    {"type": "recorder/list_statistic_ids"},
                    msg_id=1,
                )

                if not response.get("success", True):
                    return {
                        "success": False,
                        "message": response.get("error", {}).get("message", "Unknown error"),
                        "statistic_ids": [],
                    }

                # Filter by prefix
                all_stats = response.get("result", [])
                filtered = [
                    s for s in all_stats
                    if s.get("statistic_id", "").startswith(f"{prefix}:")
                ]

                logger.info(f"[HA-WS] Found {len(filtered)} statistics with prefix '{prefix}'")

                return {
                    "success": True,
                    "message": f"{len(filtered)} statistiques trouvées",
                    "statistic_ids": [s.get("statistic_id") for s in filtered],
                    "details": filtered,
                }

        except Exception as e:
            logger.error(f"[HA-WS] Failed to list statistics: {e}")
            return {
                "success": False,
                "message": f"Erreur de connexion: {str(e)}",
                "statistic_ids": [],
            }

    async def get_last_statistic_dates(self) -> dict[str, Any]:
        """Get the last recorded date for each statistic ID

        Uses WebSocket API: recorder/statistics_during_period to get recent stats
        and determine the last timestamp for each statistic.

        Returns:
            Dict with:
            - success: bool
            - message: str
            - last_dates: Dict[statistic_id, datetime] - Last recorded date per stat
            - oldest_date: datetime | None - The oldest "last date" (for incremental sync)
        """
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo

        if not self._has_websocket_config():
            return {
                "success": False,
                "message": "Configuration WebSocket manquante (ha_url, ha_token)",
                "last_dates": {},
                "oldest_date": None,
            }

        prefix = self.config.get("statistic_id_prefix", "myelectricaldata")

        # First, list all statistics with our prefix
        list_result = await self.list_statistics(prefix)
        if not list_result.get("success"):
            return {
                "success": False,
                "message": list_result.get("message", "Failed to list statistics"),
                "last_dates": {},
                "oldest_date": None,
            }

        statistic_ids = list_result.get("statistic_ids", [])
        if not statistic_ids:
            return {
                "success": True,
                "message": "Aucune statistique existante - import complet requis",
                "last_dates": {},
                "oldest_date": None,
            }

        ws_url = self._get_ws_url()
        token = self.config.get("ha_token")

        try:
            async with websockets.connect(ws_url) as ws:
                # Auth
                auth_req = json.loads(await ws.recv())
                if auth_req.get("type") != "auth_required":
                    return {"success": False, "message": "Unexpected HA response", "last_dates": {}, "oldest_date": None}

                await ws.send(json.dumps({"type": "auth", "access_token": token}))
                auth_result = json.loads(await ws.recv())

                if auth_result.get("type") != "auth_ok":
                    return {
                        "success": False,
                        "message": f"Authentification échouée: {auth_result.get('message', 'Unknown error')}",
                        "last_dates": {},
                        "oldest_date": None,
                    }

                # Query statistics for the last 30 days to find the most recent entry
                # We use a wide range to ensure we catch the latest data
                tz_paris = ZoneInfo("Europe/Paris")
                now = datetime.now(tz_paris)
                start_time = (now - timedelta(days=30)).isoformat()

                response = await self._ws_send_and_receive(
                    ws,
                    {
                        "type": "recorder/statistics_during_period",
                        "start_time": start_time,
                        "statistic_ids": statistic_ids,
                        "period": "hour",  # Get hourly data for precision
                    },
                    msg_id=1,
                )

                if not response.get("success", True):
                    return {
                        "success": False,
                        "message": response.get("error", {}).get("message", "Unknown error"),
                        "last_dates": {},
                        "oldest_date": None,
                    }

                # Extract last date for each statistic
                result_data = response.get("result", {})
                last_dates: dict[str, datetime] = {}

                for stat_id, entries in result_data.items():
                    if entries and isinstance(entries, list):
                        # Entries are sorted by time, last entry is most recent
                        last_entry = entries[-1]
                        # The "start" field contains the timestamp
                        start_ts = last_entry.get("start")
                        if start_ts:
                            # Parse ISO format timestamp
                            if isinstance(start_ts, (int, float)):
                                # Unix timestamp in seconds
                                last_dates[stat_id] = datetime.fromtimestamp(start_ts, tz=tz_paris)
                            else:
                                # ISO format string
                                try:
                                    last_dates[stat_id] = datetime.fromisoformat(str(start_ts).replace("Z", "+00:00"))
                                except ValueError:
                                    logger.warning(f"[HA-WS] Could not parse timestamp for {stat_id}: {start_ts}")

                # Find the oldest "last date" - this is where we need to start the incremental import
                oldest_date = min(last_dates.values()) if last_dates else None

                logger.info(
                    f"[HA-WS] Found last dates for {len(last_dates)}/{len(statistic_ids)} statistics. "
                    f"Oldest: {oldest_date.isoformat() if oldest_date else 'None'}"
                )

                return {
                    "success": True,
                    "message": f"Dernières dates récupérées pour {len(last_dates)} statistiques",
                    "last_dates": {k: v.isoformat() for k, v in last_dates.items()},
                    "oldest_date": oldest_date.isoformat() if oldest_date else None,
                }

        except Exception as e:
            logger.error(f"[HA-WS] Failed to get last statistic dates: {e}")
            return {
                "success": False,
                "message": f"Erreur: {str(e)}",
                "last_dates": {},
                "oldest_date": None,
            }

    async def clear_statistics(self, statistic_ids: list[str] | None = None) -> dict[str, Any]:
        """Clear statistics from Home Assistant

        Uses WebSocket API: recorder/clear_statistics

        Args:
            statistic_ids: List of statistic IDs to clear (None = all with prefix)

        Returns:
            Dict with operation result
        """
        if not self._has_websocket_config():
            return {
                "success": False,
                "message": "Configuration WebSocket manquante (ha_url, ha_token)",
            }

        prefix = self.config.get("statistic_id_prefix", "myelectricaldata")

        # If no specific IDs provided, get all with prefix
        if statistic_ids is None:
            list_result = await self.list_statistics(prefix)
            if not list_result.get("success"):
                return list_result
            statistic_ids = list_result.get("statistic_ids", [])

        if not statistic_ids:
            return {
                "success": True,
                "message": "Aucune statistique à supprimer",
                "cleared_count": 0,
            }

        ws_url = self._get_ws_url()
        token = self.config.get("ha_token")

        try:
            async with websockets.connect(ws_url) as ws:
                # Auth
                auth_req = json.loads(await ws.recv())
                if auth_req.get("type") != "auth_required":
                    return {"success": False, "message": "Unexpected HA response"}

                await ws.send(json.dumps({"type": "auth", "access_token": token}))
                auth_result = json.loads(await ws.recv())

                if auth_result.get("type") != "auth_ok":
                    return {
                        "success": False,
                        "message": f"Authentification échouée: {auth_result.get('message', 'Unknown error')}",
                    }

                # Clear statistics
                response = await self._ws_send_and_receive(
                    ws,
                    {
                        "type": "recorder/clear_statistics",
                        "statistic_ids": statistic_ids,
                    },
                    msg_id=1,
                )

                if not response.get("success", True):
                    return {
                        "success": False,
                        "message": response.get("error", {}).get("message", "Unknown error"),
                    }

                logger.info(f"[HA-WS] Cleared {len(statistic_ids)} statistics")

                return {
                    "success": True,
                    "message": f"{len(statistic_ids)} statistiques supprimées",
                    "cleared_count": len(statistic_ids),
                    "statistic_ids": statistic_ids,
                }

        except Exception as e:
            logger.error(f"[HA-WS] Failed to clear statistics: {e}")
            return {
                "success": False,
                "message": f"Erreur: {str(e)}",
            }

    async def import_statistics(
        self,
        db: AsyncSession,
        usage_point_ids: list[str],
        clear_first: bool = True,
        sync_delay_ms: int = 10000,
        chunk_size: int = 500,
        incremental: bool = False,
    ) -> dict[str, Any]:
        """Import consumption/production statistics to Home Assistant Energy Dashboard

        Uses WebSocket API: recorder/import_statistics

        Args:
            db: Database session
            usage_point_ids: List of PDL numbers
            clear_first: Clear existing statistics before import (ignored if incremental=True)
            sync_delay_ms: Delay in ms between imports to let HA ingest data (default 10s)
            chunk_size: Number of records per chunk (default 500)
            incremental: If True, only import new data since last import (faster)

        Returns:
            Dict with import results
        """
        if not self._has_websocket_config():
            return {
                "success": False,
                "message": "Configuration WebSocket manquante (ha_url, ha_token)",
            }

        prefix = self.config.get("statistic_id_prefix", "myelectricaldata")

        # For incremental mode, get the last imported date
        since_date: datetime | None = None
        if incremental:
            last_dates_result = await self.get_last_statistic_dates()
            if last_dates_result.get("success") and last_dates_result.get("oldest_date"):
                from datetime import datetime
                oldest_date_str = last_dates_result["oldest_date"]
                since_date = datetime.fromisoformat(oldest_date_str)
                logger.info(f"[HA-WS] Incremental mode: importing data since {since_date}")
            else:
                # No existing data, fall back to full import
                logger.info("[HA-WS] No existing statistics found, performing full import")
                incremental = False

        # Optionally clear existing statistics (disabled for incremental mode)
        if clear_first and not incremental:
            clear_result = await self.clear_statistics()
            if not clear_result.get("success"):
                logger.warning(f"[HA-WS] Failed to clear statistics: {clear_result.get('message')}")

        ws_url = self._get_ws_url()
        token = self.config.get("ha_token")

        results = {
            "consumption": 0,
            "production": 0,
            "cost": 0,
            "errors": [],
        }

        try:
            async with websockets.connect(ws_url) as ws:
                # Auth
                auth_req = json.loads(await ws.recv())
                if auth_req.get("type") != "auth_required":
                    return {"success": False, "message": "Unexpected HA response", **results}

                await ws.send(json.dumps({"type": "auth", "access_token": token}))
                auth_result = json.loads(await ws.recv())

                if auth_result.get("type") != "auth_ok":
                    return {
                        "success": False,
                        "message": f"Authentification échouée: {auth_result.get('message', 'Unknown error')}",
                        **results,
                    }

                msg_id = 1

                # Mapping for human-readable tariff names
                tariff_names = {
                    "base": "BASE",
                    "hc": "Heures Creuses",
                    "hp": "Heures Pleines",
                    "blue_hc": "TEMPO Bleu HC",
                    "blue_hp": "TEMPO Bleu HP",
                    "white_hc": "TEMPO Blanc HC",
                    "white_hp": "TEMPO Blanc HP",
                    "red_hc": "TEMPO Rouge HC",
                    "red_hp": "TEMPO Rouge HP",
                }

                # Import statistics for each PDL
                mode_str = "incremental" if incremental else "full"
                logger.info(f"[HA-WS] Processing {len(usage_point_ids)} PDLs ({mode_str} mode): {usage_point_ids}")
                for pdl in usage_point_ids:
                    # Get consumption data by tariff
                    logger.info(f"[HA-WS] Getting consumption data for PDL {pdl}" + (f" (since {since_date})" if since_date else ""))
                    consumption_by_tariff = await self._get_consumption_statistics_by_tariff(db, pdl, since_date)
                    logger.info(f"[HA-WS] Got {len(consumption_by_tariff)} tariff buckets for {pdl}: {list(consumption_by_tariff.keys())}")

                    for tariff_tag, stats in consumption_by_tariff.items():
                        # Import même si stats est vide pour créer l'entité dans HA
                        # Build statistic_id: myelectricaldata:consumption_{pdl}_{tariff}
                        statistic_id = f"{prefix}:consumption_{pdl}_{tariff_tag}"
                        tariff_name = tariff_names.get(tariff_tag, tariff_tag.upper())

                        # Import in chunks to avoid WebSocket timeout
                        imported, msg_id, chunk_errors = await self._import_stats_in_chunks(
                            ws,
                            stats,
                            {
                                "has_mean": False,
                                "has_sum": True,
                                "statistic_id": statistic_id,
                                "name": f"Consommation {pdl} {tariff_name}",
                                "source": prefix,
                                "unit_of_measurement": "kWh",
                            },
                            msg_id_start=msg_id,
                            chunk_size=chunk_size,
                            sync_delay_ms=sync_delay_ms,
                        )
                        results["consumption"] += imported
                        results["errors"].extend(chunk_errors)
                        if imported > 0:
                            logger.debug(f"[HA-WS] Imported {imported} consumption stats for {pdl} {tariff_tag}")

                    # Get cost data from consumption and energy offer prices
                    logger.info(f"[HA-WS] Calculating costs for PDL {pdl}")
                    cost_by_tariff = await self._get_cost_statistics_by_tariff(db, pdl, consumption_by_tariff)

                    for tariff_tag, cost_stats in cost_by_tariff.items():
                        # Import même si cost_stats est vide pour créer l'entité dans HA
                        # Build statistic_id: myelectricaldata:cost_{pdl}_{tariff}
                        statistic_id = f"{prefix}:cost_{pdl}_{tariff_tag}"
                        tariff_name = tariff_names.get(tariff_tag, tariff_tag.upper())

                        # Import in chunks to avoid WebSocket timeout
                        imported, msg_id, chunk_errors = await self._import_stats_in_chunks(
                            ws,
                            cost_stats,
                            {
                                "has_mean": False,
                                "has_sum": True,
                                "statistic_id": statistic_id,
                                "name": f"Coût {pdl} {tariff_name}",
                                "source": prefix,
                                "unit_of_measurement": "EUR",
                            },
                            msg_id_start=msg_id,
                            chunk_size=chunk_size,
                            sync_delay_ms=sync_delay_ms,
                        )
                        results["cost"] += imported
                        results["errors"].extend(chunk_errors)
                        if imported > 0:
                            logger.debug(f"[HA-WS] Imported {imported} cost stats for {pdl} {tariff_tag}")

                    # Get production data (production has no tariff distinction)
                    # Import même si vide pour créer l'entité dans HA
                    production_stats = await self._get_production_statistics(db, pdl, since_date)
                    statistic_id = f"{prefix}:production_{pdl}"

                    # Import in chunks to avoid WebSocket timeout
                    imported, msg_id, chunk_errors = await self._import_stats_in_chunks(
                        ws,
                        production_stats,
                        {
                            "has_mean": False,
                            "has_sum": True,
                            "statistic_id": statistic_id,
                            "name": f"Production {pdl}",
                            "source": prefix,
                            "unit_of_measurement": "kWh",
                        },
                        msg_id_start=msg_id,
                        chunk_size=chunk_size,
                        sync_delay_ms=sync_delay_ms,
                    )
                    results["production"] += imported
                    results["errors"].extend(chunk_errors)
                    if imported > 0:
                        logger.debug(f"[HA-WS] Imported {imported} production stats for {pdl}")

                logger.info(f"[HA-WS] Import completed: {results['consumption']} consumption, {results['cost']} cost, {results['production']} production")

                return {
                    "success": True,
                    "message": f"Import terminé: {results['consumption']} conso, {results['cost']} coût, {results['production']} prod",
                    **results,
                }

        except Exception as e:
            logger.error(f"[HA-WS] Failed to import statistics: {e}")
            return {
                "success": False,
                "message": f"Erreur: {str(e)}",
                **results,
            }

    async def import_statistics_with_progress(
        self,
        db: AsyncSession,
        usage_point_ids: list[str],
        clear_first: bool = True,
        progress_callback: Any = None,
        sync_delay_ms: int = 10000,
        chunk_size: int = 500,
        incremental: bool = False,
    ) -> dict[str, Any]:
        """Import statistics with progress callback for SSE streaming

        Same as import_statistics but calls progress_callback at each step.

        Args:
            db: Database session
            usage_point_ids: List of PDL numbers
            clear_first: Clear existing statistics before import (ignored if incremental=True)
            progress_callback: Async callback(event_dict) called at each step
            sync_delay_ms: Delay in ms between imports to let HA ingest data (default 10s)
            chunk_size: Number of statistics records per WebSocket message (default 500)
            incremental: If True, only import new data since last import (faster)

        Returns:
            Dict with import results
        """
        if not self._has_websocket_config():
            return {
                "success": False,
                "message": "Configuration WebSocket manquante (ha_url, ha_token)",
            }

        prefix = self.config.get("statistic_id_prefix", "myelectricaldata")

        # Helper pour envoyer les événements de progression
        async def emit_progress(
            step: int,
            total_steps: int,
            message: str,
            consumption: int = 0,
            cost: int = 0,
            production: int = 0,
        ) -> None:
            if progress_callback:
                await progress_callback({
                    "event_type": "progress",
                    "step": step,
                    "total_steps": total_steps,
                    "percent": round(step * 100 / total_steps) if total_steps > 0 else 0,
                    "message": message,
                    "consumption": consumption,
                    "cost": cost,
                    "production": production,
                })

        # For incremental mode, get the last imported date
        since_date: datetime | None = None
        if incremental:
            last_dates_result = await self.get_last_statistic_dates()
            if last_dates_result.get("success") and last_dates_result.get("oldest_date"):
                from datetime import datetime as dt
                oldest_date_str = last_dates_result["oldest_date"]
                since_date = dt.fromisoformat(oldest_date_str)
                logger.info(f"[HA-WS] Incremental mode: importing data since {since_date}")
            else:
                # No existing data, fall back to full import
                logger.info("[HA-WS] No existing statistics found, performing full import")
                incremental = False

        # Calculer le nombre total d'étapes
        # Pour chaque PDL: 1 (lecture conso) + N tarifs conso + N tarifs coût + 1 prod
        # Estimation: clear + auth + (PDL * ~15 étapes)
        num_pdls = len(usage_point_ids)
        total_steps = 2 + (num_pdls * 15)  # Estimation
        current_step = 0

        # Step 1: Clear si demandé (disabled for incremental mode)
        if clear_first and not incremental:
            await emit_progress(current_step, total_steps, "Suppression des anciennes statistiques...")
            clear_result = await self.clear_statistics()
            if not clear_result.get("success"):
                logger.warning(f"[HA-WS] Failed to clear statistics: {clear_result.get('message')}")
        elif incremental:
            await emit_progress(current_step, total_steps, f"Mode incrémental: import depuis {since_date.date() if since_date else 'N/A'}...")
        current_step += 1

        ws_url = self._get_ws_url()
        token = self.config.get("ha_token")

        results: dict[str, Any] = {
            "consumption": 0,
            "production": 0,
            "cost": 0,
            "errors": [],
        }

        try:
            async with websockets.connect(ws_url) as ws:
                # Step 2: Auth
                await emit_progress(current_step, total_steps, "Connexion à Home Assistant...")
                auth_req = json.loads(await ws.recv())
                if auth_req.get("type") != "auth_required":
                    return {"success": False, "message": "Unexpected HA response", **results}

                await ws.send(json.dumps({"type": "auth", "access_token": token}))
                auth_result = json.loads(await ws.recv())

                if auth_result.get("type") != "auth_ok":
                    return {
                        "success": False,
                        "message": f"Authentification échouée: {auth_result.get('message', 'Unknown error')}",
                        **results,
                    }
                current_step += 1

                msg_id = 2

                # Noms des tarifs pour l'affichage
                tariff_names = {
                    "base": "Base",
                    "hc": "Heures Creuses",
                    "hp": "Heures Pleines",
                    "blue_hc": "Bleu HC",
                    "blue_hp": "Bleu HP",
                    "white_hc": "Blanc HC",
                    "white_hp": "Blanc HP",
                    "red_hc": "Rouge HC",
                    "red_hp": "Rouge HP",
                }

                for pdl_idx, pdl in enumerate(usage_point_ids):
                    # Étape: Lecture des données de consommation
                    await emit_progress(
                        current_step, total_steps,
                        f"PDL {pdl_idx + 1}/{num_pdls}: Lecture consommation...",
                        results["consumption"], results["cost"], results["production"]
                    )
                    consumption_by_tariff = await self._get_consumption_statistics_by_tariff(db, pdl, since_date)
                    current_step += 1

                    # Import consommation par tarif
                    for tariff_tag, stats in consumption_by_tariff.items():
                        tariff_name = tariff_names.get(tariff_tag, tariff_tag.upper())
                        await emit_progress(
                            current_step, total_steps,
                            f"PDL {pdl_idx + 1}/{num_pdls}: Import conso {tariff_name}...",
                            results["consumption"], results["cost"], results["production"]
                        )

                        statistic_id = f"{prefix}:consumption_{pdl}_{tariff_tag}"
                        imported, msg_id, chunk_errors = await self._import_stats_in_chunks(
                            ws,
                            stats,
                            {
                                "has_mean": False,
                                "has_sum": True,
                                "statistic_id": statistic_id,
                                "name": f"Consommation {pdl} {tariff_name}",
                                "source": prefix,
                                "unit_of_measurement": "kWh",
                            },
                            msg_id_start=msg_id,
                            chunk_size=chunk_size,
                            sync_delay_ms=sync_delay_ms,
                        )
                        results["consumption"] += imported
                        results["errors"].extend(chunk_errors)
                        current_step += 1

                    # Calcul et import des coûts
                    await emit_progress(
                        current_step, total_steps,
                        f"PDL {pdl_idx + 1}/{num_pdls}: Calcul des coûts...",
                        results["consumption"], results["cost"], results["production"]
                    )
                    cost_by_tariff = await self._get_cost_statistics_by_tariff(db, pdl, consumption_by_tariff)
                    current_step += 1

                    for tariff_tag, cost_stats in cost_by_tariff.items():
                        tariff_name = tariff_names.get(tariff_tag, tariff_tag.upper())
                        await emit_progress(
                            current_step, total_steps,
                            f"PDL {pdl_idx + 1}/{num_pdls}: Import coût {tariff_name}...",
                            results["consumption"], results["cost"], results["production"]
                        )

                        statistic_id = f"{prefix}:cost_{pdl}_{tariff_tag}"
                        imported, msg_id, chunk_errors = await self._import_stats_in_chunks(
                            ws,
                            cost_stats,
                            {
                                "has_mean": False,
                                "has_sum": True,
                                "statistic_id": statistic_id,
                                "name": f"Coût {pdl} {tariff_name}",
                                "source": prefix,
                                "unit_of_measurement": "EUR",
                            },
                            msg_id_start=msg_id,
                            chunk_size=chunk_size,
                            sync_delay_ms=sync_delay_ms,
                        )
                        results["cost"] += imported
                        results["errors"].extend(chunk_errors)
                        current_step += 1

                    # Production
                    await emit_progress(
                        current_step, total_steps,
                        f"PDL {pdl_idx + 1}/{num_pdls}: Import production...",
                        results["consumption"], results["cost"], results["production"]
                    )
                    production_stats = await self._get_production_statistics(db, pdl, since_date)
                    statistic_id = f"{prefix}:production_{pdl}"
                    imported, msg_id, chunk_errors = await self._import_stats_in_chunks(
                        ws,
                        production_stats,
                        {
                            "has_mean": False,
                            "has_sum": True,
                            "statistic_id": statistic_id,
                            "name": f"Production {pdl}",
                            "source": prefix,
                            "unit_of_measurement": "kWh",
                        },
                        msg_id_start=msg_id,
                        chunk_size=chunk_size,
                        sync_delay_ms=sync_delay_ms,
                    )
                    results["production"] += imported
                    results["errors"].extend(chunk_errors)
                    current_step += 1

                logger.info(f"[HA-WS] Import completed: {results['consumption']} consumption, {results['cost']} cost, {results['production']} production")

                return {
                    "success": True,
                    "message": f"Import terminé: {results['consumption']} conso, {results['cost']} coût, {results['production']} prod",
                    **results,
                }

        except Exception as e:
            logger.error(f"[HA-WS] Failed to import statistics with progress: {e}")
            return {
                "success": False,
                "message": f"Erreur: {str(e)}",
                **results,
            }

    async def _get_consumption_statistics_by_tariff(
        self,
        db: AsyncSession,
        pdl: str,
        since_date: datetime | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        """Get consumption statistics grouped by tariff type for Energy Dashboard

        Returns statistics in the format expected by recorder/import_statistics,
        separated by tariff (BASE, HC, HP, or TEMPO colors).

        Based on the original MyElectricalData implementation:
        https://github.com/MyElectricalData/myelectricaldata_import/blob/main/src/models/export_home_assistant_ws.py

        Args:
            db: Database session
            pdl: Usage point ID
            since_date: Only include records after this date (for incremental import)

        Returns:
            Dict of tariff_tag -> list of statistics records
            Example: {"base": [...], "hc": [...], "hp": [...]}
            or for TEMPO: {"blue_hc": [...], "blue_hp": [...], "white_hc": [...], ...}
        """
        from datetime import timedelta
        from zoneinfo import ZoneInfo

        from ...models.client_mode import ConsumptionData, ContractData, DataGranularity
        from ...models.pdl import PDL
        from ...models.tempo_day import TempoColor, TempoDay

        tz_paris = ZoneInfo("Europe/Paris")

        # 1. Get contract info to determine pricing option
        # First try ContractData (client mode cache), then fallback to PDL.pricing_option
        contract_result = await db.execute(
            select(ContractData).where(ContractData.usage_point_id == pdl)
        )
        contract = contract_result.scalar_one_or_none()

        pricing_option = "BASE"  # Default
        offpeak_hours: list[dict] = []

        if contract and contract.pricing_option:
            pricing_option = contract.pricing_option.upper()
            # offpeak_hours format: [{"start": "22:00", "end": "06:00"}, ...]
            offpeak_hours = contract.offpeak_hours or []
        else:
            # Fallback: get pricing_option from PDL record
            pdl_result = await db.execute(
                select(PDL).where(PDL.usage_point_id == pdl)
            )
            pdl_record = pdl_result.scalar_one_or_none()
            if pdl_record and pdl_record.pricing_option:
                pricing_option = pdl_record.pricing_option.upper()
                offpeak_hours = pdl_record.offpeak_hours or []

        logger.info(f"[HA-WS] PDL {pdl}: pricing_option={pricing_option}, offpeak_hours={offpeak_hours}, since_date={since_date}")

        # 2. Try to get detailed data (30-min) first, fallback to daily
        # Apply since_date filter if provided (for incremental import)
        detailed_query = (
            select(ConsumptionData)
            .where(ConsumptionData.usage_point_id == pdl)
            .where(ConsumptionData.granularity == DataGranularity.DETAILED)
        )
        if since_date:
            detailed_query = detailed_query.where(ConsumptionData.date >= since_date.date())
        detailed_query = detailed_query.order_by(ConsumptionData.date, ConsumptionData.interval_start)

        detailed_result = await db.execute(detailed_query)
        detailed_records = detailed_result.scalars().all()

        if detailed_records:
            records = detailed_records
            use_detailed = True
            logger.info(f"[HA-WS] Using {len(records)} detailed records for {pdl}" + (f" (since {since_date.date()})" if since_date else ""))
        else:
            # Fallback to daily
            daily_query = (
                select(ConsumptionData)
                .where(ConsumptionData.usage_point_id == pdl)
                .where(ConsumptionData.granularity == DataGranularity.DAILY)
            )
            if since_date:
                daily_query = daily_query.where(ConsumptionData.date >= since_date.date())
            daily_query = daily_query.order_by(ConsumptionData.date)

            daily_result = await db.execute(daily_query)
            records = daily_result.scalars().all()
            use_detailed = False
            logger.info(f"[HA-WS] Using {len(records)} daily records for {pdl}" + (f" (since {since_date.date()})" if since_date else ""))

        if not records:
            logger.info(f"[HA-WS] No records found for {pdl}")
            return {}

        # 3. For TEMPO, load the color calendar
        tempo_colors: dict[str, TempoColor] = {}
        if "TEMPO" in pricing_option:
            tempo_result = await db.execute(select(TempoDay))
            for day in tempo_result.scalars().all():
                # Store by date string YYYY-MM-DD
                day_str = day.date.strftime("%Y-%m-%d") if hasattr(day.date, 'strftime') else str(day.date)[:10]
                tempo_colors[day_str] = day.color

        # 4. Initialize stats buckets based on pricing option
        stats_by_tariff: dict[str, list[dict[str, Any]]] = {}
        cumulative_by_tariff: dict[str, float] = {}

        if "TEMPO" in pricing_option:
            # 6 buckets: blue_hc, blue_hp, white_hc, white_hp, red_hc, red_hp
            for color in ["blue", "white", "red"]:
                for period in ["hc", "hp"]:
                    key = f"{color}_{period}"
                    stats_by_tariff[key] = []
                    cumulative_by_tariff[key] = 0.0
        elif pricing_option in ("HC/HP", "HCHP", "EJP"):
            # 2 buckets: hc, hp
            stats_by_tariff["hc"] = []
            stats_by_tariff["hp"] = []
            cumulative_by_tariff["hc"] = 0.0
            cumulative_by_tariff["hp"] = 0.0
        else:
            # BASE: 1 bucket
            stats_by_tariff["base"] = []
            cumulative_by_tariff["base"] = 0.0

        # 5. Helper to determine if an hour is in off-peak period
        def is_offpeak_hour(hour: int, minute: int = 0) -> bool:
            """Check if given time is in off-peak hours"""
            if not offpeak_hours:
                # Default: 22h-6h = heures creuses
                return hour < 6 or hour >= 22

            time_minutes = hour * 60 + minute
            for period in offpeak_hours:
                start_parts = period.get("start", "22:00").split(":")
                end_parts = period.get("end", "06:00").split(":")
                start_minutes = int(start_parts[0]) * 60 + int(start_parts[1]) if len(start_parts) >= 2 else 22 * 60
                end_minutes = int(end_parts[0]) * 60 + int(end_parts[1]) if len(end_parts) >= 2 else 6 * 60

                # Handle overnight periods (e.g., 22:00 -> 06:00)
                if start_minutes > end_minutes:
                    if time_minutes >= start_minutes or time_minutes < end_minutes:
                        return True
                else:
                    if start_minutes <= time_minutes < end_minutes:
                        return True
            return False

        # 6. Helper to convert W → Wh based on interval_length
        def convert_w_to_wh(value_w: int, raw_data: dict | None) -> float:
            """Convert Watts to Watt-hours based on interval_length

            For detailed data, values are in W (average power over interval).
            Formula: Wh = W / (60 / interval_minutes)
            - PT10M → Wh = W / 6
            - PT15M → Wh = W / 4
            - PT30M → Wh = W / 2 (default)
            - PT60M → Wh = W / 1

            For daily data, values are already in Wh.
            """
            if not raw_data:
                # Default to PT30M for detailed data without raw_data
                return value_w / 2 if use_detailed else float(value_w)

            interval_length = raw_data.get("interval_length", "PT30M")

            # Parse interval_length (e.g., "PT30M" → 30)
            match = re.match(r"PT(\d+)M", interval_length)
            if match:
                interval_minutes = int(match.group(1))
                # Wh = W / (60 / interval_minutes)
                return value_w / (60 / interval_minutes)

            # For daily data (PT1D or unknown), value is already in Wh
            return float(value_w)

        # 7. Process each record
        # Home Assistant requires hourly data (timestamps at XX:00:00)
        # For detailed (30-min) data, we aggregate by hour
        # Key: (tariff_tag, date, hour) -> value_kwh
        hourly_aggregation: dict[tuple[str, Any, int], float] = {}

        for record in records:
            # Convert W → Wh using interval_length from raw_data
            value_wh = convert_w_to_wh(record.value, record.raw_data) if record.value else 0
            value_kwh = value_wh / 1000

            # Parse time
            if use_detailed and record.interval_start:
                # Parse interval_start (e.g., "14:30")
                hour, minute = map(int, record.interval_start.split(":"))
            else:
                # Daily data: split into 24 hourly entries
                hour = 0

            # Determine tariff tag based on the hour (not the minute)
            # The tariff is determined by the START of the hour
            if "TEMPO" in pricing_option:
                # TEMPO logic: 6h-22h = HP, 22h-6h = HC
                # For data between 00:00 and 06:00, the color is from the previous day
                if 6 <= hour < 22:
                    period = "hp"
                    tempo_date = record.date
                else:
                    period = "hc"
                    # Between 00:00 and 06:00, color is from previous day
                    if hour < 6:
                        tempo_date = record.date - timedelta(days=1)
                    else:
                        tempo_date = record.date

                date_str = tempo_date.strftime("%Y-%m-%d")
                color = tempo_colors.get(date_str, TempoColor.BLUE)
                color_name = color.value.lower() if hasattr(color, 'value') else str(color).lower()
                tariff_tag = f"{color_name}_{period}"

            elif pricing_option in ("HC/HP", "HCHP", "EJP"):
                # HC/HP: use off-peak hours from contract
                # Use start of hour for tariff determination
                if is_offpeak_hour(hour, 0):
                    tariff_tag = "hc"
                else:
                    tariff_tag = "hp"
            else:
                # BASE
                tariff_tag = "base"

            # Aggregate by hour
            if use_detailed:
                # Aggregate 30-min slots into hourly
                key = (tariff_tag, record.date, hour)
                hourly_aggregation[key] = hourly_aggregation.get(key, 0) + value_kwh
            else:
                # Daily data: create 24 hourly entries with value/24 each
                # This provides granularity for tariff-based separation
                hourly_value = value_kwh / 24
                for h in range(24):
                    # Re-determine tariff for each hour
                    if "TEMPO" in pricing_option:
                        if 6 <= h < 22:
                            h_period = "hp"
                            h_tempo_date = record.date
                        else:
                            h_period = "hc"
                            if h < 6:
                                h_tempo_date = record.date - timedelta(days=1)
                            else:
                                h_tempo_date = record.date
                        h_date_str = h_tempo_date.strftime("%Y-%m-%d")
                        h_color = tempo_colors.get(h_date_str, TempoColor.BLUE)
                        h_color_name = h_color.value.lower() if hasattr(h_color, 'value') else str(h_color).lower()
                        h_tariff_tag = f"{h_color_name}_{h_period}"
                    elif pricing_option in ("HC/HP", "HCHP", "EJP"):
                        h_tariff_tag = "hc" if is_offpeak_hour(h, 0) else "hp"
                    else:
                        h_tariff_tag = "base"

                    key = (h_tariff_tag, record.date, h)
                    hourly_aggregation[key] = hourly_aggregation.get(key, 0) + hourly_value

        # 7. Build final statistics from hourly aggregation
        # Sort by (date, hour) to maintain chronological order
        sorted_keys = sorted(hourly_aggregation.keys(), key=lambda k: (k[1], k[2]))

        for tariff_tag, record_date, hour in sorted_keys:
            value_kwh = hourly_aggregation[(tariff_tag, record_date, hour)]

            # Build datetime at the start of the hour
            start_dt = datetime.combine(record_date, datetime.min.time().replace(hour=hour, minute=0, second=0))
            start_dt = start_dt.replace(tzinfo=tz_paris)

            # Ensure bucket exists (safety)
            if tariff_tag not in stats_by_tariff:
                stats_by_tariff[tariff_tag] = []
                cumulative_by_tariff[tariff_tag] = 0.0

            # Update cumulative and add stat
            cumulative_by_tariff[tariff_tag] += value_kwh

            stats_by_tariff[tariff_tag].append({
                "start": start_dt.isoformat(),
                "state": round(value_kwh, 3),
                "sum": round(cumulative_by_tariff[tariff_tag], 3),
            })

        # Log summary
        for tag, stats in stats_by_tariff.items():
            if stats:
                logger.debug(f"[HA-WS] {pdl} {tag}: {len(stats)} records, total={cumulative_by_tariff[tag]:.2f} kWh")

        return stats_by_tariff

    async def _get_cost_statistics_by_tariff(
        self,
        db: AsyncSession,
        pdl: str,
        consumption_by_tariff: dict[str, list[dict[str, Any]]],
    ) -> dict[str, list[dict[str, Any]]]:
        """Calculate cost statistics from consumption data and energy offer prices

        Uses the PDL's selected_offer to get the tariff prices, then multiplies
        consumption by price for each tariff bucket.

        Args:
            db: Database session
            pdl: Usage point ID
            consumption_by_tariff: Consumption stats from _get_consumption_statistics_by_tariff()

        Returns:
            Dict of tariff_tag -> list of cost statistics in EUR
            Example: {"blue_hc": [{start, state, sum}, ...], ...}
        """

        from ...models.energy_provider import EnergyOffer
        from ...models.pdl import PDL

        # Get PDL with selected offer
        pdl_result = await db.execute(
            select(PDL).where(PDL.usage_point_id == pdl)
        )
        pdl_record = pdl_result.scalar_one_or_none()

        if not pdl_record or not pdl_record.selected_offer_id:
            logger.warning(f"[HA-WS] PDL {pdl} has no selected_offer_id, cannot calculate costs")
            return {}

        # Get the energy offer
        offer_result = await db.execute(
            select(EnergyOffer).where(EnergyOffer.id == pdl_record.selected_offer_id)
        )
        offer = offer_result.scalar_one_or_none()

        if not offer:
            logger.warning(f"[HA-WS] Energy offer {pdl_record.selected_offer_id} not found")
            return {}

        # Build price map based on offer type
        # Convert Decimal to float for calculations
        prices: dict[str, float] = {}

        if offer.offer_type == "TEMPO":
            # TEMPO has 6 tariffs
            if offer.tempo_blue_hc:
                prices["blue_hc"] = float(offer.tempo_blue_hc)
            if offer.tempo_blue_hp:
                prices["blue_hp"] = float(offer.tempo_blue_hp)
            if offer.tempo_white_hc:
                prices["white_hc"] = float(offer.tempo_white_hc)
            if offer.tempo_white_hp:
                prices["white_hp"] = float(offer.tempo_white_hp)
            if offer.tempo_red_hc:
                prices["red_hc"] = float(offer.tempo_red_hc)
            if offer.tempo_red_hp:
                prices["red_hp"] = float(offer.tempo_red_hp)
        elif offer.offer_type in ("HC_HP", "HCHP"):
            # HC/HP has 2 tariffs
            if offer.hc_price:
                prices["hc"] = float(offer.hc_price)
            if offer.hp_price:
                prices["hp"] = float(offer.hp_price)
        else:
            # BASE has 1 tariff
            if offer.base_price:
                prices["base"] = float(offer.base_price)

        logger.info(f"[HA-WS] Using prices from offer '{offer.name}': {prices}")

        if not prices:
            logger.warning(f"[HA-WS] No prices found in offer '{offer.name}'")
            return {}

        # Calculate cost for each tariff bucket
        cost_by_tariff: dict[str, list[dict[str, Any]]] = {}

        for tariff_tag, consumption_stats in consumption_by_tariff.items():
            if tariff_tag not in prices:
                logger.debug(f"[HA-WS] No price for tariff {tariff_tag}, skipping cost calculation")
                continue

            price_per_kwh = prices[tariff_tag]
            cost_stats = []
            cumulative_cost = 0.0

            for stat in consumption_stats:
                # stat has: start, state (kWh for this period), sum (cumulative kWh)
                consumption_kwh = stat["state"]
                cost_eur = consumption_kwh * price_per_kwh
                cumulative_cost += cost_eur

                cost_stats.append({
                    "start": stat["start"],
                    "state": round(cost_eur, 4),  # Cost in EUR for this hour
                    "sum": round(cumulative_cost, 4),  # Cumulative cost
                })

            cost_by_tariff[tariff_tag] = cost_stats
            logger.debug(f"[HA-WS] {pdl} cost {tariff_tag}: {len(cost_stats)} records, total={cumulative_cost:.2f} EUR")

        return cost_by_tariff

    async def _get_production_statistics(
        self,
        db: AsyncSession,
        pdl: str,
        since_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Get production statistics for Energy Dashboard

        Returns statistics in the format expected by recorder/import_statistics.
        Uses detailed (30-min) data if available, otherwise falls back to daily.

        Args:
            db: Database session
            pdl: Usage point ID
            since_date: Only include records after this date (for incremental import)

        Returns:
            List of statistics records [{start, state, sum}, ...]
        """
        from zoneinfo import ZoneInfo

        from ...models.client_mode import ProductionData, DataGranularity

        tz_paris = ZoneInfo("Europe/Paris")

        # Try detailed data first
        try:
            detailed_query = (
                select(ProductionData)
                .where(ProductionData.usage_point_id == pdl)
                .where(ProductionData.granularity == DataGranularity.DETAILED)
            )
            if since_date:
                detailed_query = detailed_query.where(ProductionData.date >= since_date.date())
            detailed_query = detailed_query.order_by(ProductionData.date, ProductionData.interval_start)

            detailed_result = await db.execute(detailed_query)
            detailed_records = detailed_result.scalars().all()

            if detailed_records:
                records = detailed_records
                use_detailed = True
                logger.debug(f"[HA-WS] Using {len(records)} detailed production records for {pdl}" + (f" (since {since_date.date()})" if since_date else ""))
            else:
                # Fallback to daily
                daily_query = (
                    select(ProductionData)
                    .where(ProductionData.usage_point_id == pdl)
                    .where(ProductionData.granularity == DataGranularity.DAILY)
                )
                if since_date:
                    daily_query = daily_query.where(ProductionData.date >= since_date.date())
                daily_query = daily_query.order_by(ProductionData.date)

                daily_result = await db.execute(daily_query)
                records = daily_result.scalars().all()
                use_detailed = False
                logger.debug(f"[HA-WS] Using {len(records)} daily production records for {pdl}" + (f" (since {since_date.date()})" if since_date else ""))
        except Exception:
            return []

        if not records:
            return []

        # Helper to convert W → Wh based on interval_length
        def convert_w_to_wh(value_w: int, raw_data: dict | None) -> float:
            """Convert Watts to Watt-hours based on interval_length

            For detailed data, values are in W (average power over interval).
            Formula: Wh = W / (60 / interval_minutes)
            - PT10M → Wh = W / 6
            - PT15M → Wh = W / 4
            - PT30M → Wh = W / 2 (default)
            - PT60M → Wh = W / 1

            For daily data, values are already in Wh.
            """
            if not raw_data:
                # Default to PT30M for detailed data without raw_data
                return value_w / 2 if use_detailed else float(value_w)

            interval_length = raw_data.get("interval_length", "PT30M")

            # Parse interval_length (e.g., "PT30M" → 30)
            match = re.match(r"PT(\d+)M", interval_length)
            if match:
                interval_minutes = int(match.group(1))
                # Wh = W / (60 / interval_minutes)
                return value_w / (60 / interval_minutes)

            # For daily data (PT1D or unknown), value is already in Wh
            return float(value_w)

        # Build statistics with cumulative sum
        # Home Assistant requires hourly data (timestamps at XX:00:00)
        # For detailed (30-min) data, aggregate by hour
        # Key: (date, hour) -> value_kwh
        hourly_aggregation: dict[tuple[Any, int], float] = {}

        for record in records:
            # Convert W → Wh using interval_length from raw_data
            value_wh = convert_w_to_wh(record.value, record.raw_data) if record.value else 0
            value_kwh = value_wh / 1000

            if use_detailed and record.interval_start:
                hour, _ = map(int, record.interval_start.split(":"))
                key = (record.date, hour)
                hourly_aggregation[key] = hourly_aggregation.get(key, 0) + value_kwh
            else:
                # Daily data: split into 24 hourly entries
                hourly_value = value_kwh / 24
                for h in range(24):
                    key = (record.date, h)
                    hourly_aggregation[key] = hourly_aggregation.get(key, 0) + hourly_value

        # Build final statistics sorted by time
        stats = []
        cumulative_kwh = 0.0
        sorted_keys = sorted(hourly_aggregation.keys(), key=lambda k: (k[0], k[1]))

        for record_date, hour in sorted_keys:
            value_kwh = hourly_aggregation[(record_date, hour)]
            cumulative_kwh += value_kwh

            # Build datetime at the start of the hour
            start_dt = datetime.combine(record_date, datetime.min.time().replace(hour=hour, minute=0, second=0))
            start_dt = start_dt.replace(tzinfo=tz_paris)

            stats.append({
                "start": start_dt.isoformat(),
                "state": round(value_kwh, 3),
                "sum": round(cumulative_kwh, 3),
            })

        return stats
