# MarketPulse Signal Intelligence

The new movement detector reads **closed Binance Spot klines**. Its first supported events are a one-candle price rise of at least 3% with volume at least 1.5× the median of the prior 20 candles, the corresponding fall, and a 3× volume anomaly. Price and volume use the same Binance Spot trading pair. The displayed price is the confirmed candle close, not a live last trade. The score is a formula shown in the UI, not a return probability. No fair price, MEXC/DEX quote, liquidity estimate, spread, or trade size is inferred.

The detector returns typed events with a stable key, source, close time, facts, reason codes, warnings, and score components. Future range breakouts, volatility, RSI/MACD/EMA, compound, and liquidity events can use this shape after each algorithm and its data source are validated. They are intentionally not emitted by this release.

This adds `signal_subscriptions` and `signal_deliveries` tables. It does not alter price-alert rules or their event history. The bot worker is off by default (`SIGNAL_DELIVERY_ENABLED=false`). The user must opt in to each symbol and interval in the Mini App; up to three active subscriptions are allowed. The worker checks at most 20 symbol/interval groups and queues at most 20 events each cycle, with per-subscription cooldown, a four-event hourly cap per user, a unique event key, bounded retry, and a delivery journal.

Before enabling delivery on a VPS, back up PostgreSQL, deploy the code, and apply revision `20261012_03` with Alembic. Then rebuild the API and bot and verify `/api/signals/movements?symbol=BTCUSDT&interval=1h` from an authenticated Mini App. Only after the new tables and API are healthy, set `SIGNAL_DELIVERY_ENABLED=true` in the private VPS `.env` and recreate the bot. The existing `ALERT_EVALUATOR_ENABLED` setting controls **price alerts only** and must stay independent.

### Guarded VPS rollout before merging the PR

Run this only in the VPS shell after checking that `/opt/marketpulse` has no local tracked changes. It deploys the reviewed PR commit while the Pages frontend still points at the previous API. Keep the shell open until the health checks pass; do not paste `.env` or the database backup into chat.

```bash
set -euo pipefail
cd /opt/marketpulse
git status --short
git log -1 --oneline
docker compose config --quiet
docker compose ps
docker compose exec -T api alembic current
```

If the preflight looks healthy and `git status --short` is empty, make a local database backup and check the archive before changing code:

```bash
set -euo pipefail
umask 077
mkdir -p /opt/marketpulse-backups
chmod 700 /opt/marketpulse-backups
backup_file="/opt/marketpulse-backups/before-signals-$(date -u +%Y%m%d-%H%M%S).sql.gz"
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > "$backup_file"
gzip -t "$backup_file" && ls -lh "$backup_file"
```

The archive should also be copied off the VPS after rollout. Stop if any command fails or reports a non-empty Git status. Then fetch the reviewed commit, build without restarting the running containers, apply the additive migration, and recreate only the API and bot:

```bash
set -euo pipefail
git fetch origin codex/signal-intelligence-2026-10-12
git switch --detach 2c04ed5
docker compose build api bot
docker compose run --rm --no-deps api alembic upgrade head
docker compose up -d --no-build --force-recreate api bot
docker compose exec -T api alembic current
docker compose ps
curl -fsS --max-time 15 https://marketpulse-api-livan.duckdns.org/health
curl -sS -o /dev/null -w 'Movement route: HTTP %{http_code}\n' --max-time 15 'https://marketpulse-api-livan.duckdns.org/api/signals/movements?symbol=BTCUSDT&interval=1h'
```

The migration should report `20261012_03 (head)`, API and database should be healthy, and the unauthenticated movement route should return `401` (the route exists but requires Telegram authentication). `404` means old API code is still running. Leave signal delivery disabled until the UI and Telegram route are tested; existing price alerts remain independent. If API health fails after a successful migration, return to the previously recorded Git commit and rebuild/recreate only `api` and `bot`. The migration is additive, so do not downgrade it as an emergency rollback.

Telegram `sendMessage` has no idempotency key. If Telegram accepts a message just before the process crashes, one retry can still cause a duplicate. The journal records pending, delivered, cancelled, and failed outcomes; this is bounded at-least-once delivery, not an exactly-once guarantee.
