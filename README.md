# Freight Intelligence Platform

**CORE PROTOTYPE FEATURE FREEZE ? Phases 1?4 implemented and validated.**

Maritime procurement decision support for dry-bulk shipments, covering Phases 1?4. Define cargo, quantity, origin, destination and arrival deadline; compare four vessel classes using explainable port, voyage and USD logistics calculations.

**Batch 1 costs use DEMO_REFERENCE assumptions. Batch 2 market data is explicitly SIMULATED or USER_IMPORT. Batch 3 forecasts retain those source labels. Phase 4 adds auditable, uncertainty-aware charter timing under explicit assumptions. No external feeds are connected. This is a prototype, not validated for operational chartering.**

## Run locally (Windows PowerShell)

Requires Python 3.13+ and Node.js 22.12+ (verified with Python 3.13 and Node 24).

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend\requirements-lock.txt
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal, from the repository root:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev -- --host 127.0.0.1
```

Open http://127.0.0.1:5173. API documentation: http://127.0.0.1:8000/docs. Vite proxies `/api` and `/health` to port 8000; the browser makes real REST requests. Analyze the prefilled shipment to populate results and the control center. Haldia demonstrates a no-feasible-option outcome. Select `Why?` to inspect both ports and capacity checks.

## Verify

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest -q
cd ..\frontend
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run build
npm.cmd run test:e2e
```

The browser smoke test uses locally installed Google Chrome and starts isolated backend/frontend servers on ports 8100/5174 and uses data/e2e-market.sqlite3; the normal app can remain running. It verifies real API submission, constraint explanations, navigation, stale-input messaging and the no-feasible-option state.

## Implemented scope

- Typed shipment/reference/result models with reusable provenance metadata.
- Both-port draft, LOA, beam and cargo support checks; sequential voyage counts for excess cargo.
- Reference maritime-route distances, explicit sea/return/loading/unloading/waiting time.
- Six visible USD cost components and per-tonne costs.
- Cheapest deadline-compliant and port-compatible option; deterministic tie-breaks.
- Working voyage optimizer, port/vessel matrix and control center; charter decisions and saved decision history; future-work states for scenarios and portfolio.
- SQLite JSON snapshots saved on flagship analysis/optimizer requests in `data/analyses.sqlite3`. Phase 4 charter snapshots share this database and can be browsed in Decision history.
- Protocols for reference adapters, future forecasting, timing and scenarios. No LLM.
- Batch 2 Market Intelligence: source registry, 15 seeded SIMULATED histories, CSV imports, quality reports, catalog, snapshots, descriptive trends and point-in-time feature exports.

## API

`GET /health`, `GET /api/reference/ports`, `GET /api/reference/vessels`.

All POST endpoints accept the same ShipmentRequirement JSON:
`/api/feasibility/check`, `/api/voyage/estimate`, `/api/cost/estimate`, `/api/optimizer/vessel`, `/api/shipments/analyze`.
The first three return named vessel results; the last two return the complete analysis and save a snapshot. See generated OpenAPI schemas at `/docs`. Bad inputs, unknown routes/countries and past deadlines return 422.

## Limits

Demo class dimensions are not vessel particulars. Demo port limits are not official terminal restrictions. No tides, under-keel clearance, cargo stowage/hold-volume constraints, vessel positioning, charter availability, weather, canal charges, port fuel, commercial laytime contracts, taxes, insurance, inland transport or commodity purchase costs are modelled. Immediate departure from origin is assumed. Partial loads retain the class reference draft conservatively. One vessel performs sequential deliveries and returns between them. Arrival rounds duration upward to whole days; Phase 4 adds a configurable schedule buffer. No FX conversion is performed.

The production build is static output in `frontend/dist`; deployment requires a same-origin reverse proxy for `/api` and `/health`. The Vite development proxy does not configure a production server.

See [architecture](docs/ARCHITECTURE.md), [assumptions](docs/ASSUMPTIONS.md), [provenance](docs/DATA_PROVENANCE.md), [roadmap](docs/ROADMAP.md), and [development receipt](docs/DEVELOPMENT_RECEIPT.md).


## Batch 2 workflow

Open **Market intelligence**. History shows source labels, date filters, quality and descriptive statistics; Data catalog lists all datasets plus unavailable source entries. Demo seeding occurs on the first market API request and is idempotent. The fixed historical demo window can be stale; this is shown rather than hidden.

In **Import data**, choose category, file (or paste CSV), source/series names, column mapping, original unit/currency and relevant metadata. Validate, review accepted/rejected rows and warnings, then ingest. Publication time is optional but crucial: without it, data is only knowable from ingestion onward. An authorized user-supplied historical publication column remains an unverified assertion. A small illustrative CSV template is in `data/demo/import-template.csv`; it is not real market data.

