# Price alerts deployment

This release adds price-threshold alerts with crossing detection, a 15-minute default cooldown, bounded retries, and a 50-event user history. Only Binance Spot `price >= threshold` and `price <= threshold` rules are evaluated. Older free-form conditions remain in the database but are ignored until edited into a supported price rule. The Mini App shows whether background evaluation is enabled.

The bot worker is disabled by default (`ALERT_EVALUATOR_ENABLED=false`). On the VPS, use this order so that the existing PostgreSQL rows are preserved and the new column exists before the new API/bot starts:

```bash
cd /opt/marketpulse
git pull --ff-only origin main
umask 077
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > "/root/marketpulse-db-$(date +%Y%m%d-%H%M%S).sql"
docker compose build api bot
docker compose run --rm api alembic upgrade head
docker compose up -d --no-build api bot
docker compose ps
docker compose exec -T api alembic current
```

Confirm the API is healthy, the bot remains running, and the Mini App can save/list a price rule. To turn on real notifications, set `ALERT_EVALUATOR_ENABLED=true` in the private `.env` and recreate only the bot:

```bash
docker compose up -d --no-build --force-recreate bot
docker compose ps bot
docker compose logs --no-color --tail=40 bot
```

For a safe functional check, start the bot with `/start`, create a price rule near the current BTCUSDT price, and watch its history and Telegram message. A rule fires once on entering the threshold zone; it rearms only after a later price check outside that zone. If Binance is unavailable, that cycle is skipped. After a failed Telegram send, the worker tries up to three times with short backoff, then records failure in history. A process crash after Telegram accepts a message but before its database acknowledgement may lead to one duplicate; Telegram Bot API has no message idempotency key.
