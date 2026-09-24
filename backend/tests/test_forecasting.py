from datetime import datetime, timezone
from pathlib import Path
import copy
import numpy as np
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.market.store import MarketStore
from app.market.api import get_store
from app.forecasting.models import ForecastTarget
from app.forecasting.dataset import make_dataset,chronological_split,training_pairs,ForecastDataError
from app.forecasting.estimators import baseline,fit_model,point,predict_quantiles,correct_quantiles,CONFIG
from app.forecasting.evaluation import metrics,select_model
from app.forecasting.artifacts import ArtifactRepository
from app.forecasting.service import FreightForecastService
from app.forecasting.api import get_artifacts

AS_OF=datetime(2026,8,31,23,59,59,tzinfo=timezone.utc)

@pytest.fixture(scope='module')
def resources(tmp_path_factory):
    root=tmp_path_factory.mktemp('forecasts')
    store=MarketStore(root/'market.sqlite3')
    repo=ArtifactRepository(root/'artifacts')
    request=ForecastTarget(series_id='demo_panamax_index',as_of_time=AS_OF)
    service=FreightForecastService(store,repo)
    result=service.train(request)
    return store,repo,request,service,result


def test_chronological_splits(resources):
    store,_,request,_,_=resources
    dataset=make_dataset(store,request)
    split=chronological_split(dataset['rows'])
    names=['train','calibration','validation','test']
    for a,b in zip(names,names[1:]): assert split[a][-1]['date']<split[b][0]['date']
    assert sum(len(rows) for rows in split.values())==len(dataset['rows'])


def test_future_values_never_enter_features(tmp_path):
    store=MarketStore(tmp_path/'market.sqlite3')
    request=ForecastTarget(series_id='demo_panamax_index',as_of_time=datetime(2026,6,1,23,59,59,tzinfo=timezone.utc))
    before=make_dataset(store,request)
    with store.connection() as db:
        db.execute("UPDATE freight_observations SET value=99999999 WHERE series_id='demo_panamax_index' AND timestamp>'2026-06-01T23:59:59+00:00'")
    after=make_dataset(store,request)
    assert before==after
    for row in after['rows']:
        for cell in row['lineage'][request.series_id]:
            assert cell['timestamp'].isoformat()<=row['evaluation_time']
            assert cell['available_at'].isoformat()<=row['evaluation_time']


def test_training_pairs_purge_future_labels(resources):
    store,_,request,_,_=resources
    dataset=make_dataset(store,request)
    origin=dataset['rows'][200]['evaluation_time']
    _,_,audit=training_pairs(dataset,14,origin)
    assert audit
    assert all(a[0]<origin[:10] and a[2]<=origin for a in audit)
    assert max(a[1] for a in audit)<=origin[:10]


def test_scaler_and_imputer_train_only():
    x=np.array([[1,np.nan],[2,2],[3,4]],dtype=float);y=np.array([1,2,3.0])
    model=fit_model('Ridge',x,y)
    np.testing.assert_allclose(model.named_steps['scaler'].mean_,[2,3])
    model.predict([[999,999]])
    np.testing.assert_allclose(model.named_steps['scaler'].mean_,[2,3])
    assert model.named_steps['imputer'].statistics_[1]==3


def test_baselines():
    x=[100,99,98,97,93,86,99,97,93,1,.01,7,8,3,0,1]
    assert baseline('Persistence',x,7)==100
    assert baseline('Moving average',x,7)==97
    assert baseline('Drift',x,7)==107


def test_metrics_exact():
    rows=[dict(actual=10,current=8,p10=8,p50=9,p90=12,quantile_crossing=False),
          dict(actual=20,current=21,p10=12,p50=18,p90=19,quantile_crossing=False)]
    m=metrics(rows)
    assert m['mae']==1.5 and m['rmse']==pytest.approx(np.sqrt(2.5))
    assert m['pinball']['p10']==pytest.approx(.5)
    assert m['pinball']['p50']==.75
    assert m['pinball']['p90']==pytest.approx(.55)
    assert m['coverage']==.5 and m['directional_accuracy']==1


def test_quantile_correction_is_recorded():
    values,crossed,clipped=correct_quantiles([3,-1,2])
    assert values==[0,2,3] and crossed and clipped


def test_quantiles_use_out_of_sample_residuals():
    r=predict_quantiles('Persistence',None,[10],1,[-2,-1,0,1,2])
    assert r['p50']==10 and r['p10']==pytest.approx(8.4) and r['p90']==pytest.approx(11.6)
    with pytest.raises(ValueError,match='CALIBRATION'): predict_quantiles('Persistence',None,[10],1,[])


