# Batch 3 development receipt

## Baseline status

Inspected the existing repository, both receipts, market schema/provenance, feature builder and frontend. Baseline: 62 backend tests, lint, TypeScript and production build passed. Existing Batch 1 and 2 contracts were preserved. See BATCH_3_BASELINE.md.

## Files created

- Backend forecasting: models.py, dataset.py, estimators.py, evaluation.py, engine.py, artifacts.py, service.py and api.py under backend/app/forecasting/. The pre-existing interfaces.py is unchanged.
- backend/tests/test_forecasting.py.
- frontend/src/types/forecast.ts, frontend/src/pages/FreightForecast.tsx, frontend/src/components/FreightOutlook.tsx, frontend/e2e/forecast.spec.ts.
- docs/BATCH_3_BASELINE.md, FORECASTING.md, MODEL_CARD.md and this receipt. Generated artifacts are ignored, not committed.

## Files modified

- backend/app/main.py; backend/requirements.txt and requirements-lock.txt; .gitignore.
- frontend/src/App.tsx, src/types/market.ts, src/styles/app.css, playwright.config.ts.
- README.md, ARCHITECTURE.md, ROADMAP.md, DATA_PROVENANCE.md, DATA_SOURCES.md, DATA_DICTIONARY.md and CHANGELOG.md.
- scikit-learn is the only new direct dependency; its transitive dependencies are locked. No forecasting replacements were made in the market-data or voyage engines.

## Concrete demonstration run

Model ID: `18231d6ae75aaa0be9cc2bfd`. Version: `freight-v1.1`. Library: scikit-learn 1.9.1. Dataset hash: `4a9e3bb679410d1a43b8c45f5dee4203e235f067f9969e98a2643521872b81a0`.

Target: DEMO_PANAMAX_INDEX, original unit index_points, no currency. Horizons: 1, 3, 7 and 14 calendar days. Explicit historical origin: 2026-08-31 23:59:59 UTC. This is not a forecast made from current market observations.

Dataset: 365 target observations, 351 complete feature rows, 0 target rows dropped after lag warm-up; range 2025-09-01 through 2026-08-31.

**All target/context data is SIMULATED.** No real/public or user-imported observations are used in this demonstration. Imported histories are supported subject to publication evidence and minimum history; no real-world performance is claimed.

Features: current, lag_1, lag_2, lag_3, lag_7, lag_14, mean_3, mean_7, mean_14, volatility_14, change_1, momentum_7, month, quarter, day_of_week, monsoon_flag, context:demo_dry_bulk_index, context_missing:demo_dry_bulk_index, context_change_7:demo_dry_bulk_index, context:demo_vlsfo_singapore, context_missing:demo_vlsfo_singapore, context_change_7:demo_vlsfo_singapore, context:demo_coking_coal_benchmark, context_missing:demo_coking_coal_benchmark, context_change_7:demo_coking_coal_benchmark, context:demo_paradip_congestion, context_missing:demo_paradip_congestion, context_change_7:demo_paradip_congestion.

Unavailable/not used: actual licensed Baltic observations, real bunker/commodity/port histories, weather, authoritative holiday calendars, vessel availability, geopolitical scores, inventory and charter-timing economics.

## Chronological periods

| Period | Start | End | Feature rows |
|---|---|---|---:|
| train | 2025-09-15 | 2026-04-12 | 210 |
| calibration | 2026-04-13 | 2026-05-17 | 35 |
| validation | 2026-05-18 | 2026-06-21 | 35 |
| test | 2026-06-22 | 2026-08-31 | 71 |

## Models, configuration and backtest

Baselines: persistence, seven-day moving average, 14-day drift. Candidates: Ridge alpha=10 with train-only imputation/scaling; quantile gradient boosting with losses 0.1/0.5/0.9, 40 trees, depth 2, learning rate 0.05, min leaf 8, seed 26054.

Expanding-window fits at eight deterministically spaced eligible origins per calibration/validation/test stage and horizon. Labels crossing stage boundaries are purged. Every fit admits only labels published by that origin. Non-native quantile models add frozen out-of-sample calibration residual quantiles; their calibrated median can differ from their raw point baseline. Final selected estimators are refit on all known labels after final-test evaluation.

## Model comparison (SIMULATED DATA BACKTEST)

All errors below are in index points. Direction/coverage percentages summarize only eight held-out origins per model/horizon; they are not real-world accuracy claims. Nominal P10-P90 coverage is 80%.

