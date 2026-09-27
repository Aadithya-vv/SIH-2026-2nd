# Charter timing decision support — Phase 4

The business question is shipment-specific: does waiting offer sufficient median cost advantage without violating the delivery deadline or the procurement policy's downside limits? This prototype compares transparent scenarios, not expected utility or a mathematically optimal real-world stopping policy.

## Inputs and service boundary

`CharterTimingRequest` embeds the unchanged Phase 1 `ShipmentRequirement`, plus vessel class, timezone-aware analysis_as_of, optional saved forecast_model_id, risk profile (BALANCED by default), buffer, total loading/unloading overrides, optional USD/day demurrage, optional USD/tonne/day storage, optional explicit index proxy and anchor, downside limit override and window tolerance. Blank optional cost rates mean NOT MODELLED; explicit zero means user-provided zero. No inventory dollars are fabricated from stock levels without a consumption/stockout model.

`CharterTimingService` calls Phase 1 analysis for both-port dimensional/cargo feasibility, capacity, route, sea and return legs. It consumes Phase 2 snapshots and Phase 3 saved forecast metadata. It does not call train, load estimator binaries, revise model selection or tune against test results. The separate **Prepare seeded demo forecasts** action explicitly invokes the existing Phase 3 training workflow before any decision analysis.

The selected vessel is an explicit procurement input. It is checked rather than silently switched to a different vessel/forecast. The voyage optimizer remains the separate vessel-class comparison tool.

## Time and hard feasibility

Charter dates use the existing daily UTC planning semantics. Chartering begins the vessel's service at the origin, including loading; there is no extra unmodelled charter-to-departure offset. Actual availability/positioning is assumed, not observed. No intraday booking promise is made. Required arrival means completion of final unloading, consistently with Phase 1's voyage totals.

For N sequential deliveries by one vessel:

`D = outbound_sea_days × N + return_sea_days_per_leg × (N−1) + total_loading_days + total_unloading_days + N × (origin_wait_days + destination_wait_days)`

The Phase 1 voyage object already aggregates sea/return legs, so Phase 4 does **not multiply these aggregates again**. Loading/unloading overrides refer to the complete shipment, not each voyage. Default handling days remain quantity/loading throughput and quantity/unloading throughput.

`latest_safe_charter_date = required_arrival_date − ceil(D + buffer_days)`

For candidate wait w, charter date = analysis date + w; final delivery = charter date + ceil(D); buffered delivery = charter date + ceil(D + buffer); residual slack = (required arrival − charter date).days − D − buffer.

If vessel/port/cargo checks fail or latest_safe precedes analysis day: NO_SAFE_WAIT_WINDOW, no candidate can win. Otherwise enumerate **every integer day** from zero through `min(max saved horizon, latest_safe − analysis_date)`. No extrapolation beyond the forecast or cost estimates for unsafe dates. The first unsafe date and count of deadline-excluded dates are reported separately and shaded on the chart. Safe candidates with residual slack <1 day are TIGHT; others FEASIBLE. The buffer is a hard gate; risk profiles may impose additional slack on waiting candidates. Chartering now is not excluded by an optional waiting-policy slack preference when it meets the hard buffered deadline.

## Market, congestion and source discipline

Both origin and destination port waiting observations are requested from MarketSnapshotService, with timestamp and available_at <= analysis_as_of. A fresh, unflagged observation in day units **replaces**, not adds to, the reference waiting days. It is multiplied by N port calls. Missing, stale, flagged or incompatible congestion returns PORT CONGESTION DATA UNAVAILABLE OR STALE; the existing port reference assumption remains explicitly labelled ASSUMED_REFERENCE_FALLBACK. It is never represented as observed congestion. Future waiting is held constant across candidates, not forecast.

The full market snapshot, chosen observation, source type, publication time, age and reference fallback are stored. Fuel remains the Phase 1 disclosed USD 600/tonne assumption; a Singapore context observation does not silently become the shipment's bunker contract.

## Forecast and units

