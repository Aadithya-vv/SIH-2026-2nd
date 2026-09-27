from datetime import datetime, timedelta, timezone
from math import ceil
import hashlib
import json
from time import perf_counter
from fastapi.encoders import jsonable_encoder
from app.audit.service import analyze
from app.core.assumptions import ASSUMPTIONS
from app.costing.engine import estimate_cost, rounded
from app.market.service import MarketSnapshotService
from .models import CharterTimingDecision
from .engine import POLICY_VERSION, resolved_policy, validate_forecast, interpolate, compare_candidates


class CharterTimingService:
    """Orchestrates existing engines; consumes saved forecast metadata only."""
    def __init__(self, provider, store, forecasts, repository):
        self.provider, self.store, self.forecasts, self.repository = provider, store, forecasts, repository

    def analyze(self, request):
        started = perf_counter()
        if request.analysis_as_of > datetime.now(timezone.utc):
            raise ValueError('analysis_as_of cannot be in the future.')
        shipment, day = request.shipment, request.analysis_as_of.date()
        baseline = analyze(shipment, self.provider, day)
        option = next(o for o in baseline.options if o.vessel.name == request.vessel_class)
        snapshot_service = MarketSnapshotService(self.store)
        snapshot = snapshot_service.snapshot(shipment.origin_port, shipment.destination_port,
                    request.vessel_class, shipment.cargo_type, request.analysis_as_of, shipment.origin_country)
        origin_snapshot = snapshot_service.snapshot(shipment.destination_port, shipment.origin_port,
                    request.vessel_class, shipment.cargo_type, request.analysis_as_of)
        ports = [p.model_copy(deep=True) for p in baseline.reference_ports]
        congestion = []
        for port, observation in zip(ports,[origin_snapshot['context']['port'],snapshot['context']['port']]):
            usable = (observation.get('available') and observation.get('unit') == 'day' and
                      observation['freshness']['status'] == 'WITHIN_THRESHOLD' and not observation['quality_flags'])
            if usable: port.reference_waiting_days = observation['value']
            congestion.append({'port':port.name, 'used_days_per_call':port.reference_waiting_days,
                'basis':'MARKET_OBSERVATION' if usable else 'ASSUMED_REFERENCE_FALLBACK',
                'status':'AVAILABLE' if usable else 'PORT CONGESTION DATA UNAVAILABLE OR STALE',
                'observation':observation, 'reference_provenance':port.provenance.model_dump(mode='json')})
        count = option.feasibility.voyage_count
        voyage = option.voyage.model_copy(deep=True)
        if request.loading_days is not None: voyage.loading_days = request.loading_days
        if request.unloading_days is not None: voyage.unloading_days = request.unloading_days
        voyage.port_days = voyage.loading_days+voyage.unloading_days
        voyage.expected_delay_days = sum(p.reference_waiting_days for p in ports)*count
        duration = voyage.sea_days+voyage.return_sea_days+voyage.port_days+voyage.expected_delay_days
        voyage.estimated_total_days = duration
        voyage.estimated_arrival = day+timedelta(days=ceil(duration))
        voyage.arrival_feasible = voyage.estimated_arrival <= shipment.required_arrival_date
        safe_days = ceil(duration+request.schedule_buffer_days)
        latest = shipment.required_arrival_date-timedelta(days=safe_days)
        policy = resolved_policy(request)
        result = CharterTimingDecision(analysis_id='', generated_at=datetime.now(timezone.utc).isoformat(),
            policy_version=POLICY_VERSION, request=request, recommendation='INSUFFICIENT_DATA',
            latest_safe_charter_date=latest.isoformat(), policy=policy,
            market_snapshot=jsonable_encoder({'destination':snapshot,'origin_port':origin_snapshot['context']['port'],'congestion_used':congestion}),
            voyage_context={'baseline':baseline.model_dump(mode='json'), 'selected_vessel':option.vessel.model_dump(mode='json'),
                'feasibility':option.feasibility.model_dump(mode='json'), 'voyage':voyage.model_dump(mode='json'),
                'voyage_count':count, 'rounded_buffered_duration_days':safe_days,
                'latest_safe_formula':'required_arrival_date - ceil(total sequential delivery days + schedule_buffer_days)'},
            assumptions={**ASSUMPTIONS, 'loading_override_days':request.loading_days,
                'unloading_override_days':request.unloading_days, 'schedule_buffer_days':request.schedule_buffer_days,
                'storage_usd_per_tonne_day':request.storage_usd_per_tonne_day,
                'waiting_cost_status':'USER_INPUT' if request.storage_usd_per_tonne_day is not None else 'NOT_MODELLED',
                'congestion_projection':'Latest usable per-port waiting days held constant across candidate dates and each voyage call.',
                'charter_semantics':'Daily UTC planning buckets; hire starts at origin including loading. Vessel immediately available. Deadline means final unloading complete; duration rounded upward.',
                'loading_unloading_overrides':'Total across all deliveries, not per voyage.',
                'schedule_buffer':'Reserved time, not billed hire or demurrage unless actually incurred.'},
            limitations=['Prototype decision support; not an operational charter instruction.',
                'Demo vessel/port/distance references remain ASSUMED, not verified particulars.',
                'Vessel availability and positioning are assumed; no observed availability feed.',
                'Inventory consumption, stockout and financing costs are UNQUANTIFIED, not zero-risk.',
                'P50 is a median scenario, not an expected value. No probabilities or expected regret are invented.',
                'Interpolated scenarios are not calibrated daily quantiles. No joint forecast dependence is estimated.',
                'Scenario regret compares matching quantile labels across dates; it is not worst-case regret over all market paths.',
                'Port waiting, bunker and port tariffs are held fixed across dates; no operational disruption distribution.'])
        if request.storage_usd_per_tonne_day is None:
            result.limitations.append('Storage waiting cost NOT MODELLED: no rate supplied; potential saving may be overstated.')
        if option.feasibility.status == 'FAIL' or latest < day:
            result.recommendation = 'NO_SAFE_WAIT_WINDOW'
            result.explanation = ['No operationally safe charter candidate exists under the selected vessel, ports and buffered deadline.',
                f'Latest safe charter date {latest}; analysis day {day}; buffered delivery requires {safe_days} calendar days.',
                'Port/cargo feasibility failed.' if option.feasibility.status == 'FAIL' else 'Even chartering now misses the buffered deadline.']
            return self._finish(result, started)
        try:
            if request.forecast_model_id:
                forecast = self.forecasts.artifacts.get(request.forecast_model_id)
            else:
                series_id = snapshot['context']['freight'].get('series_id')
                if not series_id: raise ValueError('FORECAST_UNAVAILABLE: no matching freight series.')
                forecast = self.forecasts.forecast(series_id, request.analysis_as_of)
                # Retrieve immutable basis, avoiding wall-clock-derived stale labels in historical replay.
                forecast = self.forecasts.artifacts.get(forecast['model_id'])
            result.forecast_metadata = forecast
            points = validate_forecast(forecast, request)
            target, current = forecast['target'], forecast['current_rate']
            if target['unit'] == 'day' and target['currency'] == 'USD':
                scale = 1.
                conversion = {'method':'DIRECT_USD_PER_DAY', 'anchor_hire':current, 'source':'FORECAST_TARGET'}
            elif target['unit'] == 'index_points' and request.allow_index_proxy:
                anchor = request.index_anchor_hire_usd_per_day or option.vessel.reference_daily_charter_rate
                scale = anchor/current
                conversion = {'method':'EXPLICIT_INDEX_RATIO_PROXY', 'anchor_hire':anchor,
                    'anchor_index':current, 'source':'USER_INPUT' if request.index_anchor_hire_usd_per_day else 'ASSUMED_DEMO_REFERENCE',
                    'formula':'hire_usd_per_day = anchor_hire * forecast_index / current_index; unit elasticity assumed, not estimated'}
                result.limitations.append('Index-to-hire ratio is an unvalidated assumption, not currency conversion or a broker quote.')
            else:
                raise ValueError('UNSUPPORTED_FREIGHT_UNITS: require USD/day, or explicit consent for an index-ratio proxy. No USD/tonne or FX conversion is inferred.')
        except (KeyError,ValueError) as exc:
            result.explanation = [str(exc), 'No timing recommendation fabricated. Select a compatible saved forecast and explicit cost basis.']
            return self._finish(result, started)
        result.rate_conversion = conversion
        base_hire = current*scale
        demurrage_rate = request.demurrage_usd_per_day if request.demurrage_usd_per_day is not None else base_hire*ASSUMPTIONS['demurrage_fraction_of_daily_hire']
        excess = max(0, voyage.expected_delay_days-ASSUMPTIONS['free_waiting_days_per_voyage']*count)
        result.assumptions.update({'demurrage_usd_per_day':demurrage_rate,
            'demurrage_source':'USER_INPUT' if request.demurrage_usd_per_day is not None else 'ASSUMED_0.8_OF_CURRENT_HIRE_FIXED_ACROSS_DATES',
            'excess_waiting_days':excess, 'hire_days':duration-excess,
            'current_hire_status':'REFERENCE_OR_OBSERVATION_NOT_EXECUTABLE_QUOTE'})
        horizon = max(p['horizon'] for p in points)
        limit = min(horizon,(latest-day).days)
        result.rejected_region = {'first_unsafe_date':(latest+timedelta(days=1)).isoformat(),
            'forecast_end_date':(day+timedelta(days=horizon)).isoformat(),
            'excluded_by_deadline_count':max(0,horizon-limit),
            'reason':'Beyond latest safe date: INFEASIBLE under configured buffer; excluded before costing.'}
        candidates = []
        for wait in range(limit+1):
            charter = day+timedelta(days=wait)
            raw, bounds = interpolate(points,current,wait)
            rates = {q:raw[q]*scale for q in raw}
            slack = (shipment.required_arrival_date-charter).days-duration-request.schedule_buffer_days
            costs = {}
            for q,rate in rates.items():
                # model_copy permits a valid zero nonnegative forecast even though class reference hire is positive.
                vessel = option.vessel.model_copy(update={'reference_daily_charter_rate':rate})
                cost = estimate_cost(vessel,ports,voyage,count,shipment.cargo_quantity_tonnes).model_dump(mode='json')
                cost['expected_demurrage'] = rounded(excess*demurrage_rate)
                cost['storage_if_applicable'] = rounded(ASSUMPTIONS['storage_usd']+wait*shipment.cargo_quantity_tonnes*(request.storage_usd_per_tonne_day or 0))
                components = ['ocean_freight','bunker_component','port_cost','expected_demurrage','lighterage_if_applicable','storage_if_applicable']
                cost['total_logistics_cost'] = rounded(sum(cost[k] for k in components))
                cost['cost_per_tonne'] = rounded(cost['total_logistics_cost']/shipment.cargo_quantity_tonnes)
                cost['provenance'] = {'source_type':'DERIVED','source_name':POLICY_VERSION,
                    'notes':'Phase 1 costing with scenario hire, fixed disclosed demurrage rate and optional waiting storage.'}
                costs[q] = cost
            candidates.append({'wait_days':wait, 'charter_date':charter.isoformat(),
                'estimated_arrival':(charter+timedelta(days=ceil(duration))).isoformat(),
                'buffered_arrival':(charter+timedelta(days=safe_days)).isoformat(),
                'arrival_status':'TIGHT' if slack < 1 else 'FEASIBLE', 'schedule_slack_days':slack,
                'freight_quantiles':raw, 'hire_usd_per_day':rates, 'interpolation_bounds':bounds,
                'forecast_basis':'CURRENT_ANCHOR' if wait==0 else 'MODEL_OUTPUT' if bounds[0]==bounds[1] else 'LINEAR_INTERPOLATION',
                'costs':costs})
        chosen, start, end = compare_candidates(candidates,current,forecast['uncertainty_status'],policy)
        result.candidate_decisions = candidates
        result.selected_wait_days = chosen['wait_days']
        result.recommendation = 'WAIT' if chosen['wait_days'] else 'LOCK_NOW'
        if chosen['wait_days']:
            result.recommended_window_start = (day+timedelta(days=start)).isoformat()
            result.recommended_window_end = (day+timedelta(days=end)).isoformat()
        result.current_charter_cost = candidates[0]['costs']['p50']['total_logistics_cost']
        result.recommended_median_cost = chosen['costs']['p50']['total_logistics_cost']
        result.median_saving = chosen['savings_vs_now']['p50']
        result.downside_exposure = chosen['downside_exposure']
        result.schedule_slack = chosen['schedule_slack_days']
        coverage = [r['validation']['coverage'] for r in forecast.get('leaderboard',[]) if r['selected']]
        counts = [r['validation']['count'] for r in forecast.get('leaderboard',[]) if r['selected']]
        poor_calibration = not coverage or any(abs(v-.8)>.2 for v in coverage)
        scenario_agreement = all(chosen['costs'][q]['total_logistics_cost'] <= candidates[0]['costs'][q]['total_logistics_cost'] for q in ('p10','p50','p90'))
        historical = day != datetime.now(timezone.utc).date()
        result.evidence_factors = {'historical_replay':historical, 'poor_validation_calibration':poor_calibration,
            'validation_coverages':coverage, 'validation_counts':counts, 'scenario_agreement':scenario_agreement,
            'relative_interval_width':chosen['relative_interval_width'],
            'missing_storage_rate':request.storage_usd_per_tonne_day is None,
            'missing_congestion':any(c['basis']!='MARKET_OBSERVATION' for c in congestion),
            'assumed_reference_geometry':True, 'forecast_uncertainty':forecast['uncertainty_status'],
            'generated_after_origin':datetime.fromisoformat(forecast['forecast_generated_at']) > request.analysis_as_of}
        # Demo geometry and absent actual vessel availability cap evidence at LIMITED.
        # STRONG/MODERATE are reserved for a validated non-demo reference adapter.
        result.evidence_status = 'LIMITED'
        rejected = sorted({r for c in candidates[1:] for r in c['policy_rejections']})
        result.explanation = [
            f"{result.recommendation.replace('_',' ')}: selected wait {chosen['wait_days']} day(s); median total USD {result.recommended_median_cost:,.2f}, saving USD {result.median_saving:,.2f} versus now.",
            f"Final delivery {chosen['estimated_arrival']}; {chosen['schedule_slack_days']:.2f} days slack remains after {request.schedule_buffer_days:g} days buffer. Latest safe charter {latest}.",
            f"P90 downside USD {result.downside_exposure:,.2f}; {request.risk_profile} limit USD {result.current_charter_cost*policy['maximum_downside_fraction']:,.2f}. Maximum aligned-scenario regret USD {chosen['maximum_scenario_regret']:,.2f}.",
            f"{len(candidates)} candidate dates checked; {len(rejected)} distinct rejection reasons: {', '.join(rejected) if rejected else 'none'}. No dates beyond the safe deadline were eligible.",
            f"Evidence LIMITED: demo operational references, forecast {forecast['uncertainty_status']}; historical replay={historical}. Storage {'included' if request.storage_usd_per_tonne_day is not None else 'not modelled'}; inventory/availability risk unquantified."]
        return self._finish(result, started)

    def _finish(self, result, started):
        # Exclude clocks/latency from content hash: identical evidence gives the same ID.
        payload = result.model_dump(mode='json',exclude={'analysis_id','generated_at','performance'})
        signature = json.dumps(payload,sort_keys=True,allow_nan=False,separators=(',',':'))
        result.analysis_id = hashlib.sha256(signature.encode()).hexdigest()[:24]
        result.performance = {'analysis_ms':round((perf_counter()-started)*1000,3),
            'candidate_dates':len(result.candidate_decisions), 'cost_scenarios':len(result.candidate_decisions)*3,
            'forecast_training_calls':0}
        self.repository.save(result)
        return result
