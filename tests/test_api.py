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
        "alpha_price_tao": float(i),
        "raw_data": {
            "label": "Compounding Quality" if i == 1 else "Evidence Limited",
            "thesis": "test thesis",
            "analysis": {
                "primary_outputs": {
                    "fundamental_quality": 70.0 - i,
                    "mispricing_signal": 60.0 - i,
                    "fragility_risk": 20.0 + i,
                    "signal_confidence": 80.0 - i,
                },
                "component_scores": {
                    "opportunity_gap": 12.0,
                    "stress_robustness": 66.0,
                }
            },
            "raw_metrics": {
                "slippage_10_tao": 0.1 * i,
                "performance_driven_by_few_actors": 0.2 * i,
            },
        },
    }
    for i in range(1, 6)
]  # scores: 75, 60, 45, 30, 15

ROOT_ROW = {
    "id": 999,
    "netuid": 0,
    "score": 99.0,
    "capital_score": 25.0,
    "activity_score": 25.0,
    "efficiency_score": 20.0,
    "health_score": 15.0,
    "dev_score": 10.0,
    "rank": None,
    "computed_at": NOW,
    "score_version": "v4_signal_separation",
    "alpha_price_tao": 1.0,
    "raw_data": {
        "label": "Root Infrastructure",
        "thesis": "context only",
        "investable": False,
        "special_case": "root_subnet",
        "analysis": {},
    },
}


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
    meta = _make_meta(meta_netuid)
    all_meta = {meta_netuid: {"name": meta.name, "github_url": meta.github_url,
                               "website": meta.website, "first_seen": meta.first_seen,
                               "last_updated": meta.last_updated}}
    return patch.multiple(
        "api.main",
        get_scores_since=MagicMock(return_value=SCORES),
        get_latest_scores=MagicMock(return_value=SCORES),
        get_score_history=MagicMock(return_value=HISTORY),
        get_score_distribution=MagicMock(return_value=[
            {"range_start": i * 20.0, "range_end": (i + 1) * 20.0, "count": 1}
            for i in range(5)
        ]),
        get_all_metadata=MagicMock(return_value=all_meta),
        _get_metadata=MagicMock(return_value=_make_meta(meta_netuid)),
    )


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------

def test_root():
    from api.main import app
    with TestClient(app) as c:
        resp = c.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "subnet-intelligence-api"
    assert data["health_url"] == "/health"


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


def test_api_health_ok():
    with _with_db_mocks():
        from api.main import app
        with TestClient(app) as c:
            resp = c.get("/api/health")
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


def test_list_subnets_includes_investability_status_and_warning_flags():
    rows = [
        {
            **SCORES[0],
            "raw_data": {
                **SCORES[0]["raw_data"],
                "analysis": {
                    **SCORES[0]["raw_data"]["analysis"],
                    "block_scores": {"market_legitimacy": 40.0},
                    "conditioning": {"visibility": {"discarded": ["alpha_price_tao"]}},
                },
                "raw_metrics": {
                    "slippage_10_tao": 0.12,
                    "performance_driven_by_few_actors": 0.72,
                },
            },
        }
    ]
    with patch("api.main.get_latest_scores", return_value=rows), \
         patch("api.main.get_all_metadata", return_value={}), \
         patch("api.main.get_score_history", return_value=HISTORY), \
         patch("api.main.get_score_distribution", return_value=[]), \
         patch("api.main.get_scores_since", return_value=rows), \
         patch("api.main._get_metadata", return_value=None):
        from api.main import app
        with TestClient(app) as c:
            resp = c.get("/api/v1/subnets")

    assert resp.status_code == 200
    row = resp.json()["subnets"][0]
    assert row["investability_status"] == "constrained"
    assert "thin_liquidity" in row["warning_flags"]
    assert "concentration" in row["warning_flags"]
    assert "telemetry_gap" in row["warning_flags"]


