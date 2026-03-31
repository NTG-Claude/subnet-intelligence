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
from scorer.taostats_client import TaostatsClient


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

_NAMES_CACHE_FILE = Path(__file__).parent.parent / "data" / "subnet_names.json"
_NAMES_MAX_AGE_SECONDS = 86_400  # refresh at most once per day


async def _load_subnet_names() -> dict[int, str]:
    """
    Return {netuid: name} dict from Taostats, using a disk cache.
    The cache file (data/subnet_names.json) is refreshed at most once per day,
    keeping API usage minimal regardless of how many score runs happen.
    """
    # Use disk cache if it's fresh enough
    try:
        if _NAMES_CACHE_FILE.exists():
            age = time.time() - _NAMES_CACHE_FILE.stat().st_mtime
            if age < _NAMES_MAX_AGE_SECONDS:
                data = json.loads(_NAMES_CACHE_FILE.read_text())
                names = {int(k): v for k, v in data.items() if str(k).isdigit()}
                logger.info("Subnet names loaded from disk cache (%d subnets, %.0fh old)",
                            len(names), age / 3600)
                return names
    except Exception as exc:
        logger.warning("Could not read names cache: %s", exc)

    # Cache stale or missing — fetch from Taostats (1 API call)
    names: dict[int, str] = {}
    try:
        async with TaostatsClient() as tc:
            subnets = await tc.get_all_subnets()
        if subnets:
            names = {s.netuid: s.name for s in subnets if s.name}
        logger.info("Taostats: fetched names for %d subnets", len(names))
        # Persist to disk
        out = {str(k): v for k, v in names.items()}
        out["_fetched_at"] = datetime.now(timezone.utc).isoformat()
        _NAMES_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _NAMES_CACHE_FILE.write_text(json.dumps(out, indent=2))
    except Exception as exc:
        logger.warning("Taostats name fetch failed: %s", exc)

    return names


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
    top3 = [score for score in scores if score.analysis.get("investable", True)][:3]
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
        taostats_names = await _load_subnet_names()

        # 6. Update metadata — chain identity first, taostats name as fallback.
        identities = await asyncio.gather(
            *[get_subnet_identity(s.netuid) for s in scores]
        )
        for identity in identities:
            nid = identity.netuid
            upsert_metadata(
                netuid=nid,
                name=identity.name or taostats_names.get(nid),
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
