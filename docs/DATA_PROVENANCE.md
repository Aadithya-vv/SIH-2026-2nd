# Data provenance

The reusable ProvenanceMetadata model supports USER_INPUT, PUBLIC_SOURCE, HISTORICAL, DERIVED, FORECAST, ASSUMED and SIMULATED. Each record includes source name, effective date, optional retrieved_at and notes. No external retrieval occurred, so retrieved_at is null for bundled demo references.

- Shipment fields: USER_INPUT, effective analysis date. The prefilled UI is an editable example and becomes the submitted requirement only when analyzed.
- Ports, vessel classes, route distances and cost/time assumptions: ASSUMED, named DEMO_REFERENCE v1. Record-level metadata applies to every numeric field. Route records include the same metadata; the analysis embeds route and port lineage at its top level. Full selected port records and vessel records are embedded in the snapshot; the exact route distance is retained in every voyage estimate.
- Feasibility, voyage, costs and recommendation: DERIVED, linked through the saved shipment, reference identity, embedded assumptions and source metadata. Each voyage and cost result carries provenance directly.
- Analysis date: DERIVED from server UTC clock; pure analysis accepts it explicitly for repeatability.
- PUBLIC_SOURCE, HISTORICAL, FORECAST and SIMULATED are reserved categories; none are claimed for current outputs. Demo does not imply measured or randomly simulated market data.

References are assumed inputs. The execution engines and API are real software. All recommendation numbers are calculated from those inputs, not hardcoded display values. No accuracy percentage, live-feed badge or fake charter timing is displayed.

Reference effective dates identify the version, not freshness. An adapter for real data must carry actual source attribution, retrieval time, effective time, units and licensing constraints; it must never silently fall back to demo values. Batch 2 must add source validation/staleness rules and immutable source snapshots/version hashes before operational use.


## Batch 2 additions

USER_IMPORT is an additive source type; all previous enum values remain valid. SIMULATED now applies to seeded market observations, and DERIVED to quality/trends/features. No PUBLIC_SOURCE or licensed historical feed has been ingested. Previous statements about unused SIMULATED apply only to Batch 1.

Each series retains reusable ProvenanceMetadata; observations inherit it and retain timestamp, available_at, original value/unit/currency, normalized value and flags. Import records keep exact CSV, mappings, payload hash and ingestion timestamp. Raw rejected rows are quarantined, not erased. Record-level lineage appears in charts/catalog/context, and feature exports include cell-level source times/transformations. Immutable imports keep revisions separate.

Observation date, publication availability and ingestion time are distinct. A user assertion of past publication is not independently verified. Missing availability defaults conservatively to ingestion time. No real-world forecast accuracy or licensed data access may be inferred from successful feature export.


## Batch 3 forecast provenance

FORECAST identifies model outputs. Input source types remain SIMULATED/USER_IMPORT/etc. Metadata retains complete source-series provenance, dataset hash, feature transformations, model/library version, seed, hyperparameters, training cutoff and evaluation period. Feature rows retain availability lineage; backtest records retain forecast origin, target date, actual publication time and maximum training feature/label times. Simulated inputs force the label SIMULATED DATA BACKTEST even when mixed with imports. Historical forecasts are anchored to their recorded as-of, not the current clock.


## Phase 4 decision provenance

Charter decisions are DERIVED; evidence embeds original shipment, reference assumptions, complete forecast, model version/cutoff, market source/publication times and exact candidate calculations. Both-port waiting observations replace reference assumptions only when fresh, compatible and unflagged. Otherwise a visible ASSUMED_REFERENCE_FALLBACK is used with an unavailable/stale status; missing congestion is never invented as a current observation.

USD/day targets retain currency and unit. An explicitly consented index ratio is ASSUMED (or user-anchored), not a foreign exchange conversion. Storage and contractual demurrage inputs are USER_INPUT; default demurrage is an ASSUMED fixed fraction of current hire. Missing stockout/storage economics are NOT MODELLED or UNQUANTIFIED. Historical forecasts generated after their origin are replay calculations, not evidence they were available then. Demo reference versions are assumptions even when their effective date follows a replay origin.

Two Phase 4 demo histories use fixed seeds 26054/26055 and are labelled SIMULATED in the Phase 2 registry and every downstream forecast. Real Phase 3 training generates their predictions; no forecasts, scores, savings or decisions are hardcoded. Synthetic demonstration performance must not be presented as market skill. See CHARTER_TIMING.md for exact generator and cost mapping.
