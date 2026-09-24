# Data source register

Batch 2 connects **no external market feed**. The registry is API-readable at `/api/data/sources`; it contains implemented demo/import sources and clearly unavailable candidates. A source entry is not evidence of data possession.

| Category | Needed / why | Current source | Access / frequency / units | Limits and replacement plan |
|---|---|---|---|---|
| Freight | Vessel index and route hire/rate history for future targets and features | Five seeded DEMO dry-bulk/class indices; CSV imports | DEMO daily index_points; USER_IMPORT declared calendar-day frequency and index_points, currency/day or currency/tonne | No actual BDI/BCI/BPI/BSI data. Obtain a suitable licensed source or user-supplied authorized archive; preserve publication/revision timestamps. |
| Commodity | Coking coal, thermal coal, iron ore benchmark history | Three explicitly DEMO Australian reference series; CSV imports | DEMO daily USD/tonne; import original currency | No Newcastle/API2/Indonesian benchmark entitlement claimed. Benchmark, cargo and origin metadata are retained for replacements. |
| Bunker | Fuel-cost environment at bunkering hubs | DEMO_VLSFO_SINGAPORE; CSV imports supporting VLSFO/MGO and any named hub | DEMO daily USD/tonne; imported currency/tonne | Singapore is an explicit representative hub, not an optimized bunkering decision. Fujairah/Rotterdam can be imported but have no bundled observations. |
| Port | Waiting and congestion history relevant to destination | Six DEMO Indian-port waiting-day series; CSV imports | DEMO daily waiting days | Not AIS or port authority observations. Obtain official terminal/port observations, berth and coverage definitions. |
| Weather | Wind, waves, cyclone and route disruption inputs for later scenarios | Typed interface and empty relational table only | SOURCE_NOT_CONNECTED; knots/metres/flags | PUBLIC_API is a candidate access type, not an implemented integration. Select provider, terms, latency and geographic coverage first. |
| Calendar | Deterministic alignment features | Derived from UTC row dates | DERIVED daily | Weekday/month/quarter and coarse June-September Indian monsoon flag. No holiday source: holiday indicator remains null. |

## Licensing and source honesty

Baltic Exchange describes different license/subscription structures for its market data. This application's Baltic registry entry remains COMMERCIAL_FEED_REQUIRED because no entitlement or dataset is configured. See the provider's [Market Data access information](https://www.balticexchange.com/en/data-services/Methodology/market-data.html) and [indices descriptions](https://www.balticexchange.com/en/data-services/market-information0/indices.html), reviewed 2026-09-20. No scraping or restricted-data access is implemented.

Other commercial entries are unconfigured candidates, not an assertion that every possible dataset requires payment. User imports are not independently authenticated or licensed by this application. Their provider name is user supplied and is displayed with USER_IMPORT provenance, never PUBLIC_SOURCE.

## Demo generator

`backend/app/market/adapters.py`: fixed seed 26054 plus stable series index; NumPy default_rng; 365 daily observations from 2025-09-01 through 2026-08-31. Each series uses a base level, annual sinusoid, autoregressive noise (0.86 persistence), and a decaying shock during days 170-220. Values are floored at 5% of their base and rounded to four decimals. Publication at 18:00 UTC is simulated. Source names begin DEMO; provenance is SIMULATED. No generator parameters were fitted to make a future model appear accurate. This dataset cannot measure real-world forecasting skill.

Restarting the app does not shift dates or regenerate a newer window. SQLite seeding is idempotent. Old observations become STALE according to the ordinary rules. Last ingestion is a local ingestion timestamp, not a claim that the provider refreshed prices.

## Import availability

A mapped publication/availability column is an explicit, unverified user assertion. It must be at or after the observation and no later than ingestion. Without it, availability equals ingestion time; historical values therefore remain missing from earlier point-in-time feature rows. For serious backtesting, obtain historical publication/revision evidence. Existing imports are immutable snapshots; there is no automatic concatenation across separately uploaded files.


## Batch 3 usage

Forecasting consumes these existing sources; it does not add external feeds. The reference demonstration uses the simulated Panamax target and simulated broad dry-bulk, VLSFO, coking-coal and Paradip contexts. Source quality/availability constraints are retained. No simulated evaluation may be described as Baltic Exchange forecast accuracy.
