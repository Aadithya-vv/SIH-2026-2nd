import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.ensemble import GradientBoostingRegressor

SEED=26054
MODEL_NAMES=('Persistence','Moving average','Drift','Ridge','Quantile boosting')
CONFIG={'seed':SEED,'ridge_alpha':10.0,'tree_n_estimators':40,'tree_learning_rate':.05,
        'tree_max_depth':2,'tree_min_samples_leaf':8,'max_origins_per_stage':8,'minimum_calibration_residuals':5,
        'split':'60% initial train / 10% calibration / 10% selection validation / 20% final test',
        'selection':'Lowest validation P50 MAE, then mean pinball loss, then |coverage-0.8|, then fixed model order; independently by horizon.'}


def baseline(name,x,horizon):
    if name=='Persistence': return float(x[0])
    if name=='Moving average': return float(x[7])  # mean_7, named feature order locked by dataset module
    if name=='Drift': return max(0.0,float(x[0]+horizon*(x[0]-x[5])/14))
    raise ValueError('Unknown baseline')


def fit_model(name,x,y):
    if name in MODEL_NAMES[:3]: return None
    imputer=SimpleImputer(strategy='median',keep_empty_features=True)
    if name=='Ridge':
        model=Pipeline([('imputer',imputer),('scaler',StandardScaler()),('model',Ridge(alpha=CONFIG['ridge_alpha']))])
        return model.fit(x,y)
    if name=='Quantile boosting':
        models=[]
        for quantile in (.1,.5,.9):
            model=Pipeline([('imputer',SimpleImputer(strategy='median',keep_empty_features=True)),
                ('model',GradientBoostingRegressor(loss='quantile',alpha=quantile,n_estimators=CONFIG['tree_n_estimators'],
                    learning_rate=CONFIG['tree_learning_rate'],max_depth=CONFIG['tree_max_depth'],
                    min_samples_leaf=CONFIG['tree_min_samples_leaf'],random_state=SEED))])
            models.append(model.fit(x,y))
        return models
    raise ValueError('Unknown model')


def point(name,model,x,horizon):
    if model is None: return baseline(name,x,horizon)
    if name=='Quantile boosting': return float(model[1].predict(np.array([x],dtype=float))[0])
    return float(model.predict(np.array([x],dtype=float))[0])


def correct_quantiles(raw):
    if not np.isfinite(raw).all(): raise ValueError('MODEL_FAILURE: Non-finite forecast.')
    crossing=not(raw[0]<=raw[1]<=raw[2])
    clipped=any(v<0 for v in raw)
    return np.maximum(np.sort(raw),0).tolist(),crossing,clipped


def predict_quantiles(name,model,x,horizon,residuals):
    if name=='Quantile boosting':
        raw=[float(m.predict(np.array([x],dtype=float))[0]) for m in model]
    else:
        if len(residuals)<CONFIG['minimum_calibration_residuals']:
            raise ValueError('INSUFFICIENT_CALIBRATION: Need at least five out-of-sample residuals.')
        raw=(point(name,model,x,horizon)+np.quantile(residuals,[.1,.5,.9])).tolist()
    corrected,crossing,clipped=correct_quantiles(raw)
    return {'p10':corrected[0],'p50':corrected[1],'p90':corrected[2],
            'raw_quantiles':raw,'quantile_crossing':crossing,'nonnegative_correction':clipped}
