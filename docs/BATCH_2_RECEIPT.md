# Batch 2 development receipt

## Baseline status

Inspected the existing repository before edits. Baseline: 28 pytest tests passed, lint passed, TypeScript passed, production build passed. See BATCH_2_BASELINE.md. Batch 1 analytical code, endpoints and shipment/result contracts were preserved; USER_IMPORT is the only additive shared enum member. This workspace still contains uncommitted Batch 1 files, so Git's untracked listing is not a Batch 2 diff.

## Files created

- `backend/app/market/__init__.py`, `models.py`, `normalization.py`, `quality.py`, `adapters.py`, `store.py`, `service.py`, `features.py`, `api.py`.
- `backend/tests/test_market.py`.
- `frontend/src/types/market.ts`, `components/MarketContext.tsx`, `components/ImportData.tsx`, `components/FeatureBuilder.tsx`, `pages/MarketIntelligence.tsx`, `frontend/e2e/market.spec.ts`.
- `data/demo/import-template.csv`.
- `docs/BATCH_2_BASELINE.md`, `docs/DATA_SOURCES.md`, `docs/DATA_DICTIONARY.md`, this receipt.

## Files modified

- `backend/app/domain/models.py` (additive provenance enum), `backend/app/main.py` (new router/version).
- `frontend/src/App.tsx` (navigation/context integration), `frontend/src/api/client.ts` (validation messages), `frontend/src/styles/app.css` (matching workspace styles).
- `frontend/vite.config.ts`, `frontend/playwright.config.ts` (isolated browser-test ports and database; normal app defaults preserved).
- README, ARCHITECTURE, ASSUMPTIONS, DATA_PROVENANCE, ROADMAP and CHANGELOG.
- No runtime dependencies added or replaced.

## Database changes

Separate additive market.sqlite3 database, schema version 1. Relational sources and series, individual freight/commodity/bunker/port/weather observation tables, import records, rejected/accepted raw-row audit, quality reports. Indexed series/time/availability and route/port lookups. Foreign keys and atomic idempotent imports. Existing analyses.sqlite3 remains untouched by schema work. A distinct e2e-market.sqlite3 isolates browser fixtures.

## Data sources and demo datasets

Four implemented category demo adapters plus mapped CSV import. Fifteen fixed historical SIMULATED daily series: five dry-bulk/vessel indices, three commodity benchmarks, Singapore VLSFO, six Indian-port waiting histories. Each has 365 observations, 2025-09-01 through 2026-08-31, seed 26054 plus stable series offset. No actual Baltic/commodity exchange/port data is bundled. Source registry exposes unconfigured commercial, bunker, port and weather candidates explicitly.

## Provenance, quality and normalization

Source, effective date, retrieval/ingestion context, original values/units/currency, observation date and publication availability remain traceable. USER_IMPORT is distinct from PUBLIC_SOURCE and SIMULATED. Raw invalid rows are quarantined; duplicates are retained and flagged rather than erased.

Quality covers missing values, duplicate timestamps/publications, invalid/future timestamps, nonnumeric/nonfinite values, negatives, order, unit mismatch, missing periods and staleness. Freshness threshold is max(7 days, twice expected calendar-day interval). Canonical tonne/day/index_points conversions are explicit. No FX conversion. Full rules are in DATA_DICTIONARY.md.

## Market snapshot logic

Filter relevant vessel class/route, cargo benchmark, representative Singapore VLSFO and destination port. Require observation and availability times no later than as_of. Rank freshness, non-demo source, matching origin region and recency deterministically. Return source/provenance/age/context notes for every value; unavailable matches return available=false. Market observations are context only and do not alter Batch 1 estimates.

## Feature dataset schema

Daily rows: date, evaluation_time, freight_target, series-keyed values, calendar fields and per-cell lineage. Metadata includes source records, missing/filled counts, cutoff and transformations. Both observation and availability timestamps must precede each row's evaluation. Latest known revision only; duplicates excluded. Predictor filling is past-only and bounded (default 3 days); target never filled across days. No interpolation/backfill. Missing holidays remain null. SIMULATED inputs yield DEMO_ONLY suitability.

## API endpoints

GET `/api/data/sources`, `/api/data/catalog`, `/api/data/series`, `/api/data/series/{id}`, `/api/data/series/{id}/quality`, `/api/market/snapshot`, `/api/market/trends`.

POST `/api/data/import/csv` for preview/commit with content+mapping fingerprint; POST `/api/features/build` for point-in-time datasets. No Batch 1 endpoint was removed or changed.

## Frontend changes

New Market Intelligence workspace with category/source status, history/date filters, source provenance, quality, descriptive statistics, catalog, unavailable source registry, CSV upload/paste + mapping + preview + ingestion and feature JSON export. Optimizer and Control Center fetch backend market context. Charts explicitly label SIMULATED/USER_IMPORT, exclude duplicates, select latest known revisions and break time gaps. Existing operational visual identity preserved. Shell label now says COST MODE: DEMO because market imports have separate provenance.

## Verification

Backend: 62 tests passed, including all 28 unchanged Batch 1 tests. Browser: 2 tests passed against real FastAPI/Vite services, including the complete upload/preview/ingestion/catalog/feature-export flow and Batch 1 regression. No browser page errors. Desktop screenshots inspected. Frontend lint, TypeScript and production build passed. Two upstream Starlette testing deprecation warnings and Node color-environment notices remain non-failing.

## Known limitations

No connected public or licensed external feed; user source/publication assertions are unverified. Fixed demo histories become stale and cannot establish real forecasting skill. Daily frequency is calendar-based, not a vetted exchange/holiday schedule. Imported datasets remain separate immutable snapshots; no cross-upload merging/deduplication. Optional port auxiliary fields have model/storage contracts but no CSV mappings yet. Weather is a typed future interface/table only. Holiday indicator unavailable. SQLite/local workflows have no auth, quotas, deployment hardening or large-scale ingestion. No forecasting, LSTM, optimal stopping, copilot, AIS or invented accuracy/savings was implemented.

## Data classification

- REAL/PUBLIC: no external observations connected; the functioning APIs, storage and calculations are real software.
- USER IMPORTED: supplied CSVs, with explicit source labels, original units/currency and unverified publication assertions.
- DERIVED: normalization, quality, trends, calendar fields, snapshots selected from stored evidence, and feature alignment/lineage.
- ASSUMED: unchanged Batch 1 cost/port/vessel references; declared frequency, freshness and filling rules are documented modelling assumptions.
- SIMULATED: 15 seeded demonstration histories and their simulated publication schedule.
- CURRENTLY UNAVAILABLE: licensed Baltic/commodity feeds, actual bunker/port sources, weather integration and authoritative holiday calendars.

## Exact next development action

Begin Batch 3 with a reviewed, authorized historical target and predictor dataset plus publication evidence. Freeze a dataset manifest, implement naive baselines and chronological train/validation/test splits, then backtest candidate probabilistic models and report P10/P50/P90 calibration and errors. Do not report simulated backtest performance as real-world accuracy. No Batch 3 model was implemented here.
