# Phase 4 baseline

2026-09-26: inspected repository inventory, Phase 1–3 API routes, domain models, feasibility, voyage, cost, snapshot, forecast and persistence services, frontend navigation and required architecture/data/model receipts. Working tree clean on master at f44501a.

Before edits: 79 backend tests passed (61.95 s; two upstream Starlette deprecation warnings). Frontend lint, TypeScript and production build passed.

Compatibility constraints: one vessel performs sequential deliveries and return legs; Phase 1 arrival rounds elapsed days upward; waiting charged as demurrage is excluded from hire. Market congestion is destination-specific, historical and provenance-bearing. Bundled freight targets use index_points, which cannot silently become USD/day. Forecast models are explicitly trained and saved; timing must consume metadata without retraining. Existing analysis snapshots use SQLite; history browsing was a placeholder.
