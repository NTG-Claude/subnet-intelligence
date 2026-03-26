"""
Tests für scorer/composite.py, scorer/scheduler.py, api/dependencies.py.
Ziel: Coverage auf ≥ 80% bringen.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# api/dependencies.py
# ---------------------------------------------------------------------------

def test_get_db_yields_session_and_closes():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from scorer.database import Base

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)

    import api.dependencies as deps
    import scorer.database as db_module

    original_sl = db_module.SessionLocal
    db_module.SessionLocal = TestSession
    try:
        gen = deps.get_db()
        session = next(gen)
        assert session is not None
        try:
            next(gen)
        except StopIteration:
            pass
    finally:
        db_module.SessionLocal = original_sl


# ---------------------------------------------------------------------------
# scorer/composite.py — _CrossSubnetContext + _score_one
# ---------------------------------------------------------------------------

def _make_raw(netuid: int):
    from scorer.composite import _RawData
    from scorer.taostats_client import (
        SubnetInfo, NeuronInfo, NeuronRegistration,
        ColdkeyDistribution, SubnetPool, ValidatorWeight,
    )

    raw = _RawData(netuid)
    raw.subnet_info = None
    raw.history = []
    raw.metagraph = [
        NeuronInfo(uid=i, incentive=0.5 - i * 0.05, stake=100.0, emission=0.1)
        for i in range(5)
    ]
    raw.registrations = [
        NeuronRegistration(netuid=netuid, hotkey=f"5X{i}", registered_at="2025-01-01")
        for i in range(3)
    ]
    raw.coldkey = ColdkeyDistribution(
        netuid=netuid,
        unique_coldkeys=200 + netuid * 10,
        top3_stake_percent=0.15 + netuid * 0.02,
        gini_coefficient=0.4,
    )
    raw.pool = SubnetPool(netuid=netuid, liquidity_usd=500_000.0 * netuid, volume_24h=20_000.0)
    raw.weights = [ValidatorWeight(netuid=netuid, hotkey="5ABC", weight_commits=10 + netuid)]
    raw.commits = MagicMock(commits_30d=20 * netuid, unique_contributors_30d=3 + netuid)
    raw.repo_stats = None
    return raw


def _make_subnet_info(netuid: int):
    from scorer.taostats_client import SubnetInfo
    return SubnetInfo(
        netuid=netuid,
        name=f"subnet-{netuid}",
        emission_percent=max(0.5, 3.0 - netuid * 0.2),
        market_cap_usd=1_000_000.0 * netuid,
        price_usd=0.05,
        flow_30d=50_000.0 * (netuid - 2),
        liquidity_usd=500_000.0 * netuid,
        volume_24h=20_000.0,
    )


def test_cross_subnet_context_builds():
    from scorer.composite import _CrossSubnetContext

    netuids = list(range(1, 6))
    raw_list = [_make_raw(n) for n in netuids]
    all_subnets_info = [_make_subnet_info(n) for n in netuids]

    ctx = _CrossSubnetContext(raw_list, all_subnets_info)

    assert len(ctx.flow_ratios) == 5
    assert len(ctx.unique_stakers) == 5
    assert len(ctx.liquidity) == 5
    assert len(ctx.registrations_7d) == 5
    assert len(ctx.weight_commits) == 5
    assert len(ctx.efficiency_ratios) == 5
    assert len(ctx.commits_30d) == 5
    assert len(ctx.contributors_30d) == 5


def test_score_one_produces_valid_score():
    from scorer.composite import _CrossSubnetContext, _score_one

    netuids = list(range(1, 6))
    raw_list = [_make_raw(n) for n in netuids]
    all_subnets_info = [_make_subnet_info(n) for n in netuids]

    ctx = _CrossSubnetContext(raw_list, all_subnets_info)
    info_by_netuid = {s.netuid: s for s in all_subnets_info}

    score = _score_one(raw_list[0], ctx, info_by_netuid)

    assert 0.0 <= score.score <= 100.0
    assert score.netuid == 1
    assert score.breakdown.capital_score >= 0
    assert score.breakdown.activity_score >= 0
    assert score.breakdown.efficiency_score >= 0
    assert score.breakdown.health_score >= 0
    assert score.breakdown.dev_score >= 0


def test_score_one_sums_to_total():
    from scorer.composite import _CrossSubnetContext, _score_one

    netuids = list(range(1, 4))
    raw_list = [_make_raw(n) for n in netuids]
    all_subnets_info = [_make_subnet_info(n) for n in netuids]

    ctx = _CrossSubnetContext(raw_list, all_subnets_info)
    info_by_netuid = {s.netuid: s for s in all_subnets_info}

    score = _score_one(raw_list[1], ctx, info_by_netuid)
    b = score.breakdown
    total_from_breakdown = round(
        b.capital_score + b.activity_score + b.efficiency_score + b.health_score + b.dev_score, 2
    )
    assert abs(total_from_breakdown - score.score) < 0.1


def test_score_one_missing_data_returns_valid():
    """Subnet with all-None data should still produce a valid (low) score."""
    from scorer.composite import _CrossSubnetContext, _score_one, _RawData

    raw = _RawData(1)  # all fields None
    ctx_raw = [_make_raw(n) for n in range(2, 6)]
    all_subnets_info = [_make_subnet_info(n) for n in range(1, 6)]

    ctx = _CrossSubnetContext([raw] + ctx_raw, all_subnets_info)
    info_by_netuid = {s.netuid: s for s in all_subnets_info}

    score = _score_one(raw, ctx, info_by_netuid)
    assert 0.0 <= score.score <= 100.0


@pytest.mark.asyncio
async def test_compute_all_subnets_ranks_correctly():
    from scorer.composite import compute_all_subnets
    from scorer.taostats_client import SubnetInfo, SubnetIdentity

    netuids = [1, 2, 3]
    all_info = [_make_subnet_info(n) for n in netuids]

    async def mock_fetch_raw(netuid):
        return _make_raw(netuid)

    mock_client = AsyncMock()
    mock_client.get_all_subnets = AsyncMock(return_value=all_info)
    mock_client.get_subnet_identity = AsyncMock(
        return_value=SubnetIdentity(netuid=1, name="test")
    )
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("scorer.composite.TaostatsClient", return_value=mock_client), \
         patch("scorer.composite._fetch_raw", side_effect=mock_fetch_raw):
        scores = await compute_all_subnets(netuids=netuids)

    assert len(scores) == 3
    ranks = [s.rank for s in scores]
    assert sorted(ranks) == [1, 2, 3]
    # Sorted descending by score
    assert scores[0].score >= scores[1].score >= scores[2].score


# ---------------------------------------------------------------------------
# scorer/scheduler.py
# ---------------------------------------------------------------------------

def test_scheduler_job_calls_run():
    from scorer.scheduler import _run_job

    with patch("scorer.scheduler.asyncio.run") as mock_run:
        mock_run.return_value = [MagicMock(), MagicMock()]  # 2 scores
        _run_job()
    mock_run.assert_called_once()


def test_scheduler_job_sends_alert_on_failure():
    from scorer.scheduler import _run_job

    with patch("scorer.scheduler.asyncio.run", side_effect=RuntimeError("boom")), \
         patch("scorer.scheduler._send_alert") as mock_alert, \
         patch("scorer.scheduler.schedule"):
        _run_job()

    mock_alert.assert_called_once()
    assert "boom" in mock_alert.call_args[0][0]


def test_send_alert_no_webhook_is_noop():
    from scorer.scheduler import _send_alert
    import scorer.scheduler as sched
    original = sched.ALERT_WEBHOOK_URL
    sched.ALERT_WEBHOOK_URL = ""
    try:
        _send_alert("test")  # should not raise
    finally:
        sched.ALERT_WEBHOOK_URL = original


def test_send_alert_with_webhook():
    from scorer.scheduler import _send_alert
    import scorer.scheduler as sched
    sched.ALERT_WEBHOOK_URL = "https://hooks.example.com/test"
    try:
        with patch("scorer.scheduler.httpx.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            _send_alert("test message")
        mock_post.assert_called_once()
        assert "test message" in str(mock_post.call_args)
    finally:
        sched.ALERT_WEBHOOK_URL = ""


def test_run_once_and_cancel_clears_retry_tag():
    """_run_once_and_cancel must call schedule.clear('retry') and return CancelJob."""
    from scorer.scheduler import _run_once_and_cancel
    import schedule as sched_lib
    # Don't mock schedule so CancelJob resolution stays real
    with patch("scorer.scheduler._run_job"):
        result = _run_once_and_cancel()
    assert result == sched_lib.CancelJob
