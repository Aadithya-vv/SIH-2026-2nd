# Batch 1 development receipt

Date: 2026-09-20. Built from an empty workspace; Git repository initialized. No existing application files were modified. All source, configuration and documentation files were created in this batch.

## Files created

- Backend: `app/domain/models.py`, `core/assumptions.py`, `data/reference.py`, `feasibility/engine.py`, `voyage/engine.py`, `costing/engine.py`, `optimization/vessel.py`, `audit/service.py`, `persistence/sqlite.py`, `api/routes.py`, `main.py`, `app/__init__.py`.
- Future interfaces: `forecasting/interfaces.py`, `optimization/timing.py`, `scenarios/interfaces.py`.
- Backend validation/setup: `tests/test_engine.py`, `pytest.ini`, `requirements.txt`, `requirements-lock.txt`.
- Frontend: `src/App.tsx`, `src/main.tsx`, `src/api/client.ts`, `src/types/index.ts`, `src/components/CostChart.tsx`, `src/styles/app.css`, `index.html`, `package.json`, `package-lock.json`, `tsconfig.json`, `vite.config.ts`, `eslint.config.js`, `playwright.config.ts`, `e2e/analysis.spec.ts`.
- Data/docs: `data/demo/reference.json`, `data/reference/README.md`, root `README.md`, `.gitignore`, `CHANGELOG.md`, and architecture, assumptions, provenance, roadmap and this receipt in `docs/`.
- Generated and ignored: virtual environment, dependencies, production build, test screenshots and local SQLite analysis snapshots.

## Architecture implemented

Validated shipment -> replaceable reference adapter -> both-port feasibility -> sequential voyage schedule -> explicit USD costs -> constrained minimum-cost selection -> FastAPI -> React. SQLite stores analytical snapshots. Every important input/output has record-level or output-level provenance. Full selected port references, vessel records, assumptions, route distances and submitted fields survive in the result.

## Demo data and assumptions

Nine illustrative ports, four vessel-class references and 18 explicit route distances. USD 600/tonne bunker price; 25,000/20,000 tonnes/day loading/unloading; one waiting allowance day per delivery; excess delay charged at 80% daily hire, excluded from charter hire. Sequential returns between deliveries, immediate departure at origin, fixed reference draft, zero storage/lighterage. Exact values are centralized and exposed in the application.

## API endpoints

- GET `/health`
- GET `/api/reference/ports`
- GET `/api/reference/vessels`
- POST `/api/feasibility/check`
- POST `/api/voyage/estimate`
- POST `/api/cost/estimate`
- POST `/api/optimizer/vessel`
- POST `/api/shipments/analyze`

## Verification

- Backend: **28 pytest cases passed**. Covers individual dimensional constraints, origin restrictions, equality boundaries, unsupported cargo, multiple deliveries, return passage, arrival rounding, cost sum, demurrage/no-demurrage, cheapest eligible selection, deadline-driven vessel change, no eligible option, deterministic output, provenance, API validation, stage endpoints and SQLite round-trip.
- Frontend lint: **passed**.
- TypeScript validation: **passed**.
- Vite production build: **passed**, chart vendor bundle separated from application bundle.
- Chrome browser smoke assertions: **passed** against real FastAPI and Vite servers. Submitted a shipment, rendered recommendation/costs, inspected Capesize draft rejection, navigated the control center, detected edited inputs and analyzed Haldia with no feasible result. No browser page errors. Screenshot inspected at desktop size.
- Two dependency deprecation warnings remain in the FastAPI/Starlette testing stack; they do not fail tests. Node reports a harmless color-environment warning during browser execution.

## Known limitations

Prototype estimates, not operational advice. Port and vessel values are unverified class-level assumptions. No tide, under-keel clearance, berth specifics, stowage factors, positioning, availability, weather, commercial charter-party settlement, port fuel, canal tolls, insurance, taxes, inland logistics or commodity purchase costs. No uncertainty distribution, numerical accuracy claim, forecast, charter-timing advice or live feed. Optional inventory/cargo value is retained but not used in optimization. History browsing and reports are planned; snapshots are persisted locally. Layout inspected on desktop; extensive cross-browser/accessibility testing is future work.

## What is real, derived, assumed or simulated

- **Real:** runnable engines, validation, REST communication, UI interaction, SQLite storage and tests.
- **Derived:** capacity voyage counts, dimensional margins, voyage times, deadline status, six cost components, cost per tonne and vessel selection.
- **Assumed:** all reference port/vessel/route/rate data, immediate availability, scheduling and cost constants. USER_INPUT identifies the submitted shipment separately.
- **Simulated:** no stochastic simulator or market feed is implemented. DEMO_REFERENCE is explicitly ASSUMED, not measured live data.

## Exact next recommended batch

**Batch 2: Freight / Commodity Data Ingestion.** Establish vetted source and license registers; implement real-data adapters and official port/terminal reference ingestion; add units, timestamps, validation, missing/stale-data handling and immutable source snapshots. Preserve explicit separation from demo mode. Forecasting follows in Batch 3 after usable historical data exists.
