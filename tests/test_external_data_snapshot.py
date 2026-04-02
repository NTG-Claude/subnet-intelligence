from unittest.mock import AsyncMock, patch

import pytest

from scorer.external_data_snapshot import refresh_external_data_snapshots


@pytest.mark.asyncio
async def test_refresh_external_data_snapshots_creates_tables_before_upsert():
    with patch("scorer.external_data_snapshot.create_tables") as mock_create_tables, \
         patch("scorer.external_data_snapshot.get_all_netuids", new=AsyncMock(return_value=[4])), \
         patch("scorer.external_data_snapshot._snapshot_for_netuid", new=AsyncMock(return_value=AsyncMock(
             github_url="https://github.com/manifold-inc/targon",
             owner="manifold-inc",
             repo="targon",
             source_status="active_repo",
             fetched_at="2026-04-02T08:15:00+00:00",
             commits_30d=3,
             contributors_30d=2,
             stars=10,
             forks=1,
             open_issues=0,
             last_push="2026-04-02T00:00:00+00:00",
         ))), \
         patch("scorer.external_data_snapshot.upsert_external_data_snapshot") as mock_upsert:
        await refresh_external_data_snapshots()

    mock_create_tables.assert_called_once()
    mock_upsert.assert_called_once()
