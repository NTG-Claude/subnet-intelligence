"""
CoinGecko price client — TAO/USD price, free tier, no key required.
"""

import asyncio
import logging
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"
_CACHE_TTL = 3600.0

_cached_price: Optional[float] = None
_cached_at: float = 0.0
_lock: Optional[asyncio.Lock] = None


def _get_lock() -> asyncio.Lock:
    global _lock
    if _lock is None:
        _lock = asyncio.Lock()
    return _lock


async def get_tao_price_usd() -> Optional[float]:
    """Return current TAO/USD price with a 1-hour in-memory cache."""
    global _cached_price, _cached_at

    if _cached_price is not None and (time.monotonic() - _cached_at) < _CACHE_TTL:
        return _cached_price

    async with _get_lock():
        # Re-check after acquiring lock
        if _cached_price is not None and (time.monotonic() - _cached_at) < _CACHE_TTL:
            return _cached_price

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    _PRICE_URL,
                    params={"ids": "bittensor", "vs_currencies": "usd"},
                )
                resp.raise_for_status()
                data = resp.json()
                price = float(data["bittensor"]["usd"])
                _cached_price = price
                _cached_at = time.monotonic()
                logger.info("TAO/USD price fetched: %.4f", price)
                return price
        except Exception as exc:
            logger.error("CoinGecko price fetch failed: %s", exc)
            return _cached_price  # return stale value if available
