# Phase 4 development receipt

Status: **CORE PROTOTYPE FEATURE FREEZE**. Phase 4 completed and validated 2026-09-27. No Phase 5 started.

## Baseline

Clean master at f44501a. Required repository/docs/API/domain/forecast/snapshot/frontend inspection completed before edits. Baseline: 79 backend tests passed (61.95 s), frontend lint, TypeScript and production build passed. See PHASE_4_BASELINE.md.

## Files created

- backend/app/charter/__init__.py, models.py, engine.py, service.py, repository.py, api.py, demos.py.
- backend/tests/test_charter.py.
- frontend/src/types/charter.ts; frontend/src/pages/CharterDecision.tsx and DecisionHistory.tsx; frontend/e2e/charter.spec.ts.
- docs/PHASE_4_BASELINE.md, CHARTER_TIMING.md, END_TO_END_FLOW.md and PHASE_4_RECEIPT.md.

## Files modified

- backend/app/main.py (router/version 0.4.0). Existing Phase 1-3 analytical engines and forecasting training/selection remain unchanged.
- frontend/src/App.tsx, frontend/src/styles/app.css, frontend/playwright.config.ts; frontend/e2e/analysis.spec.ts updates the obsolete timing-placeholder assertion.
- README.md; docs/ARCHITECTURE.md, ROADMAP.md, DATA_PROVENANCE.md, DATA_SOURCES.md, FORECASTING.md, MODEL_CARD.md; CHANGELOG.md.
- No new dependency. Generated forecast artifacts, database snapshots and browser screenshots remain ignored.

## Architecture and contracts

CharterTimingRequest embeds the existing ShipmentRequirement with selected vessel, exact analysis origin, saved forecast ID, risk profile, buffer, optional handling/storage/demurrage inputs and explicit index-proxy consent. The central CharterTimingService resolves Phase 1 feasibility/voyage/cost, Phase 2 market snapshots and immutable Phase 3 forecast metadata. Pure policy/interpolation is separate from orchestration, forecast training and persistence.

POST /api/charter/analyze returns the full comparison and saves it. GET /api/charter/history, /api/charter/{analysis_id}, /api/charter/{analysis_id}/explanation retrieve original evidence. GET /api/charter/demos resolves preset inputs; POST /api/charter/demos/prepare explicitly prepares synthetic histories/forecasts outside the analysis service. No redundant compare endpoint: analyze already returns all candidates.

## Exact decision calculations

- Daily candidates: wait 0 through min(saved maximum horizon, latest_safe_date - analysis_date), inclusive. Every integer day, no extrapolation.
- Latest safe: required arrival - ceil(total sequential delivery duration + schedule buffer). Charter begins service/loading at origin; arrival means final unloading complete. Extra deliveries include return passages.
- Physical port/cargo failure or no buffered feasible NOW date: NO_SAFE_WAIT_WINDOW. Otherwise date candidates beyond the hard safe region never receive costs or enter selection. Residual slack <1 day is TIGHT.
- Fresh unflagged per-port day observations replace reference waiting. Missing/stale observations retain an explicitly labelled assumed reference fallback; not fabricated current congestion. Per-call delay is multiplied by voyage count.
- Direct USD/day forecasts or explicit index-ratio proxy; incompatible units, route/vessel or origin/cutoff produce INSUFFICIENT_DATA. Between saved horizons, linearly interpolate scenarios without claiming calibrated daily quantiles.
- Reuse Phase 1 costs. Hire excludes excess waiting charged as demurrage. Demurrage = excess wait times user rate or fixed 0.8 of current hire assumption. Bunker/port/lighterage stay disclosed existing assumptions.
- Optional waiting storage = wait days times tonnes times user USD/tonne/day. Missing storage remains NOT MODELLED. Stockout/inventory/availability risks are UNQUANTIFIED.
- Saving(q) = NOW total - candidate total(q). Downside = max(0, candidate P90 total - NOW total). P50 is a median scenario, never a claimed expected value.
- Regret(c,q) = cost(c,q) - minimum cost among all hard-feasible dates in the same quantile-labelled scenario. Maximum scenario regret = maximum of these three differences. Not a joint-distribution worst-case or probability-weighted metric.

## Policy, window and evidence

