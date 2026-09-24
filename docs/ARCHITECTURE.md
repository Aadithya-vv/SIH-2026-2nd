# Architecture

Shipment -> replaceable reference provider -> feasibility -> voyage -> costing -> optimization -> audit/application service -> FastAPI -> React.

`backend/app/domain/models.py` owns typed, validated contracts. Numeric reference fields inherit their record-level provenance; derived outputs carry their own metadata. `data/demo/reference.json` is the explicit illustrative dataset. `app/data/reference.py` implements a replaceable ReferenceProvider protocol. The pure engines do not perform HTTP calls, read clocks or mutate input records. `audit/service.py` orchestrates all four vessel options with an explicit analysis date. API routes inject the UTC date and serialize results; analytical decisions never live in route handlers.

Feasibility applies draft, LOA, beam and cargo-type checks at origin and destination. Capacity produces ceil(quantity / capacity) deliveries and CONDITIONAL status if more than one is required. A conditional option is eligible because the sequential schedule explicitly accounts for the extra deliveries. A failed dimensional or cargo check always excludes it.

Voyage duration includes outbound legs for every delivery and return legs between deliveries. Costs cover all deliveries. Deadline compliance is a hard constraint. Eligible options sort lexicographically by total USD cost, voyage count, elapsed duration and vessel name. There are no hidden weights. No eligible option produces an explicit null recommendation, not a fallback to an impossible vessel.

The UI owns draft form state and the last analyzed shipment separately. Editing inputs marks results stale; submit clears previous results and displays loading/errors. Navigation retains the current analysis. Costs for impossible vessels remain visible as hypothetical comparisons, clearly excluded from selection.

SQLite persistence is isolated in `app/persistence/sqlite.py`. Full analyses are stored as immutable JSON snapshots with embedded assumptions and provenance. History retrieval, schema migrations and reporting are deferred to Batch 7. Storage timestamps/row IDs are not inserted into deterministic analytical outputs.

Forecasting, timing and scenario protocols reserve boundaries without fake implementations. The forecasting interface accepts historical feature tables (freight, bunker, congestion, seasonality, commodity indicators) and returns P10/P50/P90 by horizon. Forecast provenance, calibration and model versioning must be added before exposing forecasts. NumPy/Pandas are available for that future data pipeline; current arithmetic does not need ML.


## Batch 2 market data foundation

Adapters -> structural/row validation -> unit normalization -> source/provenance -> relational SQLite -> snapshots/trends/point-in-time features -> market workspace.

The existing Batch 1 engines and REST request/response models remain unchanged. The only shared domain extension is an additive USER_IMPORT SourceType. `app/market` separates typed contracts, source adapters, normalization, quality rules, persistence, services, features and thin API routes. Market context is shown separately and does not mutate Batch 1 cost assumptions.

`data/market.sqlite3` (override via FIP_MARKET_DB) stores data_sources, data_series, category-specific freight_observations / commodity_observations / bunker_observations / port_observations / weather_observations, data_imports, data_import_rows, data_quality_reports and market_schema_versions. Version 1 creation is additive and idempotent; Batch 1 analyses.sqlite3 is untouched. Indexes cover series/time/availability plus route/port metadata and weather route/port/time. Numeric observations are relational columns; JSON is limited to provenance, quality flags/reports and raw-row audit evidence. Foreign keys and transactional writes prevent partial imports. Identical payload hashes are idempotent; distinct imports are immutable datasets.

MarketSnapshotService filters by vessel class/route, cargo type, Singapore VLSFO hub and exact destination port. Both observation time and availability must be <= as_of. Selection ranks fresh before stale, non-demo before demo, origin-matched metadata before proxy, then latest observation. Every returned value carries source, provenance, availability and age; absence returns available=false. Singapore/cargo proxies are explicitly identified. No route quotation or charter decision is inferred.

The feature builder uses an explicit daily knowledge cutoff and never reads later publications into earlier rows. Predictor filling is bounded; labels are not filled. This protects the current point-in-time transformation, but reliable historical availability still depends on trustworthy source publication evidence. There is no forecasting model.

React adds independent MarketIntelligence, ImportData, FeatureBuilder and MarketContext components. Existing optimizer, compatibility and control-center behavior remains. Browser tests use isolated ports 8100/5174 and a separate SQLite database, leaving the running app on 8000/5173 alone.


## Batch 3 forecasting

The existing market-store and feature-builder contracts are preserved. app/forecasting adds target validation, supervised dataset construction, baseline/estimator adapters, chronological evaluation, explanations, artifact storage, FreightForecastService and thin routes. Selection validation and final-test evaluation are distinct. Model artifacts are separate from market/reference SQLite data. Forecast retrieval is read-only; training is explicit. The UI adds Freight forecast and saved-outlook panels without altering voyage-cost calculations. Charter timing remains unimplemented. See FORECASTING.md for temporal boundaries and MODEL_CARD.md for limitations.
