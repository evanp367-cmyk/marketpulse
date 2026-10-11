# MarketPulse 0.4.1 — QA audit report

## Scope
Reviewed the current 0.4.0 source archive: FastAPI routes, authentication, SQLAlchemy models/session setup, Binance and FX providers, indicator calculations, RSS news parsing, Telegram Stars bot flow, React API wrapper, key React app flows, and test coverage. This was a static/code-level review plus the automated checks listed below, not a claim of formal certification or a live production payment test.

## Fixed in 0.4.1

1. **RSI edge case:** flat prices previously returned RSI 100 because zero average loss was treated as a one-sided rise. Flat series now return neutral RSI 50; all-rise and all-fall series return 100 and 0 respectively.
2. **Indicator parameter validation:** Bollinger Bands now reject invalid periods and negative/non-finite deviation multipliers; ATR rejects invalid periods.
3. **Candle timestamps:** the provider now retains Binance's exact close time in milliseconds. Signal metadata no longer estimates a monthly candle end using a fixed 30-day duration.
4. **Neutral technical indicators:** equal EMA values and a zero MACD histogram are reported as neutral, not incorrectly counted as bearish.
5. **Database URL compatibility:** common `postgres://`, `postgresql://`, and `sqlite://` URLs are normalized to asynchronous SQLAlchemy driver URLs.
6. **Telegram initData parsing:** duplicate query fields are rejected to avoid ambiguous authentication inputs.
7. **Ticker filtering:** symbol matching is case-insensitive; an explicitly empty symbol filter no longer accidentally returns the whole market.
8. **RSS feed behavior:** feeds are fetched concurrently, merged by publication time, deduplicated, summaries are converted to plain text, and links are restricted to HTTP(S).
9. **Watchlist persistence:** the UI loads the authenticated user's saved watchlist from the backend; optimistic UI state is not changed until a save/delete request succeeds.
10. **Type declarations and product truthfulness:** Telegram `openInvoice` is typed in the frontend; plan copy now distinguishes saved alert rules from automated evaluation/delivery, which is not implemented.

## Automated checks run

- `python3 -m compileall -q backend` — passed.
- `python3 -m pytest -q` — **37 passed**.
- TypeScript transpilation syntax check for `App.tsx`, `api.ts`, `Chart.tsx`, and `main.tsx` — passed.

## Checks not completed in this environment

- **Full React type-check and Vite production build:** npm registry access failed with DNS error `EAI_AGAIN`, so frontend dependencies could not be installed here. TypeScript syntax transpilation is not equivalent to `npm run build`.
- **Full API startup/integration tests:** the audit environment does not have the `aiosqlite` dependency installed even though it is declared in `requirements.txt`; a complete app lifespan/database integration test could not be run here.
- **Live Binance/RSS tests and Telegram payment tests:** not run as automated integration tests. Payment activation needs a real bot, Telegram's environment, and end-to-end validation.
- **Production security certification:** not performed. Before launch, use migrations for schema changes, verify deployment secrets/CORS/HTTPS, add rate limiting and security headers, check data redistribution rights, and test database backup/restore.

## Required release checks on the developer's Mac

1. Create/activate the project virtual environment and run `pip install -r requirements.txt`.
2. Run `python -m pytest -q`.
3. In `frontend`, run `npm install` and `npm run build` (commit the generated lockfile for repeatable installs).
4. Start backend and frontend; verify watchlist persistence, all pages, missing-provider behavior, Free limits, Pro indicator gating, and browser console.
5. In a Telegram test setup, test invoice creation, cancellation, successful payment, duplicate payment updates, subscription expiry and re-opening the Mini App.

This report intentionally does not describe MarketPulse as production-ready until the uncompleted checks above pass.


## Follow-up UI change in 0.4.2
Added portfolio asset autocomplete as a separate UI enhancement. It derives suggestions from the ticker response already used by the application, supports known Russian/English names and tickers, and marks existing positions. The backend tests remain unchanged and all 37 pass. TypeScript syntax transpilation passed; full dependency-backed Vite build and browser interaction test still need to be run in the user's local environment.


## Follow-up QA patch 0.4.3
- Added both common Vite local origins to development CORS, including older `.env` configurations.
- Market tickers and chart candles are now requested independently; a candle failure no longer marks a successfully loaded ticker list as failed.
- The portfolio picker shows an actionable error and retry control if ticker data cannot be loaded.
- The picker escapes the add-panel clipping and uses an elevated stacking order.
- API network failures now include the configured API base URL and local startup hint.
- Verification in this build environment: 37 Python tests passed; Python compileall passed; TypeScript transpile syntax checks passed for the four frontend TSX/TS files. Full Vite build and live provider requests remain unverified because npm registry/network DNS and the `aiosqlite` package are unavailable in this environment.