CONSERVATIVE: residual slack >=2d, median saving >=0.5% of NOW, downside <=0.5%, relative freight interval width <=25%, HIGH_UNCERTAINTY waiting veto. BALANCED: >=1d, saving >=0.25%, downside <=2%, width <=50%. COST_FOCUSED: >=0d, saving >=0.1%, downside <=8%, width <=100%. BALANCED/COST_FOCUSED allow HIGH uncertainty inside their stated caps. Maximum downside is explicitly overridable. No hidden normalization or weights.

Choose minimum P50 cost among eligible NOW/wait candidates; break ties by maximum scenario regret then earlier day. Grow a contiguous WAIT window through adjacent policy-eligible dates costing <= selected P50 + 0.25% of NOW (configurable). LOCK_NOW has no future window. The UI displays selected-day metrics and each window date separately.

All present results have LIMITED evidence: demo operational references and unobserved vessel availability cap the status. Interval width, calibration/sample counts, scenario agreement and missing/freshness evidence remain stored; no invented confidence percentage.

## Frontend

Charter decision is workspace 06. Shipment/risk form, exact historical forecast basis, explicit proxy checkbox, four seeded presets, market context, prominent decision/window, latest safe date, calculated reasons, date-cost band, safe/unsafe regions, timeline, all-candidate comparison, cost components, model metrics/provenance and assumptions. Deadline/buffer and other edits debounce automatic recalculation after first analysis. Stale inputs and request races are handled. Decision history reopens complete immutable evidence. Existing pages remain available.

## Deterministic demo calculations

All scenarios: SIMULATED historical replay at 2026-08-31 23:59:59 UTC. Panamax, 70,000 t coking coal, Newcastle to Paradip, one voyage. Reference distance 6,200 nm; sea 19.87179487 d; loading 2.8 d; unloading 3.5 d; origin wait 1 d ASSUMED; destination wait 1.9593 d SIMULATED. Total 29.13109487 d. Buffer 2 d; ceil(31.13109487)=32 calendar days. Excess waiting 1.9593 d; hire 27.17179487 d. Storage rate supplied as USD 0.001/t/day, i.e. USD 70 per wait day.

Seeded daily USD/day histories use 40000 - 45*day + normal noise, 365 days, seeds 26054/26055, sigma 70/2200. Real Phase 3 training/model selection generates the saved forecasts; predictions and decisions are not overwritten. These constructed scenarios are not real-market performance evidence.

| Scenario | Result | Selected wait | Charter window | Latest safe | NOW USD | Selected P50 USD | Median saving USD | Selected slack d |
|---|---|---:|---|---|---:|---:|---:|---:|
| A - Wait opportunity | WAIT | 14 | 2026-09-09 to 2026-09-14 | 2026-09-18 | 1,233,494.80 | 1,217,686.75 | 15,808.05 | 4.87 |
| B - Tight deadline | LOCK_NOW | 0 | - | 2026-08-31 | 1,233,494.80 | 1,233,494.80 | 0.00 | 0.87 |
| C - High uncertainty | LOCK_NOW | 0 | - | 2026-09-18 | 1,301,562.28 | 1,301,562.28 | 0.00 | 18.87 |
| D - Insufficient data | INSUFFICIENT_DATA | - | - | 2026-09-18 | - | - | - | - |

### A - WAIT

Model a13b6f97bdfea4ceb8b5bafd, version freight-v1.1. Current hire USD 23,729.1057/day; required final delivery 2026-10-20. Fifteen dates / 45 cost cases. Selected P90 downside USD 0.00; policy limit USD 24,669.90. Window dates all pass policy and the USD 3,083.74 cost tolerance.

| Selected day 14 cost component | P10 USD | P50 USD | P90 USD |
|---|---:|---:|---:|
| ocean_freight | 625,332.01 | 627,974.34 | 633,167.78 |
| bunker_component | 381,538.46 | 381,538.46 | 381,538.46 |
| port_cost | 170,000.00 | 170,000.00 | 170,000.00 |
| expected_demurrage | 37,193.95 | 37,193.95 | 37,193.95 |
| storage_if_applicable | 980.00 | 980.00 | 980.00 |
| lighterage_if_applicable | 0.00 | 0.00 | 0.00 |
| total_logistics_cost | 1,215,044.42 | 1,217,686.75 | 1,222,880.19 |

### B - LOCK NOW despite lower future freight

Uses the identical A forecast. Required final delivery is calculated as 2026-10-02 = origin +32 days. Latest safe date equals origin 2026-08-31. Only NOW is feasible; 14 later horizon dates are excluded before cost selection. Slack after buffer is 0.868905 days. Falling forecast cannot overrule this constraint.

### C - LOCK NOW under conservative uncertainty limits

