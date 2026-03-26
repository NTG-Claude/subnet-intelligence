"""
Tests für scorer/database.py — verwendet eine In-Memory SQLite DB.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from scorer.database import (
    Base,
    SubnetScoreRow,
    SubnetMetadataRow,
    _row_to_dict,
    get_latest_scores,
    get_score_at,
    get_score_distribution,
    get_score_history,
    get_top_subnets,
    save_scores,
    upsert_metadata,
)
from scorer.composite import ScoreBreakdown, SubnetScore


# ---------------------------------------------------------------------------
# In-memory DB fixture
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def in_memory_db(monkeypatch):
    """Replace the module-level engine + SessionLocal with an in-memory SQLite."""
    test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=test_engine)
    TestSession = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)

    import scorer.database as db_module
    monkeypatch.setattr(db_module, "engine", test_engine)
    monkeypatch.setattr(db_module, "SessionLocal", TestSession)
    yield TestSession


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_score(netuid: int, score: float, rank: int = 1) -> SubnetScore:
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
        rank=rank,
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="v1",
    )


# ---------------------------------------------------------------------------
# save_scores / get_latest_scores
# ---------------------------------------------------------------------------

def test_save_and_retrieve_scores():
    scores = [_make_score(1, 80.0, rank=1), _make_score(5, 60.0, rank=2)]
    save_scores(scores)
    rows = get_latest_scores()
    assert len(rows) == 2
    assert rows[0]["score"] == 80.0
    assert rows[1]["score"] == 60.0


def test_get_latest_scores_returns_most_recent():
    """When a subnet has multiple score rows, only the latest is returned."""
    old_score = _make_score(1, 50.0)
    new_score = _make_score(1, 75.0)

    import scorer.database as db_module
    from datetime import datetime, timezone

    # Manually insert with different timestamps
    with db_module.SessionLocal() as session:
        session.add(SubnetScoreRow(
            netuid=1, score=50.0,
            capital_score=12.5, activity_score=12.5,
            efficiency_score=10.0, health_score=7.5, dev_score=7.5,
            rank=2,
            computed_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            score_version="v1",
        ))
        session.add(SubnetScoreRow(
            netuid=1, score=75.0,
            capital_score=18.75, activity_score=18.75,
            efficiency_score=15.0, health_score=11.25, dev_score=11.25,
            rank=1,
            computed_at=datetime(2025, 1, 10, tzinfo=timezone.utc),
            score_version="v1",
        ))
        session.commit()

    rows = get_latest_scores()
    assert len(rows) == 1
    assert rows[0]["score"] == 75.0


def test_save_scores_with_raw_data():
    scores = [_make_score(3, 55.0)]
    raw = {3: {"some": "data", "value": 42}}
    save_scores(scores, raw_data_by_netuid=raw)
    rows = get_latest_scores()
    assert rows[0]["netuid"] == 3


def test_save_empty_list_does_not_crash():
    save_scores([])
    assert get_latest_scores() == []


# ---------------------------------------------------------------------------
# get_score_history
# ---------------------------------------------------------------------------

def test_get_score_history():
    import scorer.database as db_module

    now = datetime.now(timezone.utc)
    with db_module.SessionLocal() as session:
        for days_ago, score in [(25, 40.0), (15, 55.0), (5, 70.0)]:
            session.add(SubnetScoreRow(
                netuid=7, score=score,
                capital_score=0, activity_score=0,
                efficiency_score=0, health_score=0, dev_score=0,
                computed_at=now - timedelta(days=days_ago),
                score_version="v1",
            ))
        session.commit()

    history = get_score_history(7, days=30)
    assert len(history) == 3
    # Should be ordered by computed_at ascending
    assert history[0]["score"] == 40.0
    assert history[-1]["score"] == 70.0


def test_get_score_history_filters_by_days():
    import scorer.database as db_module

    now = datetime.now(timezone.utc)
    with db_module.SessionLocal() as session:
        session.add(SubnetScoreRow(
            netuid=8, score=30.0,
            capital_score=0, activity_score=0,
            efficiency_score=0, health_score=0, dev_score=0,
            computed_at=now - timedelta(days=60),  # outside window
            score_version="v1",
        ))
        session.add(SubnetScoreRow(
            netuid=8, score=65.0,
            capital_score=0, activity_score=0,
            efficiency_score=0, health_score=0, dev_score=0,
            computed_at=now - timedelta(days=5),   # inside window
            score_version="v1",
        ))
        session.commit()

    history = get_score_history(8, days=30)
    assert len(history) == 1
    assert history[0]["score"] == 65.0


# ---------------------------------------------------------------------------
# get_score_at
# ---------------------------------------------------------------------------

def test_get_score_at():
    import scorer.database as db_module

    ts = datetime(2025, 6, 15, 12, 0, tzinfo=timezone.utc)
    with db_module.SessionLocal() as session:
        session.add(SubnetScoreRow(
            netuid=2, score=42.0,
            capital_score=0, activity_score=0,
            efficiency_score=0, health_score=0, dev_score=0,
            computed_at=ts,
            score_version="v1",
        ))
        session.commit()

    result = get_score_at(2, datetime(2025, 6, 16, tzinfo=timezone.utc))
    assert result is not None
    assert result["score"] == 42.0


def test_get_score_at_returns_none_when_no_data():
    result = get_score_at(999, datetime.now(timezone.utc))
    assert result is None


# ---------------------------------------------------------------------------
# get_top_subnets
# ---------------------------------------------------------------------------

def test_get_top_subnets():
    scores = [_make_score(i, float(i * 10), rank=10 - i) for i in range(1, 11)]
    save_scores(scores)

    top3 = get_top_subnets(n=3)
    assert len(top3) == 3
    assert top3[0]["score"] == 100.0
    assert top3[1]["score"] == 90.0


# ---------------------------------------------------------------------------
# get_score_distribution
# ---------------------------------------------------------------------------

def test_get_score_distribution():
    scores = [_make_score(i, float(i * 10), rank=i) for i in range(1, 11)]
    save_scores(scores)

    dist = get_score_distribution(buckets=10)
    assert len(dist) == 10
    total = sum(b["count"] for b in dist)
    assert total == 10


def test_get_score_distribution_empty():
    dist = get_score_distribution()
    assert dist == []


# ---------------------------------------------------------------------------
# upsert_metadata
# ---------------------------------------------------------------------------

def test_upsert_metadata_insert_and_update():
    import scorer.database as db_module

    upsert_metadata(42, "mysubnet", "https://github.com/o/r", "https://mysite.io")
    with db_module.SessionLocal() as session:
        row = session.get(SubnetMetadataRow, 42)
        assert row.name == "mysubnet"
        first_seen = row.first_seen

    # Update
    upsert_metadata(42, "mysubnet-v2", None, None)
    with db_module.SessionLocal() as session:
        row = session.get(SubnetMetadataRow, 42)
        assert row.name == "mysubnet-v2"
        assert row.github_url is None
        assert row.first_seen == first_seen  # first_seen unchanged
