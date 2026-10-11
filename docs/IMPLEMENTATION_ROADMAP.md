# MarketPulse implementation roadmap

## Agreed direction
- Binance Spot public market data is the primary crypto quote/candle source for the first release.
- Do not purchase a paid market-data API until product demand or source limitations justify it.
- Preserve the current frontend design; add functionality within the existing layout.
- Do not display fabricated market prices, placeholder news, or pretend alert delivery works when it does not.
- Finish portfolio, then implement/test signals and connect a verified news source; only then harden hosting and add Telegram Mini App monetization.

## Current merged milestone: 0.3.0
- Base: MarketPulse 0.2.0.
- Applied: portfolio 0.3.0 patch.
- Portfolio uses manual Spot positions and Binance Spot prices. Unrealized P/L is only calculated when an entry price is entered. Totals are grouped by quote asset, not incorrectly added across currencies.
- Backend tests: `python -m pytest -q` — 22 passed in this build environment.
- Frontend production build is not verified here because dependencies are not installed in this environment. Run `npm install` and `npm run build` on the development Mac.

## Next milestones
1. Run the merged build on the developer's Mac and confirm portfolio UI and live Binance connectivity.
2. Signals: define supported conditions, evaluate rules against live Binance quotes/candles, persist alert firing history, add cooldown/deduplication, and deliver through Telegram with retries. Until this is implemented, saved alert rules must not be described as active signals.
3. News: select a source whose licensing permits the intended commercial use; add source attribution, timestamps, language/category filters, caching, and explicit unavailable/stale states. Do not fabricate articles or AI sentiment.
4. Production: configuration/secrets review, database migrations, rate limiting, logging, health checks, backups, deployment and smoke tests.
5. Telegram Mini App: validate Telegram initData server-side, deploy frontend on HTTPS, wire bot launch button, test on mobile and desktop.
6. Monetization: Free/Pro entitlements enforced on backend, then Telegram Stars invoices and payment lifecycle handling; test successful payment, duplicate events, cancellation, expiration, and refunds before charging real users.
