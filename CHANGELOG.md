# Development receipt log

## 0.1.0 - 2026-09-20 - Batch 1

Created the repository from scratch: typed backend contracts, reference adapter, both-port checks, sequential voyage estimator, transparent USD cost engine, deterministic constrained vessel selection, FastAPI endpoints, SQLite snapshot repository, and React/TypeScript operational UI with Recharts costs. Added analytical/API/persistence tests, explicit provenance, assumption documentation and future-module protocols. No forecasting, timing advice, live feeds, authentication, AIS, LLM or blockchain.

Verification and limitations are recorded in `docs/DEVELOPMENT_RECEIPT.md`.


## 0.2.0 - 2026-09-20 - Batch 2

Preserved the Batch 1 analytical contracts. Added source registry, category observation storage, CSV preview/ingestion with audit quarantine, deterministic quality/normalization, seeded SIMULATED market histories, market snapshots/trends and point-in-time feature generation with publication cutoffs and bounded filling. Added the Market Intelligence workspace, catalog, import workflow, feature export and context panels in existing shipment views. Extended tests and data/source documentation. No external feeds or forecasting implemented. See docs/BATCH_2_RECEIPT.md for results and limitations.


## 0.3.0 - 2026-09-20 - Batch 3

Added point-in-time freight forecasting, three baselines, Ridge and quantile gradient boosting, chronological calibration/selection/final-test evaluation, audited expanding-origin backtests, per-horizon quantiles/metrics/selection, versioned artifacts and forecasting APIs. Added Freight Forecast UI, historical-vs-forecast chart, performance/association panels and saved outlook integrations. Preserved Batch 1/2 contracts and tests. Added scikit-learn with locked transitive dependencies. No Batch 4 charter decision. See docs/BATCH_3_RECEIPT.md.


## 0.4.0 - 2026-09-27 - Phase 4 / core prototype feature freeze

Added CharterTimingService consuming saved Phase 3 forecasts without retraining, explicit daily-hire/index-proxy mapping, both-port congestion integration, hard buffered arrival gates, daily candidate costing, waiting storage, disclosed demurrage, aligned-scenario regret, deterministic risk profiles and contiguous charter windows. Added flagship Charter decision UI and immutable Decision history. Four seeded scenario presets use real Phase 3 training on explicitly synthetic histories. Existing analytical engines and model-selection methodology remain unchanged.

Validation: 112 backend tests, four browser workflows, lint, TypeScript and production build passed. Visual desktop/mobile review completed. See docs/PHASE_4_RECEIPT.md. Core prototype feature freeze; no Phase 5 started.
