from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import numpy as np
from app.market.features import build_features
from app.market.models import FeatureRequest

LAGS=(1,2,3,7,14)
BASE_FEATURES=['current']+[f'lag_{i}' for i in LAGS]+['mean_3','mean_7','mean_14','volatility_14','change_1','momentum_7','month','quarter','day_of_week','monsoon_flag']


class ForecastDataError(ValueError): pass


def make_dataset(store,request):
    target=store.series(request.series_id)
    if target.category!='FREIGHT': raise ForecastDataError('INVALID_TARGET: Choose a freight series.')
    if target.frequency_days!=1: raise ForecastDataError('UNSUPPORTED_FREQUENCY: Batch 3 requires daily target observations.')
    if request.route and request.route!=target.route: raise ForecastDataError('ROUTE_MISMATCH: Target metadata does not match the requested route.')
    if request.vessel_class and request.vessel_class!=target.vessel_class: raise ForecastDataError('VESSEL_MISMATCH: Target metadata does not match the requested vessel class.')
    known=store.observations(target.series_id,end=request.as_of_time,cutoff=request.as_of_time)
    if not known: raise ForecastDataError('INSUFFICIENT_DATA: No target history known at the requested as-of time.')
    if (request.as_of_time-known[-1].timestamp).total_seconds()/86400>7:
        raise ForecastDataError('STALE_DATA: Latest target is more than 7 days old. Choose an explicit historical as-of date or import recent observations.')
    start=max(known[0].timestamp.date(),request.as_of_time.date()-timedelta(days=1095))
    base=build_features(store,FeatureRequest(series_ids=[request.series_id]+request.context_series_ids,
        target_series_id=request.series_id,start=start,end=request.as_of_time.date(),cutoff_time=request.as_of_time,max_fill_days=3))
    base_rows=base['rows']
    features=BASE_FEATURES.copy()
    for key in request.context_series_ids:
        features.extend([f'context:{key}',f'context_missing:{key}',f'context_change_7:{key}'])
    rows=[]
    for i in range(14,len(base_rows)):
        row=base_rows[i]
        history=[r['freight_target'] for r in base_rows[i-14:i+1]]
        if any(v is None for v in history): continue  # Never fill target history.
        x=[history[-1]]+[history[-1-lag] for lag in LAGS]
        x += [float(np.mean(history[-n:])) for n in (3,7,14)]
        x += [float(np.std(np.diff(history[-14:]),ddof=1)),
              (history[-1]/history[-2]-1) if history[-2]!=0 else 0.0,history[-1]-history[-8]]
        x += [row['calendar'][k] for k in ('month','quarter','day_of_week','monsoon_flag')]
        missing=[]
        lineage={request.series_id:[r['lineage'][request.series_id] for r in base_rows[i-14:i+1]]}
        for key in request.context_series_ids:
            value=row['values'][key];past=base_rows[i-7]['values'][key]
            x += [value,int(value is None),value-past if value is not None and past is not None else None]
            if value is None: missing.append(key)
            lineage[key]=[row['lineage'][key],base_rows[i-7]['lineage'][key]]
        rows.append({'date':row['date'],'evaluation_time':row['evaluation_time'].isoformat(),
            'x':x,'current':history[-1],'missing_context':missing,'lineage':lineage})
    if not rows or rows[-1]['date']!=request.as_of_time.date().isoformat():
        raise ForecastDataError('INSUFFICIENT_DATA: As-of day and 14 previous calendar days need target observations available on their respective days. No target backfill is performed.')
    if len(rows)<250:
        raise ForecastDataError(f'INSUFFICIENT_DATA: Need 250 complete daily feature rows for separated training, calibration, selection and test; found {len(rows)}. Import publication times for historical backtesting.')
    missing_fraction=1-len(rows)/max(1,len(base_rows)-14)
    if missing_fraction>.1: raise ForecastDataError('LARGE_MISSING_PERIODS: More than 10% of target feature rows are unavailable.')
    # Labels are frozen to the contemporaneously observable day-end value, never a later revision.
    labels={r['date']:{'value':r['freight_target'],'available_at':r['lineage'][request.series_id].get('available_at')} for r in base_rows if r['freight_target'] is not None}
    serialized=json.dumps({'rows':rows,'labels':labels,'series':[s.model_dump(mode='json') for s in base['series']]},sort_keys=True,default=str)
    return {'rows':rows,'labels':labels,'features':features,'series':[s.model_dump(mode='json') for s in base['series']],
        'dataset_id':hashlib.sha256(serialized.encode()).hexdigest(),'start':base_rows[0]['date'],'end':base_rows[-1]['date'],
        'raw_observations':len(known),'usable_rows':len(rows),'dropped_target_rows':len(base_rows)-14-len(rows),
        'transformations':base['transformations'],'missing_context_counts':{k:sum(k in r['missing_context'] for r in rows) for k in request.context_series_ids}}


def chronological_split(rows):
    n=len(rows);train=int(n*.6);cal=int(n*.7);validation=int(n*.8)
    return {'train':rows[:train],'calibration':rows[train:cal],'validation':rows[cal:validation],'test':rows[validation:]}


def training_pairs(dataset,horizon,origin):
    x=[];y=[];audit=[]
    for row in dataset['rows']:
        # Features must precede origin, labels must already be observable at origin.
        if row['evaluation_time']>=origin: continue
        target_date=(date.fromisoformat(row['date'])+timedelta(days=horizon)).isoformat()
        label=dataset['labels'].get(target_date)
        if not label or label['available_at'].isoformat()>origin: continue
        x.append(row['x']);y.append(label['value']);audit.append((row['date'],target_date,label['available_at'].isoformat()))
    return np.array(x,dtype=float),np.array(y,dtype=float),audit


def actual_for(dataset,row,horizon):
    target_date=(date.fromisoformat(row['date'])+timedelta(days=horizon)).isoformat()
    return dataset['labels'].get(target_date),target_date