def test_list_subnets_ignores_history_only_visibility_gaps():
    rows = [
        {
            **SCORES[0],
            "raw_data": {
                **SCORES[0]["raw_data"],
                "analysis": {
                    **SCORES[0]["raw_data"]["analysis"],
                    "conditioning": {
                        "visibility": {
                            "discarded": ["history.alpha_price_tao", "history.market_structure_floor"],
                            "reconstructed": ["history.opportunity_gap"],
                        }
                    },
                },
                "raw_metrics": {
                    "slippage_10_tao": 0.01,
                    "performance_driven_by_few_actors": 0.10,
                },
            },
        }
    ]
    with patch("api.main.get_latest_scores", return_value=rows), \
         patch("api.main.get_all_metadata", return_value={}), \
         patch("api.main.get_score_history", return_value=HISTORY), \
         patch("api.main.get_score_distribution", return_value=[]), \
         patch("api.main.get_scores_since", return_value=rows), \
         patch("api.main._get_metadata", return_value=None), \
         patch("api.main._cache_get", return_value=None):
        from api.main import app
        with TestClient(app) as c:
            resp = c.get("/api/v1/subnets")

    assert resp.status_code == 200
    row = resp.json()["subnets"][0]
    assert "telemetry_gap" not in row["warning_flags"]
    assert "reconstructed_inputs" not in row["warning_flags"]


def test_concentration_alone_does_not_force_speculative_when_structure_is_strong():
    row = {
        **SCORES[0],
        "raw_data": {
            **SCORES[0]["raw_data"],
            "analysis": {
                **SCORES[0]["raw_data"]["analysis"],
                "block_scores": {
                    "market_legitimacy": 72.0,
                    "structural_validity": 82.0,
                    "investability_gate": 75.0,
                },
            },
            "raw_metrics": {
                "slippage_10_tao": 0.03,
                "performance_driven_by_few_actors": 0.61,
            },
        },
    }
    row["raw_data"]["analysis"]["primary_outputs"] = {
        "fundamental_quality": 76.0,
        "mispricing_signal": 46.0,
        "fragility_risk": 22.0,
        "signal_confidence": 54.0,
    }

    with patch("api.main.get_latest_scores", return_value=[row]), \
         patch("api.main.get_all_metadata", return_value={}), \
         patch("api.main.get_score_history", return_value=HISTORY), \
         patch("api.main.get_score_distribution", return_value=[]), \
         patch("api.main.get_scores_since", return_value=[row]), \
         patch("api.main._get_metadata", return_value=None):
        from api.main import app
        with TestClient(app) as c:
            resp = c.get("/api/v1/subnets")

    assert resp.status_code == 200
    summary = resp.json()["subnets"][0]
    assert summary["investability_status"] == "investable"


def test_strong_quality_case_with_just_below_old_threshold_can_be_investable():
    row = {
        **SCORES[0],
        "raw_data": {
            **SCORES[0]["raw_data"],
            "analysis": {
                **SCORES[0]["raw_data"]["analysis"],
                "block_scores": {
                    "market_legitimacy": 70.0,
                    "structural_validity": 78.0,
                    "investability_gate": 74.5,
                },
            },
            "raw_metrics": {
                "slippage_10_tao": 0.03,
                "performance_driven_by_few_actors": 0.40,
            },
        },
    }
    row["raw_data"]["analysis"]["primary_outputs"] = {
        "fundamental_quality": 67.0,
        "mispricing_signal": 44.2,
        "fragility_risk": 24.0,
        "signal_confidence": 53.2,
    }

    with patch("api.main.get_latest_scores", return_value=[row]), \
         patch("api.main.get_all_metadata", return_value={}), \
         patch("api.main.get_score_history", return_value=HISTORY), \
         patch("api.main.get_score_distribution", return_value=[]), \
         patch("api.main.get_scores_since", return_value=[row]), \
         patch("api.main._get_metadata", return_value=None):
        from api.main import app
        with TestClient(app) as c:
            resp = c.get("/api/v1/subnets")

    assert resp.status_code == 200
    summary = resp.json()["subnets"][0]
    assert summary["warning_flags"] == []
    assert summary["investability_status"] == "investable"


def test_list_subnets_excludes_root_subnet():
    rows = [ROOT_ROW, *SCORES]
    with patch("api.main.get_latest_scores", return_value=rows), \
         patch("api.main.get_all_metadata", return_value={}), \
         patch("api.main.get_score_history", return_value=HISTORY), \
         patch("api.main.get_score_distribution", return_value=[]), \
         patch("api.main.get_scores_since", return_value=rows), \
         patch("api.main._get_metadata", return_value=None):
        from api.main import app
        with TestClient(app) as c:
            resp = c.get("/api/v1/subnets")
    assert resp.status_code == 200
    netuids = [row["netuid"] for row in resp.json()["subnets"]]
    assert 0 not in netuids


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


