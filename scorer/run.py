"""
scorer/run.py — Haupt-Entry-Point für den täglichen Score-Run.

Verwendung:
  python -m scorer.run --all-subnets
  python -m scorer.run --netuid 4
  python -m scorer.run --dry-run
  python -m scorer.run --force-refresh
  python -m scorer.run --all-subnets --verbose
"""

import argparse
import asyncio
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

import scorer.bittensor_client as _bt_client
from scorer.bittensor_client import clear_caches, get_all_netuids, get_subnet_identity, prefetch_all_identities
from scorer.composite import compute_all_subnets
from scorer.database import create_tables, save_scores, upsert_metadata
from scorer.taostats_client import TaostatsClient, _normalize_public_subnet_name


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    # bittensor overrides logging handlers on import — clear and re-add ours
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    ))
    root.setLevel(level)
    root.addHandler(handler)
    # Quieten noisy third-party loggers
    for noisy in ("httpx", "httpcore", "sqlalchemy.engine", "bittensor", "websockets", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


logger = logging.getLogger(__name__)

_SEED_NAMES_FILE = Path(__file__).parent.parent / "data" / "subnet_names.json"
_NAMES_CACHE_FILE = Path(__file__).parent.parent / "data" / "subnet_names_cache.json"
_NAMES_MAX_AGE_SECONDS = 86_400  # refresh at most once per day


def _read_names_file(path: Path) -> tuple[dict[int, str], Optional[datetime]]:
    try:
        data = json.loads(path.read_text())
        names = {
            int(k): _normalize_public_subnet_name(v)
            for k, v in data.items()
            if str(k).isdigit()
        }
        fetched_at_raw = data.get("_fetched_at")
        fetched_at = None
        if isinstance(fetched_at_raw, str):
            try:
                fetched_at = datetime.fromisoformat(fetched_at_raw)
            except ValueError:
                fetched_at = None
        return names, fetched_at
    except Exception:
        return {}, None


def _read_seed_names() -> dict[int, str]:
    names, _ = _read_names_file(_SEED_NAMES_FILE)
    return names


def _read_cached_names() -> tuple[dict[int, str], Optional[datetime]]:
    return _read_names_file(_NAMES_CACHE_FILE)


def _cache_is_fresh(fetched_at: Optional[datetime]) -> bool:
    if fetched_at is None:
        return False
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)
    age_seconds = (datetime.now(timezone.utc) - fetched_at).total_seconds()
    return age_seconds < _NAMES_MAX_AGE_SECONDS


def _canonical_name_key(value: Optional[str]) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _choose_preferred_subnet_name(
    identity_name: Optional[str],
    taostats_name: Optional[str],
    seed_name: Optional[str],
) -> Optional[str]:
    candidates = [name for name in (identity_name, taostats_name, seed_name) if name]
    if not candidates:
        return None

    best = candidates[0]
    best_key = _canonical_name_key(best)

    for candidate in candidates[1:]:
        candidate_key = _canonical_name_key(candidate)
        if not candidate_key:
            continue

        if candidate_key == best_key and len(candidate) > len(best):
            best = candidate
            best_key = candidate_key
            continue

        if best_key and candidate_key.startswith(best_key) and len(candidate_key) > len(best_key):
            best = candidate
            best_key = candidate_key
            continue

        if not best_key:
            best = candidate
            best_key = candidate_key

    return best


async def _refresh_names_from_public_sources(
    base_names: dict[int, str],
    target_netuids: list[int],
) -> dict[int, str]:
    if not target_netuids:
        return base_names

    refreshed = dict(base_names)
    try:
        async with TaostatsClient() as tc:
            scraped_names = await tc.scrape_public_subnet_names(target_netuids)
        for netuid, scraped_name in scraped_names.items():
            refreshed[netuid] = _choose_preferred_subnet_name(
                refreshed.get(netuid),
                _normalize_public_subnet_name(scraped_name),
                None,
            ) or refreshed.get(netuid) or _normalize_public_subnet_name(scraped_name)
    except Exception as exc:
        logger.warning("Public subnet name refresh failed: %s", exc)

    return refreshed


