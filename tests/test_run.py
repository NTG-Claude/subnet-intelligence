"""
Tests für scorer/run.py
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

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
        version="v1",
    )


def _mock_taostats_client(subnets=None):
    from scorer.taostats_client import SubnetInfo, SubnetIdentity

    if subnets is None:
        subnets = [SubnetInfo(netuid=1, name="apex"), SubnetInfo(netuid=4, name="targon")]

    identity = SubnetIdentity(netuid=1, name="apex", github_url=None, website=None)

    instance = AsyncMock()
    instance.get_all_subnets = AsyncMock(return_value=subnets)
    instance.get_subnet_identity = AsyncMock(return_value=identity)
    instance.__aenter__ = AsyncMock(return_value=instance)
    instance.__aexit__ = AsyncMock(return_value=None)
    return instance


@pytest.mark.asyncio
async def test_run_dry_run_does_not_save():
    scores = [_make_score(1, 80.0), _make_score(4, 65.0)]
    mock_client = _mock_taostats_client()

    with patch("scorer.run.TaostatsClient", return_value=mock_client), \
         patch("scorer.run.compute_all_subnets", new=AsyncMock(return_value=scores)), \
         patch("scorer.run.save_scores") as mock_save, \
         patch("scorer.run.create_tables"):

        result = await run(dry_run=True)

    assert len(result) == 2
    mock_save.assert_not_called()


@pytest.mark.asyncio
async def test_run_saves_when_not_dry_run():
    scores = [_make_score(1, 80.0)]
    mock_client = _mock_taostats_client()

    with patch("scorer.run.TaostatsClient", return_value=mock_client), \
         patch("scorer.run.compute_all_subnets", new=AsyncMock(return_value=scores)), \
         patch("scorer.run.save_scores") as mock_save, \
         patch("scorer.run.upsert_metadata"), \
         patch("scorer.run.create_tables"):

        result = await run(dry_run=False)

    assert len(result) == 1
    mock_save.assert_called_once_with(scores)


@pytest.mark.asyncio
async def test_run_force_refresh_clears_cache():
    import scorer.taostats_client as tc

    tc._cache["some_key"] = ("data", 9999999999.0)
    scores = [_make_score(1, 70.0)]
    mock_client = _mock_taostats_client()

    with patch("scorer.run.TaostatsClient", return_value=mock_client), \
         patch("scorer.run.compute_all_subnets", new=AsyncMock(return_value=scores)), \
         patch("scorer.run.save_scores"), \
         patch("scorer.run.upsert_metadata"), \
         patch("scorer.run.create_tables"):

        await run(force_refresh=True)

    assert "some_key" not in tc._cache


@pytest.mark.asyncio
async def test_run_returns_empty_when_no_subnets():
    mock_client = _mock_taostats_client(subnets=[])

    with patch("scorer.run.TaostatsClient", return_value=mock_client):
        result = await run()

    assert result == []


@pytest.mark.asyncio
async def test_run_specific_netuids():
    scores = [_make_score(4, 72.0)]
    mock_client = _mock_taostats_client()

    with patch("scorer.run.TaostatsClient", return_value=mock_client), \
         patch("scorer.run.compute_all_subnets", new=AsyncMock(return_value=scores)) as mock_compute, \
         patch("scorer.run.save_scores"), \
         patch("scorer.run.upsert_metadata"), \
         patch("scorer.run.create_tables"):

        result = await run(netuids=[4], dry_run=False)

    mock_compute.assert_called_once_with(netuids=[4])
    assert result[0].netuid == 4
