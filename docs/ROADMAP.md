# Roadmap

1. **Batch 1 - Vessel + Port + Voyage + Cost Decision Engine.** Current vertical slice, demo references and deterministic explanations.
2. **Batch 2 - Market & Operational Data Intelligence (implemented).** Replaceable adapters, source/license register, official port/terminal references, route evidence, validation, units, retrieval/effective timestamps, stale/missing-data handling and immutable input snapshots. No silent demo fallback.
3. **Batch 3 - Probabilistic Freight Forecasting.** Historical baselines, time-aware backtests, P10/P50/P90, calibration and model provenance. No invented accuracy.
4. **Batch 4 - Optimal Charter Timing.** Charter today vs expected value of waiting with uncertainty, deadlines, inventory and operational risk.
5. **Batch 5 - Scenario / Disruption Simulation.** Seeded reproducible fuel, freight, congestion, cyclone and inventory changes; baseline comparison.
6. **Batch 6 - Annual Procurement Portfolio Optimization.** Cargo allocation, schedule and budget constraints.
7. **Batch 7 - Decision History + Reports.** Queryable snapshots, comparative audit, export and reporting.
8. **Batch 8 - Context-Aware Procurement Copilot.** Explain validated engine outputs and translate intent; never invent calculations.


Batch 2 delivers source registry, seeded demo/CSV adapters, validation, historical storage, provenance, quality, market context, descriptive trends and point-in-time feature export. External provider feeds remain unconfigured. Next: Batch 3 probabilistic forecasting, starting with vetted histories/publication evidence, naive baselines and chronological splits; evaluate P10/P50/P90 coverage and error honestly. Do not interpret simulated performance as real-world skill.


Batch 3 implemented: naive baselines, Ridge, quantile boosting, chronological calibration/selection/test, walk-forward audit, quantiles, artifacts and forecast UI. Demonstration results are SIMULATED; real-world skill is not established. Batch 4 remains unimplemented and must integrate forecast distributions with operational constraints rather than inferring WAIT from a falling median.