async def _load_subnet_names(netuids: Optional[list[int]] = None) -> dict[int, str]:
    """
    Return {netuid: name} dict from Taostats, using a disk cache.
    The cache file (data/subnet_names.json) is refreshed at most once per day,
    keeping API usage minimal regardless of how many score runs happen.
    """
    target_netuids = sorted(set(netuids or []))

    try:
        if _NAMES_CACHE_FILE.exists():
            names, fetched_at = _read_cached_names()
            if _cache_is_fresh(fetched_at):
                names = await _refresh_names_from_public_sources(names, target_netuids)
                age_hours = (datetime.now(timezone.utc) - fetched_at).total_seconds() / 3600 if fetched_at else 0.0
                logger.info("Subnet names loaded from disk cache (%d subnets, %.0fh old)",
                            len(names), age_hours)
                out = {str(k): v for k, v in names.items()}
                out["_fetched_at"] = datetime.now(timezone.utc).isoformat()
                _NAMES_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
                _NAMES_CACHE_FILE.write_text(json.dumps(out, indent=2))
                return names
    except Exception as exc:
        logger.warning("Could not read names cache: %s", exc)

    # Cache stale or missing — fetch from Taostats API first, then reconcile
    # with public-page scraping because the API occasionally serves truncated
    # display names while the public subnet pages expose the fuller label.
    names: dict[int, str] = {}
    try:
        async with TaostatsClient() as tc:
            subnets = await tc.get_all_subnets()
            if subnets:
                names = {s.netuid: _normalize_public_subnet_name(s.name) for s in subnets if s.name}
                scrape_targets = target_netuids or sorted(names.keys())
                if scrape_targets:
                    scraped_names = await tc.scrape_public_subnet_names(scrape_targets)
                    for netuid, scraped_name in scraped_names.items():
                        names[netuid] = _choose_preferred_subnet_name(
                            names.get(netuid),
                            _normalize_public_subnet_name(scraped_name),
                            None,
                        ) or names.get(netuid) or _normalize_public_subnet_name(scraped_name)
        logger.info("Taostats: fetched names for %d subnets", len(names))
        if names:
            out = {str(k): v for k, v in names.items()}
            out["_fetched_at"] = datetime.now(timezone.utc).isoformat()
            _NAMES_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            _NAMES_CACHE_FILE.write_text(json.dumps(out, indent=2))
            return names
    except Exception as exc:
        logger.warning("Taostats name fetch failed: %s", exc)

    fallback_names = _read_seed_names()
    scrape_targets = sorted(set(netuids or fallback_names.keys()))
    if scrape_targets:
        try:
            async with TaostatsClient() as tc:
                scraped_names = await tc.scrape_public_subnet_names(scrape_targets)
            if scraped_names:
                fallback_names.update({netuid: _normalize_public_subnet_name(name) for netuid, name in scraped_names.items()})
                logger.info("Taostats public scrape: fetched names for %d subnets", len(scraped_names))
        except Exception as exc:
            logger.warning("Taostats public name scrape failed: %s", exc)

    # Negative-cache the fallback result for one day so repeated score runs
    # do not keep re-hitting Taostats when the API is unavailable.
    out = {str(k): v for k, v in fallback_names.items()}
    out["_fetched_at"] = datetime.now(timezone.utc).isoformat()
    out["_note"] = "Cached subnet names from seed data plus public Taostats scraping fallback"
    _NAMES_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _NAMES_CACHE_FILE.write_text(json.dumps(out, indent=2))
    logger.info("Subnet names fallback cached for 24h after Taostats fetch miss (%d subnets)", len(fallback_names))
    return fallback_names


# ---------------------------------------------------------------------------
# Core run logic
# ---------------------------------------------------------------------------

async def run(
    netuids: Optional[list[int]] = None,
    dry_run: bool = False,
    force_refresh: bool = False,
) -> list:
    """
    Fetch data, compute scores, persist results.

    Args:
        netuids:       None → all subnets; otherwise a specific list.
        dry_run:       compute but do not write to DB.
        force_refresh: clear in-memory caches before fetching.

    Returns:
        list of SubnetScore
    """
    start = time.monotonic()
    logger.info("=== Score run started at %s ===", datetime.now(timezone.utc).isoformat())

    if force_refresh:
        clear_caches()
        logger.info("In-memory bittensor caches cleared due to --force-refresh")

    # 1. Pre-fetch ALL subnet identities in a single batch query_map call.
    # This populates _identity_cache so _fetch_data() can use GitHub URLs immediately.
    logger.info("Pre-fetching all subnet identities (batch query_map)...")
    await prefetch_all_identities()
    logger.info("Identity pre-fetch complete (%d cached)", len(_bt_client._identity_cache))

    # 2. Compute scores (uses pre-cached identities for GitHub URL discovery)
    scores = await compute_all_subnets(netuids=netuids)

    if not scores:
        logger.warning("No scores computed")
        return []

    elapsed_fetch = time.monotonic() - start
    logger.info("Computed %d scores in %.1fs", len(scores), elapsed_fetch)

    # 3. Summary log: Top 3
    top3 = sorted(
        [score for score in scores if score.analysis.get("investable", True)],
        key=lambda score: score.score,
        reverse=True,
    )[:3]
    top3_str = ", ".join(f"SN{s.netuid}({s.score:.0f})" for s in top3)
    logger.info("Top 3: %s", top3_str)

    # 4. Persist
    if dry_run:
        logger.info("--dry-run: skipping database write")
    else:
        create_tables()
        save_scores(scores)
        logger.info("Scores saved to database")

        # 5. Subnet names from Taostats (disk-cached, refreshed once per day).
        taostats_names = await _load_subnet_names([score.netuid for score in scores])
        seed_names = _read_seed_names()

        # 6. Update metadata — chain identity first, taostats name as fallback.
        identities = await asyncio.gather(
            *[get_subnet_identity(s.netuid) for s in scores]
        )
        for identity in identities:
            nid = identity.netuid
            upsert_metadata(
                netuid=nid,
                name=_choose_preferred_subnet_name(
                    identity.name,
                    taostats_names.get(nid),
                    seed_names.get(nid),
                ),
                github_url=identity.github_url,
                website=identity.website,
            )

        logger.info("Metadata updated for %d subnets", len(scores))

    total_elapsed = time.monotonic() - start
    logger.info("=== Run complete in %.1fs ===", total_elapsed)
    return scores


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bittensor Subnet Intelligence — Score Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--all-subnets",
        action="store_true",
        help="Score all subnets",
    )
    group.add_argument(
        "--netuid",
        type=int,
        metavar="N",
        help="Score a single subnet by netuid",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute scores without writing to the database",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Ignore in-memory cache and re-fetch all data",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG logging",
    )

    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    _setup_logging(args.verbose)

    netuids = None if args.all_subnets else [args.netuid]

    try:
        scores = asyncio.run(
            run(
                netuids=netuids,
                dry_run=args.dry_run,
                force_refresh=args.force_refresh,
            )
        )
    except Exception:
        import traceback
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)

    if not scores:
        os._exit(1)

    # Force-exit: bittensor keeps WebSocket background threads alive,
    # which would prevent Python from exiting normally and hang CI.
    os._exit(0)


if __name__ == "__main__":
    main()
