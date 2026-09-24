from datetime import datetime, timezone
import hashlib
import json
import threading
import sklearn
from .dataset import make_dataset
from .estimators import CONFIG
from .engine import evaluate,explain

MODEL_VERSION='freight-v1.1'
TRAINING_LOCK=threading.Lock()


class FreightForecastService:
    def __init__(self,store,artifacts): self.store=store;self.artifacts=artifacts

    def train(self,request):
        if request.as_of_time>datetime.now(timezone.utc): raise ValueError('As-of time cannot be in the future.')
        with TRAINING_LOCK:
            dataset=make_dataset(self.store,request)
            signature=json.dumps({'dataset_id':dataset['dataset_id'],'request':request.model_dump(mode='json'),
                'config':CONFIG,'version':MODEL_VERSION,'sklearn':sklearn.__version__},sort_keys=True)
            model_id=hashlib.sha256(signature.encode()).hexdigest()[:24]
            try: return self.artifacts.get(model_id)
            except KeyError: pass
            evaluation,bundles=evaluate(dataset,request)
            context=explain(dataset,evaluation)
            target=dataset['series'][0]
            simulated=any(s['provenance']['source_type']=='SIMULATED' for s in dataset['series'])
            label='SIMULATED DATA BACKTEST' if simulated else 'USER-IMPORTED DATA BACKTEST' if any(s['provenance']['source_type']=='USER_IMPORT' for s in dataset['series']) else 'HISTORICAL DATA BACKTEST'
            metadata={'model_id':model_id,'model_version':MODEL_VERSION,'library_version':sklearn.__version__,
                'forecast_generated_at':datetime.now(timezone.utc).isoformat(),'training_cutoff':request.as_of_time.isoformat(),
                'as_of_time':request.as_of_time.isoformat(),'target':target,'request':request.model_dump(mode='json'),
                'dataset_id':dataset['dataset_id'],'dataset_summary':{k:dataset[k] for k in ('start','end','raw_observations','usable_rows','dropped_target_rows','missing_context_counts')},
                'features':dataset['features'],'feature_importance':evaluation['feature_importance'],'hyperparameters':CONFIG,'seed':CONFIG['seed'],
                'data_provenance':[s['provenance'] for s in dataset['series']],'source_series':dataset['series'],
                'output_provenance':'FORECAST','evaluation_label':label,'periods':evaluation['periods'],
                'leaderboard':evaluation['leaderboard'],'selected_models':evaluation['selected_models'],
                'selection_reason':CONFIG['selection'],'forecast_points':evaluation['forecast_points'],
                'current_rate':dataset['rows'][-1]['current'],'history':[{'date':r['date'],'actual':r['current']} for r in dataset['rows'][-60:]],
                'training_policy':'Expanding windows; both feature and label availability checked. Parameters selected on validation only. Final-test scores never affect selection. Selected models refit on all known labels only after scoring.',
                'uncertainty_method':'Quantile boosting fits 0.1/0.5/0.9 loss models. Other models use frozen expanding-origin calibration residual quantiles; no in-sample residuals. Crossing quantiles sorted and negatives clipped with flags.',
                'limitations':['Neural sequence model deferred until sufficient real historical data is available.',
                    'Small evaluation samples and overlapping horizons; no independent confidence claim.',
                    'No charter timing or price-to-voyage-cost conversion. Index points are not USD/day.',
                    'Imported publication times are user assertions, not independently verified.'],**context}
            if simulated: metadata['warnings'].append('SIMULATED_DATA: Demonstrates pipeline behavior, not real freight-market accuracy.')
            return self.artifacts.save(model_id,metadata,bundles,dataset,{'records':evaluation['records'],'training_audit':evaluation['training_audit'],
                'periods':evaluation['periods'],'residuals':evaluation['residuals'],'evaluation_label':label,'model_id':model_id})

    def forecast(self,series_id,as_of=None):
        candidates=[m for m in self.artifacts.list() if m['target']['series_id']==series_id and
                    (as_of is None or datetime.fromisoformat(m['as_of_time'])==as_of)]
        if not candidates: raise KeyError('FORECAST_UNAVAILABLE: No trained model for this series/as-of. Train on sufficient history first.')
        result=max(candidates,key=lambda m:(m['as_of_time'],m['forecast_generated_at']))
        age=(datetime.now(timezone.utc)-datetime.fromisoformat(result['as_of_time'])).total_seconds()/86400
        result['as_of_age_days']=round(age,2)
        result['is_historical_as_of']=datetime.fromisoformat(result['as_of_time']).date()!=datetime.now(timezone.utc).date()
        if age>7:
            result['uncertainty_status']='HIGH_UNCERTAINTY'
            result['warnings']=result['warnings']+['STALE_FORECAST_ORIGIN: Saved historical forecast, not a current outlook.']
        return result
