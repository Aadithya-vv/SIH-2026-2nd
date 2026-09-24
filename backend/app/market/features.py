from datetime import datetime, time, timedelta, timezone
from .service import usable_history


def build_features(store,request):
    series=[store.series(key) for key in request.series_ids]
    if next(s for s in series if s.series_id==request.target_series_id).category != 'FREIGHT':
        raise ValueError('The target must be a freight series.')
    observations={s.series_id:store.observations(s.series_id,end=request.cutoff_time,cutoff=request.cutoff_time) for s in series}
    rows=[]
    missing={s.series_id:0 for s in series}
    filled={s.series_id:0 for s in series}
    day=request.start
    while day<=request.end and day<=request.cutoff_time.date():
        evaluation=min(datetime.combine(day,time.max,tzinfo=timezone.utc),request.cutoff_time)
        values={}
        lineage={}
        for s in series:
            history=usable_history(observations[s.series_id],evaluation)
            candidate=history[-1] if history else None
            age=(day-candidate.timestamp.date()).days if candidate else None
            limit=0 if s.series_id==request.target_series_id else request.max_fill_days
            accepted=candidate is not None and age<=limit
            value=candidate.value if accepted else None
            values[s.series_id]=value
            if accepted:
                method='OBSERVED' if age==0 else 'BOUNDED_FORWARD_FILL'
                if age: filled[s.series_id]+=1
                lineage[s.series_id]={'timestamp':candidate.timestamp,'available_at':candidate.available_at,
                    'method':method,'age_days':age,'source_id':s.source_id,'quality_flags':candidate.quality_flags}
            else:
                missing[s.series_id]+=1
                lineage[s.series_id]={'method':'MISSING','reason':'No eligible known observation within gap bound.'}
        rows.append({'date':day.isoformat(),'evaluation_time':evaluation,'freight_target':values[request.target_series_id],
            'values':values,'calendar':{'day_of_week':day.weekday(),'month':day.month,'quarter':(day.month-1)//3+1,
                'monsoon_flag':int(6<=day.month<=9),'major_holiday_indicator':None,
                'days_to_required_arrival':(request.required_arrival_date-day).days if request.required_arrival_date else None},
            'lineage':lineage})
        day+=timedelta(days=1)
    return {'target_series_id':request.target_series_id,'cutoff_time':request.cutoff_time,'rows':rows,
        'series':series,'missing_by_series':missing,'filled_by_series':filled,
        'transformations':{'grid':'Daily UTC, evaluated at day end or cutoff, whichever is earlier.',
            'alignment':'Latest observation with timestamp AND available_at <= evaluation_time. Latest known revision wins; duplicate rows excluded.',
            'fill':'Past-only bounded forward fill for predictors. No interpolation or backfill. Target never filled across days.',
            'max_fill_days':request.max_fill_days,'calendar':'Monday=0; quarter 1-4; June-September monsoon is a coarse Indian calendar flag, not observed weather. Holidays unavailable without a vetted calendar.',
            'currency':'Original currency retained per series; no FX conversion.',
            'training_note':'Daily rows represent end-of-day information. Shift future forecast labels separately using chronological evaluation in Batch 3.'},
        'suitability':'DEMO_ONLY' if any(s.provenance.source_type=='SIMULATED' for s in series) else 'REVIEW_QUALITY_AND_PUBLICATION_ASSERTIONS',
        'provenance':'DERIVED; per-cell lineage and source provenance retained.'}
