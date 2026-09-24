from datetime import date, datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.market.api import get_store
from app.market.store import MarketStore
from app.market.models import ImportRequest, FeatureRequest
from app.market.service import MarketDataService, MarketSnapshotService
from app.market.features import build_features
from app.market.adapters import DemoFreightAdapter

NOW=datetime(2026,9,20,tzinfo=timezone.utc)

@pytest.fixture
def store(tmp_path): return MarketStore(tmp_path/'market.sqlite3',seed_demo=False)

@pytest.fixture
def service(store): return MarketDataService(store)


def request(csv='date,value,known\n2026-09-01,10,2026-09-01T18:00:00Z\n2026-09-02,20,2026-09-02T18:00:00Z',**kwargs):
    return ImportRequest(**({'category':'FREIGHT','source_name':'Internal records','series_name':'Test freight',
        'csv_text':csv,'unit':'index_points','available_at_column':'known','vessel_class':'PANAMAX'}|kwargs))


def ingest(service,r):
    preview=service.import_csv(r,NOW)
    return service.import_csv(r.model_copy(update={'commit':True,'preview_hash':preview['preview_hash']}),NOW)


def test_valid_import_persistence_and_idempotence(store,service):
    r=request(); result=ingest(service,r)
    assert result['quality']['rows_accepted']==2
    assert result['committed']
    assert ingest(service,r)['already_ingested']
    assert len(store.observations(result['series_id']))==2
    assert store.series(result['series_id']).provenance.source_type=='USER_IMPORT'
    assert store.source(store.series(result['series_id']).source_id).access_type=='USER_IMPORT'
    assert MarketStore(store.path,seed_demo=False).observations(result['series_id'])[0].value==10

@pytest.mark.parametrize('csv',['wrong,header\na,b','date,value,known\n"unterminated','date,date,value\na,b,1','date,value,known\n'])
def test_invalid_csv_rejected(service,csv):
    with pytest.raises(ValueError): service.import_csv(request(csv),NOW)


def test_quality_flags_and_quarantine(store,service):
    r=request('date,value,known,unit\n2026-09-02,2,2026-09-02T18:00:00Z,index_points\n2026-09-02,2,2026-09-02T18:00:00Z,index_points\n2026-09-01,-2,2026-09-01T18:00:00Z,index_points\n2026-09-03,,2026-09-03T18:00:00Z,index_points\nbad,text,bad,index_points\n2026-09-04,3,2026-09-04T18:00:00Z,tonne',unit_column='unit')
    result=ingest(service,r);q=result['quality']
    assert q['duplicates']==1
    assert q['missing_values']==1
    assert q['negative_values']==1
    assert q['invalid_timestamps']==1
    assert q['unit_inconsistency']==1
    assert q['out_of_order']==1
    assert q['rows_rejected']==4
    assert len(store.observations(result['series_id']))==2
    with store.connection() as db:
        assert db.execute('SELECT count(*) FROM data_import_rows').fetchone()[0]==6

@pytest.mark.parametrize('category,unit,currency,value,expected,extra',[
 ('COMMODITY','kg','USD',.2,200,{'commodity':'COKING_COAL','benchmark':'internal'}),
 ('BUNKER','metric_ton','EUR',600,600,{'fuel_type':'VLSFO','port':'Singapore'}),
 ('PORT','hours',None,48,2,{'port':'Paradip'}),
 ('FREIGHT','hour','USD',1000,24000,{})])
def test_units_and_no_fx(store,service,category,unit,currency,value,expected,extra):
    r=request(f'date,value,known\n2026-09-01,{value},2026-09-01T18:00:00Z',category=category,unit=unit,currency=currency,**extra)
    result=ingest(service,r);o=store.observations(result['series_id'])[0]
    assert o.value==expected
    assert o.original_value==value
    assert o.original_currency==currency
    assert store.series(result['series_id']).currency==currency


def test_invalid_unit_and_preview_hash(service):
    with pytest.raises(ValueError):service.import_csv(request(unit='barrel'),NOW)
    with pytest.raises(ValueError):service.import_csv(request(commit=True),NOW)
    with pytest.raises(ValueError):service.import_csv(request(currency='USD'),NOW)


def test_historical_range(store,service):
    key=ingest(service,request())['series_id']
    rows=store.observations(key,start=datetime(2026,9,2,tzinfo=timezone.utc),end=NOW)
    assert len(rows)==1 and rows[0].value==20


