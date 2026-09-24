from typing import Protocol
from app.domain.models import Analysis


class ScenarioEngine(Protocol):
    def compare(self, baseline: Analysis, overrides: dict[str, float]) -> Analysis: ...
