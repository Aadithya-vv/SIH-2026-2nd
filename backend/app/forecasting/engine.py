from datetime import datetime, date, timedelta, timezone
import numpy as np
from .dataset import chronological_split, training_pairs, actual_for
from .estimators import MODEL_NAMES, CONFIG, fit_model, point, predict_quantiles
from .evaluation import metrics, select_model


def stage_origins(dataset,rows,horizon):
    last=rows[-1]['evaluation_time']
    eligible=[]
    for row in rows:
        label,target_date=actual_for(dataset,row,horizon)
        if label and target_date<=rows[-1]['date'] and label['available_at'].isoformat()<=last:
            eligible.append(row)
    # Fixed deterministic budget; ordered expanding-origin samples, never shuffled.
    indexes=np.unique(np.linspace(0,len(eligible)-1,min(8,len(eligible)),dtype=int)) if eligible else []
    return [eligible[i] for i in indexes]


def evaluate(dataset,request):
    split=chronological_split(dataset['rows'])
    periods={name:{'start':rows[0]['date'],'end':rows[-1]['date'],'feature_rows':len(rows)} for name,rows in split.items()}
    records=[];leaderboard=[];selections={};bundles={};points=[];all_residuals={};training_audit=[];importance={}
    for horizon in request.horizons:
        residuals={name:[] for name in MODEL_NAMES}
        horizon_board=[]
        for stage in ('calibration','validation','test'):
            origins=stage_origins(dataset,split[stage],horizon)
            if len(origins)<5: raise ValueError(f'INSUFFICIENT_DATA: Fewer than five {stage} origins for horizon {horizon}.')
            for row in origins:
                x,y,audit=training_pairs(dataset,horizon,row['evaluation_time'])
                if len(y)<60: raise ValueError('INSUFFICIENT_TRAINING: Fewer than 60 observable training labels.')
                label,target_date=actual_for(dataset,row,horizon)
                bounds={'stage':stage,'horizon':horizon,'origin':row['evaluation_time'],'training_rows':len(y),
                    'max_training_feature_date':audit[-1][0],
                    'max_training_label_date':max(a[1] for a in audit),
                    'max_training_label_available_at':max(a[2] for a in audit)}
                training_audit.append(bounds)
                for name in MODEL_NAMES:
                    model=fit_model(name,x,y)
                    if name=='Quantile boosting' and stage=='test':
                        weights=model[1].named_steps['model'].feature_importances_
                        importance[str(horizon)]={'model':'Quantile boosting median','fit_origin':row['evaluation_time'],
                            'note':'Impurity-based association in the final test-origin training fit; not causal, not a selection criterion.',
                            'features':sorted([{'feature':f,'importance':float(w)} for f,w in zip(dataset['features'],weights)],key=lambda r:-r['importance'])}
                    if stage=='calibration':
                        estimate=point(name,model,row['x'],horizon)
                        residuals[name].append(label['value']-estimate)
                        records.append({'stage':stage,'horizon':horizon,'model':name,'origin':row['date'],
                            'target_date':target_date,'actual':label['value'],'point':estimate,'residual':label['value']-estimate,
                            'actual_available_at':label['available_at'].isoformat(),**bounds})
                    else:
                        forecast=predict_quantiles(name,model,row['x'],horizon,residuals[name])
                        records.append({'stage':stage,'horizon':horizon,'model':name,'origin_date':row['date'],
                            'target_date':target_date,'actual':label['value'],'actual_available_at':label['available_at'].isoformat(),
                            'current':row['current'],**forecast,**bounds})
            if stage=='validation':
                # Freeze selection before looking at a single final-test metric.
                horizon_board=[{'model':name,'horizon':horizon,
                    'validation':metrics([r for r in records if r['stage']=='validation' and r['horizon']==horizon and r['model']==name]),
                    'test':None} for name in MODEL_NAMES]
                selections[str(horizon)]=select_model(horizon_board)
        for entry in horizon_board:
            entry['test']=metrics([r for r in records if r['stage']=='test' and r['horizon']==horizon and r['model']==entry['model']])
            entry['selected']=entry['model']==selections[str(horizon)]
        leaderboard.extend(horizon_board)
        # Refit the already-selected configuration on all labels known at as_of, AFTER final-test scoring.
        latest=dataset['rows'][-1]
        x,y,audit=training_pairs(dataset,horizon,request.as_of_time.isoformat())
        name=selections[str(horizon)]
        model=fit_model(name,x,y)
        forecast=predict_quantiles(name,model,latest['x'],horizon,residuals[name])
        points.append({'horizon':horizon,'date':(request.as_of_time.date()+timedelta(days=horizon)).isoformat(),
            'model_name':name,'training_rows':len(y),'calibration_residual_count':len(residuals[name]),**forecast})
        bundles[str(horizon)]={'name':name,'model':model,'residuals':residuals[name]}
        all_residuals[str(horizon)]=residuals
    return {'periods':periods,'leaderboard':leaderboard,'selected_models':selections,'forecast_points':points,
            'records':records,'training_audit':training_audit,'residuals':all_residuals,'feature_importance':importance},bundles


