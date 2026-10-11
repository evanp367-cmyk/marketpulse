# MarketPulse 0.4.3 — focused reliability QA

## Scope
This patch addresses the reported local market-data loading failure visibility and the portfolio asset-picker stacking/clipping issue. It does not add product features.

## Changes
- In development, CORS allows both `http://localhost:5173` and `http://127.0.0.1:5173`, even if an existing `.env` only lists one origin.
- Ticker and candle requests are independent. If candles fail but tickers load, the market list remains usable.
- The portfolio picker shows a clear loading failure and a retry button instead of an endless loading message.
- The picker is elevated above sibling panels and is not clipped by the add-position panel.
- Network-level API failures include the configured API URL and a local-startup hint.
- Trailing slashes are normalized from `VITE_API_URL`.

## Verification completed in the build environment
- `python3 -m compileall -q backend`: passed.
- `python3 -m pytest -q`: 37 passed.
- TypeScript transpile syntax checks: passed for `App.tsx`, `api.ts`, `Chart.tsx`, and `main.tsx`.
- ZIP integrity: checked after packaging.

## Not certified / still requires a local run
- Full `npm run build` was not completed here because npm dependencies could not be retrieved in the isolated environment.
- Full API startup and real provider requests were not completed here because `aiosqlite` is absent from the audit runtime and outbound DNS is unavailable.
- Binance/Frankfurter/CBR uptime and network access depend on the user's machine and network; no market values are fabricated as a fallback.
- Real Telegram authentication and payments are not tested by this patch.

## Local verification on macOS
From the project root:

```bash
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
uvicorn backend.app.main:app --reload
```

In a second terminal:

```bash
cd frontend
npm install
npm run build
npm run dev
```

Open the exact Vite URL printed by the terminal. In another browser tab, check `http://127.0.0.1:8000/health`. Then check `http://127.0.0.1:8000/api/market/tickers` and confirm that JSON contains a non-empty `items` array. If this direct endpoint fails, the issue is on the backend/provider/network side, not the dropdown UI.
