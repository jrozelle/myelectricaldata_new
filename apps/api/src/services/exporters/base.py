"""Base Exporter Class

Abstract base class for all exporters.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class BaseExporter(ABC):
    """Abstract base class for data exporters

    All exporters must implement:
    - test_connection(): Verify the connection to the target
    - export_consumption(): Export consumption data
    - export_production(): Export production data
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize exporter with configuration

        Args:
            config: Type-specific configuration dict
        """
        self.config = config
        self._validate_config()

    @abstractmethod
    def _validate_config(self) -> None:
        """Validate the configuration

        Raises:
            ValueError if configuration is invalid
        """
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """Test the connection to the export target

        Returns:
            True if connection successful

        Raises:
            Exception if connection fails
        """
        pass

    @abstractmethod
    async def export_consumption(
        self,
        usage_point_id: str,
        data: list[dict[str, Any]],
        granularity: str,
    ) -> int:
        """Export consumption data

        Args:
            usage_point_id: PDL number
            data: List of consumption records
            granularity: 'daily' or 'detailed'

        Returns:
            Number of records exported
        """
        pass

    @abstractmethod
    async def export_production(
        self,
        usage_point_id: str,
        data: list[dict[str, Any]],
        granularity: str,
    ) -> int:
        """Export production data

        Args:
            usage_point_id: PDL number
            data: List of production records
            granularity: 'daily' or 'detailed'

        Returns:
            Number of records exported
        """
        pass

    async def close(self) -> None:
        """Close any open connections"""
        pass

    async def read_metrics(self, usage_point_ids: list[str] | None = None) -> dict[str, Any]:
        """Read metrics from the export destination

        Retrieves the current state of exported metrics from the target system.
        This allows users to verify what data has been sent and is currently stored.

        Args:
            usage_point_ids: Optional list of PDL numbers to filter metrics

        Returns:
            Dict containing:
            - success: bool indicating if read was successful
            - metrics: list of metric objects with name, value, timestamp, etc.
            - errors: list of any errors encountered
            - timestamp: when the read was performed

        Note:
            Not all exporters support reading back metrics. Those that don't
            should return success=False with an appropriate message.
        """
        return {
            "success": False,
            "message": "La lecture des métriques n'est pas supportée pour cet exporteur",
            "metrics": [],
            "errors": [],
        }