def test_list_subnets_sort_by_signal_confidence_desc():
    with _with_db_mocks():
        from api.main import app
        with TestClient(app) as c:
            resp = c.get("/api/v1/subnets?sort_by=signal_confidence&sort_order=desc")
    assert resp.status_code == 200
    values = [row["primary_outputs"]["signal_confidence"] for row in resp.json()["subnets"]]
    assert values == sorted(values, reverse=True)


def test_list_subnets_sort_by_mispricing_signal_desc():
    with _with_db_mocks():
        from api.main import app
        with TestClient(app) as c:
            resp = c.get("/api/v1/subnets?sort_by=mispricing_signal&sort_order=desc")
    assert resp.status_code == 200
    values = [row["primary_outputs"]["mispricing_signal"] for row in resp.json()["subnets"]]
    assert values == sorted(values, reverse=True)


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
    assert data["primary_outputs"]["fundamental_quality"] == 69.0
    assert "breakdown" in data
    assert "history" in data
    assert data["metadata"]["name"] == "subnet-1"
    assert data["investability_status"] is not None
    assert isinstance(data["warning_flags"], list)
    assert data["research_summary"]["setup_status"] in {
        "strong_setup",
        "improving_setup",
        "fragile_setup",
        "not_investable",
    }
    assert data["research_summary"]["market_capacity"] in {"very_low", "low", "medium", "high"}
    assert data["research_summary"]["evidence_strength"] in {"low", "medium", "high"}
    assert data["research_summary"]["why_now"]
    assert data["research_summary"]["main_constraint"]
    assert data["research_summary"]["break_condition"]
    assert data["research_summary"]["relative_peer_context"]


def test_list_subnets_uses_override_name_fallback():
    rows = [
        {
            **SCORES[0],
            "netuid": 64,
            "raw_data": {"label": "Evidence Limited", "thesis": "test thesis", "analysis": {}},
        }
    ]
    with patch("api.main.get_latest_scores", return_value=rows), \
         patch("api.main.get_all_metadata", return_value={}), \
         patch("api.main.get_score_history", return_value=HISTORY), \
         patch("api.main.get_score_distribution", return_value=[]), \
         patch("api.main.get_scores_since", return_value=rows), \
          patch("api.main._get_metadata", return_value=None), \
         patch("api.main._override_name_map", return_value={64: "Chutes"}), \
         patch("api.main._cache_get", return_value=None):
        from api.main import app
        with TestClient(app) as c:
            resp = c.get("/api/v1/subnets")
    assert resp.status_code == 200
    assert resp.json()["subnets"][0]["name"] == "Chutes"


def test_get_root_subnet_detail_still_available():
    rows = [ROOT_ROW, *SCORES]
    with patch("api.main.get_latest_scores", return_value=rows), \
         patch("api.main.get_all_metadata", return_value={}), \
         patch("api.main.get_score_history", return_value=HISTORY), \
         patch("api.main.get_score_distribution", return_value=[]), \
         patch("api.main.get_scores_since", return_value=rows), \
         patch("api.main._get_metadata", return_value=None):
        from api.main import app
        with TestClient(app) as c:
            resp = c.get("/api/v1/subnets/0")
    assert resp.status_code == 200
    data = resp.json()
    assert data["netuid"] == 0
    assert data["rank"] is None
    assert data["label"] == "Root Infrastructure"
    assert data["research_summary"]["setup_status"] == "not_investable"


def test_get_subnet_detail_research_summary_respects_breakers_and_telemetry():
    row = {
        **SCORES[0],
        "market_cap_tao": 82000.0,
        "tao_in_pool": 9800.0,
        "raw_data": {
            **SCORES[0]["raw_data"],
            "analysis": {
                **SCORES[0]["raw_data"]["analysis"],
                "top_positive_drivers": [{"name": "fundamental_health", "short_explanation": "fundamental health is improving"}],
                "top_negative_drags": [{"name": "reserve_growth_without_price", "short_explanation": "price still lags the fundamentals"}],
                "key_uncertainties": [{"name": "external_data_reliability", "short_explanation": "external evidence is still thin"}],
                "thesis_breakers": ["The setup breaks if the market stops rewarding improving quality."],
                "conditioning": {
                    "reliability": {
                        "market_data_reliability": 0.81,
                        "history_data_reliability": 0.76,
                    },
                    "visibility": {"discarded": []},
                },
            },
        },
    }

    with patch("api.main.get_latest_scores", return_value=[row]), \
         patch("api.main.get_all_metadata", return_value={}), \
         patch("api.main.get_score_history", return_value=HISTORY), \
         patch("api.main.get_score_distribution", return_value=[]), \
         patch("api.main.get_scores_since", return_value=[row]), \
         patch("api.main._get_metadata", return_value=None), \
         patch("api.main._cache_get", return_value=None):
        from api.main import app
        with TestClient(app) as c:
            resp = c.get("/api/v1/subnets/1")

    assert resp.status_code == 200
    summary = resp.json()["research_summary"]
    assert summary["market_capacity"] == "medium"
    assert summary["evidence_strength"] == "high"
    assert "operating quality" in summary["why_now"].lower()
    assert "price" in summary["main_constraint"].lower()
    assert summary["break_condition"] == "The setup breaks if the market stops rewarding improving quality."


