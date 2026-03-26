"""
Tests für api/main.py — alle Endpoints mit TestClient + gemockter DB-Schicht.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

NOW = "2025-06-01T06:00:00+00:00"

SCORES = [
    {
        "id": i, "netuid": i, "score": float((6 - i) * 15),
        "capital_score": float((6 - i) * 15 * 0.25),
        "activity_score": float((6 - i) * 15 * 0.25),
        "efficiency_score": float((6 - i) * 15 * 0.20),
        "health_score": float((6 - i) * 15 * 0.15),
        "dev_score": float((6 - i) * 15 * 0.15),
        "rank": i, "computed_at": NOW, "score_version": "v1",
    }
    for i in range(1, 6)
]  # scores: 75, 60, 45, 30, 15


def _make_meta(netuid: int):
    from api.models import SubnetMetadataResponse
    return SubnetMetadataResponse(
        netuid=netuid,
        name=f"subnet-{netuid}",
        github_url=f"https://github.com/org/repo{netuid}",
        website=f"https://subnet{netuid}.io",
        first_seen=NOW,
        last_updated=NOW,
    )


HISTORY = [
    {"computed_at": NOW, "score": 75.0, "rank": 1}
]


@pytest.fixture(scope="module")
def client():
    with patch("scorer.database.get_latest_scores", return_value=SCORES), \
         patch("scorer.database.get_score_history", return_value=HISTORY), \
         patch("scorer.database.get_score_distribution", return_value=[
             {"range_start": i * 20.0, "range_end": (i + 1) * 20.0, "count": 1}
             for i in range(5)
         ]):
        from api.main import app
        with TestClient(app) as c:
            yield c


def _with_db_mocks(meta_netuid=1):
    """Context manager that patches all DB-touching functions used by the API."""
    return patch.multiple(
        "api.main",
        get_latest_scores=MagicMock(return_value=SCORES),
        get_score_history=MagicMock(return_value=HISTORY),
        get_score_distribution=MagicMock(return_value=[
            {"range_start": i * 20.0, "range_end": (i + 1) * 20.0, "count": 1}
            for i in range(5)
        ]),
        _get_metadata=MagicMock(return_value=_make_meta(meta_netuid)),
    )


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

def test_health_ok():
    with _with_db_mocks():
        from api.main import app
        with TestClient(app) as c:
            resp = c.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["subnet_count"] == 5


# ---------------------------------------------------------------------------
# GET /api/v1/subnets
# ---------------------------------------------------------------------------

def test_list_subnets():
    with _with_db_mocks():
        from api.main import app
        with TestClient(app) as c:
            resp = c.get("/api/v1/subnets")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    scores = [s["score"] for s in data["subnets"]]
    assert scores == sorted(scores, reverse=True)


def test_list_subnets_limit():
    with _with_db_mocks():
        from api.main import app
        with TestClient(app) as c:
            resp = c.get("/api/v1/subnets?limit=2")
    assert resp.status_code == 200
    assert len(resp.json()["subnets"]) == 2


def test_list_subnets_offset():
    with _with_db_mocks():
        from api.main import app
        with TestClient(app) as c:
            resp = c.get("/api/v1/subnets?offset=3")
    assert resp.status_code == 200
    assert len(resp.json()["subnets"]) == 2


def test_list_subnets_min_score_filter():
    with _with_db_mocks():
        from api.main import app
        with TestClient(app) as c:
            resp = c.get("/api/v1/subnets?min_score=50")
    assert resp.status_code == 200
    for s in resp.json()["subnets"]:
        assert s["score"] >= 50


def test_list_subnets_max_score_filter():
    with _with_db_mocks():
        from api.main import app
        with TestClient(app) as c:
            resp = c.get("/api/v1/subnets?max_score=40")
    assert resp.status_code == 200
    for s in resp.json()["subnets"]:
        assert s["score"] <= 40


# ---------------------------------------------------------------------------
# GET /api/v1/subnets/{netuid}
# ---------------------------------------------------------------------------

def test_get_subnet_detail():
    with _with_db_mocks(meta_netuid=1):
        from api.main import app
        with TestClient(app) as c:
            resp = c.get("/api/v1/subnets/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["netuid"] == 1
    assert data["score"] == 75.0
    assert data["rank"] == 1
    assert "breakdown" in data
    assert "history" in data
    assert data["metadata"]["name"] == "subnet-1"


def test_get_subnet_includes_percentile():
    with _with_db_mocks(meta_netuid=1):
        from api.main import app
        with TestClient(app) as c:
            resp = c.get("/api/v1/subnets/1")
    data = resp.json()
    assert data["percentile"] is not None
    assert 0 <= data["percentile"] <= 100


def test_get_subnet_not_found():
    with _with_db_mocks():
        from api.main import app
        with TestClient(app) as c:
            resp = c.get("/api/v1/subnets/999")
    assert resp.status_code == 404
    assert "detail" in resp.json()


# ---------------------------------------------------------------------------
# GET /api/v1/subnets/{netuid}/history
# ---------------------------------------------------------------------------

def test_subnet_history():
    with _with_db_mocks():
        from api.main import app
        with TestClient(app) as c:
            resp = c.get("/api/v1/subnets/1/history?days=30")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "score" in data[0]
    assert "computed_at" in data[0]


def test_subnet_history_not_found():
    with patch("api.main.get_score_history", return_value=[]), \
         patch("api.main.get_latest_scores", return_value=SCORES):
        from api.main import app
        with TestClient(app) as c:
            resp = c.get("/api/v1/subnets/999/history")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/v1/scores/latest
# ---------------------------------------------------------------------------

def test_latest_run():
    with _with_db_mocks():
        from api.main import app
        with TestClient(app) as c:
            resp = c.get("/api/v1/scores/latest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["subnet_count"] == 5
    assert data["last_score_run"] is not None


# ---------------------------------------------------------------------------
# GET /api/v1/leaderboard
# ---------------------------------------------------------------------------

def test_leaderboard():
    with _with_db_mocks():
        from api.main import app
        with TestClient(app) as c:
            resp = c.get("/api/v1/leaderboard")
    assert resp.status_code == 200
    data = resp.json()
    assert "top" in data
    assert "bottom" in data
    top_scores = [s["score"] for s in data["top"]]
    assert top_scores == sorted(top_scores, reverse=True)
    assert data["bottom"][-1]["score"] == 15.0


# ---------------------------------------------------------------------------
# GET /api/v1/scores/distribution
# ---------------------------------------------------------------------------

def test_score_distribution():
    with _with_db_mocks():
        from api.main import app
        with TestClient(app) as c:
            resp = c.get("/api/v1/scores/distribution?buckets=5")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["buckets"]) == 5
    assert data["total_subnets"] == 5


# ---------------------------------------------------------------------------
# OpenAPI schema
# ---------------------------------------------------------------------------

def test_openapi_schema_available():
    from api.main import app
    with TestClient(app) as c:
        resp = c.get("/docs")
    assert resp.status_code == 200


def test_openapi_json():
    from api.main import app
    with TestClient(app) as c:
        resp = c.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert "/api/v1/subnets" in schema["paths"]
    assert "/api/v1/leaderboard" in schema["paths"]
    assert "/health" in schema["paths"]
