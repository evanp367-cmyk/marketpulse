# MarketPulse 0.4.6 — large currency selector

This is a complete project ZIP based on the 0.3.1 quote-freshness version, not a partial patch. It includes the backend and frontend source but excludes `.env`, `.venv`, local database files, `node_modules`, and caches.

## New features
- Expanded daily reference currency coverage to all quote currencies returned by Frankfurter and all currencies in the Bank of Russia daily feed. Added a searchable world-rate view with progressive rendering.
- Hardened Telegram Mini App identity and Stars subscription flow, configurable price, idempotent successful-payment processing, subscription expiry handling, `/terms`, and admin-forwarded `/paysupport`.
- Technical overview from real closed Binance Spot candles: RSI, EMA20/50, MACD, Pro Bollinger Bands, indicator explanations and timestamps.
- News headline screen using RSS feeds from CoinDesk and Cointelegraph; each headline links to the publisher's original page.
- Free / Pro plans, server-side entitlement checks, portfolio/alert/news limits, subscription and payment tables.
- Telegram Stars invoice-link endpoint and bot handlers to verify pre-checkout and activate Pro only after Telegram reports a successful payment.
- Existing market, FX, watchlist, portfolio and quote-freshness features retained.

## Run locally on macOS
From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
uvicorn backend.app.main:app --reload
```

In a second Terminal window:

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in Terminal, normally `http://localhost:5173`.

Run backend checks from the project root:

```bash
python -m pytest -q
```

Build the frontend when npm dependencies are installed:

```bash
cd frontend
npm run build
```

## Telegram Stars setup (not automatic)
1. Create a bot with Telegram's official `@BotFather`.
2. Put the bot token in `.env` as `TELEGRAM_BOT_TOKEN=...` and set `MINI_APP_URL` to the public HTTPS frontend URL.
3. Set `DEV_AUTH_ENABLED=false` and configure the exact deployed frontend origin in `CORS_ORIGINS` before production.
4. Run the bot separately from the project root: `python -m backend.app.telegram.bot`.
5. Test invoice creation, successful payment, duplicate payment events and expiry in a test environment before launch.

The Pro price of 250 is in Telegram Stars, not RUB, and is a starting hypothesis. Telegram payment only works in a real Telegram Mini App/bot environment with valid initData. The bot must remain online to receive successful-payment updates. RSS and Binance terms must be checked before commercial launch.


## QA audit notes
This release fixes identified correctness issues without adding new product features. See `docs/QA_AUDIT_0.4.1.md` for checks performed and known release blockers.


## Portfolio asset autocomplete (0.4.2)
- Search by symbol or common coin name in Russian/English.
- Suggestions use existing `/api/market/tickers` response; no extra API request is introduced by typing.
- Select a suggestion to populate the actual Binance Spot trading pair.
- Existing positions are marked as added and cannot be selected again.
- No exchange orders are created.


## 0.4.6 release gate
See `docs/QA_REPORT_0.4.6.md` for exactly which checks passed and which could not be run in the isolated build environment. Backend unit tests (`51 passed`), Python compile checks, and TypeScript syntax transpilation passed. The full npm production build could not be verified because dependency installation timed out; real Telegram payment lifecycle testing still requires a configured bot and HTTPS Mini App.


## 0.4.6 changes
- Added a free currency converter backed by the same cached daily reference-rate provider.
- Reduced the default MarketPulse Pro subscription price to 250 Telegram Stars per 30 days.
- Set `TELEGRAM_PRO_PRICE_STARS=250` in a pre-existing local `.env` file as well as in `.env.example`; existing `.env` values are not overwritten automatically.
- See `docs/QA_REPORT_0.4.6.md` for checks and known environment limitations.


## 0.4.6 change
- Replaced small native currency dropdowns with a large searchable modal picker. See `docs/QA_REPORT_0.4.6.md`.
