import csv
import hashlib
import io
import json
from datetime import datetime, timedelta, timezone
from typing import Protocol
import numpy as np
from app.domain.models import ProvenanceMetadata, SourceType
from .models import Observation, Series, Source
from .normalization import numeric, parse_time, unit_rule
from .quality import report


class BaseDataAdapter(Protocol):
    def fetch(self): ...
    def validate(self, raw, as_of): ...
    def normalize(self, raw, as_of): ...
    def get_metadata(self): ...


class CSVImportAdapter:
    def __init__(self, request):
        self.request = request
        body = request.model_dump(exclude={'preview_hash','commit'})
        self.fingerprint = hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest()

    def fetch(self):
        r = self.request
        try:
            reader = csv.DictReader(io.StringIO(r.csv_text.lstrip('\ufeff')), strict=True)
            columns = reader.fieldnames or []
            required = [r.date_column,r.value_column] + [c for c in [r.available_at_column,r.unit_column] if c]
            if len(columns)!=len(set(columns)) or not all(c in columns for c in required):
                raise ValueError('CSV must contain unique headers and all mapped columns.')
            rows = list(reader)
            if not rows or len(rows)>10000:
                raise ValueError('CSV must contain 1 to 10,000 data rows.')
            if any(None in row for row in rows):
                raise ValueError('CSV has rows with too many fields.')
            return rows
        except csv.Error as exc:
            raise ValueError(f'Malformed CSV: {exc}') from exc

    def get_metadata(self):
        r = self.request
        unit, _ = unit_rule(r.category,r.unit,r.currency)
        source_id = 'import-' + hashlib.sha256((r.source_name+'|'+r.category).encode()).hexdigest()[:20]
        source = Source(source_id=source_id,name=r.source_name,category=r.category,provider='User supplied',
            access_type='USER_IMPORT',expected_units=[unit],license_notes='User responsible for permission to use supplied data; not independently verified.',
            availability_status='IMPORTED',notes='No provider or publication claim has been independently verified.')
        return source

    def validate(self, raw, as_of):
        return self.normalize(raw,as_of)

    def normalize(self, raw, as_of):
        r = self.request
        unit, factor = unit_rule(r.category,r.unit,r.currency)
        source = self.get_metadata()
        provenance = ProvenanceMetadata(source_type=SourceType.USER_IMPORT,source_name=r.source_name,
            retrieved_at=as_of,effective_date=as_of.date(),notes='USER_IMPORT. Publication times are user assertions if mapped; otherwise availability is ingestion time. Naive dates mean UTC. Original values/units retained; no FX conversion.')
        metadata = {k:getattr(r,k) for k in ['route','vessel_class','commodity','benchmark','origin_region','fuel_type','port']}
        series = Series(series_id='import-'+self.fingerprint[:24],name=r.series_name,category=r.category,
            source_id=source.source_id,unit=unit,currency=r.currency,frequency_days=r.frequency_days,
            provenance=provenance,**metadata)
        rows, observations, seen = [], [], set()
        previous = None
        for index,row in enumerate(raw,2):
            issues, observation = [], None
            date_raw,value_raw = row.get(r.date_column),row.get(r.value_column)
            if not date_raw or not value_raw or not str(date_raw).strip() or not str(value_raw).strip():
                issues.append('MISSING_VALUE')
            try:
                timestamp = parse_time(date_raw)
                available = parse_time(row.get(r.available_at_column)) if r.available_at_column else as_of
                if timestamp > as_of or available > as_of or available < timestamp:
                    raise ValueError('Future or inconsistent timestamp.')
            except (ValueError,TypeError):
                issues.append('INVALID_TIMESTAMP')
                timestamp = available = None
            try:
                original = numeric(value_raw)
                if original < 0:
                    issues.append('NEGATIVE_VALUE')
            except (ValueError,TypeError):
                original = None
                issues.append('NON_NUMERIC')
            if r.unit_column and row.get(r.unit_column) != r.unit:
                issues.append('UNIT_INCONSISTENCY')
            if timestamp:
                if previous and timestamp < previous:
                    issues.append('OUT_OF_ORDER')
                previous = timestamp
                key = (timestamp,available)
                if key in seen:
                    issues.append('DUPLICATE')
                seen.add(key)
            rejected = any(i in issues for i in ['MISSING_VALUE','INVALID_TIMESTAMP','NON_NUMERIC','NEGATIVE_VALUE','UNIT_INCONSISTENCY'])
            if not rejected:
                observation = Observation(timestamp=timestamp,available_at=available,value=original*factor,
                    original_value=original,original_unit=r.unit,original_currency=r.currency,quality_flags=issues)
                observations.append(observation)
            rows.append({'row_number':index,'raw':row,'accepted':not rejected,'issues':issues})
        quality = report(rows,observations,r.frequency_days,as_of)
        return source,series,observations,rows,quality


