"""
Taostats API Client
Async, rate-limited, retry-capable client for api.taostats.io
"""

import asyncio
import html
import logging
import os
import re
import time
import unicodedata
from typing import Any, Optional

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

logger = logging.getLogger(__name__)

BASE_URL = "https://api.taostats.io/api"
PUBLIC_BASE_URL = "https://taostats.io"
TAO_APP_BASE_URL = "https://www.tao.app"
_API_KEY = os.getenv("TAOSTATS_API_KEY", "")
_PUBLIC_REQUEST_DELAY_SECONDS = 0.35
_TITLE_RE = re.compile(r"<title>\s*(?P<title>.*?)\s*</title>", re.IGNORECASE | re.DOTALL)
_NETUID_RE = re.compile(r'"netuid"\s*:\s*(?P<netuid>\d+)', re.IGNORECASE)
_TAO_APP_NAME_RE_TEMPLATE = r"Subnet\s*{netuid}\s*:\s*(?P<name>[^<\n\r|]+)"
_JSON_NAME_PATTERNS = (
    re.compile(r'"subnet_name"\s*:\s*"(?P<name>[^"]+)"', re.IGNORECASE),
    re.compile(r'"name"\s*:\s*"(?P<name>[^"]+)"', re.IGNORECASE),
)
_JSON_GITHUB_PATTERNS = (
    re.compile(r'"github"\s*:\s*"(?P<url>[^"]+)"', re.IGNORECASE),
    re.compile(r'"github_url"\s*:\s*"(?P<url>[^"]+)"', re.IGNORECASE),
    re.compile(r'"github_repo"\s*:\s*"(?P<url>[^"]+)"', re.IGNORECASE),
)
_JSON_WEBSITE_PATTERNS = (
    re.compile(r'"subnet_url"\s*:\s*"(?P<url>[^"]+)"', re.IGNORECASE),
    re.compile(r'"website"\s*:\s*"(?P<url>[^"]+)"', re.IGNORECASE),
    re.compile(r'"url"\s*:\s*"(?P<url>[^"]+)"', re.IGNORECASE),
)
_PUBLIC_NAME_RE_TEMPLATE = r"SN\s*{netuid}\s*(?:\s*[^\w\s]+\s*)+(?P<name>.+?)\s*(?:\s*[^\w\s]+\s*)+taostats"
_PUBLIC_NAME_PATHS = (
    "/subnets/{netuid}/distribution",
    "/subnets/{netuid}/metagraph",
    "/subnets/{netuid}",
)
_SUBNETS_PAGE_PATH = "/subnets"


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
    if not _API_KEY:
        logger.info("Taostats API key missing; skipping %s", path)
        return None

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

            # Taostats returns HTTP 200 with an error body when credits are exhausted
            # or the request is otherwise rejected at the application level.
            if isinstance(data, dict) and data.get("status_code") in (429, 402, 403):
                logger.warning(
                    "Taostats API error on %s: %s", path, data.get("message", data)
                )
                return None

            if cache_key:
                _cache_set(cache_key, data)
            return data

        except httpx.HTTPStatusError as exc:
            if exc.response is not None and exc.response.status_code == 401:
                logger.warning("Taostats unauthorized on %s; skipping live Taostats fetches", path)
                return None
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

    async def scrape_public_subnet_names(self, netuids: list[int]) -> dict[int, str]:
        names: dict[int, str] = {}
        if not netuids:
            return names

        for index, netuid in enumerate(netuids):
            if index > 0:
                await asyncio.sleep(_PUBLIC_REQUEST_DELAY_SECONDS)
            candidates = await self._scrape_public_subnet_name_candidates(netuid)
            name = _merge_public_name_candidates(candidates)
            if name:
                names[netuid] = name
        return names

    async def scrape_all_subnet_names_from_subnets_page(self) -> dict[int, str]:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        url = f"{PUBLIC_BASE_URL}{_SUBNETS_PAGE_PATH}"
        response = await self._c.get(url, timeout=30.0, headers=headers)
        response.raise_for_status()
        return _extract_subnet_names_from_subnets_page(response.text)

    async def scrape_all_subnet_external_links_from_subnets_page(self) -> dict[int, dict[str, str]]:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        url = f"{PUBLIC_BASE_URL}{_SUBNETS_PAGE_PATH}"
        response = await self._c.get(url, timeout=30.0, headers=headers)
        response.raise_for_status()
        return _extract_subnet_external_links_from_subnets_page(response.text)

    async def scrape_public_subnet_name_candidates(self, netuids: list[int]) -> dict[int, dict[str, str]]:
        names: dict[int, dict[str, str]] = {}
        if not netuids:
            return names

        for index, netuid in enumerate(netuids):
            if index > 0:
                await asyncio.sleep(_PUBLIC_REQUEST_DELAY_SECONDS)
            candidates = await self._scrape_public_subnet_name_candidates(netuid)
            if candidates:
                names[netuid] = candidates
        return names

    async def _scrape_public_subnet_name(self, netuid: int) -> Optional[str]:
        return _merge_public_name_candidates(await self._scrape_public_subnet_name_candidates(netuid))

    async def _scrape_public_subnet_name_candidates(self, netuid: int) -> dict[str, str]:
        candidates: dict[str, str] = {}
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        for path_template in _PUBLIC_NAME_PATHS:
            url = f"{PUBLIC_BASE_URL}{path_template.format(netuid=netuid)}"
            try:
                response = await self._c.get(url, timeout=15.0, headers=headers)
                response.raise_for_status()
            except Exception as exc:  # noqa: BLE001
                logger.debug("Taostats public scrape failed for SN%d (%s): %s", netuid, path_template, exc)
                continue
            candidate = _extract_public_subnet_name(response.text, netuid)
            if candidate:
                candidates["taostats_public"] = candidate
                break

        tao_app_candidate = await self._scrape_tao_app_subnet_name(netuid, headers)
        if tao_app_candidate:
            candidates["tao_app_public"] = tao_app_candidate
        return candidates

    async def _scrape_tao_app_subnet_name(
        self,
        netuid: int,
        headers: Optional[dict[str, str]] = None,
    ) -> Optional[str]:
        url = f"{TAO_APP_BASE_URL}/subnets/{netuid}?active_tab=metagraph"
        try:
            response = await self._c.get(url, timeout=15.0, headers=headers)
            response.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            logger.debug("TAO.app public scrape failed for SN%d: %s", netuid, exc)
            return None
        return _extract_tao_app_subnet_name(response.text, netuid)