In **Feature dataset**, select a freight target and predictors, dates, UTC cutoff and fill limit. Build and export JSON with per-cell lineage. Missing or too-old values remain null. Demo inputs are marked DEMO_ONLY. Forecasting is available separately in the Batch 3 workspace.

Market context on the Voyage Optimizer and Control Center comes from the backend. It does not replace Batch 1 fuel, charter or waiting assumptions. Weather integration and holidays remain unavailable.

Batch 2 endpoints: GET `/api/data/sources`, `/api/data/catalog`, `/api/data/series`, `/api/data/series/{id}`, `/api/data/series/{id}/quality`, `/api/market/snapshot`, `/api/market/trends`; POST `/api/data/import/csv`, `/api/features/build`. CSV is sent as JSON text plus mappings, avoiding a separate upload dependency. See `/docs` for schemas.

Market SQLite storage defaults to `data/market.sqlite3`; override with FIP_MARKET_DB. Original analysis snapshots remain in `data/analyses.sqlite3`. Source models, quality thresholds, unit rules, snapshot selection and leakage protections are documented in [data sources](docs/DATA_SOURCES.md), [data dictionary](docs/DATA_DICTIONARY.md) and [Batch 2 receipt](docs/BATCH_2_RECEIPT.md).

No new runtime technology or dependency was introduced in Batch 2. The existing NumPy dependency powers deterministic demo generation and descriptive statistics.


## Batch 3 workflow

Open **Freight forecast**, select a daily freight series, optional context and an explicit UTC as-of day; click **Train & evaluate**. Requires 250 complete daily feature rows and historical publication evidence. Demo data ends 2026-08-31, so the preselected date is a historical replay, not today. Training compares three baselines, Ridge and quantile boosting at 1/3/7/14-day horizons and may take a minute. No model runs automatically in the background.

Inspect P10/P50/P90, per-horizon validation/test metrics and **Out-of-sample backtest**. Baselines may win. Poor coverage stays visible. Market indexes retain index_points; there is no conversion into charter costs. Optional contextual features are selected explicitly and retained in model metadata. Saved forecasts appear in shipment outlook panels with their original as-of date. Charter timing is implemented in Phase 4 and consumes saved forecasts without retraining.

Artifacts live in `artifacts/freight/<model_id>/` (ignored by Git); override via FIP_ARTIFACT_DIR. Model metadata, selected estimators, full feature/label lineage and every backtest record are stored together. Training and forecast API endpoints are documented in [FORECASTING.md](docs/FORECASTING.md). See [model card](docs/MODEL_CARD.md) and [Batch 3 receipt](docs/BATCH_3_RECEIPT.md) for the actual simulated evaluation and limitations.

Install the updated backend requirements-lock.txt before running Batch 3; scikit-learn is the only new direct dependency. Browser tests use isolated ports and `artifacts/e2e-freight`.


## Phase 4 ? Charter decision

Open **Charter decision**. Select a saved forecast and its exact historical origin, shipment, vessel, arrival deadline, buffer and procurement profile. USD/day forecasts are consumed directly; index forecasts require explicit consent for an assumed ratio to daily hire. No implicit index-to-dollar or FX conversion occurs. Optional storage and demurrage rates remain visible; missing costs are not fabricated.

Click **Analyze charter timing**. Every safe integer wait day is evaluated with P10/P50/P90 shipment costs, schedule slack, downside and scenario regret. WAIT always includes a contiguous charter window. Deadline/buffer edits automatically recalculate after the first analysis. Missing or incompatible forecasts produce INSUFFICIENT DATA; impossible shipments produce NO SAFE WAIT WINDOW. Open **Decision history** to reconstruct saved evidence.

For the reproducible demonstration, click **Prepare seeded demo forecasts** once (about a minute or two on a fresh installation). This explicitly seeds two SIMULATED USD/day histories and runs Phase 3 training; charter analyses themselves never train. Presets A?D demonstrate wait opportunity, deadline-driven lock, uncertainty-driven lock and missing forecast. These are historical scenarios at 2026-08-31, not current markets.

New API: POST `/api/charter/analyze`; GET `/api/charter/history`, `/api/charter/{analysis_id}`, `/api/charter/{analysis_id}/explanation`, `/api/charter/demos`; POST `/api/charter/demos/prepare`. Compare results are included in analyze. Optional FIP_ANALYSIS_DB isolates charter history. No new dependencies.

See [charter timing calculations](docs/CHARTER_TIMING.md), [end-to-end flow](docs/END_TO_END_FLOW.md) and [Phase 4 receipt](docs/PHASE_4_RECEIPT.md). The scope ends at Phase 4; future integrations and additional major features remain outside this prototype.
