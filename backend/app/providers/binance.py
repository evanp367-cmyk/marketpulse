import asyncio
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from time import monotonic
import httpx
from backend.app.core.config import settings

class MarketDataError(RuntimeError): pass
class BinancePublicProvider:
    """Public spot market-data adapter. Commercial redistribution rights must be checked separately."""
    def __init__(self):
        self.base = settings.binance_rest_base.rstrip("/")
        self._ticker_snapshot: list[dict] | None = None
        self._ticker_snapshot_at = 0.0
        self._ticker_lock = asyncio.Lock()
        self._client_lock = asyncio.Lock()
        self._client: httpx.AsyncClient | None = None
    async def _http_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            async with self._client_lock:
                if self._client is None or self._client.is_closed:
                    self._client = httpx.AsyncClient(
                        timeout=httpx.Timeout(10.0, connect=5.0),
                        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
                    )
        return self._client
    async def aclose(self):
        if self._client is not None:
            await self._client.aclose()
            self._client = None
    async def _get(self, path: str, params: dict | None = None):
        try:
            client = await self._http_client()
            for attempt in range(2):
                try:
                    response = await client.get(f"{self.base}{path}", params=params)
                except (httpx.ConnectError, httpx.ConnectTimeout):
                    if attempt == 0:
                        continue
                    raise
                response.raise_for_status()
                return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise MarketDataError(f"Binance market data unavailable: {type(exc).__name__}") from exc
    async def ticker_24h(self, symbols: list[str] | None = None):
        normalized_symbols = {item.strip().upper() for item in symbols or [] if item and item.strip()}
        if symbols is not None and not normalized_symbols:
            return []
        if symbols is not None and len(normalized_symbols) == 1:
            symbol = next(iter(normalized_symbols))
            if self._ticker_snapshot is not None and monotonic() - self._ticker_snapshot_at < 15:
                return [item for item in self._ticker_snapshot if item["symbol"].upper() == symbol]
            try:
                data = await self._get("/api/v3/ticker/24hr", {"symbol": symbol})
            except MarketDataError as exc:
                upstream = exc.__cause__
                if isinstance(upstream, httpx.HTTPStatusError) and upstream.response.status_code == 400:
                    return []
                raise
            items = self._normalize_tickers([data] if isinstance(data, dict) else data)
            return [item for item in items if item["symbol"].upper() == symbol]

        if self._ticker_snapshot is None or monotonic() - self._ticker_snapshot_at >= 15:
            async with self._ticker_lock:
                if self._ticker_snapshot is None or monotonic() - self._ticker_snapshot_at >= 15:
                    # MINI contains the fields used by the UI in about half
                    # the bytes of Binance's full 24-hour ticker response.
                    data = await self._get("/api/v3/ticker/24hr", {"type": "MINI"})
                    self._ticker_snapshot = self._normalize_tickers(data)
                    self._ticker_snapshot_at = monotonic()
        if symbols is None:
            return self._ticker_snapshot
        return [item for item in self._ticker_snapshot if item["symbol"].upper() in normalized_symbols]

    @staticmethod
    def _normalize_tickers(data: list[dict]) -> list[dict]:
        updated_at = datetime.now(timezone.utc).isoformat()
        result = []
        for item in data:
            try:
                price = Decimal(item["lastPrice"])
                quote_volume = Decimal(item["quoteVolume"])
                if "priceChangePercent" in item:
                    change = Decimal(item["priceChangePercent"])
                else:
                    open_price = Decimal(item["openPrice"])
                    if open_price <= 0:
                        continue
                    change = ((price - open_price) / open_price * 100).quantize(Decimal("0.001"))
                if not all(value.is_finite() for value in (price, change, quote_volume)) or price <= 0 or quote_volume < 0:
                    continue
                result.append({"symbol": item["symbol"], "price": str(price), "change_percent": str(change), "quote_volume": str(quote_volume), "source": "Binance Spot", "updated_at": updated_at})
            except (KeyError, InvalidOperation, TypeError, ZeroDivisionError):
                continue
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
