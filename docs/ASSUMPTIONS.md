# Demo assumptions

Every reference value in `data/demo/reference.json` is **DEMO_REFERENCE / ASSUMED**, effective 2026-09-01. No public source or port authority has verified these numbers. Exact port dimensions, waiting durations, costs, route distances and vessel characteristics are centralized there. The cost/time constants are centralized in `backend/app/core/assumptions.py` and returned in every analysis.

| Input | Assumption |
|---|---|
| Currency | USD throughout; no implicit INR conversion |
| Bunker price | USD 600 / tonne |
| Loading | 25,000 cargo tonnes / day |
| Unloading | 20,000 cargo tonnes / day |
| Waiting allowance | 1 day per delivery across both ports |
| Excess waiting | Sum of both ports' waiting assumptions minus allowance, floored at zero |
| Demurrage | Excess waiting days x daily hire x 0.8 |
| Charter | (Total days minus excess waiting) x daily hire |
| Bunker | (Outbound + return sea days) x class fuel tonnes/day x bunker price |
| Port cost | Sum of origin/destination reference costs x delivery count |
| Lighterage and storage | USD 0; not used to override a failed port check |
| Commodity price / cargo value | Excluded from logistics cost; optional cargo value retains its own submitted currency |
| Inventory | Optional inputs retained but not used in Batch 1 |
| Start | Analysis date at UTC day boundary; immediate availability at origin |
| Multi-voyage scheduling | One vessel, sequential delivery, same-speed return between deliveries; no final return |
| Arrival date | Start + ceiling(total elapsed days); equality with deadline passes |
| Distance | Explicit illustrative sea-route lookup, not geographic straight-line routing |
| Sea days | Distance nautical miles / (speed knots x 24) per leg |
| Draft | Full class reference draft even with partial cargo; no draft/load interpolation |
| Capacity | Usable cargo tonnage, below DWT; hold volume/stowage factor not modelled |

Cost components round to USD cents using decimal half-up; total is the exact sum of rounded components; cost/tonne rounds separately. USD/t times quantity can therefore differ slightly from the total. Time remains unrounded internally.

Port waiting is an assumed delay, not observed congestion or a probabilistic expected value. Dimensional PASS is only a pass against the demo table. Actual operations require official port circulars, berth-specific limits, tides, under-keel clearance and vessel-specific particulars. No lighterage, weather, bunker consumption in port, ballast optimization, positioning leg, canal tolls, taxes, insurance or inland logistics is included. Charter-plus-demurrage is a simplified mutually exclusive time-cost model, not a commercial charter-party settlement model.

There is no numerical confidence or accuracy claim. Every recommendation is DEMO_ESTIMATE_NOT_VALIDATED. No uncertainty distribution has been fitted.


## Batch 2 assumptions (separate from cost estimates)

Demo market values are SIMULATED, unlike Batch 1 ASSUMED references. Generator configuration, fixed date range and limitations are documented in DATA_SOURCES.md. Source records never imply a connected feed. All values retain original currency; only documented physical unit conversions occur.

Freshness uses max(7 days, twice declared frequency). Missing periods use calendar days and do not infer weekends/holidays. USER_IMPORT publication times are user assertions; absent publication means ingestion-time availability. Daily features evaluate at UTC day end or cutoff with a default maximum 3-day predictor fill; target values are not carried across days. Coarse June-September monsoon flags indicate calendar season only; holiday flags remain unavailable. None of these rules change the Batch 1 voyage/cost assumptions.

Snapshot commodity benchmarks may be regional proxies; Singapore VLSFO is a fixed representative hub, not a calculated optimal bunker stop. See DATA_DICTIONARY.md for precise rules and units. Non-negative import validation is a prototype contract; if a legitimate provider uses negative index conventions, implement and document that source's semantics rather than coercing its data.