Require the exact saved forecast origin to equal analysis_as_of, training cutoff no later than that origin, matching vessel class and compatible route metadata. A generic vessel-class forecast remains a non-route quotation. Horizons/date pairs and finite ordered nonnegative quantiles are validated. Missing/incompatible basis yields INSUFFICIENT_DATA, never a replacement model. A physical infeasibility may be reported before forecast lookup.

At day zero all three freight scenarios equal the forecast's current observed basis; this is a **reference anchor, not an executable quote**. At saved horizons the quantiles are preserved. Between knots (0,1,3,7,14 as available), interpolate each quantile linearly. Convex interpolation preserves ordering. These interpolated values are scenario assumptions, not newly calibrated daily quantiles. No probabilities or joint distribution are inferred.

USD/day targets map directly to daily hire. Index points require explicit consent: `scenario_hire = anchor_hire × scenario_index / current_index`. The user may supply the anchor or knowingly use the demo vessel reference. The unit elasticity of one is assumed, unvalidated and fully disclosed. Index points are not dollars. Currency conversion and USD/tonne-to-time-charter conversion are unsupported and return INSUFFICIENT_DATA. Phase 3 outputs are never mutated.

Historical origin labels remain visible. Forecasts generated after their origin are historical replays using publication-gated data, not proof a forecast existed at that date. Demo reference effective dates identify assumption versions, not historical operational facts. No real-time recommendation is manufactured by relabelling an old model as today.

## Cost model and waiting

Reuses Phase 1 estimate_cost for each candidate and quantile, retaining all sequential deliveries. For each scenario:

- `excess_wait = max(0, total_expected_port_wait − free_wait_days_per_voyage × N)`.
- `hire_days = D − excess_wait`; ocean hire = scenario daily hire × hire_days.
- Bunker = aggregate outbound/return sea days × vessel fuel tonnes/day × assumed fuel USD/tonne.
- Port charges = sum of both reference port costs × N.
- Demurrage = excess_wait × explicit USD/day rate, or disclosed assumption `0.8 × current anchored hire`. This rate stays **fixed across charter dates/scenarios**, not falsely forecast as a contractual term. Hire excludes these excess days, avoiding double-counting.
- Storage = existing reference storage + wait_days × shipment tonnes × supplied storage USD/tonne/day. Missing rate adds no fabricated dollars and is prominently NOT MODELLED.
- Existing lighterage assumption is retained. No invented additional category.

Components are rounded half-up to USD cents by the existing rounding function. Total = sum of displayed components; USD/tonne = total / shipment quantity. Schedule buffer is reserved time, not automatically billed hire. Stockout, financing, vessel availability and inventory consumption are unquantified. P50 cost is a **median scenario**, not an expected value.

## Opportunity, downside and regret

For candidate c and quantile label q:

`saving[c,q] = now_cost − cost[c,q]` (negative means loss).

`downside[c] = max(0, cost[c,P90] − now_cost)`.

`regret[c,q] = cost[c,q] − min(cost[j,q] for all hard-feasible candidates j)`.

`maximum_scenario_regret[c] = max_q regret[c,q]`.

Regret aligns P10 with P10 etc across dates. Marginal quantiles do not specify a joint market path: this is a diagnostic, **not expected regret or the worst possible cross-date loss**. No fake scenario probabilities, generic AI score or savings guarantee.

## Deterministic policy

First enforce physical feasibility and buffered arrival. For each waiting candidate apply all profile limits:

| Profile | Additional residual slack | Minimum median saving / now cost | Max P90 downside / now cost | Max freight interval width / current rate | HIGH_UNCERTAINTY allowed? |
|---|---:|---:|---:|---:|---|
| CONSERVATIVE | 2 days | 0.5% | 0.5% | 25% | No |
| BALANCED | 1 day | 0.25% | 2% | 50% | Yes, within these caps |
| COST_FOCUSED | 0 days | 0.1% | 8% | 100% | Yes, within these caps |

