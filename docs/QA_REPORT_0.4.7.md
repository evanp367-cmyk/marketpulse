# MarketPulse 0.4.7 — production deployment pack QA

## Changes
- Added Render Blueprint for three services: FastAPI API, Vite static frontend, and a separate Telegram long-polling bot worker.
- Added production-startup validation for PostgreSQL, disabled development auth, Telegram credentials, HTTPS Mini App URL, HTTPS-only exact CORS origins, and Telegram's 10,000-Star amount ceiling.
- Added a production launch checklist for a dedicated Supabase database, GitHub, Render variables, Telegram BotFather setup, and smoke tests.
- Kept the default Pro price at 250 Telegram Stars per 30-day subscription period.

## Checks passed in the build environment
- `python3 -m compileall -q backend`
- `python3 -m pytest -q`: **56 passed**
- `frontend/package.json` JSON parsing and version consistency
- `render.yaml` YAML parsing; exactly three services are defined
- Archive integrity check

## Not verified here
- Dependency-backed `npm run build`: must be run on a network-enabled machine before deployment.
- No live Render/Supabase/GitHub accounts were accessed; no services have been deployed by this pack.
- No real Telegram Mini App auth/payment test was run. The user must test the full Stars lifecycle before selling access.
- This release still creates the initial SQLAlchemy schema at API startup; Alembic migration workflow should be added before making destructive schema changes on live data.
- Commercial redistribution terms for external market/news sources still need owner review.
