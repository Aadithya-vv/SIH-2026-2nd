# End-to-end prototype flow

1. Submit ShipmentRequirement (cargo, tonnes, origin/destination, arrival date) plus selected vessel, saved forecast origin and procurement preferences.
2. Phase 1 checks both ports, cargo support and capacity; calculates sequential delivery count, route sea days, return passages and total handling days. Failed vessel checks cannot be overridden by low cost.
3. Phase 2 loads publication-gated market snapshots at analysis_as_of. Exact-port fresh waiting observations replace reference waits; missing/stale data retains a clearly labelled reference assumption.
4. Phase 3 supplies an already saved, origin/vessel/route-compatible probabilistic forecast, model version, cutoff, source, selected models and validation/test metrics. Phase 4 does not fit a model.
5. Phase 4 derives buffered latest-safe date, enumerates daily charter candidates through the available horizon, and rejects unsafe dates before cost optimization.
6. Each candidate uses the existing cost engine at P10/P50/P90 daily hire (or explicitly consented index proxy). Add disclosed demurrage and storage; preserve unquantified waiting consequences.
7. Compare median advantage, P90 downside, residual schedule slack and aligned-scenario regret. Apply deterministic procurement limits and select a day and contiguous eligible window.
8. Return WAIT, LOCK_NOW, NO_SAFE_WAIT_WINDOW or INSUFFICIENT_DATA with calculated reasons. UI displays market basis, hero decision, timeline, cost band, comparison table and assumptions.
9. Save complete immutable evidence alongside existing analysis snapshots. Decision history reopens that exact evidence, without reading a newer market or model.

The automated charter browser workflow runs the real backend, seeded histories, Phase 3 training and Phase 4 calculations. It checks derived cost arithmetic and arrival feasibility; then demonstrates the same falling forecast changing from WAIT to LOCK_NOW when the deadline tightens, automatic deadline/buffer recalculation, uncertainty refusal, missing forecast, infeasible port, audit replay and a narrow viewport. Existing Phase 1–3 browser workflows remain covered.

This is a simulated/reference-based procurement prototype. The full saved pipeline is inspectable; successful software tests are not evidence of real-world savings or forecast accuracy.
