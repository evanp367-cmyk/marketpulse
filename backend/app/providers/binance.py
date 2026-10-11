from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import httpx
from backend.app.core.config import settings

class MarketDataError(RuntimeError): pass
class BinancePublicProvider:
    """Public spot market-data adapter. Commercial redistribution rights must be checked separately."""
    def __init__(self): self.base = settings.binance_rest_base.rstrip("/")
    async def _get(self, path: str, params: dict | None = None):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base}{path}", params=params)
                response.raise_for_status()
                return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise MarketDataError(f"Binance market data unavailable: {type(exc).__name__}") from exc
    async def ticker_24h(self, symbols: list[str] | None = None):
        data = await self._get("/api/v3/ticker/24hr")
        normalized_symbols = {item.strip().upper() for item in symbols or [] if item and item.strip()}
        if symbols is not None:
            data = [x for x in data if str(x.get("symbol", "")).upper() in normalized_symbols]
        result=[]
        for x in data:
            try:
                result.append({"symbol": x["symbol"], "price": str(Decimal(x["lastPrice"])), "change_percent": str(Decimal(x["priceChangePercent"])), "quote_volume": str(Decimal(x["quoteVolume"])), "source": "Binance Spot", "updated_at": datetime.now(timezone.utc).isoformat()})
            except (KeyError, InvalidOperation): continue
        return result
    async def ticker_prices(self, symbols: list[str]) -> dict[str, str]:
        """Fetch current last-traded prices for a bounded list of Spot symbols."""
        normalized = sorted({symbol.strip().upper() for symbol in symbols if symbol and symbol.strip()})
        if not normalized:
            return {}
        import json
        result: dict[str, str] = {}
        # Binance's batch ticker endpoint accepts up to 100 requested symbols at once.
        for start in range(0, len(normalized), 100):
            chunk = normalized[start:start + 100]
            data = await self._get(
                "/api/v3/ticker/price",
                {"symbols": json.dumps(chunk, separators=(",", ":"))},
            )
            if isinstance(data, dict):
                data = [data]
            for item in data:
                try:
                    price = Decimal(str(item["price"]))
                    if price.is_finite() and price > 0:
                        result[str(item["symbol"]).upper()] = format(price, "f")
                except (KeyError, InvalidOperation, TypeError):
                    continue
        return result

    async def klines(self, symbol: str, interval: str = "1h", limit: int = 300):
        allowed={"1m","3m","5m","15m","30m","1h","2h","4h","6h","8h","12h","1d","3d","1w","1M"}
        if interval not in allowed: raise ValueError("Unsupported candle interval")
        limit=max(1,min(int(limit),1000))
        rows=await self._get("/api/v3/klines", {"symbol":symbol.upper(),"interval":interval,"limit":limit})
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        return [{"time": int(r[0] // 1000), "close_time": int(r[6]), "open": float(r[1]), "high": float(r[2]), "low": float(r[3]), "close": float(r[4]), "volume": float(r[5]), "closed": int(r[6]) < now_ms} for r in rows]
