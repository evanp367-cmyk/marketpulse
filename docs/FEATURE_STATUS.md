# Feature status — MarketPulse 0.3.0

Status below distinguishes code that exists from functionality verified against live third-party services. Provider availability and commercial data rights must be checked from the deployment environment before public release.

## Implemented and locally testable
- FastAPI backend with health endpoint and OpenAPI docs.
- SQLite/PostgreSQL URL configuration and SQLAlchemy models for user, watchlist, portfolio positions and alert rules.
- Server-side Telegram Mini App `initData` HMAC/auth-date validation and explicitly gated development browser identity.
- Binance Spot public REST ticker and historical candle endpoints; no bundled fake prices.
- SMA, EMA, RSI, MACD, Bollinger Bands and ATR calculations with unit tests.
- React/TypeScript terminal shell, market list, selected crypto chart, language and theme controls.
- Manual crypto portfolio UI: add/delete positions, current market value, cost basis and unrealized P/L for positions with an entry price. Values are calculated from current Binance Spot prices and grouped by quote asset.
- Bank of Russia daily XML parser with normalization of `Value / Nominal` and parser tests.
- Frankfurter v2 response parser with ISO code normalization, date/source metadata, explicit missing-quote reporting, and parser tests.

## Implemented but requires external connectivity/configuration
- `GET /api/fx/cbr/daily`: official daily Bank of Russia rates for available currencies. Not real-time Forex.
- `GET /api/fx/world/daily`: daily reference/cross rates from Frankfurter v2, no API key required by the provider documentation. The source may not return every requested pair; unavailable pairs are reported, not synthesized.
- Currency interface with a source switch between Frankfurter world reference rates and Bank of Russia official daily rates; base-currency selection for the Frankfurter view; rate date, source, stale-cache warning, and RU/EN labels.
- Binance public REST calls require network access. Live third-party connectivity from the target machine should be checked by the developer.
- Telegram bot `/start` requires a BotFather token; production Mini App auth requires launching through Telegram with a real bot token.
- PostgreSQL requires a reachable instance and a configured `DATABASE_URL`.

## Planned, unavailable, or blocked pending verification
- True streaming Forex and executable bid/ask quotes; daily reference rates must not be labelled realtime.
- Public/commercial redistribution rights for currency sources and Binance market data; verify current terms before launch.
- Alert evaluator, background polling, durable delivery/retries and firing history. Alert records can currently be saved but are not evaluated or delivered.
- Portfolio trade ledger, realized P/L, fees, tax lots, historic portfolio value chart, fiat conversion across quote currencies, and exchange account sync. Current release values manual spot positions only and has no transaction history.
- News, economic calendar, and AI sentiment: no verified source/model wired in this milestone.
- Production rate limiting, structured monitoring, comprehensive migrations and deployment hardening.
- Subscription billing and exchange account sync.

## Validation status for this bundle
- Backend unit tests: 22 passed after the portfolio valuation implementation.
- Frontend production build in this build container: not yet verified because the container has no `node_modules`; install frontend dependencies and run `npm run build` to confirm. The user successfully built the earlier 0.2.0 frontend on their Mac; this does not confirm the new portfolio screen until they rebuild it locally.
- Frontend production build: not verified in the build environment because npm dependencies were not present and npm installation timed out. Run `npm install` then `npm run build` on the Mac before publishing.
- Live Frankfurter and CBR fetches: must be confirmed from the developer's Mac/network; unit tests do not prove upstream connectivity.
