"""
Taostats API Client
Async, rate-limited, retry-capable client for api.taostats.io
"""

import asyncio
import logging
import os
import time
from typing import Any, Optional

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

logger = logging.getLogger(__name__)

BASE_URL = "https://api.taostats.io/api"
_API_KEY = os.getenv("TAOSTATS_API_KEY", "")

# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------

class SubnetInfo(BaseModel):
    netuid: int
    name: Optional[str] = None
    emission_percent: Optional[float] = None
    market_cap_usd: Optional[float] = None
    price_usd: Optional[float] = None
    flow_24h: Optional[float] = None
    flow_7d: Optional[float] = None
    flow_30d: Optional[float] = None
    liquidity_usd: Optional[float] = None
    volume_24h: Optional[float] = None


class SubnetHistoryPoint(BaseModel):
    netuid: int
    timestamp: Optional[str] = None
    price_usd: Optional[float] = None
    market_cap_usd: Optional[float] = None
    emission_percent: Optional[float] = None


class NeuronInfo(BaseModel):
    uid: int
    hotkey: Optional[str] = None
    stake: Optional[float] = None
    emission: Optional[float] = None
    incentive: Optional[float] = None
    trust: Optional[float] = None
    rank: Optional[float] = None
    active: Optional[bool] = None


class NeuronRegistration(BaseModel):
    netuid: int
    hotkey: Optional[str] = None
    registered_at: Optional[str] = None


class ColdkeyDistribution(BaseModel):
    netuid: int
    unique_coldkeys: Optional[int] = None
    top3_stake_percent: Optional[float] = None
    gini_coefficient: Optional[float] = None


class SubnetPool(BaseModel):
    netuid: int
    liquidity_usd: Optional[float] = None
    volume_24h: Optional[float] = None
    price: Optional[float] = None


class SubnetIdentity(BaseModel):
    netuid: int
    name: Optional[str] = None
    github_url: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None


class ValidatorWeight(BaseModel):
    netuid: int
    hotkey: Optional[str] = None
    weight_commits: Optional[int] = None
    last_updated: Optional[str] = None


# ---------------------------------------------------------------------------
# In-memory cache
# ---------------------------------------------------------------------------

_cache: dict[str, tuple[Any, float]] = {}
_CACHE_TTL = 3600.0  # 1 hour


def _cache_get(key: str) -> Optional[Any]:
    entry = _cache.get(key)
    if entry and (time.monotonic() - entry[1]) < _CACHE_TTL:
        return entry[0]
    return None


def _cache_set(key: str, value: Any) -> None:
    _cache[key] = (value, time.monotonic())


# ---------------------------------------------------------------------------
# Rate limiter: max 4 requests / minute (stay under 5/min Taostats limit)
# ---------------------------------------------------------------------------

_rate_semaphore = asyncio.Semaphore(1)
_last_request_times: list[float] = []
_RATE_WINDOW = 60.0  # seconds
_MAX_REQUESTS_PER_WINDOW = 4


async def _rate_limit() -> None:
    async with _rate_semaphore:
        now = time.monotonic()
        # Remove timestamps older than 60 seconds
        while _last_request_times and now - _last_request_times[0] > _RATE_WINDOW:
            _last_request_times.pop(0)
        if len(_last_request_times) >= _MAX_REQUESTS_PER_WINDOW:
            sleep_for = _RATE_WINDOW - (now - _last_request_times[0])
            if sleep_for > 0:
                await asyncio.sleep(sleep_for)
        _last_request_times.append(time.monotonic())


# ---------------------------------------------------------------------------
# Core request helper
# ---------------------------------------------------------------------------

