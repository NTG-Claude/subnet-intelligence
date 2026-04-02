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
from scorer.database import create_tables, upsert_external_data_snapshot
from scorer.github_client import get_commit_activity_summary, get_repo_from_url, get_repo_stats
from scorer.subnet_github_mapper import get_github_coords
from scorer.taostats_client import TaostatsClient

logger = logging.getLogger(__name__)


def _github_url(owner: Optional[str], repo: Optional[str]) -> Optional[str]:
    if owner and repo:
        return f"https://github.com/{owner}/{repo}"
    return None


async def _snapshot_for_netuid(
    netuid: int,
    client: httpx.AsyncClient,
    taostats_links: Optional[dict[int, dict[str, str]]] = None,
) -> RepoActivitySnapshot:
    fetched_at = datetime.now(timezone.utc).isoformat()
    github_url = None
    if taostats_links:
        github_url = (taostats_links.get(netuid) or {}).get("github_url")

    coords = get_repo_from_url(github_url) if github_url else None
    if coords is None:
        coords = await get_github_coords(netuid, live_fetch=True)
    if not coords:
        return RepoActivitySnapshot(
            source_status="unmapped",
            fetched_at=fetched_at,
        )

    commit_activity, repo = await asyncio.gather(
        get_commit_activity_summary(coords.owner, coords.repo, client=client),
        get_repo_stats(coords.owner, coords.repo, client=client),
    )
    has_recent_activity = bool(
        commit_activity
        and (
            commit_activity.commits_180d > 0
            or commit_activity.unique_contributors_180d > 0
            or commit_activity.last_commit_at
        )
    )
    source_status = "active_repo" if has_recent_activity or repo else "mapped_no_data"
    return RepoActivitySnapshot(
        github_url=github_url or _github_url(coords.owner, coords.repo),
        owner=coords.owner,
        repo=coords.repo,
        source_status=source_status,
        fetched_at=fetched_at,
        commits_30d=commit_activity.commits_30d if commit_activity else 0,
        contributors_30d=commit_activity.unique_contributors_30d if commit_activity else 0,
        commits_90d=commit_activity.commits_90d if commit_activity else 0,
        contributors_90d=commit_activity.unique_contributors_90d if commit_activity else 0,
        commits_180d=commit_activity.commits_180d if commit_activity else 0,
        contributors_180d=commit_activity.unique_contributors_180d if commit_activity else 0,
        stars=repo.stars if repo else 0,
        forks=repo.forks if repo else 0,
        open_issues=repo.open_issues if repo else 0,
        last_push=repo.last_push if repo else None,
        last_commit_at=commit_activity.last_commit_at if commit_activity else None,
    )


async def refresh_external_data_snapshots(
    netuids: Optional[list[int]] = None,
) -> dict[int, RepoActivitySnapshot]:
    create_tables()
    if netuids is None:
        netuids = await get_all_netuids()
    if not netuids:
        logger.warning("No netuids available for external data refresh")
        return {}

    results: dict[int, RepoActivitySnapshot] = {}
    taostats_links: dict[int, dict[str, str]] = {}
    try:
        async with TaostatsClient() as tc:
            taostats_links = await tc.scrape_all_subnet_external_links_from_subnets_page()
        logger.info("Loaded TaoStats external links for %d subnets", len(taostats_links))
    except Exception as exc:  # noqa: BLE001
        logger.warning("TaoStats external link scrape failed: %s", exc)

    async with httpx.AsyncClient(follow_redirects=True) as client:
        for netuid in netuids:
            try:
                snapshot = await _snapshot_for_netuid(netuid, client, taostats_links=taostats_links)
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
                commits_90d=snapshot.commits_90d,
                contributors_90d=snapshot.contributors_90d,
                commits_180d=snapshot.commits_180d,
                contributors_180d=snapshot.contributors_180d,
                stars=snapshot.stars,
                forks=snapshot.forks,
                open_issues=snapshot.open_issues,
                last_push=snapshot.last_push,
                last_commit_at=snapshot.last_commit_at,
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
