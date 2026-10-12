# MarketPulse 0.4.9 — production launch

The deployment target is **REG.RU VPS + Docker Compose + PostgreSQL on the VPS + Caddy HTTPS + DuckDNS + GitHub Pages + Telegram Mini App**. Supabase is not part of this architecture.

Read [`VPS_GITHUB_PAGES_GUIDE.md`](VPS_GITHUB_PAGES_GUIDE.md) before deploying.

## Design and safety points

- GitHub Pages publishes the frontend under `/<repository-name>/` using `.github/workflows/deploy-pages.yml`.
- GitHub Actions reads only the public `VITE_API_URL` repository variable. No private secrets belong in Vite variables.
- The `db` service stores PostgreSQL data in named Docker volume `postgres_data`; port 5432 is not published on the host.
- API and bot connect to PostgreSQL over the private Compose network using `db:5432`.
- Caddy provides the public HTTPS reverse proxy. Port 8000 is not published to the host.
- Production requires `ENVIRONMENT=production`, `DEV_AUTH_ENABLED=false`, a real Telegram bot token, exact HTTPS origins, and the public Mini App URL.
- If the VPS cannot reach Telegram directly, `TELEGRAM_PROXY_URL` can point to a trusted foreign `socks5://` or `http://` proxy. The bot polling session and API invoice requests use the same setting. Keep proxy credentials only in the private VPS `.env`; an unavailable proxy prevents bot replies and invoice creation. This setting does not proxy Binance, the Bank of Russia, or other market-data providers.
- A Cloudflare Worker can instead relay only Telegram Bot API calls using `TELEGRAM_API_BASE_URL`. See [`CLOUDFLARE_WORKER.md`](CLOUDFLARE_WORKER.md). Set only one of these two options.
- Pro pricing is 250 Telegram Stars per 30-day period. A payment is not certified until real Telegram pre-checkout/successful-payment flow and idempotency are verified in a suitable test setup.
- Initial schema creation currently uses SQLAlchemy `create_all`; use backups and don't assume it replaces a migration system. Store backups off the VPS.
