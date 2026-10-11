# Changelog

## 0.4.9 — PostgreSQL on VPS

- Switched the deployment architecture from Supabase to a self-hosted PostgreSQL 16 service inside Docker Compose on the REG.RU VPS.
- Added PostgreSQL health checks and persistent named volume `postgres_data`.
- Kept PostgreSQL private on the internal Compose network; no public 5432 mapping.
- Configured API and Telegram bot to build their async SQLAlchemy URL from PostgreSQL environment variables.
- Added an end-to-end beginner guide for database backup/restore and VPS deployment.
- Maintained GitHub Pages frontend, DuckDNS, Caddy automatic HTTPS, and Telegram Stars at 250 per 30-day Pro period.

## 0.4.8 — deployment target: VPS + GitHub Pages

- Added GitHub Pages workflow with project-path-aware Vite build.
- Added Docker Compose and Caddy HTTPS reverse proxy configuration.
- Added production config checks and launch documentation for Telegram Mini App.
- Documented secrets handling and public repository implications.