def _extract_public_subnet_name(page_html: str, netuid: int) -> Optional[str]:
    html_text = html.unescape(page_html)

    json_candidate = _extract_public_subnet_name_from_json(html_text, netuid)
    if json_candidate:
        return json_candidate

    pattern = re.compile(
        _PUBLIC_NAME_RE_TEMPLATE.format(netuid=netuid),
        re.IGNORECASE,
    )
    html_match = pattern.search(html_text)
    if html_match:
        candidate = _normalize_public_subnet_name(html_match.group("name"))
        if _is_valid_public_subnet_name(candidate):
            return candidate

    match = _TITLE_RE.search(page_html)
    if not match:
        return None

    title = html.unescape(match.group("title"))
    parts = [part.strip() for part in re.split(r"\s*[^\w\s]+\s*", title) if part.strip()]
    sn_tokens = {f"SN{netuid}".lower(), f"SN {netuid}".lower()}

    for index, part in enumerate(parts):
        if part.lower() in sn_tokens:
            for candidate in parts[index + 1:]:
                lower = candidate.lower()
                if lower == "taostats":
                    break
                if lower in sn_tokens or re.fullmatch(r"sn\s*\d+", lower):
                    continue
                if re.fullmatch(r"\d+(?:\.\d+)?", candidate):
                    continue
                candidate = _normalize_public_subnet_name(candidate)
                if _is_valid_public_subnet_name(candidate):
                    return candidate
    return None


def _extract_public_subnet_name_from_json(html_text: str, netuid: int) -> Optional[str]:
    matches = list(_NETUID_RE.finditer(html_text))
    for index, match in enumerate(matches):
        if int(match.group("netuid")) != netuid:
            continue
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else min(len(html_text), start + 4000)
        window = html_text[start:end]
        for pattern in _JSON_NAME_PATTERNS:
            name_match = pattern.search(window)
            if not name_match:
                continue
            candidate = _normalize_public_subnet_name(name_match.group("name"))
            if _is_valid_public_subnet_name(candidate):
                return candidate
    return None


def _extract_subnet_names_from_subnets_page(page_html: str) -> dict[int, str]:
    # The subnets page embeds large escaped JSON payloads in script tags.
    # Decode common escape sequences first, then scan object windows by netuid.
    decoded = (
        page_html
        .replace('\\"', '"')
        .replace("\\/", "/")
        .replace("\\n", " ")
        .replace("\\t", " ")
        .replace("\\u002F", "/")
    )
    names: dict[int, str] = {}
    netuid_matches = list(_NETUID_RE.finditer(decoded))
    for index, netuid_match in enumerate(netuid_matches):
        netuid = int(netuid_match.group("netuid"))
        start = netuid_match.start()
        end = netuid_matches[index + 1].start() if index + 1 < len(netuid_matches) else min(len(decoded), start + 5000)
        window = decoded[start:end]

        candidate: Optional[str] = None
        subnet_name_match = re.search(r'"subnet_name"\s*:\s*"(?P<name>[^"]+)"', window, re.IGNORECASE)
        if subnet_name_match:
            normalized = _normalize_public_subnet_name(subnet_name_match.group("name"))
            if _is_valid_public_subnet_name(normalized):
                candidate = normalized

        if candidate is None:
            name_match = re.search(r'"name"\s*:\s*"(?P<name>[^"]+)"', window, re.IGNORECASE)
            if name_match:
                normalized = _normalize_public_subnet_name(name_match.group("name"))
                if _is_valid_public_subnet_name(normalized):
                    candidate = normalized

        if candidate is None:
            continue
        previous = names.get(netuid)
        if previous is None:
            names[netuid] = candidate
        else:
            names[netuid] = _prefer_richer_public_name(previous, candidate) or previous

    # Normalize mojibake and tau-prefixed names into canonical display labels.
    for netuid, name in list(names.items()):
        value = _normalize_public_subnet_name(name)
        if _canonical_public_name_key(value) in {"templar", "tauemplar"}:
            value = "Templar"
        names[netuid] = value

    return names


