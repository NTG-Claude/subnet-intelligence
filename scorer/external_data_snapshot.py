"""
External evidence snapshot refresh.

Fetches external subnet data once, stores it in the database, and allows the
score run to read stable snapshots instead of live GitHub data.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

from collectors.models import RepoActivitySnapshot
from scorer.bittensor_client import get_all_netuids
from scorer.database import upsert_external_data_snapshot
from scorer.github_client import get_commits_last_30d, get_repo_stats
from scorer.subnet_github_mapper import get_github_coords

logger = logging.getLogger(__name__)


def _github_url(owner: Optional[str], repo: Optional[str]) -> Optional[str]:
    if owner and repo:
        return f"https://github.com/{owner}/{repo}"
    return None


async def _snapshot_for_netuid(
    netuid: int,
    client: httpx.AsyncClient,
) -> RepoActivitySnapshot:
    fetched_at = datetime.now(timezone.utc).isoformat()
    coords = await get_github_coords(netuid, live_fetch=True)
    if not coords:
        return RepoActivitySnapshot(
            source_status="unmapped",
            fetched_at=fetched_at,
        )

    commits, repo = await asyncio.gather(
        get_commits_last_30d(coords.owner, coords.repo, client=client),
        get_repo_stats(coords.owner, coords.repo, client=client),
    )
    source_status = "active_repo" if commits or repo else "mapped_no_data"
    return RepoActivitySnapshot(
        github_url=_github_url(coords.owner, coords.repo),
        owner=coords.owner,
        repo=coords.repo,
        source_status=source_status,
        fetched_at=fetched_at,
        commits_30d=commits.commits_30d if commits else 0,
        contributors_30d=commits.unique_contributors_30d if commits else 0,
        stars=repo.stars if repo else 0,
        forks=repo.forks if repo else 0,
        open_issues=repo.open_issues if repo else 0,
        last_push=repo.last_push if repo else None,
    )


async def refresh_external_data_snapshots(
    netuids: Optional[list[int]] = None,
) -> dict[int, RepoActivitySnapshot]:
    if netuids is None:
        netuids = await get_all_netuids()
    if not netuids:
        logger.warning("No netuids available for external data refresh")
        return {}

    results: dict[int, RepoActivitySnapshot] = {}
    async with httpx.AsyncClient(follow_redirects=True) as client:
        for netuid in netuids:
            try:
                snapshot = await _snapshot_for_netuid(netuid, client)
            except Exception as exc:  # noqa: BLE001
                logger.warning("External data refresh failed for SN%d: %s", netuid, exc)
                snapshot = RepoActivitySnapshot(
                    source_status="fetch_failed",
                    fetched_at=datetime.now(timezone.utc).isoformat(),
                )
            results[netuid] = snapshot
            upsert_external_data_snapshot(
                netuid=netuid,
                github_url=snapshot.github_url,
                owner=snapshot.owner,
                repo=snapshot.repo,
                source_status=snapshot.source_status,
                fetched_at=datetime.fromisoformat(snapshot.fetched_at) if snapshot.fetched_at else datetime.now(timezone.utc),
                commits_30d=snapshot.commits_30d,
                contributors_30d=snapshot.contributors_30d,
                stars=snapshot.stars,
                forks=snapshot.forks,
                open_issues=snapshot.open_issues,
                last_push=snapshot.last_push,
            )
    logger.info("External data snapshot refreshed for %d subnets", len(results))
    return results


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh external subnet data snapshots")
    parser.add_argument("--netuid", type=int, metavar="N", help="Refresh only one subnet", default=None)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    netuids = [args.netuid] if args.netuid is not None else None
    asyncio.run(refresh_external_data_snapshots(netuids=netuids))


if __name__ == "__main__":
    main()