def explain(dataset,evaluation):
    rows=dataset['rows'];latest=rows[-1];x=latest['x'];current=x[0]
    momentum=x[11];volatility=x[9]
    values=np.array([r['current'] for r in rows[-31:]])
    returns=np.diff(values)/np.maximum(values[:-1],1e-9)
    relative_vol=float(np.std(returns,ddof=1))
    trend=momentum/max(current,1e-9)
    regime='VOLATILE' if relative_vol>.03 else 'TRENDING' if abs(trend)>.03 else 'STABLE'
    explanation=[f'Target changed {momentum:+.4f} original units over the previous 7 calendar days.',
        f'Recent 30-return sample volatility is {relative_vol:.4f}; this is descriptive context, not causal evidence.',
        'Models selected independently by horizon using validation MAE, then pinball loss and calibration. Final-test results were not used for selection.',
        'P10-P90 is a nominal 80% prediction range, not a price guarantee. No charter timing decision is made.']
    context=[]
    for i,key in enumerate(dataset['missing_context_counts']):
        offset=16+3*i
        context.append({'series_id':key,'value':x[offset],'change_7':x[offset+2],'available':x[offset] is not None})
    relative_width=max((p['p90']-p['p10'])/max(current,1e-9) for p in evaluation['forecast_points'])
    coverage=[r['validation']['coverage'] for r in evaluation['leaderboard'] if r['selected']]
    sparse=any(r['validation']['count']<20 for r in evaluation['leaderboard'] if r['selected'])
    warnings=[]
    if sparse: warnings.append('SMALL_EVALUATION_SAMPLE: fewer than 20 origins per selected validation horizon.')
    if latest['missing_context']: warnings.append('MISSING_CONTEXT: optional inputs missing; train-only imputation and indicators used.')
    # Compare the latest finite feature vector against initial train ranges; do not hide extrapolation.
    initial=chronological_split(rows)['train']
    matrix=np.array([r['x'] for r in initial],dtype=float);vector=np.array(x,dtype=float)
    ood=[]
    for i,name in enumerate(dataset['features']):
        finite=matrix[:,i][np.isfinite(matrix[:,i])]
        if len(finite) and np.isfinite(vector[i]):
            lo,hi=np.min(finite),np.max(finite);spread=max(hi-lo,abs(float(np.mean(finite)))*.05,1e-9)
            if vector[i]<lo-3*spread or vector[i]>hi+3*spread: ood.append(name)
    if ood: warnings.append('OUT_OF_DISTRIBUTION: '+', '.join(ood))
    poor_coverage=any(abs(c-.8)>.2 for c in coverage)
    status='HIGH_UNCERTAINTY' if relative_width>.5 or poor_coverage or ood else 'ELEVATED_UNCERTAINTY' if relative_width>.25 or sparse or latest['missing_context'] or relative_vol>.03 else 'NORMAL_UNCERTAINTY'
    return {'market_regime':regime,'uncertainty_status':status,'explanation':explanation,'warnings':warnings,
            'drivers':{'momentum_7':momentum,'rolling_volatility_14':volatility,'fractional_volatility_30':relative_vol,'context':context},
            'uncertainty_factors':{'relative_interval_width':relative_width,'validation_coverages':coverage,'small_sample':sparse,'ood_features':ood},
            'feature_importance_note':'Context and statistical associations do not establish causation. No causal attribution is claimed.'}
