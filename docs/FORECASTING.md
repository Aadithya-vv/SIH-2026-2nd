# Probabilistic freight forecasting (Batch 3)

## Scope and targets

Daily freight series from the existing MarketStore. Original units/currencies, route and vessel metadata are preserved. Index points are never converted into USD/day or voyage costs. ForecastTarget accepts series_id, timezone-aware as_of_time, a subset of horizons [1,3,7,14], up to eight context series and optional route/vessel assertions. Forecasts remain separate from charter timing. No Batch 4 decisions exist.

A historical as-of date is an explicit replay of what was knowable then. The demo ends on 2026-08-31; forecasts anchored there must not be described as forecasts from today. GET responses identify historical origins and flag origins older than seven days. Training at a stale origin with no recent data fails rather than generating invented current forecasts.

## Dataset and point-in-time guarantees

Extends Batch 2's feature builder without changing its contract. Observations and available_at must both precede each daily evaluation time. Target lags use exact UTC calendar days; no target fill. Optional contexts retain Batch 2's maximum three-day past-only fill. Default maximum lookback is 1096 days.

Features: current target; lags 1/2/3/7/14; 3/7/14-day rolling means; sample standard deviation of 14-day level changes; one-day fractional change; seven-day level momentum; month, quarter, weekday, monsoon calendar flag. Optional context adds current value, missing indicator and seven-day level change. Availability lineage is saved for every feature row. Route/vessel are immutable target metadata, not encoded arbitrary numerical risk scores.

Labels are exact T+h calendar-day values knowable at that day's evaluation, frozen to their contemporaneous revision. Late publications that were unknown on their observation day do not populate that day's labels or target history. This conservative policy may exclude real imported archives; missing publication evidence must not be guessed. Supervised fitting additionally requires label available_at <= fit origin and feature time < fit origin. Preprocessing medians and Ridge scaling are fitted only on that origin's training window.

Require at least 250 complete target feature rows and no more than 10% dropped target windows, plus at least five eligible origins per evaluation stage/horizon. Each forecast origin requires the current day and preceding 14 target days. Imported histories without historical publication times generally cannot satisfy historical replay and return INSUFFICIENT_DATA. Optional missing context stays null in the dataset; train-only median imputation is a disclosed estimator transformation, not an invented observed market value. Entirely missing training columns use zero internally with a missing indicator.

## Models and fixed configuration

- Persistence point baseline: latest value.
- Moving-average point baseline: mean of the latest seven daily observations.
- Drift point baseline: latest + horizon * (latest - 14-day lag) / 14, floored at zero.
- Ridge: alpha=10, train-fitted median imputer and StandardScaler.
- Quantile gradient boosting: separate losses at 0.1/0.5/0.9; 40 estimators, learning_rate=0.05, max_depth=2, min_samples_leaf=8, random_state=26054, train-fitted imputer.

Baselines and Ridge obtain P10/P50/P90 by adding empirical calibration residual quantiles to their point forecasts. Consequently their **calibrated P50 can differ from the raw persistence/moving-average/drift point forecast**. The leaderboard evaluates the delivered calibrated P50, consistently across candidates. Raw calibration point forecasts and residuals are saved for inspection. No training residuals are used as uncertainty estimates.

No hyperparameter search is performed. The small fixed model set avoids final-test tuning. Neural sequence model deferred until sufficient real historical data is available. No ARIMA dependency was added.

## Chronological split and walk-forward evaluation

Chronological feature origins: 60% initial training, 10% residual calibration, 10% model-selection validation, 20% final test. Together the two middle blocks form the validation/calibration allocation. There is no shuffle.

Each stage/horizon chooses at most eight deterministically spaced eligible origins in chronological order. Training expands at each origin using only labels published by that origin. Labels crossing a stage boundary are excluded from that stage's scoring; this purges multi-horizon overlap at boundaries. At least five origins per stage are required. The eight-origin cap is a prototype runtime budget, not a claim of statistical sufficiency.

