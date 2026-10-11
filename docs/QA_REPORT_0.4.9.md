# MarketPulse 0.4.9 — QA report

## Scope
- Switched deployment from external Supabase PostgreSQL to PostgreSQL 16 as a Docker Compose service on the VPS.
- Added persistent named volume `postgres_data`; PostgreSQL port 5432 has no published host mapping.
- API and Telegram bot connect to `db:5432` via Compose network; service order waits for database health.
- Kept GitHub Pages, DuckDNS, Caddy HTTPS, production config and Telegram Stars price at 250.
- Added beginner guide and backup/restore instructions.

## Local checks
- Python `compileall`: pass.
- Pytest: **56 passed**.
- Compose and GitHub workflow YAML parse: pass (structural parse only).
- Production structure assertions: pass (PostgreSQL service and persistent volume present; no host port mapping for database; API and bot use internal database URL).
- Docker Compose CLI/runtime: not available in this audit environment, so containers were not started here.
- Frontend full npm build: not confirmed in this environment due dependency-network limitations from the previous release audit; run `npm install && npm run build` on Mac or let GitHub Actions build it.
- Not run against the owner's REG.RU account, DNS, Telegram bot, real HTTPS certificate, or actual Stars payment.

## Operational warnings
- PostgreSQL persists in `postgres_data`; `docker compose down -v` can delete it. Keep off-server encrypted backups.
- This setup self-hosts the DB on the same VPS as API/bot. Server deletion/outage affects both; it is suited to a one-week test but requires backups before real user data.
- This is not payment certification. Validate Telegram pre-checkout and successful-payment handling in an appropriate test setup before inviting users to pay.
