from copy import deepcopy
from datetime import datetime, timedelta, timezone
from math import ceil
from pathlib import Path
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.routes import provider
from app.market.store import MarketStore
from app.charter.models import CharterTimingRequest
from app.charter.service import CharterTimingService
from app.charter.repository import CharterRepository
from app.charter.engine import interpolate, PROFILES
from app.charter.api import get_service, get_repository
from app.charter.demos import seed_histories

ORIGIN = datetime(2026,8,31,23,59,59,tzinfo=timezone.utc)


def basis():
    return {'model_id':'a'*24,'model_version':'test-fixture','as_of_time':ORIGIN.isoformat(),
        'training_cutoff':ORIGIN.isoformat(),'forecast_generated_at':'2026-09-01T00:00:00+00:00',
        'target':{'series_id':'test','unit':'day','currency':'USD','vessel_class':'PANAMAX','route':None,
                  'provenance':{'source_type':'SIMULATED'}},
        'data_provenance':[{'source_type':'SIMULATED'}], 'current_rate':20000.,'uncertainty_status':'ELEVATED_UNCERTAINTY',
        'leaderboard':[{'selected':True,'validation':{'count':8,'coverage':.75}}],
        'forecast_points':[{'horizon':h,'date':(ORIGIN.date()+timedelta(days=h)).isoformat(),
            'p10':20000-180*h,'p50':20000-150*h,'p90':20000-100*h} for h in [1,3,7,14]]}


def req(**kwargs):
    return CharterTimingRequest(**{'shipment':{'cargo_type':'COKING_COAL','cargo_quantity_tonnes':70000,
        'origin_country':'Australia','origin_port':'Newcastle','destination_country':'India','destination_port':'Paradip',
        'required_arrival_date':'2026-10-30'},'vessel_class':'PANAMAX','analysis_as_of':ORIGIN,
        'forecast_model_id':'a'*24, 'storage_usd_per_tonne_day':.001, **kwargs})


@pytest.fixture
def setup(tmp_path):
    forecast = basis()
    class Artifacts:
        def get(self, model_id):
            if model_id != 'a'*24: raise KeyError('FORECAST_UNAVAILABLE')
            return deepcopy(forecast)
    class Forecasts:
        artifacts = Artifacts()
        def train(self, *args): raise AssertionError('Timing must not train!')
        def forecast(self,*args): return deepcopy(forecast)
    store = MarketStore(tmp_path/'market.sqlite3')
    repo = CharterRepository(tmp_path/'analyses.sqlite3')
    service = CharterTimingService(provider,store,Forecasts(),repo)
    return service,forecast,store,repo


def test_daily_candidates_horizon_safe_date_and_window(setup):
    service,_,_,_ = setup
    r=service.analyze(req())
    assert r.recommendation=='WAIT'
    assert [c['wait_days'] for c in r.candidate_decisions]==list(range(15))
    assert r.recommended_window_start and r.recommended_window_end
    assert r.latest_safe_charter_date == (req().shipment.required_arrival_date-timedelta(days=ceil(r.voyage_context['voyage']['estimated_total_days']+2))).isoformat()
    assert all(c['charter_date']<=r.latest_safe_charter_date and c['buffered_arrival']<=req().shipment.required_arrival_date.isoformat() for c in r.candidate_decisions)
    assert r.performance['forecast_training_calls']==0


@pytest.mark.parametrize('wait',[0,1,2,3,5,7,10,14])
def test_quantile_interpolation(setup,wait):
    service,f,_,_ = setup
    c=service.analyze(req()).candidate_decisions[wait]
    raw,bounds=interpolate(f['forecast_points'],20000,wait)
    assert c['freight_quantiles']==raw and c['interpolation_bounds']==bounds
    assert c['freight_quantiles']['p50']==20000-150*wait
    assert c['hire_usd_per_day']==raw


def test_cost_math_waiting_demurrage_and_savings(setup):
    service,_,_,_ = setup
    r=service.analyze(req(storage_usd_per_tonne_day=.012,demurrage_usd_per_day=12345))
    hire_days = r.assumptions['hire_days']
    now = r.current_charter_cost
    for c in r.candidate_decisions:
        for q in ['p10','p50','p90']:
            cost=c['costs'][q]
            assert cost['ocean_freight']==pytest.approx(round(c['hire_usd_per_day'][q]*hire_days,2))
            assert cost['expected_demurrage']==pytest.approx(round(r.assumptions['excess_waiting_days']*12345,2))
            assert cost['storage_if_applicable']==pytest.approx(c['wait_days']*70000*.012)
            assert cost['total_logistics_cost']==pytest.approx(sum(cost[k] for k in ['ocean_freight','bunker_component','port_cost','expected_demurrage','storage_if_applicable','lighterage_if_applicable']))
            assert c['savings_vs_now'][q]==pytest.approx(round(now-cost['total_logistics_cost'],2))
        assert c['downside_exposure']==max(0,round(c['costs']['p90']['total_logistics_cost']-now,2))


