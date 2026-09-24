from datetime import datetime, timezone, date
from enum import StrEnum
from typing import Literal
from pydantic import Field, field_validator, model_validator
from app.domain.models import Model, ProvenanceMetadata


class Category(StrEnum):
    FREIGHT = 'FREIGHT'
    COMMODITY = 'COMMODITY'
    BUNKER = 'BUNKER'
    PORT = 'PORT'
    WEATHER = 'WEATHER'


class Source(Model):
    source_id: str
    name: str
    category: Category
    provider: str
    access_type: Literal['PUBLIC_API', 'PUBLIC_DOWNLOAD', 'USER_IMPORT', 'COMMERCIAL_REQUIRED', 'DEMO']
    update_frequency: str = 'DAILY'
    expected_units: list[str]
    license_notes: str
    availability_status: str
    last_successful_ingestion: datetime | None = None
    notes: str = ''


class Series(Model):
    series_id: str
    name: str
    category: Category
    source_id: str
    unit: str
    currency: str | None = None
    frequency_days: int = Field(default=1, ge=1, le=366)
    route: str | None = None
    vessel_class: str | None = None
    commodity: str | None = None
    benchmark: str | None = None
    origin_region: str | None = None
    fuel_type: str | None = None
    port: str | None = None
    provenance: ProvenanceMetadata


class Observation(Model):
    timestamp: datetime
    available_at: datetime
    value: float = Field(ge=0)
    original_value: float
    original_unit: str
    original_currency: str | None = None
    quality_flags: list[str] = Field(default_factory=list)
    vessels_waiting: int | None = Field(default=None, ge=0)
    berth_delay: float | None = Field(default=None, ge=0)
    congestion_level: str | None = None

    @field_validator('timestamp', 'available_at')
    @classmethod
    def utc(cls, value):
        if value.tzinfo is None:
            raise ValueError('Timezone required; timestamps are stored in UTC.')
        return value.astimezone(timezone.utc)

    @model_validator(mode='after')
    def publication_order(self):
        if self.available_at < self.timestamp:
            raise ValueError('Availability cannot precede observation timestamp.')
        return self


class WeatherObservation(Model):
    timestamp: datetime
    available_at: datetime
    port: str | None = None
    route: str | None = None
    wind_knots: float | None = Field(default=None, ge=0)
    wave_height_metres: float | None = Field(default=None, ge=0)
    cyclone_flag: bool | None = None
    severity: Literal['LOW', 'MODERATE', 'HIGH', 'SEVERE'] | None = None
    route_disruption: str | None = None
    provenance: ProvenanceMetadata

    @field_validator('timestamp', 'available_at')
    @classmethod
    def utc(cls, value):
        if value.tzinfo is None:
            raise ValueError('Weather timestamps require a timezone.')
        return value.astimezone(timezone.utc)

    @model_validator(mode='after')
    def publication_order(self):
        if self.available_at < self.timestamp:
            raise ValueError('Availability cannot precede weather observation.')
        return self


class ImportRequest(Model):
    category: Literal['FREIGHT', 'COMMODITY', 'BUNKER', 'PORT']
    source_name: str = Field(min_length=1, max_length=150)
    series_name: str = Field(min_length=1, max_length=150)
    csv_text: str = Field(min_length=1, max_length=2_000_000)
    date_column: str = 'date'
    value_column: str = 'value'
    available_at_column: str | None = None
    unit_column: str | None = None
    unit: str
    currency: str | None = None
    frequency_days: int = Field(default=1, ge=1, le=366)
    route: str | None = None
    vessel_class: Literal['HANDYSIZE','SUPRAMAX','PANAMAX','CAPESIZE'] | None = None
    commodity: Literal['COKING_COAL','THERMAL_COAL','IRON_ORE'] | None = None
    benchmark: str | None = None
    origin_region: str | None = None
    fuel_type: Literal['VLSFO','MGO'] | None = None
    port: str | None = None
    preview_hash: str | None = None
    commit: bool = False

    @field_validator('port','route','benchmark','origin_region')
    @classmethod
    def optional_text(cls, value):
        return (value.strip() or None) if value is not None else None

    @field_validator('source_name','series_name','unit')
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError('Must not be blank.')
        return value.strip()

    @model_validator(mode='after')
    def required_metadata(self):
        if self.category == 'COMMODITY' and (not self.commodity or not self.benchmark):
            raise ValueError('Commodity and benchmark metadata are required.')
        if self.category == 'BUNKER' and (not self.fuel_type or not self.port):
            raise ValueError('Fuel type and bunkering hub are required.')
        if self.category == 'PORT' and not self.port:
            raise ValueError('Port metadata is required.')
        return self


class FeatureRequest(Model):
    series_ids: list[str] = Field(min_length=1, max_length=20)
    target_series_id: str
    start: date
    end: date
    cutoff_time: datetime
    max_fill_days: int = Field(default=3, ge=0, le=30)
    required_arrival_date: date | None = None

    @field_validator('cutoff_time')
    @classmethod
    def cutoff_utc(cls, value):
        if value.tzinfo is None:
            raise ValueError('cutoff_time must include a timezone.')
        return value.astimezone(timezone.utc)

    @model_validator(mode='after')
    def valid_window(self):
        if self.end < self.start or (self.end-self.start).days > 1095:
            raise ValueError('Choose an ordered date range of at most 1096 days.')
        if len(set(self.series_ids)) != len(self.series_ids):
            raise ValueError('Duplicate series IDs are not allowed.')
        if self.target_series_id not in self.series_ids:
            raise ValueError('Target must be one of the selected series.')
        return self
