from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class SourceType(StrEnum):
    USER_INPUT = 'USER_INPUT'
    USER_IMPORT = 'USER_IMPORT'
    PUBLIC_SOURCE = 'PUBLIC_SOURCE'
    HISTORICAL = 'HISTORICAL'
    DERIVED = 'DERIVED'
    FORECAST = 'FORECAST'
    ASSUMED = 'ASSUMED'
    SIMULATED = 'SIMULATED'


class ProvenanceMetadata(BaseModel):
    source_type: SourceType
    source_name: str
    retrieved_at: datetime | None = None
    effective_date: date
    notes: str


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


Positive = Annotated[float, Field(gt=0)]
Nonnegative = Annotated[float, Field(ge=0)]


class Money(Model):
    amount: Nonnegative
    currency: str = Field(default='USD', pattern='^[A-Z]{3}$')


class ShipmentRequirement(Model):
    cargo_type: str = Field(pattern='^(COKING_COAL|THERMAL_COAL|IRON_ORE)$')
    cargo_quantity_tonnes: Positive = Field(le=1_000_000)
    origin_country: str
    origin_port: str
    destination_country: str
    destination_port: str
    required_arrival_date: date
    current_inventory: Nonnegative | None = None
    minimum_inventory: Nonnegative | None = None
    cargo_value: Money | None = None
    notes: str = Field(default='', max_length=2000)


class VesselClass(Model):
    name: Literal['HANDYSIZE', 'SUPRAMAX', 'PANAMAX', 'CAPESIZE']
    typical_dwt: Positive
    usable_cargo_capacity: Positive
    typical_draft: Positive
    typical_loa: Positive
    typical_beam: Positive
    reference_speed: Positive
    reference_daily_charter_rate: Positive
    fuel_tonnes_per_sea_day: Positive
    provenance: ProvenanceMetadata


class Port(Model):
    name: str
    country: str
    maximum_draft: Positive
    maximum_loa: Positive
    maximum_beam: Positive
    cargo_capabilities: list[str]
    reference_port_cost: Nonnegative
    reference_waiting_days: Nonnegative
    provenance: ProvenanceMetadata


class Check(Model):
    constraint: str
    location: str
    status: Literal['PASS', 'FAIL', 'CONDITIONAL']
    required: float
    available: float
    margin: float
    unit: str
    explanation: str


class Feasibility(Model):
    status: Literal['PASS', 'FAIL', 'CONDITIONAL']
    voyage_count: int
    checks: list[Check]


class VoyageEstimate(Model):
    distance_nm: float
    sea_days: float
    return_sea_days: float
    loading_days: float
    unloading_days: float
    port_days: float
    expected_delay_days: float
    estimated_total_days: float
    estimated_arrival: date
    arrival_feasible: bool
    provenance: ProvenanceMetadata


class CostBreakdown(Model):
    currency: str = 'USD'
    ocean_freight: float
    bunker_component: float
    port_cost: float
    expected_demurrage: float
    lighterage_if_applicable: float
    storage_if_applicable: float
    total_logistics_cost: float
    cost_per_tonne: float
    provenance: ProvenanceMetadata


class VesselOption(Model):
    vessel: VesselClass
    feasibility: Feasibility
    voyage: VoyageEstimate
    cost: CostBreakdown


class Recommendation(Model):
    recommended_vessel: str | None
    feasible: bool
    decision: str
    reason_codes: list[str]
    human_explanation: list[str]
    estimated_cost: Money | None
    confidence_status: str = 'DEMO_ESTIMATE_NOT_VALIDATED'
    charter_timing: str = 'NOT_YET_MODELLED'


class Analysis(Model):
    analysis_date: date
    data_mode: str = 'DEMO_REFERENCE'
    shipment: ShipmentRequirement
    reference_ports: list[Port]
    options: list[VesselOption]
    recommendation: Recommendation
    provenance: dict[str, ProvenanceMetadata]
    assumptions: dict[str, float | str]
