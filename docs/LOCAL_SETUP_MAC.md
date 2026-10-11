# Local setup on macOS / PyCharm

## Requirements
- Python 3.11 or newer (recommended 3.12). Check with `python3 --version`.
- Node.js 20 LTS or newer. Check `node --version` and `npm --version`.
- Docker and PostgreSQL are not required for the local SQLite run.

## Setup
1. Open the `marketpulse` folder in PyCharm.
2. In the PyCharm terminal, from the project root run:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   ```
3. Edit `.env` if necessary. Leave `DEV_AUTH_ENABLED=true` only for local development. The Binance public data endpoint needs no API key.
4. Start backend from the project root: `uvicorn backend.app.main:app --reload`.
5. In another terminal: `cd frontend && npm install && npm run dev`.
6. Open the Vite URL printed in the terminal, normally `http://localhost:5173`. API health: `http://127.0.0.1:8000/health`; API docs: `http://127.0.0.1:8000/docs`.
7. Run backend tests from the root: `pytest -q`. Frontend production build: `cd frontend && npm run build`.

## Telegram bot
1. Open the official `@BotFather` in Telegram and create a bot with `/newbot`.
2. Put its token in `.env` as `TELEGRAM_BOT_TOKEN=...`; never share the token.
3. Run `python -m backend.app.telegram.bot` from the project root. This bot currently supports `/start` and links to a Mini App only if `MINI_APP_URL` is configured in the environment; the Mini App URL must be HTTPS for Telegram.
4. For Telegram testing, expose the frontend through a trusted HTTPS tunnel and configure the Mini App URL with BotFather. Do not expose the backend or turn on development auth publicly.

## Stop services
Press `Ctrl+C` in each terminal.

## Troubleshooting
- `ModuleNotFoundError`: confirm `.venv` is activated and install requirements again.
- `npm: command not found`: install Node.js LTS.
- `Database is locked`: stop duplicate backend processes; SQLite is for local development.
- Market endpoint error: check network/provider availability; UI should show the failure rather than invented data.
- Telegram auth error in browser: expected unless development auth is enabled locally. Telegram production auth requires genuine Mini App `initData`.

## 0.4.5 currency converter and payment settings
- `TELEGRAM_PRO_PRICE_STARS=250` controls the Pro invoice price. The backend and bot use the same setting. `SUPPORT_ADMIN_IDS` can contain comma-separated Telegram IDs that should receive payment-support requests.
- The `/api/fx/currencies` endpoint returns the currency metadata available from Frankfurter. `/api/fx/world/daily?base=EUR` returns all rates available for that base; optional `quotes=USD,GBP` can limit the response.
- Local browser mode uses a development-only identity and intentionally cannot start a real Stars payment. Test payment only from the Telegram Mini App with verified `initData`, a real bot token and a public HTTPS Mini App URL.
- Production must set `ENVIRONMENT=production` and `DEV_AUTH_ENABLED=false`, use PostgreSQL, configure CORS and secrets, and never expose the bot token in the frontend.

- Free converter endpoint example: `curl -sS "http://127.0.0.1:8000/api/fx/convert?amount=100&from_currency=USD&to_currency=EUR"`. The returned rate is a daily reference rate, not a tradable live Forex quote.
- If upgrading an existing checkout folder, update the local `.env` setting manually to `TELEGRAM_PRO_PRICE_STARS=250` and restart the backend/bot. The `.env` file is not overwritten by extracting a new version.
