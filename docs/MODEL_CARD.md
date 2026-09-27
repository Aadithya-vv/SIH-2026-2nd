# Freight forecasting model card

## Intended use

Inspect probabilistic freight scenarios, baseline comparisons and point-in-time evaluation. Supply saved probabilistic inputs to the separate Phase 4 decision-support engine. **Not an autonomous chartering authority**, broker quote, trading signal or production forecasting service.

## Current data and provenance

Demonstration run: DEMO_PANAMAX_INDEX, 365 synthetic daily values from 2025-09-01 to 2026-08-31, with explicitly simulated broad dry-bulk, Singapore VLSFO, coking-coal and Paradip waiting contexts. Generator seed 26054 plus stable series offsets. Nothing in this run is actual Baltic Exchange or port-authority data. USER_IMPORT histories are supported but require trustworthy publication timestamps; the application cannot verify user source assertions.

## Model family and methodology

Persistence, seven-day moving average, 14-day drift, Ridge and native quantile gradient boosting. Fixed hyperparameters and seed; no neural network. Calibration residuals for non-quantile models are genuinely out-of-sample and frozen before selection. Chronological 60/10/10/20 split, purged stage labels and expanding-origin fits. Selection uses validation only; final-test results remain inspectable for all candidates. See FORECASTING.md for exact mechanics and formulas.

## Evaluation

Per-horizon MAE, RMSE, three pinball losses, directional sign match and empirical nominal-80% range coverage. The concrete comparison tables, dataset ID and artifact version are in BATCH_3_RECEIPT.md. Only eight origins per stage/horizon are scored in the current prototype. Some selected demo models substantially under-cover on the test period. These results demonstrate pipeline functionality and its limitations, not real-world freight accuracy.

## Limitations

Synthetic-to-real transfer is untested. A synthetic generator's seasonality/noise/shock structure is not a validated freight-market process. Short history, few overlapping test origins, changes in market structure, biased imported sources and incomplete publication metadata can invalidate apparent performance. Nonnegative quantile clipping and crossing rearrangement alter raw model output and are disclosed. Empirical residual ranges do not guarantee coverage. Feature importance is associative and may be unreliable under correlated predictors.

No vessel availability, charter contracts, inventories, arrival economics or optimal stopping enters forecast model selection. Forecast direction must not be interpreted as LOCK NOW or WAIT. Index values retain index units and cannot directly replace daily charter rates.

## Safeguards and next work

Publication cutoffs, train-only preprocessing, explicit missing/stale states, versioned artifacts, fixed seeds, stored origin-level audit, visible baselines and untouched final-test selection policy. Next scientific work is reviewed real histories, richer publication/revision evidence and more rolling origins with chronological probabilistic benchmarking. Phase 4 charter timing is implemented separately; it consumes immutable forecast metadata without retraining or test-based tuning.


## Phase 4 consumer limitations

The timing engine uses P10/P50/P90 as scenarios, interpolates between saved horizons and compares shipment-level costs. It does not claim a joint distribution, expected cost, expected regret, calibrated daily interpolation or real-world optimal stopping. CONSERVATIVE vetoes HIGH_UNCERTAINTY waiting; other profiles apply disclosed interval-width, downside and slack caps. All current decisions have LIMITED evidence because operational references and vessel availability are assumed, regardless of favorable synthetic forecast metrics.

Two explicitly constructed seeded demonstration histories exercise timing branches using the unchanged forecasting methodology. Their chosen trend/noise structure is for demonstration and cannot establish real-market performance. Test scores remain reported without tuning the decision policy against them. Index-to-hire conversion only occurs in the separate timing consumer with explicit consent and a disclosed unvalidated ratio assumption. No forecast quantities are changed by risk preferences.