Calibration residuals come from expanding-origin out-of-sample forecasts in the calibration block and are frozen before selection validation. Models are selected **independently by horizon** using validation P50 MAE, then mean pinball, then distance from nominal 80% coverage, then fixed model order. The selection is stored before any final-test metric is computed.

Final test also uses expanding fits: earlier test labels may enter a later test origin once actually published. This is prequential evaluation, not a single frozen-holdout fit. The model families/configuration/selection and residual calibration are not tuned on test results. All five candidates are reported on identical origins per horizon even if unselected. After test scoring, only the selected configuration is refit on all labels known at the requested as-of for the final forecast. That final refit is not reused to calculate historical test metrics.

## Metrics

MAE = mean absolute actual-minus-P50 error. RMSE = square root of mean squared error. Quantile pinball(q,e) = max(q*e,(q-1)*e); report each quantile and their mean. Coverage = fraction of actuals inside inclusive P10/P90, nominal 80%. Directional accuracy = fraction with matching sign of (P50-current) and (actual-current); unchanged is a third class. No MAPE, generic accuracy score or guarantee is reported.

Metrics and row counts are per horizon and split. Overlapping horizons and eight observations create substantial sampling uncertainty; the app does not manufacture confidence intervals for these metrics. Poor test coverage remains visible and does not trigger post-test band retuning.

## Quantile correction and interpretation

Native quantile models can cross. Every raw triple is saved; crossed triples are sorted into increasing order. Non-negative target support is enforced by flooring negative quantiles at zero; flags record crossings and clipping. Empirical residual intervals are not distribution-free conformal guarantees. P10/P50/P90 are prototype estimated quantiles, and coverage can be far from 80%.

## Explainability and reliability

Explanations show observed target momentum, recent volatility and available context movements. The final test-origin median boosting fit provides impurity-based feature associations with its fit origin; these are neither causality nor the rationale of a different selected model. Correlated features can distort importance. All drivers originate from recorded features.

Regime: VOLATILE when 30-return sample volatility >0.03; otherwise TRENDING when absolute seven-day change/current >0.03; otherwise STABLE. These are documented deterministic labels, not learned regimes.

HIGH_UNCERTAINTY: maximum relative P10-P90 width >0.5, any selected validation coverage more than 0.2 away from 0.8, or extreme out-of-distribution feature values. ELEVATED: relative width >0.25, fewer than 20 validation origins, optional current context missing or return volatility >0.03. Otherwise NORMAL. OOD means a finite latest feature more than three initial-train ranges beyond its initial-train min/max; range has a 5%-of-mean floor. Saved origins older than seven days are HIGH on retrieval and marked historical. These categories are operational flags, never probability-of-correctness claims.

## Artifacts and API

`artifacts/freight/<model_id>/`: metadata.json (completion marker), models.joblib (selected estimators/calibration), dataset.json (feature/label lineage), backtest.json (every origin/model forecast, actual and training bounds). IDs hash dataset, request, fixed config, code model version and sklearn version. Fixed seeds and dependency lock support reproducibility. Metadata is atomically published after files are saved. Artifacts are ignored by Git. The API never accepts arbitrary pickle uploads or filesystem paths; saved model binaries are not loaded from user input.

POST /api/forecast/train performs dataset validation, calibration, walk-forward comparison, selection, final-test reporting and final refit. Identical completed runs are reused. GET /api/forecast/models and /{model_id} inspect metadata. POST /api/forecast/backtest with model_id retrieves the stored audited walk-forward run; it does not refit on future data. GET /api/forecast/evaluation?model_id=... returns comparisons. GET /api/forecast/freight?series_id=... or /freight/{series_id} retrieves the latest saved forecast; optional as_of_time must exactly match a trained origin. Missing data/model returns explicit 422/404, never a substitute forecast.

Training is synchronous and serialized in this prototype process; the frontend displays progress state. No queue or distributed training was added. Optional FIP_ARTIFACT_DIR isolates storage. Browser tests use a separate artifact root.
