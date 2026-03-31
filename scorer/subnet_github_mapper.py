"""
Subnet → GitHub Repo Mapper

Resolves netuid → (owner, repo) by:
1. Checking manual overrides in data/github_map_overrides.json
2. Fetching github_url from on-chain SubnetIdentity via bittensor_client
3. Caching results in data/github_map.json
"""

import json
import logging
from pathlib import Path
from typing import Optional

from scorer.bittensor_client import get_subnet_identity
from scorer.github_client import RepoCoords, get_repo_from_url

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent / "data"
_MAP_PATH = _DATA_DIR / "github_map.json"
_OVERRIDES_PATH = _DATA_DIR / "github_map_overrides.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not read %s: %s", path, exc)
    return {}


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _coords_from_dict(d: dict) -> Optional[RepoCoords]:
    owner = d.get("owner")
    repo = d.get("repo")
    if owner and repo:
        return RepoCoords(owner=owner, repo=repo)
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def get_github_coords(netuid: int, live_fetch: bool = False) -> Optional[RepoCoords]:
    """
    Resolve netuid → (owner, repo).

    Resolution order:
    1. Manual override in data/github_map_overrides.json
    2. In-memory / on-disk cache in data/github_map.json
    3. Live fetch from on-chain SubnetIdentity (only if live_fetch=True)

    live_fetch is disabled by default during scoring runs to avoid
    doubling chain calls. The identity fetch in run.py populates the
    cache after each run so subsequent runs are fully cached.
    """
    key = str(netuid)

    # 1. Manual overrides (highest priority, never cached-over)
    overrides = _load_json(_OVERRIDES_PATH)
    if key in overrides:
        coords = _coords_from_dict(overrides[key])
        if coords:
            logger.debug("netuid %s → override %s/%s", netuid, coords.owner, coords.repo)
            return coords

    # 2. Disk cache
    cache = _load_json(_MAP_PATH)
    if key in cache:
        coords = _coords_from_dict(cache[key])
        if coords:
            logger.debug("netuid %s → cache %s/%s", netuid, coords.owner, coords.repo)
            return coords

    # 3. Live fetch (disabled during scoring to avoid double chain calls)
    if not live_fetch:
        return None

    coords = await _fetch_and_cache(netuid, cache)
    return coords


async def _fetch_and_cache(netuid: int, cache: dict) -> Optional[RepoCoords]:
    key = str(netuid)
    identity = await get_subnet_identity(netuid)

    if identity is None:
        logger.debug("No identity found for netuid %s", netuid)
        return None

    github_url = identity.github_url
    if not github_url:
        logger.debug("No GitHub URL in identity for netuid %s", netuid)
        cache[key] = {"owner": None, "repo": None}
        _save_json(_MAP_PATH, cache)
        return None

    coords = get_repo_from_url(github_url)
    if coords is None:
        logger.warning("Could not parse GitHub URL for netuid %s: %s", netuid, github_url)
        cache[key] = {"owner": None, "repo": None, "raw_url": github_url}
        _save_json(_MAP_PATH, cache)
        return None

    logger.info("netuid %s → %s/%s (from identity)", netuid, coords.owner, coords.repo)
    cache[key] = {"owner": coords.owner, "repo": coords.repo}
    _save_json(_MAP_PATH, cache)
    return coords


async def refresh_all_mappings(netuids: list[int]) -> dict[int, Optional[RepoCoords]]:
    """
    Re-fetch GitHub mappings for all given netuids (skips overrides).
    Updates the cache file. Returns a dict of netuid → RepoCoords.
    """
    cache = _load_json(_MAP_PATH)
    results: dict[int, Optional[RepoCoords]] = {}
    for netuid in netuids:
        coords = await _fetch_and_cache(netuid, cache)
        results[netuid] = coords
    return results
