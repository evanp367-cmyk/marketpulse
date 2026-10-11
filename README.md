# MarketPulse 0.4.9

MarketPulse is a Telegram-first crypto market dashboard with a React/Vite frontend, FastAPI API, Telegram bot, FX reference rates, news feed, portfolio records, and Telegram Stars Pro subscriptions.

## Deployment target

This release uses **REG.RU VPS + Docker Compose + PostgreSQL on the same VPS + Caddy HTTPS + DuckDNS + GitHub Pages + Telegram Mini App**. Supabase is not required. The VPS database is private to the Docker network; PostgreSQL port 5432 is not published to the internet.

- GitHub Pages publishes the static frontend from the public `marketpulse` repository.
- DuckDNS provides a free hostname for the API.
- Caddy obtains and renews HTTPS certificates for the API host.
- PostgreSQL persists data in a Docker named volume (`postgres_data`).
- FastAPI and the Telegram polling bot run in separate containers.
- Pro costs 250 Telegram Stars for 30 days; real payment handling must be tested in Telegram before launch.

## Local quick start (Mac)

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
cp .env.example .env  # only if .env does not already exist
python3 -m compileall -q backend
python3 -m pytest -q
```

Terminal 1 — API:

```bash
source .venv/bin/activate
python3 -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2 — frontend:

```bash
cd frontend
npm install
npm run build
npm run dev
```

Open `http://localhost:5173`.

## Production docs

Read [`docs/VPS_GITHUB_PAGES_GUIDE.md`](docs/VPS_GITHUB_PAGES_GUIDE.md) for the complete beginner guide, GitHub Pages setup, VPS commands, Docker, PostgreSQL, HTTPS, backups, and Telegram configuration.

## Security essentials

- Never commit `.env`, bot token, DB password, DuckDNS token, backup files, `.venv`, `node_modules`, or `dist`.
- Do not publish port 5432 or port 8000; outside traffic must reach the API through Caddy HTTPS.
- Do not use `docker compose down -v` unless you intentionally want to delete the persistent database volume.
- Keep off-server backups. A VPS volume protects against container recreation, not disk failure or accidental server deletion.
- No live Telegram payment cycle or real owner-account deployment is certified by local unit tests alone.
