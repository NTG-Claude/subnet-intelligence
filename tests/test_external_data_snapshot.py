from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scorer.external_data_snapshot import refresh_external_data_snapshots


@pytest.mark.asyncio
async def test_refresh_external_data_snapshots_creates_tables_before_upsert():
    with patch("scorer.external_data_snapshot.create_tables") as mock_create_tables, \
         patch("scorer.external_data_snapshot.get_external_data_snapshot_map", return_value={}), \
         patch("scorer.external_data_snapshot.get_all_netuids", new=AsyncMock(return_value=[4])), \
         patch("scorer.external_data_snapshot._snapshot_for_netuid", new=AsyncMock(return_value=AsyncMock(
             github_url="https://github.com/manifold-inc/targon",
             owner="manifold-inc",
             repo="targon",
             source_status="active_repo",
             fetched_at="2026-04-02T08:15:00+00:00",
             commits_30d=3,
             contributors_30d=2,
             commits_90d=7,
             contributors_90d=3,
             commits_180d=11,
             contributors_180d=4,
             stars=10,
             forks=1,
             open_issues=0,
             last_push="2026-04-02T00:00:00+00:00",
             last_commit_at="2026-04-01T00:00:00+00:00",
         ))), \
         patch("scorer.external_data_snapshot.upsert_external_data_snapshot") as mock_upsert:
        await refresh_external_data_snapshots()

    mock_create_tables.assert_called_once()
    mock_upsert.assert_called_once()


@pytest.mark.asyncio
async def test_refresh_external_data_snapshots_prefers_taostats_bulk_github_links():
    taostats_client = AsyncMock()
    taostats_client.__aenter__.return_value.scrape_all_subnet_external_links_from_subnets_page = AsyncMock(
        return_value={39: {"github_url": "https://github.com/basilicaai/basilica"}}
    )

    with patch("scorer.external_data_snapshot.create_tables"), \
         patch("scorer.external_data_snapshot.get_external_data_snapshot_map", return_value={}), \
         patch("scorer.external_data_snapshot.get_all_netuids", new=AsyncMock(return_value=[39])), \
         patch("scorer.external_data_snapshot.TaostatsClient", return_value=taostats_client), \
         patch("scorer.external_data_snapshot.get_github_coords", new=AsyncMock(return_value=None)), \
         patch("scorer.external_data_snapshot.get_commit_activity_summary", new=AsyncMock(return_value=MagicMock(
             commits_30d=5,
             unique_contributors_30d=2,
             commits_90d=12,
             unique_contributors_90d=4,
             commits_180d=20,
             unique_contributors_180d=5,
             last_commit_at="2026-04-02T00:00:00+00:00",
         ))), \
         patch("scorer.external_data_snapshot.get_repo_stats", new=AsyncMock(return_value=MagicMock(
             stars=11,
             forks=3,
             open_issues=1,
             last_push="2026-04-02T00:00:00+00:00",
         ))), \
         patch("scorer.external_data_snapshot.upsert_external_data_snapshot") as mock_upsert:
        results = await refresh_external_data_snapshots()

    assert results[39].github_url == "https://github.com/basilicaai/basilica"
    assert results[39].owner == "basilicaai"
    assert results[39].repo == "basilica"
    assert results[39].commits_90d == 12
    assert results[39].contributors_180d == 5
    assert mock_upsert.call_args.kwargs["github_url"] == "https://github.com/basilicaai/basilica"


@pytest.mark.asyncio
async def test_refresh_external_data_snapshots_keeps_existing_snapshot_on_fetch_failure():
    taostats_client = AsyncMock()
    taostats_client.__aenter__.return_value.scrape_all_subnet_external_links_from_subnets_page = AsyncMock(
        return_value={39: {"github_url": "https://github.com/basilicaai/basilica"}}
    )
    existing = {
        39: {
            "github_url": "https://github.com/basilicaai/basilica",
            "owner": "basilicaai",
            "repo": "basilica",
            "source_status": "active_repo",
            "fetched_at": "2026-04-02T08:00:00+00:00",
            "commits_30d": 7,
            "contributors_30d": 2,
            "commits_90d": 15,
            "contributors_90d": 4,
            "commits_180d": 22,
            "contributors_180d": 5,
            "stars": 13,
            "forks": 4,
            "open_issues": 1,
            "last_push": "2026-04-02T00:00:00+00:00",
            "last_commit_at": "2026-04-01T00:00:00+00:00",
        }
    }

    with patch("scorer.external_data_snapshot.create_tables"), \
         patch("scorer.external_data_snapshot.get_external_data_snapshot_map", return_value=existing), \
         patch("scorer.external_data_snapshot.get_all_netuids", new=AsyncMock(return_value=[39])), \
         patch("scorer.external_data_snapshot.TaostatsClient", return_value=taostats_client), \
         patch("scorer.external_data_snapshot.get_github_coords", new=AsyncMock(return_value=None)), \
         patch("scorer.external_data_snapshot.get_commit_activity_summary", new=AsyncMock(return_value=None)), \
         patch("scorer.external_data_snapshot.get_repo_stats", new=AsyncMock(return_value=None)), \
         patch("scorer.external_data_snapshot.upsert_external_data_snapshot"):
        results = await refresh_external_data_snapshots()

    assert results[39].source_status == "stale_repo"
    assert results[39].commits_180d == 22
    assert results[39].last_commit_at == "2026-04-01T00:00:00+00:00"
    assert results[39].stars == 13
