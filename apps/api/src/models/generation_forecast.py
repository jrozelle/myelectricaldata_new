"""
Generation Forecast data model for storing RTE production forecast data
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, String, DateTime, Integer, Float, Index
from pydantic import BaseModel

from .base import Base


class GenerationForecast(Base):
    """Model for storing French generation forecast data from RTE"""

    __tablename__ = "generation_forecast"

    id = Column(Integer, primary_key=True, index=True)

    # Type de production : SOLAR, WIND, AGGREGATED_PROGRAMMABLE_FRANCE
    production_type = Column(String(50), nullable=False)

    # Type de prévision : D-3, D-2, D-1, ID, CURRENT
    forecast_type = Column(String(20), nullable=False)

    # Période
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)

    # Valeur en MW
    value = Column(Float, nullable=False)

    # Date de mise à jour par RTE
    updated_date = Column(DateTime, nullable=True)

    # Métadonnées
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_generation_forecast_prod_type", "production_type", "forecast_type", "start_date"),
        Index("idx_generation_forecast_start", "start_date"),
    )


# Pydantic models for API responses
class GenerationForecastValue(BaseModel):
    """Single generation forecast value"""

    start_date: datetime
    end_date: datetime
    value: float  # MW
    updated_date: Optional[datetime] = None


class GenerationForecastData(BaseModel):
    """Generation forecast data for a production type"""

    production_type: str  # SOLAR, WIND, etc.
    forecast_type: str  # D-3, D-2, D-1, ID, CURRENT
    start_date: datetime
    end_date: datetime
    values: List[GenerationForecastValue]


class GenerationForecastResponse(BaseModel):
    """Response model for generation forecast data"""

    forecasts: List[GenerationForecastData]
    cached_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Constantes pour les types
class ProductionType:
    SOLAR = "SOLAR"
    WIND = "WIND"
    AGGREGATED_PROGRAMMABLE = "AGGREGATED_PROGRAMMABLE_FRANCE"


class ForecastType:
    D_3 = "D-3"
    D_2 = "D-2"
    D_1 = "D-1"
    ID = "ID"  # Intraday
    CURRENT = "CURRENT"
