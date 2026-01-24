"""VictoriaMetrics Exporter

Full-featured exporter to VictoriaMetrics time-series database.
Uses the InfluxDB line protocol for easy data insertion.

Metrics exported:
- electricity_consumption{usage_point_id, granularity} value_wh, value_kwh
- electricity_production{usage_point_id, granularity} value_wh, value_kwh
- electricity_stats{usage_point_id, direction, period, tempo_color} value_wh, value_kwh, value_euro
- tempo_color{date} color
- tempo_days{color} total, remaining
- ecowatt_level{day} value
"""

import logging
from datetime import date, datetime, timedelta
from typing import Any, Optional

import httpx
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


class VictoriaMetricsExporter(BaseExporter):
    """Full-featured VictoriaMetrics exporter

    Configuration:
        url: VictoriaMetrics URL (e.g., http://vm:8428)
        database: Database/tenant name (default: myelectricaldata)
        username: Basic auth username (optional)
        password: Basic auth password (optional)
        export_consumption: Export consumption data (default: True)
        export_production: Export production data (default: True)
        export_tempo: Export Tempo data (default: True)
        export_ecowatt: Export EcoWatt data (default: True)
        export_stats: Export aggregated statistics (default: True)

    Uses the InfluxDB line protocol endpoint for easy data insertion.
    """

    def _validate_config(self) -> None:
        """Validate VictoriaMetrics configuration"""
        if not self.config.get("url"):
            raise ValueError("VictoriaMetrics URL is required")

        self.url = self.config["url"].rstrip("/")
        self.database = self.config.get("database", "myelectricaldata")
        self.username = self.config.get("username")
        self.password = self.config.get("password")

        # Feature toggles
        self.export_consumption_enabled = self.config.get("export_consumption", True)
        self.export_production_enabled = self.config.get("export_production", True)
        self.export_tempo_enabled = self.config.get("export_tempo", True)
        self.export_ecowatt_enabled = self.config.get("export_ecowatt", True)
        self.export_stats_enabled = self.config.get("export_stats", True)

    def _get_auth(self) -> Optional[httpx.BasicAuth]:
        """Get basic auth if configured"""
        if self.username and self.password:
            return httpx.BasicAuth(self.username, self.password)
        return None

    async def test_connection(self) -> bool:
        """Test connection to VictoriaMetrics

        Returns:
            True if connection successful

        Raises:
            Exception if connection fails
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Check health endpoint
            response = await client.get(
                f"{self.url}/health",
                auth=self._get_auth(),
            )
            response.raise_for_status()

            logger.info(f"[VM] Connected to VictoriaMetrics at {self.url}")
            return True

    def _to_line_protocol(
        self,
        measurement: str,
        tags: dict[str, str],
        fields: dict[str, Any],
        timestamp_ns: int,
    ) -> str:
        """Convert data to InfluxDB line protocol format

        Format: measurement,tag1=val1,tag2=val2 field1=val1,field2=val2 timestamp

        Args:
            measurement: Measurement name
            tags: Tag key-value pairs
            fields: Field key-value pairs
            timestamp_ns: Timestamp in nanoseconds

        Returns:
            Line protocol string
        """
        # Tags
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        if tag_str:
            tag_str = "," + tag_str

        # Fields
        field_parts = []
        for k, v in fields.items():
            if isinstance(v, bool):
                field_parts.append(f"{k}={str(v).lower()}")
            elif isinstance(v, int):
                field_parts.append(f"{k}={v}i")
            elif isinstance(v, float):
                field_parts.append(f"{k}={v}")
            elif isinstance(v, str):
                field_parts.append(f'{k}="{v}"')
        field_str = ",".join(field_parts)

        return f"{measurement}{tag_str} {field_str} {timestamp_ns}"

    async def export_consumption(
        self,
        usage_point_id: str,
        data: list[dict[str, Any]],
        granularity: str,
    ) -> int:
        """Export consumption data to VictoriaMetrics

        Args:
            usage_point_id: PDL number
            data: List of consumption records
            granularity: 'daily' or 'detailed'

        Returns:
            Number of records exported
        """
        if not data:
            return 0

        lines = []
        for record in data:
            # Parse date to timestamp
            date_str = record.get("date", "")
            try:
                if isinstance(date_str, str):
                    if "T" in date_str or " " in date_str:
                        dt = datetime.fromisoformat(date_str.replace(" ", "T").replace("Z", "+00:00"))
                    else:
                        dt = datetime.fromisoformat(date_str)
                else:
                    dt = datetime.combine(date_str, datetime.min.time())

                timestamp_ns = int(dt.timestamp() * 1e9)
            except (ValueError, AttributeError):
                continue

            line = self._to_line_protocol(
                measurement="electricity_consumption",
                tags={
                    "usage_point_id": usage_point_id,
                    "granularity": granularity,
                },
                fields={
                    "value_wh": record.get("value", 0),
                    "value_kwh": record.get("value", 0) / 1000,
                },
                timestamp_ns=timestamp_ns,
            )
            lines.append(line)

        if not lines:
            return 0

        # Send data using InfluxDB line protocol
        payload = "\n".join(lines)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.url}/write",
                params={"db": self.database},
                content=payload,
                headers={"Content-Type": "text/plain"},
                auth=self._get_auth(),
            )
            response.raise_for_status()

        logger.info(f"[VM] Exported consumption for {usage_point_id}: {len(lines)} records")
        return len(lines)

    async def export_production(
        self,
        usage_point_id: str,
        data: list[dict[str, Any]],
        granularity: str,
    ) -> int:
        """Export production data to VictoriaMetrics

        Args:
            usage_point_id: PDL number
            data: List of production records
            granularity: 'daily' or 'detailed'

        Returns:
            Number of records exported
        """
        if not data:
            return 0

        lines = []
        for record in data:
            date_str = record.get("date", "")
            try:
                if isinstance(date_str, str):
                    if "T" in date_str or " " in date_str:
                        dt = datetime.fromisoformat(date_str.replace(" ", "T").replace("Z", "+00:00"))
                    else:
                        dt = datetime.fromisoformat(date_str)
                else:
                    dt = datetime.combine(date_str, datetime.min.time())

                timestamp_ns = int(dt.timestamp() * 1e9)
            except (ValueError, AttributeError):
                continue

            line = self._to_line_protocol(
                measurement="electricity_production",
                tags={
                    "usage_point_id": usage_point_id,
                    "granularity": granularity,
                },
                fields={
                    "value_wh": record.get("value", 0),
                    "value_kwh": record.get("value", 0) / 1000,
                },
                timestamp_ns=timestamp_ns,
            )
            lines.append(line)

        if not lines:
            return 0

        payload = "\n".join(lines)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.url}/write",
                params={"db": self.database},
                content=payload,
                headers={"Content-Type": "text/plain"},
                auth=self._get_auth(),
            )
            response.raise_for_status()

        logger.info(f"[VM] Exported production for {usage_point_id}: {len(lines)} records")
        return len(lines)

    # =========================================================================
    # FULL EXPORT METHOD
    # =========================================================================

    async def run_full_export(self, db: AsyncSession, usage_point_ids: list[str]) -> dict[str, Any]:
        """Run full VictoriaMetrics export for all PDLs

        Exports:
        - Raw consumption/production data (daily and detailed)
        - Aggregated statistics (year, month, week totals)
        - Tempo data (colors, days used/remaining)
        - EcoWatt signals (j0, j1, j2)

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
            "stats": 0,
            "tempo": 0,
            "ecowatt": 0,
            "errors": [],
        }

        lines: list[str] = []
        now_ns = int(datetime.now().timestamp() * 1e9)

        # Global exports (not PDL-specific)
        if self.export_ecowatt_enabled:
            try:
                ecowatt_lines = await self._build_ecowatt_lines(db, now_ns)
                lines.extend(ecowatt_lines)
                results["ecowatt"] = len(ecowatt_lines)
            except Exception as e:
                logger.error(f"[VM] EcoWatt export failed: {e}")
                results["errors"].append(f"ecowatt: {str(e)}")

        if self.export_tempo_enabled:
            try:
                tempo_lines = await self._build_tempo_global_lines(db, now_ns)
                lines.extend(tempo_lines)
                results["tempo"] += len(tempo_lines)
            except Exception as e:
                logger.error(f"[VM] Tempo global export failed: {e}")
                results["errors"].append(f"tempo_global: {str(e)}")

        # Per-PDL exports
        for pdl in usage_point_ids:
            try:
                # Consumption data
                if self.export_consumption_enabled:
                    consumption_lines = await self._build_data_lines(db, pdl, "consumption", now_ns)
                    lines.extend(consumption_lines)
                    results["consumption"] += len(consumption_lines)

                # Production data
                if self.export_production_enabled:
                    production_lines = await self._build_data_lines(db, pdl, "production", now_ns)
                    lines.extend(production_lines)
                    results["production"] += len(production_lines)

                # Aggregated statistics
                if self.export_stats_enabled:
                    stats_lines = await self._build_stats_lines(stats, pdl, now_ns)
                    lines.extend(stats_lines)
                    results["stats"] += len(stats_lines)

                # Tempo consumption by color
                if self.export_tempo_enabled:
                    tempo_consumption_lines = await self._build_tempo_consumption_lines(stats, pdl, now_ns)
                    lines.extend(tempo_consumption_lines)
                    results["tempo"] += len(tempo_consumption_lines)

            except Exception as e:
                logger.error(f"[VM] Export failed for PDL {pdl}: {e}")
                results["errors"].append(f"{pdl}: {str(e)}")

        # Send all data to VictoriaMetrics
        if lines:
            try:
                await self._send_lines(lines)
                logger.info(f"[VM] Sent {len(lines)} metrics to VictoriaMetrics")
            except Exception as e:
                logger.error(f"[VM] Failed to send metrics: {e}")
                results["errors"].append(f"send: {str(e)}")

        logger.info(f"[VM] Full export completed: {results}")
        return results

    async def _send_lines(self, lines: list[str]) -> None:
        """Send lines to VictoriaMetrics in batches"""
        batch_size = 1000
        for i in range(0, len(lines), batch_size):
            batch = lines[i : i + batch_size]
            payload = "\n".join(batch)

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.url}/write",
                    params={"db": self.database},
                    content=payload,
                    headers={"Content-Type": "text/plain"},
                    auth=self._get_auth(),
                )
                response.raise_for_status()

    # =========================================================================
    # DATA LINES BUILDERS
    # =========================================================================

    async def _build_data_lines(
        self,
        db: AsyncSession,
        usage_point_id: str,
        direction: str,
        now_ns: int,
    ) -> list[str]:
        """Build InfluxDB lines for raw consumption/production data

        Exports the last 7 days of data.
        """
        from ...models.client_mode import ConsumptionData, ProductionData

        model = ProductionData if direction == "production" else ConsumptionData
        measurement = f"electricity_{direction}"

        end_date = (datetime.now() - timedelta(days=1)).date()
        start_date = end_date - timedelta(days=6)

        result = await db.execute(
            select(model)
            .where(model.usage_point_id == usage_point_id)
            .where(model.date >= start_date)
            .where(model.date <= end_date)
            .order_by(model.date, model.interval_start)
        )
        records = result.scalars().all()

        lines = []
        for record in records:
            try:
                # Build timestamp from date + interval_start
                if record.interval_start:
                    hour, minute = map(int, record.interval_start.split(":"))
                    dt = datetime.combine(record.date, datetime.min.time().replace(hour=hour, minute=minute))
                else:
                    dt = datetime.combine(record.date, datetime.min.time())

                timestamp_ns = int(dt.timestamp() * 1e9)

                line = self._to_line_protocol(
                    measurement=measurement,
                    tags={
                        "usage_point_id": usage_point_id,
                        "granularity": record.granularity.value,
                    },
                    fields={
                        "value_wh": record.value,
                        "value_kwh": record.value / 1000,
                    },
                    timestamp_ns=timestamp_ns,
                )
                lines.append(line)
            except Exception as e:
                logger.debug(f"[VM] Skip record {record}: {e}")

        return lines

    async def _build_stats_lines(
        self,
        stats: Any,
        usage_point_id: str,
        now_ns: int,
    ) -> list[str]:
        """Build InfluxDB lines for aggregated statistics"""
        lines = []
        today = date.today()
        current_year = today.year
        iso_year, iso_week, _ = today.isocalendar()

        for direction in ["consumption", "production"]:
            # This Year
            year_total = await stats.get_year_total(usage_point_id, current_year, direction)
            lines.append(self._to_line_protocol(
                measurement="electricity_stats",
                tags={"usage_point_id": usage_point_id, "direction": direction, "period": "this_year"},
                fields={"value_wh": year_total, "value_kwh": year_total / 1000},
                timestamp_ns=now_ns,
            ))

            # This Month
            month_total = await stats.get_month_total(usage_point_id, current_year, today.month, direction)
            lines.append(self._to_line_protocol(
                measurement="electricity_stats",
                tags={"usage_point_id": usage_point_id, "direction": direction, "period": "this_month"},
                fields={"value_wh": month_total, "value_kwh": month_total / 1000},
                timestamp_ns=now_ns,
            ))

            # This Week
            week_total = await stats.get_week_total(usage_point_id, iso_year, iso_week, direction)
            lines.append(self._to_line_protocol(
                measurement="electricity_stats",
                tags={"usage_point_id": usage_point_id, "direction": direction, "period": "this_week"},
                fields={"value_wh": week_total, "value_kwh": week_total / 1000},
                timestamp_ns=now_ns,
            ))

            # Linear stats (year, year-1, year-2, year-3)
            for years_back in range(4):
                year_label = "year" if years_back == 0 else f"year_{years_back}"
                linear_total = await stats.get_linear_year_total(usage_point_id, years_back, direction)
                lines.append(self._to_line_protocol(
                    measurement="electricity_linear",
                    tags={"usage_point_id": usage_point_id, "direction": direction, "offset": year_label},
                    fields={"value_wh": linear_total, "value_kwh": linear_total / 1000},
                    timestamp_ns=now_ns,
                ))

        return lines

    # =========================================================================
    # TEMPO LINES BUILDERS
    # =========================================================================

    async def _build_tempo_global_lines(self, db: AsyncSession, now_ns: int) -> list[str]:
        """Build InfluxDB lines for global Tempo data"""
        from ...models.tempo_day import TempoDay, TempoColor

        lines = []
        today = date.today()
        tomorrow = today + timedelta(days=1)

        # Color map for numeric values (for graphing)
        color_values = {"BLUE": 1, "WHITE": 2, "RED": 3, "UNKNOWN": 0}

        # Today's color
        today_str = today.isoformat()
        result = await db.execute(select(TempoDay).where(TempoDay.id == today_str))
        today_tempo = result.scalar_one_or_none()

        today_color = today_tempo.color.value if today_tempo else "UNKNOWN"
        lines.append(self._to_line_protocol(
            measurement="tempo_color",
            tags={"day": "today"},
            fields={"color": today_color, "color_value": color_values.get(today_color, 0)},
            timestamp_ns=now_ns,
        ))

        # Tomorrow's color
        tomorrow_str = tomorrow.isoformat()
        result = await db.execute(select(TempoDay).where(TempoDay.id == tomorrow_str))
        tomorrow_tempo = result.scalar_one_or_none()

        tomorrow_color = tomorrow_tempo.color.value if tomorrow_tempo else "UNKNOWN"
        lines.append(self._to_line_protocol(
            measurement="tempo_color",
            tags={"day": "tomorrow"},
            fields={"color": tomorrow_color, "color_value": color_values.get(tomorrow_color, 0)},
            timestamp_ns=now_ns,
        ))

        # Tempo season stats (Sept 1 to Aug 31)
        if today.month >= 9:
            season_start = date(today.year, 9, 1)
        else:
            season_start = date(today.year - 1, 9, 1)

        season_start_str = season_start.isoformat()

        for color in TempoColor:
            result = await db.execute(
                select(func.count(TempoDay.id))
                .where(TempoDay.id >= season_start_str)
                .where(TempoDay.id <= today_str)
                .where(cast(TempoDay.color, String) == color.value)
            )
            total = result.scalar() or 0
            quota = TEMPO_QUOTAS.get(color.value, 0)
            remaining = max(0, quota - total)

            lines.append(self._to_line_protocol(
                measurement="tempo_days",
                tags={"color": color.value},
                fields={"total": total, "remaining": remaining, "quota": quota},
                timestamp_ns=now_ns,
            ))

        return lines

    async def _build_tempo_consumption_lines(
        self,
        stats: Any,
        usage_point_id: str,
        now_ns: int,
    ) -> list[str]:
        """Build InfluxDB lines for consumption by Tempo color"""
        lines = []
        today = date.today()
        current_year = today.year

        # This Year by Tempo color
        year_totals = await stats.get_tempo_year_totals(usage_point_id, current_year, "consumption")
        for color, value in year_totals.items():
            lines.append(self._to_line_protocol(
                measurement="electricity_tempo",
                tags={"usage_point_id": usage_point_id, "color": color, "period": "this_year"},
                fields={"value_wh": value, "value_kwh": value / 1000},
                timestamp_ns=now_ns,
            ))

        # This Month by Tempo color
        month_totals = await stats.get_tempo_month_totals(usage_point_id, current_year, today.month, "consumption")
        for color, value in month_totals.items():
            lines.append(self._to_line_protocol(
                measurement="electricity_tempo",
                tags={"usage_point_id": usage_point_id, "color": color, "period": "this_month"},
                fields={"value_wh": value, "value_kwh": value / 1000},
                timestamp_ns=now_ns,
            ))

        return lines

    # =========================================================================
    # ECOWATT LINES BUILDER
    # =========================================================================

    async def _build_ecowatt_lines(self, db: AsyncSession, now_ns: int) -> list[str]:
        """Build InfluxDB lines for EcoWatt signals"""
        from ...models.ecowatt import EcoWatt

        lines = []
        today = date.today()

        for day_offset, day_label in enumerate(["j0", "j1", "j2"]):
            target_date = today + timedelta(days=day_offset)

            result = await db.execute(
                select(EcoWatt)
                .where(func.date(EcoWatt.periode) == target_date)
                .order_by(EcoWatt.generation_datetime.desc())
                .limit(1)
            )
            ecowatt = result.scalar_one_or_none()

            if ecowatt:
                lines.append(self._to_line_protocol(
                    measurement="ecowatt",
                    tags={"day": day_label, "date": target_date.isoformat()},
                    fields={"level": ecowatt.dvalue},
                    timestamp_ns=now_ns,
                ))

                # Hourly details
                if ecowatt.values:
                    for hour, value in enumerate(ecowatt.values):
                        lines.append(self._to_line_protocol(
                            measurement="ecowatt_hourly",
                            tags={"day": day_label, "hour": str(hour)},
                            fields={"level": value},
                            timestamp_ns=now_ns,
                        ))

        return lines

    # =========================================================================
    # READ METRICS
    # =========================================================================

    async def read_metrics(self, usage_point_ids: list[str] | None = None) -> dict[str, Any]:
        """Read metrics from VictoriaMetrics

        Uses the PromQL query API to retrieve current metric values.

        Args:
            usage_point_ids: Optional list of PDL numbers to filter

        Returns:
            Dict with metrics organized by measurement
        """
        metrics: list[dict[str, Any]] = []
        errors: list[str] = []

        # Liste des requêtes à exécuter
        # Note: VictoriaMetrics transforme le line protocol en ajoutant le nom du champ
        # Ex: electricity_stats value_kwh=1.5 → electricity_stats_value_kwh
        # On récupère dynamiquement les métriques disponibles pour ne pas rater des données

        # Mapping des préfixes vers les catégories
        category_mapping = {
            "electricity_consumption": "Consommation",
            "electricity_production": "Production",
            "electricity_stats": "Statistiques",
            "electricity_linear": "Statistiques Linéaires",
            "electricity_tempo": "Tempo Consommation",
            "tempo_color": "Tempo Couleur",
            "tempo_days": "Tempo Jours",
            "ecowatt_level": "EcoWatt",
            "ecowatt_hourly": "EcoWatt Horaire",
        }

        # Récupérer toutes les métriques disponibles
        queries = []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.url}/api/v1/label/__name__/values",
                    auth=self._get_auth(),
                )
                if response.status_code == 200:
                    data = response.json()
                    available_metrics = data.get("data", [])

                    for metric_name in available_metrics:
                        # Trouver la catégorie correspondante
                        category = "Autre"
                        for prefix, cat in category_mapping.items():
                            if metric_name.startswith(prefix):
                                category = cat
                                break

                        # Ne garder que les métriques pertinentes (pas les doublons _wh/_kwh)
                        # Préférer kWh pour la lisibilité
                        if metric_name.endswith("_wh") and f"{metric_name[:-3]}_kwh" in available_metrics:
                            continue  # Skip les _wh si _kwh existe

                        queries.append({"query": metric_name, "category": category})

                    logger.info(f"[VM] Found {len(queries)} metrics to query")
        except Exception as e:
            logger.warning(f"[VM] Could not list metrics, using defaults: {e}")
            # Fallback aux métriques connues si la liste échoue
            queries = [
                {"query": "electricity_stats_value_kwh", "category": "Statistiques"},
                {"query": "electricity_linear_value_kwh", "category": "Statistiques Linéaires"},
                {"query": "electricity_tempo_value_kwh", "category": "Tempo Consommation"},
                {"query": "tempo_color_color", "category": "Tempo Couleur"},
                {"query": "tempo_color_color_value", "category": "Tempo Couleur (numérique)"},
                {"query": "tempo_days_total", "category": "Tempo Jours"},
                {"query": "tempo_days_remaining", "category": "Tempo Jours"},
                {"query": "tempo_days_quota", "category": "Tempo Jours"},
                {"query": "ecowatt_level", "category": "EcoWatt"},
                {"query": "ecowatt_hourly_level", "category": "EcoWatt Horaire"},
            ]

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                for q in queries:
                    try:
                        # Construire la requête PromQL
                        base_query = q["query"]

                        # Certaines métriques n'ont pas de label usage_point_id (globales)
                        is_global = base_query.startswith(("tempo_", "ecowatt"))

                        if usage_point_ids and not is_global:
                            # Filtrer par PDL pour les métriques non-globales
                            pdl_filter = "|".join(usage_point_ids)
                            query = f'{base_query}{{usage_point_id=~"{pdl_filter}"}}'
                        else:
                            query = base_query

                        response = await client.get(
                            f"{self.url}/api/v1/query",
                            params={"query": query},
                            auth=self._get_auth(),
                        )

                        if response.status_code == 200:
                            data = response.json()
                            if data.get("status") == "success":
                                results = data.get("data", {}).get("result", [])
                                for result in results:
                                    metric_labels = result.get("metric", {})
                                    value_tuple = result.get("value", [])

                                    if len(value_tuple) >= 2:
                                        timestamp, value = value_tuple

                                        # Extraire le PDL des labels
                                        pdl = metric_labels.get("usage_point_id")

                                        # Construire le nom de la métrique
                                        metric_name = metric_labels.get("__name__", q["query"])
                                        tags = {k: v for k, v in metric_labels.items() if k != "__name__"}

                                        metrics.append({
                                            "name": metric_name,
                                            "category": q["category"],
                                            "pdl": pdl,
                                            "value": float(value) if value != "NaN" else None,
                                            "timestamp": datetime.fromtimestamp(float(timestamp)).isoformat(),
                                            "tags": tags,
                                        })
                        else:
                            errors.append(f"Erreur {response.status_code} pour {q['query']}")

                    except Exception as e:
                        errors.append(f"Erreur requête {q['query']}: {str(e)}")

            logger.info(f"[VM] Read {len(metrics)} metrics from VictoriaMetrics")

            return {
                "success": True,
                "message": f"{len(metrics)} métriques lues depuis VictoriaMetrics",
                "metrics": metrics,
                "errors": errors,
                "url": self.url,
                "database": self.database,
            }

        except Exception as e:
            logger.error(f"[VM] Failed to read metrics: {e}")
            return {
                "success": False,
                "message": f"Erreur de connexion: {str(e)}",
                "metrics": [],
                "errors": [str(e)],
            }
