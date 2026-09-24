# Batch 2 data dictionary

## Source and series

`Source`: source_id, name, category, provider, access_type (PUBLIC_API, PUBLIC_DOWNLOAD, USER_IMPORT, COMMERCIAL_REQUIRED, DEMO), update_frequency, expected_units, license_notes, availability_status, last_successful_ingestion, notes.

`Series`: series_id, name, category (FREIGHT/COMMODITY/BUNKER/PORT/WEATHER), source_id, canonical unit, original currency, expected frequency_days, optional route, vessel_class, commodity, benchmark, origin_region, fuel_type and port; reusable ProvenanceMetadata. A freight series name may identify an index or route-specific rate. No index provider is inferred from its name.

## Normalized observations

| Field | Meaning / unit |
|---|---|
| timestamp | Time the observation describes, UTC |
| available_at | Earliest asserted time the value was knowable, UTC; separately tracked from ingestion |
| value | Normalized non-negative finite numerical observation |
| original_value | Unmodified parsed numerical value before unit conversion |
| original_unit / original_currency | Submitted unit/currency; never silently replaced by USD |
| quality_flags | Retained row-level flags; duplicate rows excluded from analytical selection |
| vessels_waiting | Optional non-negative count; null when absent |
| berth_delay | Optional non-negative days; null when absent |
| congestion_level | Optional source label; never invented from waiting days |

Initial port CSV import maps waiting_days through the selected value column. Optional auxiliary port fields have contracts/storage reserved but no CSV mappings yet. Weather contract: timestamp, available_at, port/route, wind_knots, wave_height_metres, cyclone_flag, severity, route_disruption and provenance. No weather records are seeded or ingested in Batch 2.

## Canonical units

- Freight: index_points without currency, or original currency per day/per tonne.
- Commodity/bunker: original currency per metric tonne.
- Port waiting: day.
- Aliases `t` and `metric_ton` -> tonne, factor 1.
- Price per kg -> price per tonne, factor 1000.
- Waiting hours -> days, factor 1/24.
- Hire per hour -> hire per day, factor 24.
- points -> index_points. Unknown/incompatible units reject validation; per-row units differing from the declared unit are quarantined.
- No FX conversion exists. USD, INR, EUR etc remain distinct. Currency identifiers require three uppercase letters; code legitimacy is not independently verified. No numerical comparison or aggregation across series currencies is performed.

## CSV import API contract

`POST /api/data/import/csv` accepts a JSON object with CSV text (the browser reads the selected file), category, source_name, series_name, date_column, value_column, optional available_at_column/unit_column, unit, optional currency and category metadata. ISO dates or ISO datetimes only; naive inputs explicitly mean UTC. Max 2,000,000 characters and 10,000 data rows; browser also enforces a 2 MB file limit.

Default `commit=false` previews without persistent writes. Response contains preview_hash, candidate series_id, rows_received/accepted/rejected, date range, missing/duplicate counts, canonical unit, source label and per-row issues. Commit resends the same request with commit=true and preview_hash. Server revalidates and hashes the exact payload. Changed input requires a new preview. All-invalid datasets cannot be committed. Identical repeated imports are idempotent.

Raw CSV, mappings and every row (including rejected rows) are retained in separate import audit tables. Accepted duplicates remain stored with DUPLICATE flags. A fresh immutable series is created for each distinct input+mapping payload; cross-upload merging and duplicate reconciliation are not implemented.

## Quality rules

- MISSING_VALUE: mapped date or value empty; completeness = rows with both fields nonempty / all rows. Completeness is not accuracy.
- INVALID_TIMESTAMP: malformed, future observation/publication, or publication before observation.
- NON_NUMERIC: unparseable or non-finite value. NEGATIVE_VALUE: outside the V1 non-negative contract; no clamping of imports.
- DUPLICATE: repeated (timestamp, available_at) in one import, retained; first eligible occurrence wins. Same observation with a later publication time is a revision, not a duplicate.
- OUT_OF_ORDER: timestamp earlier than preceding input row, retained and flagged; queries sort by time.
- UNIT_INCONSISTENCY: row-unit field differs from declared unit, quarantined.
- Missing periods: sum max(0, floor(elapsed whole days / frequency_days)-1) between unique valid timestamps. This is a calendar-day rule, not an exchange holiday calendar.
- STALE_DATA: latest observation age > max(7 days, 2 * frequency_days). Recomputed on reads, not frozen at ingestion.
- UNUSABLE: no valid observations; USABLE_WITH_WARNINGS: any flag/gap/staleness; otherwise USABLE. No automatic claim of forecast fitness.

## Feature dataset

Request: series_ids, freight target_series_id, start/end dates (max 1096 days), timezone-aware cutoff_time, max_fill_days 0-30 (default 3), optional required_arrival_date.

Each daily row contains date, evaluation_time, freight_target, values keyed by series ID, calendar and per-cell lineage. Calendar: weekday Monday=0, month, quarter, June-September monsoon_flag, null major_holiday_indicator, optional days_to_required_arrival. Series-level records carry units, currencies and provenance.

Evaluation time is min(UTC end of day, cutoff). A cell can only select observations whose timestamp AND available_at are <= evaluation time. Latest eligible observation time wins; latest known revision breaks ties; DUPLICATE rows are excluded. Target uses only observations from that date; it is never filled across days. Predictors use past-only forward fill bounded by age in UTC calendar days. There is no interpolation, backfill or unlimited fill. Excess gaps remain null. A partial cutoff day is explicitly evaluated at cutoff rather than pretending the day is complete.

Metadata records alignment, fill bounds, filled/missing counts, calendar rules and currency policy. Per-cell lineage records observation/publication time, source ID, age and transformation. SIMULATED inputs make suitability DEMO_ONLY. Imported data remains subject to provenance/publication/quality review; export is not permission to claim validated forecasting performance.

## Trend analytics

Latest, last 7/30-observation means, change from preceding distinct observation, percent change (null if denominator zero), min/max in selected range and sample standard deviation of 30 fractional returns (requires 31 observations, non-zero denominators). No annualization, filling or ML. Latest known revision per timestamp is used; duplicate rows excluded. Insufficient history returns null.


## Batch 3 forecast contracts

ForecastTarget: series_id, as_of_time (aware UTC), horizons drawn from 1/3/7/14 calendar days, optional context_series_ids, route and vessel-class metadata assertions. Units/frequency/currency are inherited from the stored target, never supplied as an implicit conversion. Daily targets only.

Forecast point: horizon, date, model_name, p10/p50/p90 in original target units, raw_quantiles, quantile_crossing/nonnegative_correction flags, training_rows and calibration_residual_count. Metadata: model_id/version, library_version, forecast_generated_at, training_cutoff, dataset_id/summary, source provenance, features, fixed hyperparameters, selected models by horizon, split periods, metrics, reliability, regime and explanations.

Metrics include count, MAE, RMSE, individual/mean pinball, directional_accuracy, coverage, nominal_coverage=0.8, mean interval width and crossings. Direction/coverage are fractions internally. FORECASTING.md documents temporal mechanics, calibrated baseline medians, exact formulas and failure statuses.
