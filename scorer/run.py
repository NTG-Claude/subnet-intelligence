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
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

from scorer.bittensor_client import get_all_netuids, get_subnet_identity
from scorer.composite import compute_all_subnets
from scorer.database import create_tables, save_scores, upsert_metadata


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

    # 1. Pre-fetch all subnet identities so GitHub URLs are available during scoring.
    # get_github_coords(live_fetch=True) will hit the _identity_cache, not the chain.
    if netuids is None:
        prefetch_netuids = await get_all_netuids()
    else:
        prefetch_netuids = netuids
    if prefetch_netuids:
        logger.info("Pre-fetching identities for %d subnets...", len(prefetch_netuids))
        await asyncio.gather(*[get_subnet_identity(n) for n in prefetch_netuids])
        logger.info("Identity pre-fetch complete")

    # 2. Compute scores (uses pre-cached identities for GitHub URL discovery)
    scores = await compute_all_subnets(netuids=netuids)

    if not scores:
        logger.warning("No scores computed")
        return []

    elapsed_fetch = time.monotonic() - start
    logger.info("Computed %d scores in %.1fs", len(scores), elapsed_fetch)

    # 3. Summary log: Top 3
    top3 = scores[:3]
    top3_str = ", ".join(f"SN{s.netuid}({s.score:.0f})" for s in top3)
    logger.info("Top 3: %s", top3_str)

    # 4. Persist
    if dry_run:
        logger.info("--dry-run: skipping database write")
    else:
        create_tables()
        save_scores(scores)
        logger.info("Scores saved to database")

        # 5. Update metadata from on-chain identity (parallel)
        identities = await asyncio.gather(
            *[get_subnet_identity(s.netuid) for s in scores]
        )
        for identity in identities:
            upsert_metadata(
                netuid=identity.netuid,
                name=identity.name,
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