def test_missing_waiting_cost_is_explicit_not_fabricated(setup):
    service,_,_,_=setup
    r=service.analyze(req(storage_usd_per_tonne_day=None))
    assert r.assumptions['waiting_cost_status']=='NOT_MODELLED'
    assert all(c['costs']['p50']['storage_if_applicable']==0 for c in r.candidate_decisions)
    assert any('NOT MODELLED' in s for s in r.limitations)


def test_congestion_replaces_not_adds_reference_wait(setup):
    service,_,_,_=setup
    r=service.analyze(req())
    used=r.market_snapshot['congestion_used']
    assert used[1]['basis']=='MARKET_OBSERVATION'
    assert used[1]['observation']['provenance']['source_type']=='SIMULATED'
    assert r.voyage_context['voyage']['expected_delay_days']==sum(c['used_days_per_call'] for c in used)
    assert used[0]['basis']=='ASSUMED_REFERENCE_FALLBACK'
    assert 'UNAVAILABLE' in used[0]['status']


def test_multi_voyage_duration_and_capacity(setup):
    service,_,_,_=setup
    small=service.analyze(req())
    large_request=req();large_request.shipment.cargo_quantity_tonnes=140000
    large_request.shipment.required_arrival_date=datetime(2027,2,1).date()
    large=service.analyze(large_request)
    assert large.voyage_context['voyage_count']==2
    assert large.voyage_context['voyage']['return_sea_days']>0
    assert large.current_charter_cost>small.current_charter_cost
    assert large.voyage_context['voyage']['expected_delay_days']==2*small.voyage_context['voyage']['expected_delay_days']


def test_tight_deadline_locks_despite_declining_forecast(setup):
    service,_,_,_=setup
    r=service.analyze(req());request=req()
    request.shipment.required_arrival_date=ORIGIN.date()+timedelta(days=r.voyage_context['rounded_buffered_duration_days'])
    tight=service.analyze(request)
    assert tight.recommendation=='LOCK_NOW' and len(tight.candidate_decisions)==1
    assert tight.recommended_window_start is None and tight.recommended_window_end is None
    assert tight.rejected_region['excluded_by_deadline_count']==14


@pytest.mark.parametrize('cause',['port','deadline'])
def test_infeasible_can_never_win(setup,cause):
    service,_,_,_=setup
    request=req()
    if cause=='port': request.shipment.destination_port='Haldia'
    else: request.shipment.required_arrival_date=ORIGIN.date()+timedelta(days=1)
    r=service.analyze(request)
    assert r.recommendation=='NO_SAFE_WAIT_WINDOW'
    assert not r.candidate_decisions and r.selected_wait_days is None


def test_regret_exact_aligned_scenario_definition(setup):
    service,_,_,_=setup
    r=service.analyze(req())
    for c in r.candidate_decisions:
        for q in ['p10','p50','p90']:
            best=min(d['costs'][q]['total_logistics_cost'] for d in r.candidate_decisions)
            assert c['scenario_regret'][q]==round(c['costs'][q]['total_logistics_cost']-best,2)
        assert c['maximum_scenario_regret']==max(c['scenario_regret'].values())


def test_risk_profiles_change_policy_without_changing_forecast(setup):
    service,f,_,_=setup
    for p in f['forecast_points']: p['p90']=21000
    before=deepcopy(f)
    conservative=service.analyze(req(risk_profile='CONSERVATIVE'))
    focused=service.analyze(req(risk_profile='COST_FOCUSED'))
    assert conservative.recommendation=='LOCK_NOW'
    assert focused.recommendation=='WAIT'
    assert f==before
    assert [c['freight_quantiles'] for c in conservative.candidate_decisions]==[c['freight_quantiles'] for c in focused.candidate_decisions]
    assert conservative.policy['maximum_downside_fraction']==PROFILES['CONSERVATIVE']['maximum_downside_fraction']


