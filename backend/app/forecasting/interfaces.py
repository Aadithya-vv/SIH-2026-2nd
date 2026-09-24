from dataclasses import dataclass
from typing import Protocol
import pandas as pd


@dataclass(frozen=True)
class ForecastQuantiles:
    horizon_days: list[int]
    p10: list[float]
    p50: list[float]
    p90: list[float]
    currency: str


class FreightForecastModel(Protocol):
    def forecast(self, historical_features: pd.DataFrame, route: str,
                 vessel_class: str, horizons: list[int]) -> ForecastQuantiles: ...
