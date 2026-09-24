from datetime import datetime, timezone
from pydantic import Field, field_validator, model_validator
from app.domain.models import Model

HORIZONS=(1,3,7,14)


class ForecastTarget(Model):
    series_id: str = Field(min_length=1, max_length=150)
    as_of_time: datetime
    horizons: list[int] = Field(default_factory=lambda:list(HORIZONS), min_length=1, max_length=4)
    context_series_ids: list[str] = Field(default_factory=list, max_length=8)
    route: str | None = None
    vessel_class: str | None = None

    @field_validator('as_of_time')
    @classmethod
    def utc(cls,value):
        if value.tzinfo is None: raise ValueError('as_of_time must include a timezone.')
        return value.astimezone(timezone.utc)

    @model_validator(mode='after')
    def valid(self):
        if not set(self.horizons).issubset(HORIZONS) or len(set(self.horizons))!=len(self.horizons):
            raise ValueError('Choose distinct horizons from 1, 3, 7, 14 calendar days.')
        if len(set(self.context_series_ids))!=len(self.context_series_ids) or self.series_id in self.context_series_ids:
            raise ValueError('Context series must be distinct and exclude the target.')
        self.horizons=sorted(self.horizons)
        return self