def test_registry_unavailable_and_snapshot(store,service):
    assert store.source('unavailable-freight').access_type=='COMMERCIAL_REQUIRED'
    empty=MarketSnapshotService(store).snapshot('Newcastle','Paradip','PANAMAX','COKING_COAL',NOW)
    assert all(not item['available'] for item in empty['context'].values())
    ingest(service,request())
    result=MarketSnapshotService(store).snapshot('Newcastle','Paradip','PANAMAX','COKING_COAL',NOW)
    assert result['context']['freight']['value']==20
    assert not result['context']['port']['available']
    assert result['context']['freight']['freshness']['status']=='STALE'


def features(store,key,ids=None,**kwargs):
    r=FeatureRequest(**({'series_ids':ids or [key],'target_series_id':key,'start':date(2026,9,1),
        'end':date(2026,9,7),'cutoff_time':NOW,'max_fill_days':2}|kwargs))
    return build_features(store,r)


def test_feature_alignment_bounded_fill_and_target(store,service):
    target=ingest(service,request())['series_id']
    predictor=ingest(service,request(series_name='predictor',csv='date,value,known\n2026-09-01,5,2026-09-01T18:00:00Z'))['series_id']
    result=features(store,target,[target,predictor])
    assert result['rows'][0]['values'][predictor]==5
    assert result['rows'][2]['values'][predictor]==5
    assert result['rows'][3]['values'][predictor] is None
    assert result['rows'][2]['freight_target'] is None
    assert result['filled_by_series'][predictor]==2
    assert result['rows'][0]['calendar']['month']==9
    assert result['rows'][0]['calendar']['major_holiday_indicator'] is None


def test_cutoff_and_delayed_publication_no_leakage(store,service):
    key=ingest(service,request('date,value,known\n2026-09-01,10,2026-09-03T10:00:00Z\n2026-09-02,50,2026-09-02T18:00:00Z'))['series_id']
    result=features(store,key,cutoff_time=datetime(2026,9,2,12,tzinfo=timezone.utc))
    assert len(result['rows'])==2
    assert all(r['freight_target'] is None for r in result['rows'])


def test_revision_not_available_early(store,service):
    key=ingest(service,request('date,value,known\n2026-09-01,10,2026-09-01T18:00:00Z\n2026-09-01,99,2026-09-03T10:00:00Z'))['series_id']
    assert features(store,key)['rows'][0]['freight_target']==10
    history=store.observations(key)
    assert len(history)==2
    result=MarketSnapshotService(store).snapshot('Newcastle','Paradip','PANAMAX','COKING_COAL',datetime(2026,9,2,tzinfo=timezone.utc))
    assert result['context']['freight']['value']==10


def test_no_publication_defaults_to_import_time(store,service):
    key=ingest(service,request('date,value\n2026-09-01,10',available_at_column=None))['series_id']
    assert store.observations(key)[0].available_at==NOW
    assert features(store,key)['rows'][0]['freight_target'] is None


def test_generator_reproducible_and_positive():
    a=DemoFreightAdapter().fetch();b=DemoFreightAdapter().fetch()
    assert a==b
    assert all(o.value>0 for _,rows in a for o in rows)
    assert all(s.provenance.source_type=='SIMULATED' for s,_ in a)


def test_demo_seed_idempotent_and_snapshot(tmp_path):
    store=MarketStore(tmp_path/'demo.sqlite3')
    count=len(store.series());store.seed_demo()
    assert len(store.series())==count==15
    snapshot=MarketSnapshotService(store).snapshot('Newcastle','Paradip','PANAMAX','COKING_COAL',NOW)
    assert snapshot['context']['port']['series_name']=='DEMO_PARADIP_CONGESTION'
    assert all(c['provenance'].source_type=='SIMULATED' for c in snapshot['context'].values())


def test_trends_correct(store,service):
    csv='date,value,known\n'+'\n'.join(f'2026-08-{day:02},{day},2026-08-{day:02}T18:00:00Z' for day in range(1,32))
    key=ingest(service,request(csv))['series_id']
    t=service.trends(key,None,None,NOW)
    assert t['latest']==31 and t['mean_7']==28 and t['mean_30']==16.5
    assert t['change']==1 and t['minimum']==1 and t['maximum']==31
    assert t['rolling_volatility'] is not None
    short=service.trends(key,datetime(2026,8,31,tzinfo=timezone.utc),None,NOW)
    assert short['mean_7'] is None and short['rolling_volatility'] is None