def test_multihorizon_provenance_and_artifacts(resources):
    _,repo,request,_,result=resources
    assert [p['horizon'] for p in result['forecast_points']]==[1,3,7,14]
    assert all(p['p10']<=p['p50']<=p['p90'] for p in result['forecast_points'])
    assert result['training_cutoff']==request.as_of_time.isoformat()
    assert result['data_provenance'][0]['source_type']=='SIMULATED'
    assert result['evaluation_label']=='SIMULATED DATA BACKTEST'
    assert len(result['leaderboard'])==20
    assert (repo.path(result['model_id'])/'models.joblib').exists()
    assert result['seed']==26054 and result['features']


def test_walk_forward_endpoint_and_no_future_training(resources):
    store,repo,_,_,result=resources
    app.dependency_overrides[get_store]=lambda:store
    app.dependency_overrides[get_artifacts]=lambda:repo
    try:
        with TestClient(app) as client:
            payload=client.post('/api/forecast/backtest',json={'model_id':result['model_id']}).json()
            assert payload['training_audit']
            for row in payload['training_audit']:
                assert row['max_training_label_available_at']<=row['origin']
                assert row['max_training_feature_date']<row['origin'][:10]
            test=[r for r in payload['records'] if r['stage']=='test']
            assert test and all(r['target_date']>r['origin_date'] for r in test)
            assert client.get('/api/forecast/models').status_code==200
            assert client.get('/api/forecast/freight/demo_panamax_index').json()['is_historical_as_of']
            assert client.post('/api/forecast/train',json={'series_id':'bad','as_of_time':'2026-08-31','horizons':[2]}).status_code==422
            assert client.get('/api/forecast/freight/missing').status_code==404
            assert client.get('/api/forecast/evaluation',params={'model_id':result['model_id']}).status_code==200
    finally:
        app.dependency_overrides.clear()


def test_selection_ignores_test_metrics(resources):
    board=copy.deepcopy(resources[-1]['leaderboard'])
    h=[r for r in board if r['horizon']==7]
    selected=select_model(h)
    for row in h: row['test']={'mae':0 if row['model']!=selected else 1e20}
    assert select_model(h)==selected


def test_seeded_training_reproducible(resources,tmp_path):
    store,_,request,_,result=resources
    request=request.model_copy(update={'horizons':[1]})
    second=FreightForecastService(store,ArtifactRepository(tmp_path/'second')).train(request)
    assert second['forecast_points']==[result['forecast_points'][0]]
    assert second['leaderboard']==[r for r in result['leaderboard'] if r['horizon']==1]


def test_insufficient_stale_and_missing_context(resources):
    store,_,request,_,_=resources
    with pytest.raises(ForecastDataError,match='INSUFFICIENT_DATA'):
        make_dataset(store,request.model_copy(update={'as_of_time':datetime(2025,10,1,23,59,59,tzinfo=timezone.utc)}))
    with pytest.raises(ForecastDataError,match='STALE_DATA'):
        make_dataset(store,request.model_copy(update={'as_of_time':datetime(2026,9,20,tzinfo=timezone.utc)}))
    with pytest.raises(KeyError):make_dataset(store,request.model_copy(update={'context_series_ids':['absent']}))
    dataset=make_dataset(store,request)
    assert dataset['missing_context_counts']=={}
    assert not any(f.startswith('context:') for f in dataset['features'])


def test_context_missing_is_not_fabricated(tmp_path):
    store=MarketStore(tmp_path/'data.sqlite3')
    with store.connection() as db:
        db.execute("DELETE FROM bunker_observations WHERE series_id='demo_vlsfo_singapore' AND timestamp>'2026-08-01T00:00:00+00:00'")
    dataset=make_dataset(store,ForecastTarget(series_id='demo_panamax_index',as_of_time=AS_OF,context_series_ids=['demo_vlsfo_singapore']))
    last=dataset['rows'][-1]
    assert last['x'][16] is None and last['x'][17]==1
    assert last['missing_context']==['demo_vlsfo_singapore']


def test_artifact_path_validation(tmp_path):
    repo=ArtifactRepository(tmp_path)
    with pytest.raises(KeyError):repo.get('../outside')


def test_extreme_features_flag_ood(resources):
    from app.forecasting.engine import explain
    store,_,request,_,result=resources
    dataset=make_dataset(store,request)
    dataset['rows'][-1]['x'][0]=1e12
    context=explain(dataset,result)
    assert context['uncertainty_status']=='HIGH_UNCERTAINTY'
    assert 'current' in context['uncertainty_factors']['ood_features']


def test_tree_association_metadata_is_not_causal(resources):
    result=resources[-1]
    assert result['feature_importance']['7']['features']
    assert 'not causal' in result['feature_importance']['7']['note']