def test_get_subnet_normalizes_schema_stale_analysis_fields():
    stale_row = {
        **SCORES[0],
        "raw_data": {
            "label": "Evidence Limited",
            "thesis": "test thesis",
            "analysis": {
                "primary_outputs": {
                    "fundamental_quality": 40.0,
                    "mispricing_signal": 20.0,
                    "fragility_risk": 70.0,
                    "signal_confidence": 35.0,
                },
                "top_negative_drivers": [{"name": "fragility"}],
            },
        },
    }
    with patch("api.main.get_latest_scores", return_value=[stale_row]), \
         patch("api.main.get_all_metadata", return_value={}), \
         patch("api.main.get_score_history", return_value=HISTORY), \
         patch("api.main.get_score_distribution", return_value=[]), \
         patch("api.main.get_scores_since", return_value=[stale_row]), \
         patch("api.main._get_metadata", return_value=None), \
         patch("api.main._cache_get", return_value=None):
        from api.main import app
        with TestClient(app) as c:
            resp = c.get("/api/v1/subnets/1")

    assert resp.status_code == 200
    analysis = resp.json()["analysis"]
    assert analysis["top_negative_drags"] == [{"name": "fragility"}]
    assert analysis["key_uncertainties"] == []
    assert analysis["analysis_schema_stale"] is True


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


def test_subnet_detailed_history():
    history = [
        {
            "computed_at": NOW,
            "score": 75.0,
            "rank": 1,
            "score_version": "v5_investment_framework",
            "raw_data": {
                "label": "Compounding Quality",
                "thesis": "test thesis",
                "analysis": {
                    "primary_outputs": {
                        "fundamental_quality": 69.0,
                        "mispricing_signal": 59.0,
                        "fragility_risk": 21.0,
                        "signal_confidence": 79.0,
                    },
                    "block_scores": {
                        "fundamental_health": 70.0,
                        "opportunity_underreaction": 61.0,
                    },
                    "conditioning": {
                        "reliability": {
                            "external_data_reliability": 0.8,
                        }
                    },
                    "top_positive_drivers": [{"name": "fundamental_health"}],
                    "top_negative_drags": [{"name": "base_opportunity"}],
                },
            },
        }
    ]
    with patch("api.main.get_score_history", return_value=history), \
         patch("api.main.get_latest_scores", return_value=SCORES), \
         patch("api.main._cache_get", return_value=None):
        from api.main import app
        with TestClient(app) as c:
            resp = c.get("/api/v1/subnets/1/history/detailed?days=30")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert data[0]["computed_at"] == NOW
    assert data[0]["label"] == "Compounding Quality"
    assert data[0]["primary_outputs"]["fundamental_quality"] == 69.0
    assert data[0]["block_scores"]["fundamental_health"] == 70.0
    assert data[0]["conditioning_reliability"]["external_data_reliability"] == 0.8
    assert data[0]["top_positive_drivers"][0]["name"] == "fundamental_health"
    assert data[0]["top_negative_drags"][0]["name"] == "base_opportunity"


def test_subnet_history_not_found():
    with patch("api.main.get_score_history", return_value=[]), \
         patch("api.main.get_latest_scores", return_value=SCORES):
        from api.main import app
        with TestClient(app) as c:
            resp = c.get("/api/v1/subnets/999/history")
    assert resp.status_code == 404


def test_subnet_detailed_history_not_found():
    with patch("api.main.get_score_history", return_value=[]), \
         patch("api.main.get_latest_scores", return_value=SCORES):
        from api.main import app
        with TestClient(app) as c:
            resp = c.get("/api/v1/subnets/999/history/detailed")
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