def test_api_validation_and_import(store):
    app.dependency_overrides[get_store]=lambda:store
    try:
        with TestClient(app) as client:
            assert client.get('/api/data/sources').status_code==200
            assert client.get('/api/data/series/unknown').status_code==404
            assert client.get('/api/market/snapshot?origin=A&destination=B&vessel_class=PANAMAX&cargo_type=COKING_COAL&as_of_time=2026-09-01T00:00:00').status_code==422
            assert client.post('/api/data/import/csv',json={}).status_code==422
            body=request().model_dump(mode='json')
            preview=client.post('/api/data/import/csv',json=body)
            assert preview.status_code==200
            body.update(commit=True,preview_hash=preview.json()['preview_hash'])
            assert client.post('/api/data/import/csv',json=body).json()['committed']
            assert len(client.get('/api/data/catalog').json())==1
            assert client.get('/api/data/series/'+preview.json()['series_id']+'/quality').status_code==200
    finally:
        app.dependency_overrides.pop(get_store,None)


def test_preview_has_no_storage_side_effect(service,store):
    result=service.import_csv(request(),NOW)
    assert not result['committed']
    assert store.series()==[]
    with store.connection() as db:
        assert db.execute('SELECT count(*) FROM data_imports').fetchone()[0]==0


def test_all_rejected_cannot_be_ingested(service,store):
    r=request('date,value,known\n2026-09-01,-1,2026-09-01T18:00:00Z')
    preview=service.import_csv(r,NOW)
    assert preview['quality']['status']=='UNUSABLE'
    with pytest.raises(ValueError,match='No valid observations'):
        service.import_csv(r.model_copy(update={'commit':True,'preview_hash':preview['preview_hash']}),NOW)
    assert store.series()==[]


def test_gap_detection_and_staleness(service):
    q=service.import_csv(request('date,value,known\n2026-09-01,1,2026-09-01T18:00:00Z\n2026-09-10,2,2026-09-10T18:00:00Z'),NOW)['quality']
    assert q['missing_periods']==8
    assert 'LARGE_TIME_GAPS' in q['warnings'] and q['stale']

@pytest.mark.parametrize('value',['NaN','inf','-inf','not-a-number'])
def test_nonfinite_values_flagged(service,value):
    q=service.import_csv(request(f'date,value,known\n2026-09-01,{value},2026-09-01T18:00:00Z'),NOW)['quality']
    assert q['non_numeric']==1 and q['rows_rejected']==1


def test_source_units_aggregate_and_currency_retained(store,service):
    first=ingest(service,request())['series_id']
    ingest(service,request(unit='day',currency='INR',series_name='Daily INR hire'))
    source=store.source(store.series(first).source_id)
    assert set(source.expected_units)=={'day','index_points'}


def test_snapshot_asof_excludes_later_information(store,service):
    ingest(service,request())
    result=MarketSnapshotService(store).snapshot('Newcastle','Paradip','PANAMAX','COKING_COAL',datetime(2026,9,1,12,tzinfo=timezone.utc))
    assert not result['context']['freight']['available']


def test_zero_fill_and_cell_lineage(store,service):
    target=ingest(service,request())['series_id']
    predictor=ingest(service,request(series_name='predictor',csv='date,value,known\n2026-09-01,5,2026-09-01T18:00:00Z'))['series_id']
    result=features(store,target,[target,predictor],max_fill_days=0)
    assert result['rows'][1]['values'][predictor] is None
    for row in result['rows']:
        for cell in row['lineage'].values():
            if cell['method']!='MISSING':
                assert cell['timestamp']<=row['evaluation_time']
                assert cell['available_at']<=row['evaluation_time']


def test_feature_target_must_be_freight(store,service):
    key=ingest(service,request(category='PORT',unit='day',port='Paradip'))['series_id']
    with pytest.raises(ValueError,match='target must be a freight'):
        features(store,key)


def test_snapshot_prefers_matching_origin_region(store,service):
    ingest(service,request(category='COMMODITY',unit='tonne',currency='USD',commodity='COKING_COAL',benchmark='Other benchmark',origin_region='Indonesia',series_name='Other origin'))
    matching=ingest(service,request(category='COMMODITY',unit='tonne',currency='USD',commodity='COKING_COAL',benchmark='Australian benchmark',origin_region='Australia',series_name='Matching origin'))['series_id']
    result=MarketSnapshotService(store).snapshot('Newcastle','Paradip','PANAMAX','COKING_COAL',NOW,origin_region='Australia')
    assert result['context']['commodity']['series_id']==matching


def test_timezone_normalization(service,store):
    r=request('date,value,known\n2026-09-01T05:30:00+05:30,10,2026-09-01T23:30:00+05:30')
    key=ingest(service,r)['series_id']
    o=store.observations(key)[0]
    assert o.timestamp==datetime(2026,9,1,tzinfo=timezone.utc)
    assert o.available_at==datetime(2026,9,1,18,tzinfo=timezone.utc)
