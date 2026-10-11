# Data sources and verification log

Reviewed 2026-10-11. This is an engineering assessment, not legal advice. A public endpoint being free to query does not automatically establish a right to redistribute data commercially.

| Provider | Official documentation | Technical capabilities | Commercial/public display status | Project decision |
|---|---|---|---|---|
| Binance Spot public market data | https://github.com/binance/binance-spot-api-docs and https://github.com/binance/binance-spot-api-docs/blob/master/faqs/market_data_only.md | Public REST endpoints include tickers and klines; public WebSocket market streams are documented. API key is not needed for market-data-only REST. | Need to review current terms, regional restrictions, and rights to display/redistribute in a commercial product before public launch. | Used by the local technical MVP; source is shown in the UI. Production commercial display remains subject to terms review. |
| Frankfurter v2 | https://frankfurter.dev/ and https://frankfurter.dev/v2/ | Public API needs no API key and offers daily reference rates, currency metadata, and historical rates. Rates are from central banks and official sources, updated daily on business days; this is not a streaming FX quote feed. | API being free to query is not itself a blanket commercial redistribution licence. Confirm applicable terms and upstream data-source restrictions before commercial public launch. | Added for daily cross-currency reference rates. Missing pairs are reported as unavailable rather than fabricated. |
| Bank of Russia daily rates | https://www.cbr.ru/development/sxml/ and https://www.cbr.ru/development/dws/ | Official XML endpoint `https://www.cbr.ru/scripts/XML_daily.asp`; documented historical/dynamic endpoints. Values are normalized to price per one currency unit using `Value / Nominal`. | Specific terms for commercial redistribution in this product have not been separately confirmed. These are official reference/accounting rates, not live executable Forex quotes. | Added as a separate source, useful for official RUB rates. Not merged with Frankfurter values. |
| TradingView Lightweight Charts | https://www.tradingview.com/lightweight-charts/ and https://github.com/tradingview/lightweight-charts | Interactive chart library supports custom candle data. | Apache-2.0; follow attribution requirements. Library licence does not license market data shown in the chart. | Selected for crypto chart rendering with attribution. |
| Forex live-feed provider | No provider selected | No streaming FX provider connected. | Commercial display rights and free tier suitability not verified. | Not represented as available. |
| Financial news / economic calendar | No provider selected | No verified source connected. | Republication, rate-limit, and commercial rights not verified. | Not available; no fabricated headlines or events. |
| Local AI sentiment | No model configured | No model/provider connected in this milestone. | Model licence and resource needs need review on selection. | Not available; UI must not imply analysis has run. |

## Important distinctions

- Frankfurter rates and Bank of Russia rates are daily reference rates; neither is a substitute for executable, streaming Forex prices.
- Do not silently cross-fill one provider's missing rates using another provider. Keep source, date, and rate type visible.
- On an upstream failure, the adapter may return only a previously fetched cached response with `stale: true`. If no cached response exists, it returns an availability error.
- Telegram Mini Apps: https://core.telegram.org/bots/webapps. Validate raw `initData` on the backend; do not trust `initDataUnsafe` as authentication.
