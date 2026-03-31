"""
Tests für scorer/run.py
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from scorer.bittensor_client import SubnetIdentity
from scorer.composite import ScoreBreakdown, SubnetScore
from scorer.run import run


def _make_score(netuid: int, score: float) -> SubnetScore:
    return SubnetScore(
        netuid=netuid,
        score=score,
        breakdown=ScoreBreakdown(
            capital_score=score * 0.25,
            activity_score=score * 0.25,
            efficiency_score=score * 0.20,
            health_score=score * 0.15,
            dev_score=score * 0.15,
        ),
        rank=1,
        timestamp="2025-01-01T06:00:00+00:00",
        version="v2",
    )


def _mock_identity(netuid: int = 1) -> SubnetIdentity:
    return SubnetIdentity(netuid=netuid, name="test", github_url=None, website=None)


@pytest.mark.asyncio
async def test_run_dry_run_does_not_save():
    scores = [_make_score(1, 80.0), _make_score(4, 65.0)]

    with patch("scorer.run.prefetch_all_identities", new=AsyncMock()), \
         patch("scorer.run.compute_all_subnets", new=AsyncMock(return_value=scores)), \
         patch("scorer.run.save_scores") as mock_save, \
         patch("scorer.run.create_tables"):

        result = await run(dry_run=True)

    assert len(result) == 2
    mock_save.assert_not_called()


@pytest.mark.asyncio
async def test_run_saves_when_not_dry_run():
    scores = [_make_score(1, 80.0)]

    with patch("scorer.run.prefetch_all_identities", new=AsyncMock()), \
         patch("scorer.run.compute_all_subnets", new=AsyncMock(return_value=scores)), \
         patch("scorer.run.get_subnet_identity", new=AsyncMock(return_value=_mock_identity())), \
         patch("scorer.run._load_subnet_names", new=AsyncMock(return_value={})), \
         patch("scorer.run.save_scores") as mock_save, \
         patch("scorer.run.upsert_metadata"), \
         patch("scorer.run.create_tables"):

        result = await run(dry_run=False)

    assert len(result) == 1
    mock_save.assert_called_once_with(scores)


@pytest.mark.asyncio
async def test_run_returns_empty_when_no_scores():
    with patch("scorer.run.prefetch_all_identities", new=AsyncMock()), \
         patch("scorer.run.compute_all_subnets", new=AsyncMock(return_value=[])):
        result = await run()

    assert result == []


@pytest.mark.asyncio
async def test_run_specific_netuids():
    scores = [_make_score(4, 72.0)]

    with patch("scorer.run.prefetch_all_identities", new=AsyncMock()), \
         patch("scorer.run.compute_all_subnets", new=AsyncMock(return_value=scores)) as mock_compute, \
         patch("scorer.run.get_subnet_identity", new=AsyncMock(return_value=_mock_identity(4))), \
         patch("scorer.run._load_subnet_names", new=AsyncMock(return_value={})), \
         patch("scorer.run.save_scores"), \
         patch("scorer.run.upsert_metadata"), \
         patch("scorer.run.create_tables"):

        result = await run(netuids=[4], dry_run=False)

    mock_compute.assert_called_once_with(netuids=[4])
    assert result[0].netuid == 4


@pytest.mark.asyncio
async def test_run_force_refresh_is_accepted():
    """force_refresh clears caches before computing fresh scores."""
    scores = [_make_score(1, 70.0)]

    with patch("scorer.run.clear_caches") as mock_clear, \
         patch("scorer.run.prefetch_all_identities", new=AsyncMock()), \
         patch("scorer.run.compute_all_subnets", new=AsyncMock(return_value=scores)), \
         patch("scorer.run.get_subnet_identity", new=AsyncMock(return_value=_mock_identity())), \
         patch("scorer.run._load_subnet_names", new=AsyncMock(return_value={})), \
         patch("scorer.run.save_scores"), \
         patch("scorer.run.upsert_metadata"), \
         patch("scorer.run.create_tables"):

        result = await run(force_refresh=True)

    mock_clear.assert_called_once()
    assert len(result) == 1


@pytest.mark.asyncio
async def test_load_subnet_names_ignores_metadata_keys():
    from scorer.run import _load_subnet_names

    cache_file = Path("data/test_subnet_names_cache.json")
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        cache_file.write_text(
            '{\n'
            '  "_fetched_at": "2026-03-31T00:00:00+00:00",\n'
            '  "_note": "seed names",\n'
            '  "4": "Targon",\n'
            '  "64": "Chutes"\n'
            '}',
            encoding="utf-8",
        )

        with patch("scorer.run._NAMES_CACHE_FILE", cache_file):
            names = await _load_subnet_names()

        assert names == {4: "Targon", 64: "Chutes"}
    finally:
        if cache_file.exists():
            cache_file.unlink()


@pytest.mark.asyncio
async def test_run_logs_top3_from_investable_subnets():
    root = _make_score(0, 99.0)
    root.analysis = {"investable": False}
    investable = [_make_score(1, 80.0), _make_score(2, 70.0), _make_score(3, 60.0)]

    with patch("scorer.run.prefetch_all_identities", new=AsyncMock()), \
         patch("scorer.run.compute_all_subnets", new=AsyncMock(return_value=[root, *investable])), \
         patch("scorer.run.save_scores"), \
         patch("scorer.run.create_tables"), \
         patch("scorer.run.get_subnet_identity", new=AsyncMock(return_value=_mock_identity())), \
         patch("scorer.run._load_subnet_names", new=AsyncMock(return_value={})), \
         patch("scorer.run.upsert_metadata"), \
         patch("scorer.run.logger") as mock_logger:
        await run(dry_run=False)

    top3_logs = [call.args[1] for call in mock_logger.info.call_args_list if call.args and call.args[0] == "Top 3: %s"]
    assert top3_logs == ["SN1(80), SN2(70), SN3(60)"]
