"""
Tests for the signal-separation scorer, scheduler, and API dependencies.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from collectors.models import RawSubnetSnapshot
from scorer.bittensor_client import SubnetMetrics
from scorer.composite import _legacy_breakdown, _to_snapshot, compute_all_subnets
from scoring.engine import build_scores


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
        with pytest.raises(StopIteration):
            next(gen)
    finally:
        db_module.SessionLocal = original_sl


def _make_metrics(netuid: int) -> SubnetMetrics:
    return SubnetMetrics(
        netuid=netuid,
        n_total=256,
        yuma_n_total=128,
        n_active_7d=64 + netuid * 5,
        total_stake_tao=10_000.0 * (netuid + 1),
        unique_coldkeys=100 + netuid * 20,
        top3_stake_fraction=max(0.10, 0.45 - netuid * 0.04),
        emission_per_block_tao=0.003 * (netuid + 1),
        incentive_scores=[0.5 - i * 0.015 for i in range(20)],
        n_validators=8 + netuid,
        tao_in_pool=400.0 * (netuid + 1),
        alpha_in_pool=1000.0 * (netuid + 1),
        alpha_price_tao=0.4,
        coldkey_stakes=[1200.0, 900.0, 700.0, 500.0],
        validator_stakes=[400.0, 300.0, 200.0],
        validator_weight_matrix=[
            [0.5, 0.3, 0.2],
            [0.2, 0.5, 0.3],
            [0.2, 0.2, 0.6],
        ],
        validator_bond_matrix=[
            [0.6, 0.2, 0.2],
            [0.3, 0.4, 0.3],
        ],
        last_update_blocks=[5_000_000] * 128,
        yuma_mask=[True] * 128 + [False] * 128,
        mechanism_ids=[0] * 128 + [1] * 128,
        immunity_period=4096,
        registration_allowed=True,
        target_regs_per_interval=2,
        min_burn=0.1,
        max_burn=0.2,
        difficulty=10_000.0,
    )


def _make_snapshot(netuid: int) -> RawSubnetSnapshot:
    metrics = _make_metrics(netuid)
    data = MagicMock(netuid=netuid, metrics=metrics, repo_activity=None)
    return _to_snapshot(data, current_block=5_000_000, history=[])


def test_to_snapshot_uses_yuma_denominator():
    snapshot = _make_snapshot(1)
    assert snapshot.yuma_neurons == 128
    assert snapshot.active_neurons_7d == 69


def test_build_scores_produces_analysis_and_label():
    snapshots = [_make_snapshot(n) for n in range(1, 4)]
    artifacts = build_scores(snapshots)
    first = artifacts[1]
    assert 0.0 <= first.score <= 100.0
    assert 0.0 <= first.primary.fundamental_quality <= 1.0
    assert 0.0 <= first.primary.mispricing_signal <= 1.0
    assert 0.0 <= first.primary.fragility_risk <= 1.0
    assert 0.0 <= first.primary.signal_confidence <= 1.0
    assert "component_scores" in first.explanation
    assert "primary_outputs" in first.explanation
    assert isinstance(first.label, str)
    breakdown = _legacy_breakdown(first)
    assert 0.0 <= breakdown.capital_score <= 30.0


def test_build_scores_penalizes_closed_registration_without_paths():
    snapshot = _make_snapshot(1)
    snapshot.registration_allowed = False
    snapshot.min_burn = 0.0
    snapshot.max_burn = 0.0
    snapshot.difficulty = 0.0
    snapshot.immunity_period = 0
    snapshot.active_neurons_7d = 2
    artifacts = build_scores([snapshot])[1]
    assert "registration_closed_without_burn_or_pow_penalty" in artifacts.explanation["activated_hard_rules"]


@pytest.mark.asyncio
async def test_compute_all_subnets_ranks_correctly():
    async def mock_fetch_data(netuid, block, progress, external_data_by_netuid):
        progress[0] += 1
        data = MagicMock()
        data.netuid = netuid
        data.metrics = _make_metrics(netuid)
        data.repo_activity = None
        return data

    with patch("scorer.composite.get_current_block", new=AsyncMock(return_value=5_000_000)), \
         patch("scorer.composite.get_all_netuids", new=AsyncMock(return_value=[1, 2, 3])), \
         patch("scorer.composite.get_external_data_snapshot_map", return_value={}), \
         patch("scorer.composite._fetch_data", side_effect=mock_fetch_data), \
         patch("scorer.composite.load_recent_analysis_history", return_value={}):
        scores = await compute_all_subnets(netuids=[1, 2, 3])

    assert len(scores) == 3
    ranked = sorted(scores, key=lambda score: score.rank or 9999)
    assert ranked[0].score >= ranked[1].score >= ranked[2].score
    assert ranked[0].analysis["analysis"]["label"]


@pytest.mark.asyncio
async def test_compute_all_subnets_marks_root_as_non_investable():
    async def mock_fetch_data(netuid, block, progress, external_data_by_netuid):
        progress[0] += 1
        data = MagicMock()
        data.netuid = netuid
        data.metrics = _make_metrics(netuid)
        data.repo_activity = None
        return data

    with patch("scorer.composite.get_current_block", new=AsyncMock(return_value=5_000_000)), \
         patch("scorer.composite.get_external_data_snapshot_map", return_value={}), \
         patch("scorer.composite._fetch_data", side_effect=mock_fetch_data), \
         patch("scorer.composite.load_recent_analysis_history", return_value={}):
        scores = await compute_all_subnets(netuids=[0, 1, 2])

    by_netuid = {score.netuid: score for score in scores}
    assert by_netuid[0].rank is None
    assert by_netuid[0].analysis["investable"] is False
    assert by_netuid[0].analysis["label"] == "Root Infrastructure"
    assert by_netuid[1].rank is not None


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
    finally:
        sched.ALERT_WEBHOOK_URL = ""


def test_run_once_and_cancel_clears_retry_tag():
    from scorer.scheduler import _run_once_and_cancel
    import schedule as sched_lib
    with patch("scorer.scheduler._run_job"):
        result = _run_once_and_cancel()
    assert result == sched_lib.CancelJob
