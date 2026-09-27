"""Pure, deterministic policy and rate interpolation. No I/O or model fitting."""
from copy import deepcopy
from datetime import date, timedelta
from math import isfinite

POLICY_VERSION = 'charter-v1'
PROFILES = {
    'CONSERVATIVE': {'minimum_slack_days': 2., 'maximum_downside_fraction': .005,
                     'minimum_saving_fraction': .005, 'maximum_relative_width': .25,
                     'allow_high_uncertainty': False},
    'BALANCED': {'minimum_slack_days': 1., 'maximum_downside_fraction': .02,
                 'minimum_saving_fraction': .0025, 'maximum_relative_width': .5,
                 'allow_high_uncertainty': True},
    'COST_FOCUSED': {'minimum_slack_days': 0., 'maximum_downside_fraction': .08,
                     'minimum_saving_fraction': .001, 'maximum_relative_width': 1.,
                     'allow_high_uncertainty': True},
}


def resolved_policy(request):
    policy = deepcopy(PROFILES[request.risk_profile])
    if request.max_downside_fraction is not None:
        policy['maximum_downside_fraction'] = request.max_downside_fraction
    policy['window_cost_tolerance_fraction'] = request.window_cost_tolerance_fraction
    return policy


def validate_forecast(forecast, request):
    from datetime import datetime
    origin = datetime.fromisoformat(forecast['as_of_time'])
    if origin != request.analysis_as_of:
        raise ValueError('FORECAST_ORIGIN_MISMATCH: use the exact saved forecast as-of or train a matching origin.')
    if datetime.fromisoformat(forecast['training_cutoff']) > request.analysis_as_of:
        raise ValueError('FUTURE_TRAINING_CUTOFF: forecast was trained beyond the analysis cutoff.')
    target = forecast['target']
    if target.get('vessel_class') != request.vessel_class:
        raise ValueError('FORECAST_VESSEL_MISMATCH: an exact vessel-class target is required.')
    route = request.shipment.origin_port+' -> '+request.shipment.destination_port
    if target.get('route') and target['route'] != route:
        raise ValueError('FORECAST_ROUTE_MISMATCH: forecast is for another route.')
    current = forecast['current_rate']
    if not isfinite(current) or current <= 0:
        raise ValueError('Invalid current forecast-basis rate.')
    points = sorted(forecast['forecast_points'], key=lambda p:p['horizon'])
    if not points or len({p['horizon'] for p in points}) != len(points):
        raise ValueError('Missing or duplicate forecast horizons.')
    for p in points:
        if p['horizon'] not in (1,3,7,14) or p['date'] != (origin.date()+timedelta(days=p['horizon'])).isoformat():
            raise ValueError('Forecast target date/horizon mismatch.')
        q = [p[k] for k in ('p10','p50','p90')]
        if not all(isfinite(v) and v >= 0 for v in q) or q != sorted(q):
            raise ValueError('Invalid or crossing forecast quantiles; timing never silently alters them.')
    return points


def interpolate(points, current, wait):
    """Linear scenario interpolation, not calibrated daily quantiles or a joint law."""
    knots = [{'horizon':0, 'p10':current, 'p50':current, 'p90':current}] + points
    for p in knots:
        if p['horizon'] == wait:
            return {k:p[k] for k in ('p10','p50','p90')}, [wait,wait]
    for a,b in zip(knots,knots[1:]):
        if a['horizon'] < wait < b['horizon']:
            fraction = (wait-a['horizon'])/(b['horizon']-a['horizon'])
            return {k:a[k]+fraction*(b[k]-a[k]) for k in ('p10','p50','p90')}, [a['horizon'],b['horizon']]
    raise ValueError('No extrapolation outside saved forecast horizons.')


def compare_candidates(candidates, current_rate, uncertainty, policy):
    now = candidates[0]['costs']['p50']['total_logistics_cost']
    minima = {q:min(c['costs'][q]['total_logistics_cost'] for c in candidates) for q in ('p10','p50','p90')}
    for c in candidates:
        totals = {q:c['costs'][q]['total_logistics_cost'] for q in minima}
        c['savings_vs_now'] = {q:round(now-v,2) for q,v in totals.items()}
        c['downside_exposure'] = round(max(0,totals['p90']-now),2)
        c['scenario_regret'] = {q:round(totals[q]-minima[q],2) for q in minima}
        c['maximum_scenario_regret'] = max(c['scenario_regret'].values())
        c['relative_interval_width'] = (c['freight_quantiles']['p90']-c['freight_quantiles']['p10'])/current_rate
        reasons = []
        if c['wait_days']:
            if c['schedule_slack_days']+1e-9 < policy['minimum_slack_days']: reasons.append('POLICY_SLACK')
            if c['savings_vs_now']['p50'] < now*policy['minimum_saving_fraction']: reasons.append('INSUFFICIENT_MEDIAN_SAVING')
            if c['downside_exposure'] > now*policy['maximum_downside_fraction']: reasons.append('P90_DOWNSIDE_LIMIT')
            if c['relative_interval_width'] > policy['maximum_relative_width']: reasons.append('INTERVAL_WIDTH_LIMIT')
            if uncertainty == 'HIGH_UNCERTAINTY' and not policy['allow_high_uncertainty']: reasons.append('HIGH_UNCERTAINTY_POLICY')
        c['policy_rejections'] = reasons
        c['decision_status'] = 'ELIGIBLE' if not reasons else 'REJECTED_BY_POLICY'
    eligible = [c for c in candidates if not c['policy_rejections']]
    chosen = min(eligible,key=lambda c:(c['costs']['p50']['total_logistics_cost'],c['maximum_scenario_regret'],c['wait_days']))
    chosen['decision_status'] = 'RECOMMENDED'
    start = end = chosen['wait_days']
    if start:
        acceptable = {c['wait_days'] for c in eligible if c['wait_days'] > 0 and
                      c['costs']['p50']['total_logistics_cost'] <= chosen['costs']['p50']['total_logistics_cost']+now*policy['window_cost_tolerance_fraction']}
        while start-1 in acceptable: start -= 1
        while end+1 in acceptable: end += 1
        for c in candidates:
            c['in_recommended_window'] = start <= c['wait_days'] <= end
    else:
        for c in candidates: c['in_recommended_window'] = False
    return chosen, start, end