async def _get(
    client: httpx.AsyncClient,
    path: str,
    params: Optional[dict] = None,
    cache_key: Optional[str] = None,
) -> Optional[dict]:
    if cache_key:
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

    headers = {"authorization": _API_KEY}
    url = f"{BASE_URL}{path}"

    for attempt in range(3):
        try:
            await _rate_limit()
            resp = await client.get(url, params=params, headers=headers, timeout=15.0)

            if resp.status_code == 429:
                wait = 30 * (attempt + 1)  # 30s, 60s, 90s for rate limit
                logger.warning("HTTP 429 on %s, retrying in %ss", path, wait)
                await asyncio.sleep(wait)
                continue
            if resp.status_code in (500, 502, 503):
                wait = 2 ** attempt
                logger.warning("HTTP %s on %s, retrying in %ss", resp.status_code, path, wait)
                await asyncio.sleep(wait)
                continue

            resp.raise_for_status()
            data = resp.json()

            if cache_key:
                _cache_set(cache_key, data)
            return data

        except httpx.HTTPStatusError as exc:
            logger.error("HTTP error on %s: %s", path, exc)
        except httpx.RequestError as exc:
            logger.error("Request error on %s: %s", path, exc)
        except Exception as exc:  # noqa: BLE001
            logger.error("Unexpected error on %s: %s", path, exc)

    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class TaostatsClient:
    """Async context-manager client for the Taostats REST API."""

    def __init__(self) -> None:
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "TaostatsClient":
        self._client = httpx.AsyncClient()
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._client:
            await self._client.aclose()

    @property
    def _c(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Use TaostatsClient as an async context manager")
        return self._client

    # 1. All subnets
    async def get_all_subnets(self) -> Optional[list[SubnetInfo]]:
        data = await _get(self._c, "/subnet/latest/v1", cache_key="all_subnets")
        if data is None:
            return None
        records = data if isinstance(data, list) else data.get("data", data.get("results", []))
        result = []
        for r in records:
            try:
                result.append(SubnetInfo(**r))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not parse SubnetInfo: %s", exc)
        return result

    # 2. Subnet history
    async def get_subnet_history(
        self, netuid: int, days: int = 30
    ) -> Optional[list[SubnetHistoryPoint]]:
        data = await _get(
            self._c,
            "/subnet/history/v1",
            params={"netuid": netuid, "days": days},
            cache_key=f"subnet_history_{netuid}_{days}",
        )
        if data is None:
            return None
        records = data if isinstance(data, list) else data.get("data", data.get("results", []))
        result = []
        for r in records:
            try:
                result.append(SubnetHistoryPoint(**r))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not parse SubnetHistoryPoint: %s", exc)
        return result

    # 3. Metagraph
    async def get_metagraph(self, netuid: int) -> Optional[list[NeuronInfo]]:
        data = await _get(
            self._c,
            "/metagraph/latest/v1",
            params={"netuid": netuid},
            cache_key=f"metagraph_{netuid}",
        )
        if data is None:
            return None
        records = data if isinstance(data, list) else data.get("data", data.get("results", []))
        result = []
        for r in records:
            try:
                result.append(NeuronInfo(**r))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not parse NeuronInfo: %s", exc)
        return result

    # 4. Neuron registrations
    async def get_neuron_registrations(
        self, netuid: int, days: int = 7
    ) -> Optional[list[NeuronRegistration]]:
        data = await _get(
            self._c,
            "/subnet/neuron/registration/v1",
            params={"netuid": netuid, "days": days},
            cache_key=f"registrations_{netuid}_{days}",
        )
        if data is None:
            return None
        records = data if isinstance(data, list) else data.get("data", data.get("results", []))
        result = []
        for r in records:
            try:
                result.append(NeuronRegistration(**r))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not parse NeuronRegistration: %s", exc)
        return result

    # 5. Coldkey distribution
    async def get_coldkey_distribution(self, netuid: int) -> Optional[ColdkeyDistribution]:
        data = await _get(
            self._c,
            "/subnet/distribution/coldkey/v1",
            params={"netuid": netuid},
            cache_key=f"coldkey_{netuid}",
        )
        if data is None:
            return None
        record = data if isinstance(data, dict) else (data[0] if data else None)
        if record is None:
            return None
        try:
            return ColdkeyDistribution(**record)
        except Exception as exc:  # noqa: BLE001
            logger.error("Could not parse ColdkeyDistribution: %s", exc)
            return None

    # 6. Subnet pools
    async def get_subnet_pools(self, netuid: int) -> Optional[SubnetPool]:
        data = await _get(
            self._c,
            "/dtao/pool/latest/v1",
            params={"netuid": netuid},
            cache_key=f"pool_{netuid}",
        )
        if data is None:
            return None
        record = data if isinstance(data, dict) else (data[0] if data else None)
        if record is None:
            return None
        try:
            return SubnetPool(**record)
        except Exception as exc:  # noqa: BLE001
            logger.error("Could not parse SubnetPool: %s", exc)
            return None

    # 7. Subnet identity
    async def get_subnet_identity(self, netuid: int) -> Optional[SubnetIdentity]:
        data = await _get(
            self._c,
            "/subnet/identity/v1",
            params={"netuid": netuid},
            cache_key=f"identity_{netuid}",
        )
        if data is None:
            return None
        record = data if isinstance(data, dict) else (data[0] if data else None)
        if record is None:
            return None
        try:
            return SubnetIdentity(**record)
        except Exception as exc:  # noqa: BLE001
            logger.error("Could not parse SubnetIdentity: %s", exc)
            return None

    # 8. Validator weights
    async def get_validator_weights(self, netuid: int) -> Optional[list[ValidatorWeight]]:
        data = await _get(
            self._c,
            "/validator/weights/latest/v2",
            params={"netuid": netuid},
            cache_key=f"weights_{netuid}",
        )
        if data is None:
            return None
        records = data if isinstance(data, list) else data.get("data", data.get("results", []))
        result = []
        for r in records:
            try:
                result.append(ValidatorWeight(**r))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not parse ValidatorWeight: %s", exc)
        return result
