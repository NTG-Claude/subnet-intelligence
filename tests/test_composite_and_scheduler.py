"""
Tests für scorer/composite.py, scorer/scheduler.py, api/dependencies.py.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from scorer.bittensor_client import SubnetMetrics
from scorer.composite import (
    ScoreBreakdown,
    SubnetScore,
    _CrossSubnetContext,
    _SubnetData,
    _score_one,
)


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
# Helpers
# ---------------------------------------------------------------------------

def _make_metrics(netuid: int) -> SubnetMetrics:
    return SubnetMetrics(
        netuid=netuid,
        n_total=256,
        n_active_7d=100 + netuid * 10,
        total_stake_tao=10_000.0 * (netuid + 1),
        unique_coldkeys=100 + netuid * 20,
        top3_stake_fraction=max(0.05, 0.4 - netuid * 0.03),
        emission_per_block_tao=0.005 * (netuid + 1),
        incentive_scores=[0.5 - i * 0.02 for i in range(20)],
        n_validators=5 + netuid,
    )


def _make_data(netuid: int, tao_price: float = 300.0) -> _SubnetData:
    d = _SubnetData(netuid)
    d.metrics = _make_metrics(netuid)
    d.tao_price_usd = tao_price
    d.commits = MagicMock(commits_30d=20 * netuid, unique_contributors_30d=3 + netuid)
    return d


# ---------------------------------------------------------------------------
# _CrossSubnetContext
# ---------------------------------------------------------------------------

def test_cross_subnet_context_builds():
    all_data = [_make_data(n) for n in range(1, 6)]
    ctx = _CrossSubnetContext(all_data)

    assert len(ctx.stakes_usd) == 5
    assert len(ctx.unique_coldkeys) == 5
    assert len(ctx.active_ratios) == 5
    assert len(ctx.n_validators) == 5
    assert len(ctx.stake_per_emission) == 5
    assert len(ctx.commits_30d) == 5
    assert len(ctx.contributors_30d) == 5


def test_cross_subnet_context_no_price():
    """Zero TAO price → all stakes_usd should be None."""
    all_data = [_make_data(n, tao_price=0.0) for n in range(1, 4)]
    ctx = _CrossSubnetContext(all_data)
    assert all(v is None for v in ctx.stakes_usd)


# ---------------------------------------------------------------------------
# _score_one
# ---------------------------------------------------------------------------

def test_score_one_produces_valid_score():
    all_data = [_make_data(n) for n in range(1, 6)]
    ctx = _CrossSubnetContext(all_data)

    score = _score_one(all_data[0], ctx)
    assert 0.0 <= score.score <= 100.0
    assert score.netuid == 1
    assert score.breakdown.capital_score >= 0
    assert score.breakdown.activity_score >= 0
    assert score.breakdown.efficiency_score >= 0
    assert score.breakdown.health_score >= 0
    assert score.breakdown.dev_score >= 0


def test_score_one_sums_to_total():
    all_data = [_make_data(n) for n in range(1, 4)]
    ctx = _CrossSubnetContext(all_data)

    score = _score_one(all_data[1], ctx)
    b = score.breakdown
    total_from_breakdown = round(
        b.capital_score + b.activity_score + b.efficiency_score + b.health_score + b.dev_score, 2
    )
    assert abs(total_from_breakdown - score.score) < 0.1


def test_score_one_missing_data_returns_valid():
    """Subnet with None metrics should still produce a valid (low) score."""
    d = _SubnetData(99)
    d.metrics = None
    d.tao_price_usd = 300.0
    d.commits = None

    all_data = [_make_data(n) for n in range(1, 5)] + [d]
    ctx = _CrossSubnetContext(all_data)

    score = _score_one(d, ctx)
    assert 0.0 <= score.score <= 100.0


# ---------------------------------------------------------------------------
# compute_all_subnets
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_compute_all_subnets_ranks_correctly():
    from scorer.composite import compute_all_subnets

    netuids = [1, 2, 3]

    async def mock_fetch_data(netuid, block, price):
        return _make_data(netuid, tao_price=price)

    with patch("scorer.composite.get_current_block", new=AsyncMock(return_value=5_000_000)), \
         patch("scorer.composite.get_tao_price_usd", new=AsyncMock(return_value=300.0)), \
         patch("scorer.composite.get_all_netuids", new=AsyncMock(return_value=netuids)), \
         patch("scorer.composite._fetch_data", side_effect=mock_fetch_data):
        scores = await compute_all_subnets(netuids=netuids)

    assert len(scores) == 3
    ranks = [s.rank for s in scores]
    assert sorted(ranks) == [1, 2, 3]
    assert scores[0].score >= scores[1].score >= scores[2].score


# ---------------------------------------------------------------------------
# scorer/scheduler.py
# ---------------------------------------------------------------------------

def test_scheduler_job_calls_run():
    from scorer.scheduler import _run_job

    with patch("scorer.scheduler.asyncio.run") as mock_run:
        mock_run.return_value = [MagicMock(), MagicMock()]
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
        _send_alert("test")
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
    from scorer.scheduler import _run_once_and_cancel
    import schedule as sched_lib
    with patch("scorer.scheduler._run_job"):
        result = _run_once_and_cancel()
    assert result == sched_lib.CancelJob
