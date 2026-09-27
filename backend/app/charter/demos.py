"""Explicit demo preparation, outside CharterTimingService. Never runs on analyze."""
from datetime import datetime, timedelta, timezone
import threading
import numpy as np
from app.domain.models import ProvenanceMetadata
from app.market.models import Source, Series, Observation
from app.market.quality import report
from app.forecasting.models import ForecastTarget

AS_OF = datetime(2026,8,31,23,59,59,tzinfo=timezone.utc)
SEED = 26054
DEMO_LOCK = threading.Lock()


def seed_histories(store):
    """Two fixed synthetic USD/day histories; no edited predictions or model scores."""
    source = Source(source_id='charter-demo',name='SIMULATED charter policy demonstration',
        category='FREIGHT',provider='Local seeded generator',access_type='DEMO',expected_units=['day'],
        license_notes='Synthetic demonstration only.',availability_status='SIMULATED',
        notes='Seed 26054; declining daily hire with either small or large noise. Not market data.')
    with store.connection() as db:
        store._source(db,source)
        for index,(label,noise) in enumerate([('decline',70.),('uncertain',2200.)]):
            series_id = 'charter_demo_'+label
            if db.execute('SELECT 1 FROM data_series WHERE series_id=?',(series_id,)).fetchone(): continue
            rng = np.random.default_rng(SEED+index)
            provenance = ProvenanceMetadata(source_type='SIMULATED',source_name=source.name,
                effective_date=AS_OF.date(),notes=f'Seed {SEED+index}; 365 daily values: 40000 - 45*day + noise N(0,{noise:g}); simulated publication 18:00 UTC. Scenario construction is for policy demonstration, not accuracy evidence.')
            series = Series(series_id=series_id,name='SIMULATED_'+label.upper()+'_HIRE',category='FREIGHT',
                source_id=source.source_id,unit='day',currency='USD',vessel_class='PANAMAX',
                route='Newcastle -> Paradip',provenance=provenance)
            observations = []
            for i in range(365):
                timestamp = datetime(2025,9,1,tzinfo=timezone.utc)+timedelta(days=i)
                value = round(max(1000,40000-45*i+rng.normal(0,noise)),4)
                observations.append(Observation(timestamp=timestamp,available_at=timestamp+timedelta(hours=18),
                    value=value,original_value=value,original_unit='day',original_currency='USD'))
            quality = report([{'accepted':True,'issues':[]} for _ in observations],observations,1,AS_OF)
            store._series(db,series,observations,quality,AS_OF)


def prepare(store, forecasts):
    with DEMO_LOCK:
        seed_histories(store)
        for name in ('decline','uncertain'):
            forecasts.train(ForecastTarget(series_id='charter_demo_'+name,as_of_time=AS_OF))
    return presets(forecasts)


def presets(forecasts):
    models = {m['target']['series_id']:m for m in forecasts.artifacts.list()
              if m['target']['series_id'].startswith('charter_demo_') and datetime.fromisoformat(m['as_of_time'])==AS_OF}
    base = {'shipment':{'cargo_type':'COKING_COAL','cargo_quantity_tonnes':70000,
        'origin_country':'Australia','origin_port':'Newcastle','destination_country':'India',
        'destination_port':'Paradip','required_arrival_date':'2026-10-20'},
        'vessel_class':'PANAMAX','analysis_as_of':AS_OF.isoformat(), 'risk_profile':'BALANCED',
        'schedule_buffer_days':2, 'storage_usd_per_tonne_day':.001}
    result = []
    for key,label,series in [('A','WAIT OPPORTUNITY','decline'),('B','TIGHT DEADLINE','decline'),
                              ('C','HIGH UNCERTAINTY','uncertain'),('D','INSUFFICIENT DATA',None)]:
        request = {**base,'shipment':dict(base['shipment'])}
        model = models.get('charter_demo_'+str(series))
        request['forecast_model_id'] = model['model_id'] if model else '0'*24
        if key == 'B':
            # Deadline derived from the actual voyage later by API preset resolver.
            request['shipment']['required_arrival_date'] = '2026-09-29'
        if key == 'C': request['risk_profile'] = 'CONSERVATIVE'
        result.append({'key':key,'label':label,'ready':model is not None or key=='D',
            'source_type':'SIMULATED','request':request})
    return result