Model d7b3f913442053b410d99d56, current hire USD 26,097.5570/day. Fifteen dates / 45 cases. Conservative downside limit USD 6,507.81; HIGH_UNCERTAINTY veto applies to all waiting candidates. Some waits have lower median cost and even favorable P90, but this policy explicitly refuses high-uncertainty waiting. NOW maximum aligned-scenario regret is USD 211,681.86; this opportunity cost remains visible.

| Wait d | P50 saving USD | P90 saving / loss USD | P90 downside USD | Rejection |
|---:|---:|---:|---:|---|
| 1 | 27,971.17 | -26,979.40 | 26,979.40 | P90_DOWNSIDE_LIMIT, HIGH_UNCERTAINTY_POLICY |
| 3 | 53,490.64 | 9,649.58 | 0.00 | HIGH_UNCERTAINTY_POLICY |
| 7 | 99,733.00 | -23,901.55 | 23,901.55 | P90_DOWNSIDE_LIMIT, HIGH_UNCERTAINTY_POLICY |
| 14 | 127,689.59 | 59,378.78 | 0.00 | HIGH_UNCERTAINTY_POLICY |

### D - INSUFFICIENT DATA

Physical voyage and safe date are calculated, but the selected forecast ID does not exist. No cost scenario, fabricated saving or selected window is returned. Explanation names the missing model.

## Audit and provenance

Additive charter_analyses SQLite table stores content-hashed immutable snapshots alongside Phase 1 records. Full input, baseline feasibility/reference data, market snapshot, saved forecast, model/cutoff, policy/version, every candidate cost and explanation are retained. IDs exclude generation clock/latency; duplicate evidence retains its first stored record. History reconstruction never refreshes the forecast. Demo data is SIMULATED; geometry/cost references ASSUMED; optional rates USER_INPUT; forecasts FORECAST; scenario arithmetic DERIVED. No real public/commercial data used.

## Validation and performance

Backend: 112 tests passed (79 Phase 1-3 regressions +33 Phase 4 tests); two existing upstream Starlette deprecation warnings. Tests include daily/horizon bounds, safe-date math, port/deadline gates, interpolation/units, all cost components, storage/demurrage, multi-voyage, regret, risk preferences, uncertainty veto, incompatible/future forecasts, audit equality, API validation and deterministic/idempotent seeding. Forecast training is prohibited by a failing test stub in timing-service tests; existing publication/leakage tests remain passing.

Final frontend lint, TypeScript and production build passed after UI corrections. Four browser workflows passed in 40.5 s: Phase 1 shipment analysis, Phase 2 market/import/features, Phase 3 forecasts/backtest, and Phase 4 charter decisions. The charter end-to-end covers real upstream training/cost arithmetic, all demo decisions, automatic deadline/buffer changes, missing forecast, infeasible shipment, immutable history and a 390px viewport without page overflow. Desktop and mobile screenshots were visually inspected; panel contrast and cost-chart scale were corrected. A UTC normalization mismatch in the stale-input indicator and a select accessible-name mismatch were found and fixed during browser testing. Node color warnings are non-failing.

Representative warm analysis performance, 10 repeated 15-date /45-scenario runs: median 46.233 ms; min 45.315; max 47.725. Excludes network/browser time and includes evidence construction up to the repository save boundary; no model training calls. Local prototype timing, not a service-level guarantee.

## Known limitations and exact flow

Demo references, synthetic forecasts, limited/overlapping backtest samples, poor interval coverage, assumed immediate vessel availability, constant port waits/bunker costs, no joint uncertainty distribution or calibrated cost bands, unvalidated opt-in index elasticity, no FX/tonne-to-hire mapping, unquantified stockout/financing/availability risk, daily planning granularity. Historical replays are not contemporaneously issued forecasts or operational quotations. All evidence LIMITED. No guaranteed savings, real-world optimality or production-readiness claim.

Shipment -> both-port/vessel/capacity feasibility -> sequential voyage -> publication-gated market snapshot -> saved probabilistic forecast -> safe daily charter dates -> three shipment-cost scenarios per date -> downside/slack/regret -> deterministic policy and contiguous window -> calculated explanation -> immutable audit/history. See END_TO_END_FLOW.md and CHARTER_TIMING.md.

**CORE PROTOTYPE FEATURE FREEZE.** All requested validation completed. No Phase 5 or unrelated integration has been started. Next work, if separately requested, should focus on real historical/commercial validation and correcting identified limitations rather than additional major features.
