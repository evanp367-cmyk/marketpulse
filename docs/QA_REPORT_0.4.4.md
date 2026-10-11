# MarketPulse 0.4.4 — currency coverage and Telegram billing QA

## Changes checked
- Added a cached currency catalogue endpoint backed by Frankfurter v2.
- The world-rate endpoint returns all rates supplied for a selected base when `quotes` is omitted; optional explicit quote filtering remains supported.
- The world-rate screen supports search and renders 40 cards at a time to avoid mounting the entire catalogue at once.
- The Bank of Russia view now returns all currencies in its published daily feed by default; explicit symbol filtering still works.
- Centralized Stars price configuration and exact invoice-payload validation. A local browser development identity cannot start a real payment.
- Added idempotent payment recording, uses Telegram's subscription expiry when supplied, and supports `/terms` and forwarding `/paysupport` requests to configured `SUPPORT_ADMIN_IDS`.

## Verification performed in this build environment
- `python3 -m compileall -q backend`: passed.
- `python3 -m pytest -q`: 48 passed.
- TypeScript transpile/syntax check: passed for `App.tsx`, `api.ts`, `Chart.tsx`, and `main.tsx` using the installed TypeScript compiler.
- `package.json` JSON parsing and archive integrity: checked after packaging.

## Checks that could not be completed here
- Full `npm install` / `npm run build`: npm dependencies could not be downloaded in this isolated environment. The full production build must be run on the user's network-enabled Mac after `npm install`.
- Full FastAPI startup and real provider requests: this audit runtime lacks the project's `aiosqlite` dependency and cannot download it. The project requirements include `aiosqlite`; run `pip install -r requirements.txt` locally and then start the API.
- Real Telegram `initData`, pre-checkout, Stars payment, renewal, cancellation, and refund were not end-to-end tested because they require a configured bot and Telegram's test environment. Unit tests cover signature validation and invoice/expiry logic; do not treat this as production payment certification.

## Local release gate
1. Install all Python requirements.
2. Run the backend test suite.
3. Install frontend dependencies and run the production build.
4. Test `/api/fx/currencies`, `/api/fx/world/daily?base=EUR`, and `/api/fx/cbr/daily` against live providers.
5. Configure the bot token, HTTPS Mini App URL, Pro Stars price, and support admin IDs; then run the full payment lifecycle in Telegram's test environment before accepting real payments.