def test_high_uncertainty_conservative_refuses_wait(setup):
    service,f,_,_=setup;f['uncertainty_status']='HIGH_UNCERTAINTY'
    r=service.analyze(req(risk_profile='CONSERVATIVE'))
    assert r.recommendation=='LOCK_NOW'
    assert all('HIGH_UNCERTAINTY_POLICY' in c['policy_rejections'] for c in r.candidate_decisions[1:])


@pytest.mark.parametrize('bad',['missing','origin','cutoff','vessel','route','units','crossing','target_date'])
def test_insufficient_incompatible_or_future_forecast(setup,bad):
    service,f,_,_=setup;request=req()
    if bad=='missing': request.forecast_model_id='0'*24
    elif bad=='origin': f['as_of_time']='2026-08-30T23:59:59+00:00'
    elif bad=='cutoff': f['training_cutoff']='2026-09-01T23:59:59+00:00'
    elif bad=='vessel': f['target']['vessel_class']='CAPESIZE'
    elif bad=='route': f['target']['route']='OTHER -> ROUTE'
    elif bad=='units': f['target']['currency']='EUR'
    elif bad=='crossing': f['forecast_points'][0]['p10']=100000
    elif bad=='target_date': f['forecast_points'][0]['date']='2027-01-01'
    r=service.analyze(request)
    assert r.recommendation=='INSUFFICIENT_DATA' and not r.candidate_decisions


def test_index_proxy_requires_consent_and_uses_ratios(setup):
    service,f,_,_=setup;f['target'].update(unit='index_points',currency=None)
    assert service.analyze(req()).recommendation=='INSUFFICIENT_DATA'
    r=service.analyze(req(allow_index_proxy=True,index_anchor_hire_usd_per_day=30000))
    assert r.candidate_decisions[0]['hire_usd_per_day']['p50']==30000
    assert r.candidate_decisions[7]['hire_usd_per_day']['p50']==(20000-150*7)*1.5
    assert r.rate_conversion['source']=='USER_INPUT'


def test_overrides_buffer_and_latest_safe_date(setup):
    service,_,_,_=setup
    r=service.analyze(req(loading_days=4,unloading_days=5,schedule_buffer_days=3.5))
    assert r.voyage_context['voyage']['port_days']==9
    assert r.voyage_context['rounded_buffered_duration_days']==ceil(r.voyage_context['voyage']['estimated_total_days']+3.5)


def test_audit_reproducible_and_explanation_derived(setup):
    service,f,_,repo=setup
    a=service.analyze(req());b=service.analyze(req())
    assert a.analysis_id==b.analysis_id and len(repo.history())==1
    saved=repo.get(a.analysis_id)
    assert saved.forecast_metadata==f
    assert saved.candidate_decisions==a.candidate_decisions
    assert f'{a.median_saving:,.2f}' in a.explanation[0]
    assert a.latest_safe_charter_date in a.explanation[1]
    assert repo.history()[0]['request']==a.request.model_dump(mode='json')


def test_api_validation_history_and_missing_id(setup):
    service,_,_,repo=setup
    app.dependency_overrides[get_service]=lambda:service
    app.dependency_overrides[get_repository]=lambda:repo
    try:
        with TestClient(app) as client:
            r=client.post('/api/charter/analyze',json=req().model_dump(mode='json'))
            assert r.status_code==200
            key=r.json()['analysis_id']
            assert client.get('/api/charter/'+key).json()['candidate_decisions']==r.json()['candidate_decisions']
            assert client.get('/api/charter/'+key+'/explanation').json()['explanation']==r.json()['explanation']
            assert len(client.get('/api/charter/history').json())==1
            assert client.get('/api/charter/unknown').status_code==404
            for change in [{'schedule_buffer_days':-1},{'analysis_as_of':'2026-08-31'}, {'max_downside_fraction':2}, {'unexpected':1}]:
                assert client.post('/api/charter/analyze',json={**req().model_dump(mode='json'),**change}).status_code==422
    finally: app.dependency_overrides.clear()


def test_demo_seed_deterministic_and_idempotent(tmp_path):
    a=MarketStore(tmp_path/'a.sqlite3');b=MarketStore(tmp_path/'b.sqlite3')
    seed_histories(a);seed_histories(a);seed_histories(b)
    assert a.observations('charter_demo_decline')==b.observations('charter_demo_decline')
    assert len(a.observations('charter_demo_uncertain'))==365
    assert a.series('charter_demo_decline').provenance.source_type=='SIMULATED'


def test_no_extrapolation():
    with pytest.raises(ValueError):interpolate(basis()['forecast_points'],20000,15)