DEMO_START = datetime(2025,9,1,tzinfo=timezone.utc)
DEMO_COUNT = 365
DEMO_SEED = 26054

# Fixed historical window; never advances with the system clock.
DEMO_SPECS = [
 ('DEMO_DRY_BULK_INDEX','FREIGHT',1800,100,'index_points',None,{}),
 ('DEMO_CAPESIZE_INDEX','FREIGHT',2500,220,'index_points',None,{'vessel_class':'CAPESIZE'}),
 ('DEMO_PANAMAX_INDEX','FREIGHT',1600,110,'index_points',None,{'vessel_class':'PANAMAX'}),
 ('DEMO_SUPRAMAX_INDEX','FREIGHT',1200,75,'index_points',None,{'vessel_class':'SUPRAMAX'}),
 ('DEMO_HANDYSIZE_INDEX','FREIGHT',750,40,'index_points',None,{'vessel_class':'HANDYSIZE'}),
 ('DEMO_COKING_COAL_BENCHMARK','COMMODITY',230,12,'tonne','USD',{'commodity':'COKING_COAL','benchmark':'DEMO_AUSTRALIAN_COKING_COAL','origin_region':'Australia'}),
 ('DEMO_THERMAL_COAL_BENCHMARK','COMMODITY',110,8,'tonne','USD',{'commodity':'THERMAL_COAL','benchmark':'DEMO_NEWCASTLE_COAL','origin_region':'Australia'}),
 ('DEMO_IRON_ORE_BENCHMARK','COMMODITY',100,5,'tonne','USD',{'commodity':'IRON_ORE','benchmark':'DEMO_IRON_ORE','origin_region':'Australia'}),
 ('DEMO_VLSFO_SINGAPORE','BUNKER',600,28,'tonne','USD',{'fuel_type':'VLSFO','port':'Singapore'}),
] + [('DEMO_'+port.upper()+'_CONGESTION','PORT',base,.3,'day',None,{'port':port})
     for port,base in [('Paradip',2),('Dhamra',1),('Visakhapatnam',1.5),('Gangavaram',1),('Haldia',3),('Kamarajar',1.5)]]


class DemoAdapter:
    def __init__(self, category):
        self.category = category

    def get_metadata(self):
        return Source(source_id='demo-'+self.category.lower(),name='Seeded demonstration / '+self.category,
            category=self.category,provider='Local deterministic generator v1',access_type='DEMO',
            expected_units=['index_points'] if self.category=='FREIGHT' else ['day'] if self.category=='PORT' else ['tonne'],
            license_notes='Synthetic project demonstration. No Baltic Exchange, exchange or port-authority observations.',
            availability_status='DEMO',notes=f'Seed {DEMO_SEED}; fixed 2025-09-01 through 2026-08-31. Not suitable for real-world model evaluation.')

    def fetch(self):
        data=[]
        for index,(name,category,base,scale,unit,currency,metadata) in enumerate(DEMO_SPECS):
            if category!=self.category:
                continue
            rng=np.random.default_rng(DEMO_SEED+index)
            noise=0.0
            observations=[]
            for day in range(DEMO_COUNT):
                noise=.86*noise+rng.normal(0,scale*.25)
                seasonal=scale*np.sin(2*np.pi*day/365)
                shock=scale*2.5*np.exp(-(day-170)/12) if 170<=day<=220 else 0
                timestamp=DEMO_START+timedelta(days=day)
                observations.append(Observation(timestamp=timestamp,available_at=timestamp+timedelta(hours=18),
                    value=round(max(base*.05,base+noise+seasonal+shock),4),original_value=round(max(base*.05,base+noise+seasonal+shock),4),
                    original_unit=unit,original_currency=currency))
            prov=ProvenanceMetadata(source_type=SourceType.SIMULATED,source_name=self.get_metadata().name,
                effective_date=DEMO_START.date(),notes=f'SIMULATED, seed {DEMO_SEED+index}. Availability at 18:00 UTC is simulated. Not actual benchmark or port data.')
            series=Series(series_id=name.lower(),name=name,category=category,source_id=self.get_metadata().source_id,
                unit=unit,currency=currency,provenance=prov,**metadata)
            data.append((series,observations))
        return data

    def validate(self, raw, as_of):
        return self.normalize(raw,as_of)

    def normalize(self, raw, as_of):
        return raw


class DemoFreightAdapter(DemoAdapter):
    def __init__(self): super().__init__('FREIGHT')

class DemoCommodityAdapter(DemoAdapter):
    def __init__(self): super().__init__('COMMODITY')

class DemoBunkerAdapter(DemoAdapter):
    def __init__(self): super().__init__('BUNKER')

class DemoPortCongestionAdapter(DemoAdapter):
    def __init__(self): super().__init__('PORT')
