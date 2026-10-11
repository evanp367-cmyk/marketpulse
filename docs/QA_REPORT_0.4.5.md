# MarketPulse 0.4.5 QA report

## Scope
- Free currency converter backed by Frankfurter daily reference rates.
- Validation for positive amount, three-letter currency codes, same-currency conversion, unavailable pairs, and reference-rate metadata.
- Default Pro price lowered to 250 Telegram Stars per 30 days across server configuration, bot invoice handling, UI fallback, and setup docs.

## Checks
Results in this build environment:
- `python3 -m compileall -q backend`: passed.
- `python3 -m pytest -q`: **51 passed**.
- TypeScript `transpileModule` syntax check for `App.tsx`, `api.ts`, `Chart.tsx`, and `main.tsx`: passed.
- `frontend/package.json` JSON parse: passed; version is 0.4.5.
- Python AST parsing of all backend `.py` files: passed.
- Final ZIP integrity (`unzip -t`): passed; no `.env`, virtualenv, `node_modules`, database file, bytecode, or TypeScript build-cache artifacts included.
- Full `npm run build`: **not verified** because `npm install` timed out and React/Vite dependencies were unavailable.
- Full FastAPI startup/route integration in this audit environment: **not verified**, because `aiosqlite` is missing here (it is included in `requirements.txt`).

## Known external verification limits
- Converter amounts use daily reference rates, not live execution rates. Currency availability depends on Frankfurter's current coverage.
- A real Telegram Stars payment is not certified by unit tests alone; a configured bot, HTTPS Mini App, verified Telegram identity, and Telegram payment lifecycle test are required.
- Full frontend production build can only be verified where npm dependencies can be installed.
- Existing local `.env` files override config defaults, so update `TELEGRAM_PRO_PRICE_STARS=250` there and restart the backend/bot.
