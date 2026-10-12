# MarketPulse Signal Intelligence

The new movement detector reads **closed Binance Spot klines**. Its first supported events are a one-candle price rise of at least 3% with volume at least 1.5× the median of the prior 20 candles, the corresponding fall, and a 3× volume anomaly. Price and volume use the same Binance Spot trading pair. The displayed price is the confirmed candle close, not a live last trade. The score is a formula shown in the UI, not a return probability. No fair price, MEXC/DEX quote, liquidity estimate, spread, or trade size is inferred.

The detector returns typed events with a stable key, source, close time, facts, reason codes, warnings, and score components. Future range breakouts, volatility, RSI/MACD/EMA, compound, and liquidity events can use this shape after each algorithm and its data source are validated. They are intentionally not emitted by this release.

This adds `signal_subscriptions` and `signal_deliveries` tables. It does not alter price-alert rules or their event history. The bot worker is off by default (`SIGNAL_DELIVERY_ENABLED=false`). The user must opt in to each symbol and interval in the Mini App; up to three active subscriptions are allowed. The worker checks at most 20 symbol/interval groups and queues at most 20 events each cycle, with per-subscription cooldown, a four-event hourly cap per user, a unique event key, bounded retry, and a delivery journal.

Before enabling delivery on a VPS, back up PostgreSQL, deploy the code, and apply revision `20261012_03` with Alembic. Then rebuild the API and bot and verify `/api/signals/movements?symbol=BTCUSDT&interval=1h` from an authenticated Mini App. Only after the new tables and API are healthy, set `SIGNAL_DELIVERY_ENABLED=true` in the private VPS `.env` and recreate the bot. The existing `ALERT_EVALUATOR_ENABLED` setting controls **price alerts only** and must stay independent.

Telegram `sendMessage` has no idempotency key. If Telegram accepts a message just before the process crashes, one retry can still cause a duplicate. The journal records pending, delivered, cancelled, and failed outcomes; this is bounded at-least-once delivery, not an exactly-once guarantee.
