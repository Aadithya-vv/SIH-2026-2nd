from typing import Protocol
from app.forecasting.interfaces import ForecastQuantiles
from app.domain.models import ShipmentRequirement


class CharterTimingEngine(Protocol):
    def evaluate(self, shipment: ShipmentRequirement, forecast: ForecastQuantiles,
                 operational_risks: dict[str, float]) -> dict: ...
