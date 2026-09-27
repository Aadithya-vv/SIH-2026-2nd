from datetime import datetime, timezone
from typing import Literal
from pydantic import Field, field_validator, model_validator
from app.domain.models import Model, ShipmentRequirement

RiskProfile = Literal['CONSERVATIVE', 'BALANCED', 'COST_FOCUSED']


class CharterTimingRequest(Model):
    shipment: ShipmentRequirement
    vessel_class: Literal['HANDYSIZE', 'SUPRAMAX', 'PANAMAX', 'CAPESIZE']
    analysis_as_of: datetime
    forecast_model_id: str | None = Field(default=None, pattern='^[a-f0-9]{24}$')
    risk_profile: RiskProfile = 'BALANCED'
    schedule_buffer_days: float = Field(default=2, ge=0, le=30)
    loading_days: float | None = Field(default=None, ge=0, le=365)
    unloading_days: float | None = Field(default=None, ge=0, le=365)
    demurrage_usd_per_day: float | None = Field(default=None, ge=0, le=1_000_000)
    storage_usd_per_tonne_day: float | None = Field(default=None, ge=0, le=10000)
    allow_index_proxy: bool = False
    index_anchor_hire_usd_per_day: float | None = Field(default=None, gt=0, le=1_000_000)
    # Optional explicit overrides are policy limits, not learned probabilities.
    max_downside_fraction: float | None = Field(default=None, ge=0, le=1)
    window_cost_tolerance_fraction: float = Field(default=.0025, ge=0, le=.05)

    @field_validator('analysis_as_of')
    @classmethod
    def utc(cls, value):
        if value.tzinfo is None:
            raise ValueError('analysis_as_of must include a timezone.')
        return value.astimezone(timezone.utc)

    @model_validator(mode='after')
    def dates(self):
        if self.shipment.required_arrival_date < self.analysis_as_of.date():
            raise ValueError('Required arrival cannot precede analysis day.')
        if (self.shipment.required_arrival_date-self.analysis_as_of.date()).days > 1095:
            raise ValueError('Arrival must be within three years of analysis.')
        if self.index_anchor_hire_usd_per_day is not None and not self.allow_index_proxy:
            raise ValueError('An index anchor requires explicit index-proxy consent.')
        return self


class CharterTimingDecision(Model):
    analysis_id: str
    generated_at: str
    policy_version: str
    request: CharterTimingRequest
    recommendation: Literal['LOCK_NOW', 'WAIT', 'NO_SAFE_WAIT_WINDOW', 'INSUFFICIENT_DATA']
    recommended_window_start: str | None = None
    recommended_window_end: str | None = None
    latest_safe_charter_date: str | None = None
    selected_wait_days: int | None = None
    evidence_status: Literal['STRONG', 'MODERATE', 'LIMITED'] = 'LIMITED'
    evidence_factors: dict = Field(default_factory=dict)
    current_charter_cost: float | None = None
    recommended_median_cost: float | None = None
    median_saving: float | None = None
    downside_exposure: float | None = None
    schedule_slack: float | None = None
    candidate_decisions: list[dict] = Field(default_factory=list)
    rejected_region: dict = Field(default_factory=dict)
    explanation: list[str] = Field(default_factory=list)
    forecast_metadata: dict | None = None
    market_snapshot: dict = Field(default_factory=dict)
    voyage_context: dict = Field(default_factory=dict)
    rate_conversion: dict = Field(default_factory=dict)
    policy: dict = Field(default_factory=dict)
    assumptions: dict = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    performance: dict = Field(default_factory=dict)