def _extract_subnet_external_links_from_subnets_page(page_html: str) -> dict[int, dict[str, str]]:
    decoded = (
        page_html
        .replace('\\"', '"')
        .replace("\\/", "/")
        .replace("\\n", " ")
        .replace("\\t", " ")
        .replace("\\u002F", "/")
    )
    links: dict[int, dict[str, str]] = {}
    netuid_matches = list(_NETUID_RE.finditer(decoded))
    for index, netuid_match in enumerate(netuid_matches):
        netuid = int(netuid_match.group("netuid"))
        start = netuid_match.start()
        end = netuid_matches[index + 1].start() if index + 1 < len(netuid_matches) else min(len(decoded), start + 5000)
        window = decoded[start:end]

        github_url: Optional[str] = None
        website: Optional[str] = None

        for pattern in _JSON_GITHUB_PATTERNS:
            match = pattern.search(window)
            if match:
                candidate = html.unescape(match.group("url")).strip()
                if "github.com" in candidate.lower():
                    github_url = candidate
                    break

        for pattern in _JSON_WEBSITE_PATTERNS:
            match = pattern.search(window)
            if match:
                candidate = html.unescape(match.group("url")).strip()
                if candidate.lower().startswith(("http://", "https://")):
                    website = candidate
                    break

        if github_url or website:
            links[netuid] = {}
            if github_url:
                links[netuid]["github_url"] = github_url
            if website:
                links[netuid]["website"] = website

    return links


def _extract_tao_app_subnet_name(page_html: str, netuid: int) -> Optional[str]:
    html_text = html.unescape(page_html)
    pattern = re.compile(
        _TAO_APP_NAME_RE_TEMPLATE.format(netuid=netuid),
        re.IGNORECASE,
    )
    match = pattern.search(html_text)
    if not match:
        return None
    candidate = _normalize_public_subnet_name(match.group("name"))
    if _is_valid_public_subnet_name(candidate):
        return candidate
    return None


def _normalize_public_subnet_name(candidate: Optional[str]) -> str:
    value = unicodedata.normalize("NFKC", html.unescape(candidate or "")).strip()
    replacements = {
        "Ï„": "T",
        "τ": "T",
        "Τ": "T",
        "Â·": "·",
    }
    for source, target in replacements.items():
        if source in value:
            value = value.replace(source, target)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _canonical_public_name_key(candidate: Optional[str]) -> str:
    if not candidate:
        return ""
    return re.sub(r"[^a-z0-9]+", "", candidate.lower())


def _prefer_richer_public_name(primary: Optional[str], alternate: Optional[str]) -> Optional[str]:
    if not primary:
        return alternate
    if not alternate:
        return primary

    primary_key = _canonical_public_name_key(primary)
    alternate_key = _canonical_public_name_key(alternate)
    if alternate_key == primary_key and len(alternate) > len(primary):
        return alternate
    if primary_key and alternate_key.startswith(primary_key) and len(alternate_key) > len(primary_key):
        return alternate
    return primary


def _merge_public_name_candidates(candidates: Optional[dict[str, str]]) -> Optional[str]:
    if not candidates:
        return None
    return _prefer_richer_public_name(
        candidates.get("taostats_public"),
        candidates.get("tao_app_public"),
    ) or candidates.get("taostats_public") or candidates.get("tao_app_public")


def _is_valid_public_subnet_name(candidate: Optional[str]) -> bool:
    if not candidate:
        return False
    value = candidate.strip()
    if not value or len(value) > 128:
        return False
    if "..." in value or "…" in value:
        return False
    lower = value.lower()
    if lower in {"description", "content", "title", "viewport", "metadata"}:
        return False
    if "taostats" in lower or lower.startswith("http"):
        return False
    if any(token in value for token in ('<', '>', '{', '}', '[', ']', '\\"', "\\u", "\\n")):
        return False
    return True
