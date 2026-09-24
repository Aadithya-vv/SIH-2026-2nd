import numpy as np
from .estimators import MODEL_NAMES


def metrics(records):
    if not records: return None
    actual=np.array([r['actual'] for r in records]);median=np.array([r['p50'] for r in records]);current=np.array([r['current'] for r in records])
    errors=actual-median
    pinball={}
    for q,key in [(.1,'p10'),(.5,'p50'),(.9,'p90')]:
        e=actual-np.array([r[key] for r in records]);pinball[key]=float(np.mean(np.maximum(q*e,(q-1)*e)))
    lower=np.array([r['p10'] for r in records]);upper=np.array([r['p90'] for r in records])
    return {'count':len(records),'mae':float(np.mean(np.abs(errors))),'rmse':float(np.sqrt(np.mean(errors**2))),
        'pinball':pinball,'mean_pinball':float(np.mean(list(pinball.values()))),
        'directional_accuracy':float(np.mean(np.sign(median-current)==np.sign(actual-current))),
        'coverage':float(np.mean((actual>=lower)&(actual<=upper))),'nominal_coverage':.8,
        'mean_interval_width':float(np.mean(upper-lower)),'crossings':sum(r['quantile_crossing'] for r in records)}


def select_model(leaderboard):
    eligible=[r for r in leaderboard if r['validation'] is not None]
    if not eligible: raise ValueError('INSUFFICIENT_VALIDATION: No evaluated candidate.')
    return min(eligible,key=lambda r:(r['validation']['mae'],r['validation']['mean_pinball'],
        abs(r['validation']['coverage']-.8),MODEL_NAMES.index(r['model'])))['model']