| Days | Model | Selected | Validation MAE | Test MAE | Test RMSE | Mean pinball | Direction | Coverage |
|---:|---|---|---:|---:|---:|---:|---:|---:|
| 1 | Persistence |  | 24.323 | 37.573 | 46.870 | 10.839 | 37.5% | 62.5% |
| 1 | Moving average |  | 21.927 | 43.974 | 51.947 | 16.288 | 50.0% | 25.0% |
| 1 | Drift |  | 25.460 | 34.584 | 44.492 | 10.546 | 50.0% | 62.5% |
| 1 | Ridge | Yes | 20.867 | 30.010 | 37.018 | 8.576 | 62.5% | 87.5% |
| 1 | Quantile boosting |  | 31.225 | 27.495 | 32.963 | 9.240 | 50.0% | 100.0% |
| 3 | Persistence |  | 36.981 | 61.384 | 68.955 | 19.971 | 37.5% | 25.0% |
| 3 | Moving average |  | 31.926 | 45.891 | 57.165 | 19.552 | 75.0% | 25.0% |
| 3 | Drift |  | 39.233 | 58.337 | 69.773 | 19.033 | 50.0% | 62.5% |
| 3 | Ridge | Yes | 25.765 | 46.273 | 51.261 | 15.759 | 62.5% | 37.5% |
| 3 | Quantile boosting |  | 28.884 | 45.305 | 51.044 | 14.492 | 62.5% | 75.0% |
| 7 | Persistence |  | 38.283 | 54.429 | 65.400 | 20.040 | 37.5% | 50.0% |
| 7 | Moving average | Yes | 36.995 | 50.949 | 61.652 | 19.521 | 75.0% | 37.5% |
| 7 | Drift |  | 55.827 | 69.617 | 86.732 | 26.219 | 25.0% | 50.0% |
| 7 | Ridge |  | 41.660 | 42.735 | 48.619 | 11.942 | 75.0% | 62.5% |
| 7 | Quantile boosting |  | 44.632 | 44.394 | 56.586 | 16.255 | 37.5% | 75.0% |
| 14 | Persistence | Yes | 32.369 | 86.275 | 93.754 | 33.028 | 25.0% | 25.0% |
| 14 | Moving average |  | 39.623 | 80.301 | 94.376 | 33.589 | 37.5% | 12.5% |
| 14 | Drift |  | 55.931 | 116.353 | 125.429 | 36.939 | 12.5% | 25.0% |
| 14 | Ridge |  | 38.429 | 44.574 | 64.331 | 16.535 | 62.5% | 75.0% |
| 14 | Quantile boosting |  | 34.995 | 50.437 | 72.987 | 19.693 | 62.5% | 75.0% |

## Selected models and exact selection rule

Lowest validation P50 MAE, then mean pinball loss, then |coverage-0.8|, then fixed model order; independently by horizon.

Ridge wins days 1 and 3; moving average wins day 7; persistence wins day 14 in this four-context run. Selection is frozen before computing final-test metrics. The raw metadata retains full precision; displayed rounding does not affect selection. Different selected context sets produce different datasets and can select different models.

| Days | Selected model | Test P10 pinball | Test P50 pinball | Test P90 pinball | Test origins |
|---:|---|---:|---:|---:|---:|
| 1 | Ridge | 6.625 | 15.005 | 4.098 | 8 |
| 3 | Ridge | 10.181 | 23.136 | 13.959 | 8 |
| 7 | Moving average | 18.056 | 25.474 | 15.031 | 8 |
| 14 | Persistence | 23.529 | 43.138 | 32.418 | 8 |

Observed held-out coverage for selected days 3, 7 and 14 is only 37.5%, 37.5% and 25%, respectively. These bands under-cover materially. They were not adjusted after test inspection. The current reliability flag is HIGH_UNCERTAINTY. Neural models are deferred; this is a pipeline demonstration, not a validated maritime forecasting service.

## Forecast output at the historical origin

| Days | Date | P10 | P50 | P90 |
|---:|---|---:|---:|---:|
| 1 | 2026-09-01 | 1446.871 | 1484.265 | 1548.980 |
| 3 | 2026-09-03 | 1479.952 | 1529.733 | 1551.475 |
| 7 | 2026-09-07 | 1504.893 | 1519.495 | 1563.750 |
| 14 | 2026-09-14 | 1439.377 | 1456.855 | 1505.513 |

## API and frontend

POST /api/forecast/train; GET /api/forecast/models; GET /api/forecast/models/{model_id}; POST /api/forecast/backtest (stored audited run by model_id); GET /api/forecast/evaluation; GET /api/forecast/freight and /freight/{series_id}. Original APIs remain unchanged.

Freight Forecast page provides target/as-of/context selection, historical and forecast regions, P10-P90 area, P50 line, horizon table, measured drivers, explicitly non-causal tree associations, reliability warnings, per-horizon leaderboard, final-test visualization and metadata. Saved outlook panels appear under market context in the optimizer and control center. No WAIT/LOCK NOW decision is generated.

## Verification

Final backend: 79 tests passed, including all previous 62. Tests cover chronological boundaries, future-target exclusion, label publication purging, train-only preprocessing, baselines, exact metrics, crossing corrections, out-of-sample residuals, multi-horizon outputs, artifact provenance/cutoff, seed reproducibility, validation-only selection, missing/stale data, optional-context nulls, OOD flags, API validation and backtest training bounds.

Frontend lint, TypeScript and production build passed. Three browser workflows passed: Batch 1, Batch 2 and forecast training/quantiles/backtest/unavailable-history handling. The chart was visually inspected. Two upstream Starlette testing deprecations and Node color warnings remain non-failing.

## Known limitations and next action

Few, overlapping evaluation origins; synthetic-only demonstration; potentially unverified imported publication times; no automatic model updates; synchronous serialized training; daily targets only; no target gap imputation; limited prototype OOD diagnostics. Impurity importance is associative. No production reliability, autonomous chartering authority or guaranteed interval coverage is claimed.

Next recommended action: review these under-covered intervals against a properly authorized real historical archive, with more chronological origins and publication evidence, before operational use. The next product batch is Batch 4 Optimal Charter Timing, combining distributions with availability, deadline, voyage duration, congestion, demurrage, inventory and total costs. Batch 4 was not started.