These are disclosed procurement preferences, not optimized model parameters. Users may override the maximum downside fraction (0–1); exact applied values are stored. All limits use unrounded analytical slack/width and displayed-cent costs. Tests/forecast calibration are not used to tune these defaults. High uncertainty does not secretly alter forecast quantiles: CONSERVATIVE vetoes such waiting, other profiles constrain width/downside and show LIMITED evidence.

Among policy-eligible candidates including NOW, choose minimum P50 total, then minimum maximum scenario regret, then earliest wait day. If NOW wins, LOCK_NOW and no invented future window. If a later day wins, WAIT and an explicit window. No safe hard-feasible candidate gives NO_SAFE_WAIT_WINDOW; no compatible cost/forecast basis gives INSUFFICIENT_DATA.

## Charter window

Start with the selected waiting day. Include adjacent integer waiting days that satisfy **all** policy limits and cost no more than selected P50 + `window_tolerance × now_cost` (default tolerance 0.25%). Grow contiguously in both directions; never bridge a rejected date. NOW is not added to a WAIT window. Selected-day metrics are labelled as such; other window dates retain their individual table values.

## Evidence

Store measurable interval width, selected validation coverage and sample counts, scenario agreement, congestion/storage gaps, historical replay flag and forecast uncertainty. Poor validation calibration means any selected coverage farther than 0.2 from nominal 0.8, or no validation coverage. Current **ASSUMED demo geometry and unobserved vessel availability cap every decision at LIMITED**, regardless of favorable model metrics; there is no misleading upgrade to STRONG based on a tiny synthetic backtest. STRONG/MODERATE are reserved for a future validated reference/availability adapter. The cap and measurements are visible in saved evidence. Not a probability of correctness.

## API, audit and latency

- POST `/api/charter/analyze`: validated shipment, full scenario comparison and saved decision.
- GET `/api/charter/history`: last 100 immutable charter snapshots.
- GET `/api/charter/{analysis_id}` and `/{analysis_id}/explanation`: original evidence, no recalculation.
- GET `/api/charter/demos`: seeded preset inputs/readiness; computes the tight deadline from voyage context without saving an analysis.
- POST `/api/charter/demos/prepare`: explicit preparation of two simulated histories and their Phase 3 models; training lives outside the timing service.

No separate compare endpoint: analyze already returns every candidate/scenario. `charter_analyses` is an additive table in the existing analyses.sqlite3 (override FIP_ANALYSIS_DB). Content hash IDs exclude generation time/latency. INSERT OR IGNORE preserves the first record for identical evidence. Each record embeds the request, baseline/reference details, market snapshot, full forecast, costs, policy/version, recommendation, explanation and provenance. Reopening history returns that snapshot; it never silently refreshes its market data. Independent analyses report compute latency and candidate/scenario counts. No major runtime dependency was added.

## Seeded demonstration

365 values, 2025-09-01 through 2026-08-31. Fixed daily trend `40000 − 45×day + Normal(0,sigma)` USD/day, positive floor 1000; publication 18:00 UTC. Decline sigma=70, seed=26054; uncertainty sigma=2200, seed=26055. Explicit SIMULATED source and Newcastle→Paradip/Panamax metadata. Existing Phase 3 chronological evaluation and model selection run unchanged; no quantiles or test scores are edited to force decisions. These constructed histories demonstrate decision branches, not real-market forecasting skill.

A uses decline and loose deadline; B uses the identical forecast with required arrival computed at the first buffered possible day; C uses the noisy history and CONSERVATIVE policy; D points to a nonexistent forecast. Full calculated results are in PHASE_4_RECEIPT.md.

## Limits and freeze

No licensed market feeds, actual availability, charter contracts, validated index elasticity, stockout economics, correlated freight/port uncertainty or operational guarantees. Eight evaluation origins per stage/horizon remain statistically weak; intervals can under-cover. Before operational use, validate with authorized historical/commercial data, executable quotes, contract terms and real availability. Phase 4 ends the core feature scope; no Phase 5 is started.