def test_leaderboard_excludes_root_subnet():
    rows = [ROOT_ROW, *SCORES]
    with patch("api.main.get_latest_scores", return_value=rows), \
         patch("api.main.get_all_metadata", return_value={}), \
         patch("api.main.get_score_history", return_value=HISTORY), \
         patch("api.main.get_score_distribution", return_value=[]), \
         patch("api.main.get_scores_since", return_value=rows), \
         patch("api.main._get_metadata", return_value=None):
        from api.main import app
        with TestClient(app) as c:
            resp = c.get("/api/v1/leaderboard")
    assert resp.status_code == 200
    top_netuids = [row["netuid"] for row in resp.json()["top"]]
    assert 0 not in top_netuids


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


def test_backtest_labels():
    rows = [
        {
            "id": 1,
            "netuid": 1,
            "score": 70.0,
            "capital_score": 0.0,
            "activity_score": 0.0,
            "efficiency_score": 0.0,
            "health_score": 0.0,
            "dev_score": 0.0,
            "rank": 1,
            "computed_at": "2025-06-01T00:00:00+00:00",
            "score_version": "v1",
            "alpha_price_tao": 1.0,
            "raw_data": {
                "label": "Compounding Quality",
                "analysis": {
                    "primary_outputs": {
                        "fundamental_quality": 71.0,
                        "mispricing_signal": 62.0,
                        "fragility_risk": 28.0,
                        "signal_confidence": 76.0,
                    },
                    "component_scores": {"opportunity_gap": 15.0, "stress_robustness": 70.0},
                },
                "raw_metrics": {"slippage_10_tao": 0.10, "performance_driven_by_few_actors": 0.20},
            },
        },
        {
            "id": 2,
            "netuid": 1,
            "score": 75.0,
            "capital_score": 0.0,
            "activity_score": 0.0,
            "efficiency_score": 0.0,
            "health_score": 0.0,
            "dev_score": 0.0,
            "rank": 1,
            "computed_at": "2025-06-02T00:00:00+00:00",
            "score_version": "v1",
            "alpha_price_tao": 1.2,
            "raw_data": {
                "label": "Compounding Quality",
                "analysis": {
                    "primary_outputs": {
                        "fundamental_quality": 74.0,
                        "mispricing_signal": 65.0,
                        "fragility_risk": 30.0,
                        "signal_confidence": 79.0,
                    },
                    "component_scores": {"opportunity_gap": 17.0, "stress_robustness": 72.0},
                },
                "raw_metrics": {"slippage_10_tao": 0.12, "performance_driven_by_few_actors": 0.25},
            },
        },
    ]
    with patch("api.main.get_scores_since", return_value=rows), \
         patch("api.main.get_latest_scores", return_value=rows):
        from api.main import app
        with TestClient(app) as c:
            resp = c.get("/api/v1/backtests/labels?days=90")
    assert resp.status_code == 200
    data = resp.json()
    assert data["observations"] == 1
    assert "relative_forward_return_vs_tao_30d" in data["targets"]
    assert data["labels"][0]["label"] == "Compounding Quality"


def test_live_cache_key_changes_when_new_run_arrives():
    from api.main import _live_cache_key

    earlier_rows = [{"netuid": 1, "computed_at": "2026-03-31T14:00:00+00:00"}]
    later_rows = [{"netuid": 1, "computed_at": "2026-03-31T15:00:00+00:00"}]

    with patch("api.main.get_all_metadata", return_value={1: {"last_updated": "2026-03-31T14:01:00+00:00"}}):
        first_key = _live_cache_key("list", 50, 0, 0.0, 100.0, rows=earlier_rows)
    with patch("api.main.get_all_metadata", return_value={1: {"last_updated": "2026-03-31T15:01:00+00:00"}}):
        second_key = _live_cache_key("list", 50, 0, 0.0, 100.0, rows=later_rows)

    assert first_key != second_key
    assert "run=2026-03-31T15:00:00+00:00:1" in second_key
    assert "meta=2026-03-31T15:01:00+00:00:1" in second_key


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
    assert "/" in schema["paths"]
    assert "/api/health" in schema["paths"]
    assert "/api/v1/subnets" in schema["paths"]
    assert "/api/v1/leaderboard" in schema["paths"]
    assert "/health" in schema["paths"]


def test_openapi_marks_label_as_deprecated_compatibility_field():
    from api.main import app
    with TestClient(app) as c:
        resp = c.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    summary_props = schema["components"]["schemas"]["SubnetSummaryResponse"]["properties"]
    detail_props = schema["components"]["schemas"]["SubnetDetailResponse"]["properties"]
    assert summary_props["label"]["deprecated"] is True
    assert detail_props["label"]["deprecated"] is True
