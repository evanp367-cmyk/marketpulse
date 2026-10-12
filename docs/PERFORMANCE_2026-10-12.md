# MarketPulse performance pass — 2026-10-12

This pass changes only the market-data adapter and frontend startup path. It does not change production settings, Docker volumes, database schema, or alert delivery.

## Measurements

Read-only requests to the deployed API before this change showed `/health` around 0.84 s, one BTC ticker around 1.95 s, 180 BTC candles around 1.62 s, and the full ticker list around 3.65 s / 630,661 response bytes. Three mobile Chromium visits to the deployed GitHub Pages site showed first market rows after 2.9, 7.4, and 10.6 s. These are network-dependent observations, not service-level targets.

The original production build put the chart and the rest of the app in one 402.61 kB JS file (126.63 kB gzip). The new build has a 238.08 kB entry (73.71 kB gzip) and a 167.49 kB chart chunk (54.06 kB gzip) loaded only on the home screen. Direct entry to `#markets` fetched only the entry chunk in mobile Chromium.

With the new code and a local API, the first market row appeared after 1.7 s and a second navigation in the same tab after 0.33 s; the second visit made zero market API calls. Local and deployed timings are not directly comparable because their networks differ. The second visit shows a labelled saved snapshot, which can be refreshed explicitly. A snapshot older than 30 s is also labelled, and failed chart refreshes label cached candles.

## Why these changes

The Binance public 24-hour ticker `type=MINI` response has the price, opening price, and quote volume used by the UI while roughly halving the upstream payload in a direct sample (about 1.0 MB versus 1.9 MB). The adapter derives percentage change from `openPrice` and `lastPrice`, validates the values, and keeps its 15-second shared snapshot. It now reuses one bounded HTTP client per API process, saving repeated connection setup. The frontend reuses short-lived ticker and candle data in `sessionStorage` when the user reopens the app; older cached data remains visible with its timestamp while it refreshes. Existing independent market requests remain parallel. The full ticker list still comes from one shared API snapshot, rather than one Binance request per browser user.

The public Binance Spot WebSocket test from this cloud environment was rejected by the environment's HTTP proxy (403), so it cannot establish reachability from the REG.RU VPS. A WebSocket would still need an initial REST snapshot, a single shared upstream connection, fan-out, reconnect/backoff, and freshness handling. For the measured startup bottleneck, the smaller REST response and connection reuse are a lower-cost improvement. REST remains the supported path; no price is presented as live solely because it came from a saved snapshot. A shared stream can be evaluated later after measuring VPS-to-Binance WebSocket access and active-user load.

## Server review and limits

The repository uses one FastAPI API container, one bot container, PostgreSQL 16, and Caddy 2. Caddy already enables zstd/gzip. The new HTTP client pool is capped at 20 connections with 10 keepalive connections per API process. No additional service is required. This review used repository configuration and public endpoints; it did not inspect current VPS CPU, memory, database metrics, Docker state, or private configuration. No production commands were run.

Validation: `npm run build`, `python -m pytest -q backend/tests` (75 passed), and mobile Chromium first/repeat/direct-Markets navigation against the local production build.
