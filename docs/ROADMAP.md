# Roadmap

**CORE PROTOTYPE FEATURE FREEZE ? Phase 4 complete (2026-09-27).**

## Implemented prototype

1. **Phase 1: Logistics decision engine.** Shipment, both-port/vessel feasibility, sequential voyages, six-component cost comparison and explainable vessel recommendation.
2. **Phase 2: Market and operational intelligence.** Source registry, simulated and imported histories, quality/provenance, publication-gated snapshots and feature datasets.
3. **Phase 3: Probabilistic freight forecasts.** Five model families, chronological calibration/selection/test, 1/3/7/14-day P10/P50/P90, saved artifacts and inspectable performance.
4. **Phase 4: Charter timing decision support.** Every safe daily candidate, deadline gate, shipment-level cost scenarios, downside/regret, deterministic procurement profiles, charter windows, explanations, automatic deadline sensitivity, saved audit/history and four seeded demonstrations.

Validation: 112 backend tests, four browser workflows, frontend lint, TypeScript and production build passed. Desktop and narrow-screen charter views were visually inspected. See PHASE_4_RECEIPT.md for calculations, performance and limitations.

The functional prototype is frozen. No Phase 5 or other major functionality has been started. Corrections within this scope remain possible if needed.

## Future work ? not implemented

- Authorized/licensed real freight histories and live feeds, stronger chronological calibration studies and commercial validation.
- Actual vessel availability, AIS, official port APIs and weather/disruption feeds.
- Executable charter quotes, validated index-to-hire relationships and contractual laytime/demurrage.
- Inventory/stockout economics, enterprise ERP integrations, contract and portfolio optimization.
- General disruption simulation and extended reporting/export.
- Optional procurement assistant, only with separately approved scope and validated calculation boundaries.

These are future possibilities, not connected capabilities or promises. No authentication, chatbot/LLM, blockchain, AIS or unrelated integration was added. Current outputs remain prototype recommendations with explicit simulated data and assumed operational references; not guaranteed savings, real-world optimal dates or production readiness.
