"""
api/main.py — FastAPI REST API for Subnet Intelligence.

Run with:
  uvicorn api.main:app --reload
  Docs: http://localhost:8000/docs
"""

import logging
import json
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from functools import wraps
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.models import (
    BacktestLabelSummary,
    BacktestObservation,
    BacktestResponse,
    DistributionBucket,
    DistributionResponse,
    ErrorResponse,
    HealthResponse,
    LeaderboardResponse,
    LatestRunResponse,
    PrimaryOutputsResponse,
    ScoreBreakdownResponse,
    ScoreHistoryPoint,
    SubnetDetailResponse,
    SubnetListResponse,
    SubnetMetadataResponse,
    SubnetSummaryResponse,
)
from scorer.database import (
    SessionLocal,
    SubnetMetadataRow,
    SubnetScoreRow,
    get_all_metadata,
    get_latest_scores,
    get_scores_since,
    get_score_distribution,
    get_score_history,
    get_top_subnets,
)
from backtests.engine import build_backtest_summary

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Simple in-memory cache (TTL-based)
# ---------------------------------------------------------------------------

_cache: dict[str, tuple[Any, float]] = {}
_CACHE_TTL = 3600  # 1 hour
_SEED_NAMES_PATH = Path(__file__).resolve().parent.parent / "data" / "subnet_names.json"


def _cache_get(key: str) -> Any:
    entry = _cache.get(key)
    if entry and time.time() < entry[1]:
        return entry[0]
    return None


def _cache_set(key: str, value: Any) -> None:
    _cache[key] = (value, time.time() + _CACHE_TTL)


def _seed_name_map() -> dict[int, str]:
    cached = _cache_get("seed_names")
    if cached is not None:
        return cached
    try:
        raw = json.loads(_SEED_NAMES_PATH.read_text(encoding="utf-8"))
        result = {int(k): v for k, v in raw.items() if k.isdigit() and isinstance(v, str)}
    except Exception:
        result = {}
    _cache_set("seed_names", result)
    return result


# ---------------------------------------------------------------------------
# Simple rate limiter (sliding window, per IP)
# ---------------------------------------------------------------------------

_rate_counts: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT = 100  # requests
_RATE_WINDOW = 60  # seconds


async def _check_rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    window_start = now - _RATE_WINDOW
    hits = _rate_counts[ip]
    # prune old entries
    _rate_counts[ip] = [t for t in hits if t > window_start]
    if len(_rate_counts[ip]) >= _RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded: 100 req/min")
    _rate_counts[ip].append(now)


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Subnet Intelligence API starting up")
    yield
    logger.info("Subnet Intelligence API shutting down")


app = FastAPI(
    title="Subnet Intelligence API",
    description="Automated Bittensor Subnet Scoring — public REST API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _total_subnet_count() -> int:
    return len([row for row in get_latest_scores() if _is_investable_row(row)])


def _compute_percentile(rank: Optional[int], total: int) -> Optional[float]:
    if rank is None or total == 0:
        return None
    return round((1 - (rank - 1) / total) * 100, 1)


def _is_investable_row(row: dict) -> bool:
    raw_data = row.get("raw_data") or {}
    return raw_data.get("investable", True)


def _row_to_summary(row: dict, total: int, meta: Optional[SubnetMetadataResponse] = None) -> SubnetSummaryResponse:
    raw_data = row.get("raw_data") or {}
    fallback_name = _seed_name_map().get(row["netuid"])
    primary_outputs = raw_data.get("analysis", {}).get("primary_outputs") or raw_data.get("primary_outputs")
    return SubnetSummaryResponse(
        netuid=row["netuid"],
        name=(meta.name if meta else None) or fallback_name,
        score=row["score"],
        primary_outputs=PrimaryOutputsResponse(**primary_outputs) if primary_outputs else None,
        rank=row["rank"],
        percentile=_compute_percentile(row.get("rank"), total),
        computed_at=row.get("computed_at"),
        score_version=row.get("score_version", "v1"),
        alpha_price_tao=row.get("alpha_price_tao"),
        tao_in_pool=row.get("tao_in_pool"),
        market_cap_tao=row.get("market_cap_tao"),
        staking_apy=row.get("staking_apy"),
        label=raw_data.get("label"),
        thesis=raw_data.get("thesis"),
    )


def _get_metadata(netuid: int) -> Optional[SubnetMetadataResponse]:
    with SessionLocal() as session:
        row = session.get(SubnetMetadataRow, netuid)
        if row is None:
            return None
        return SubnetMetadataResponse(
            netuid=row.netuid,
            name=row.name or _seed_name_map().get(netuid),
            github_url=row.github_url,
            website=row.website,
            first_seen=row.first_seen.isoformat() if row.first_seen else None,
            last_updated=row.last_updated.isoformat() if row.last_updated else None,
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get(
    "/",
    summary="Service root",
    tags=["System"],
)
async def root() -> dict[str, Any]:
    return {
        "service": "subnet-intelligence-api",
        "status": "ok",
        "docs_url": "/docs",
        "health_url": "/health",
        "api_health_url": "/api/health",
    }

@app.get(
    "/api/v1/subnets",
    response_model=SubnetListResponse,
    summary="List all subnets with current scores",
    tags=["Subnets"],
)
async def list_subnets(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    min_score: float = Query(0.0, ge=0, le=100),
    max_score: float = Query(100.0, ge=0, le=100),
    _: None = Depends(_check_rate_limit),
) -> SubnetListResponse:
    cache_key = f"list:{limit}:{offset}:{min_score}:{max_score}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    all_rows = [r for r in get_latest_scores() if _is_investable_row(r)]
    meta_by_netuid = get_all_metadata()
    filtered = [r for r in all_rows if min_score <= r["score"] <= max_score]
    total = len(filtered)
    page = filtered[offset: offset + limit]

    subnets = []
    for r in page:
        meta_dict = meta_by_netuid.get(r["netuid"])
        meta = SubnetMetadataResponse(netuid=r["netuid"], **(meta_dict or {})) if meta_dict else None
        subnets.append(_row_to_summary(r, total, meta))

    result = SubnetListResponse(total=total, subnets=subnets)
    _cache_set(cache_key, result)
    return result


@app.get(
    "/api/v1/subnets/{netuid}",
    response_model=SubnetDetailResponse,
    summary="Subnet detail with breakdown and history",
    tags=["Subnets"],
    responses={404: {"model": ErrorResponse}},
)
async def get_subnet(
    request: Request,
    netuid: int,
    _: None = Depends(_check_rate_limit),
) -> SubnetDetailResponse:
    cache_key = f"subnet:{netuid}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    all_rows = get_latest_scores()
    investable_rows = [r for r in all_rows if _is_investable_row(r)]
    total = len(investable_rows)

    row = next((r for r in all_rows if r["netuid"] == netuid), None)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Subnet {netuid} not found")

    history_raw = get_score_history(netuid, days=30)
    history = [
        ScoreHistoryPoint(
            computed_at=h["computed_at"],
            score=h["score"],
            rank=h.get("rank"),
        )
        for h in history_raw
    ]

    # Score delta: current vs oldest point in 7-day window
    score_delta_7d: Optional[float] = None
    if len(history_raw) >= 2:
        score_delta_7d = round(row["score"] - history_raw[0]["score"], 1)

    meta = _get_metadata(netuid)

    detail_primary_outputs = (((row.get("raw_data") or {}).get("analysis", {}) or {}).get("primary_outputs"))

    result = SubnetDetailResponse(
        netuid=netuid,
        name=(meta.name if meta else None) or _seed_name_map().get(netuid),
        score=row["score"],
        primary_outputs=PrimaryOutputsResponse(**detail_primary_outputs) if detail_primary_outputs else None,
        rank=row.get("rank"),
        percentile=_compute_percentile(row.get("rank"), total),
        breakdown=ScoreBreakdownResponse(
            capital_score=row["capital_score"],
            activity_score=row["activity_score"],
            efficiency_score=row["efficiency_score"],
            health_score=row["health_score"],
            dev_score=row["dev_score"],
        ),
        history=history,
        metadata=meta,
        computed_at=row.get("computed_at"),
        score_version=row.get("score_version", "v1"),
        alpha_price_tao=row.get("alpha_price_tao"),
        tao_in_pool=row.get("tao_in_pool"),
        market_cap_tao=row.get("market_cap_tao"),
        staking_apy=row.get("staking_apy"),
        score_delta_7d=score_delta_7d,
        label=(row.get("raw_data") or {}).get("label"),
        thesis=(row.get("raw_data") or {}).get("thesis"),
        analysis=(row.get("raw_data") or {}).get("analysis"),
    )
    _cache_set(cache_key, result)
    return result


@app.get(
    "/api/v1/subnets/{netuid}/history",
    response_model=list[ScoreHistoryPoint],
    summary="Score history for a subnet",
    tags=["Subnets"],
    responses={404: {"model": ErrorResponse}},
)
async def get_subnet_history(
    request: Request,
    netuid: int,
    days: int = Query(30, ge=1, le=365),
    _: None = Depends(_check_rate_limit),
) -> list[ScoreHistoryPoint]:
    cache_key = f"history:{netuid}:{days}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    history_raw = get_score_history(netuid, days=days)
    if not history_raw:
        raise HTTPException(status_code=404, detail=f"No history for subnet {netuid}")

    result = [
        ScoreHistoryPoint(
            computed_at=h["computed_at"],
            score=h["score"],
            rank=h.get("rank"),
        )
        for h in history_raw
    ]
    _cache_set(cache_key, result)
    return result


@app.get(
    "/api/v1/scores/latest",
    response_model=LatestRunResponse,
    summary="Timestamp and count of the most recent score run",
    tags=["Scores"],
)
async def latest_run(
    request: Request,
    _: None = Depends(_check_rate_limit),
) -> LatestRunResponse:
    cached = _cache_get("latest_run")
    if cached is not None:
        return cached

    rows = get_latest_scores()
    investable_rows = [r for r in rows if _is_investable_row(r)]
    last_ts = max((r["computed_at"] for r in rows if r.get("computed_at")), default=None)
    result = LatestRunResponse(last_score_run=last_ts, subnet_count=len(investable_rows))
    _cache_set("latest_run", result)
    return result


@app.get(
    "/api/v1/leaderboard",
    response_model=LeaderboardResponse,
    summary="Top 20 and bottom 5 subnets",
    tags=["Scores"],
)
async def leaderboard(
    request: Request,
    _: None = Depends(_check_rate_limit),
) -> LeaderboardResponse:
    cached = _cache_get("leaderboard")
    if cached is not None:
        return cached

    all_rows = [r for r in get_latest_scores() if _is_investable_row(r)]
    meta_by_netuid = get_all_metadata()
    total = len(all_rows)

    def _with_meta(r: dict) -> SubnetSummaryResponse:
        md = meta_by_netuid.get(r["netuid"])
        m = SubnetMetadataResponse(netuid=r["netuid"], **(md or {})) if md else None
        return _row_to_summary(r, total, m)

    top = [_with_meta(r) for r in all_rows[:20]]
    bottom = [_with_meta(r) for r in all_rows[-5:]]
    result = LeaderboardResponse(top=top, bottom=bottom)
    _cache_set("leaderboard", result)
    return result


@app.get(
    "/api/v1/scores/distribution",
    response_model=DistributionResponse,
    summary="Score distribution histogram",
    tags=["Scores"],
)
async def score_distribution(
    request: Request,
    buckets: int = Query(10, ge=2, le=20),
    _: None = Depends(_check_rate_limit),
) -> DistributionResponse:
    cache_key = f"distribution:{buckets}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    dist = get_score_distribution(buckets=buckets)
    result = DistributionResponse(
        buckets=[DistributionBucket(**b) for b in dist],
        total_subnets=_total_subnet_count(),
    )
    _cache_set(cache_key, result)
    return result


@app.get(
    "/api/v1/backtests/labels",
    response_model=BacktestResponse,
    summary="Backtest summary by label and forward proxies",
    tags=["Backtests"],
)
async def backtest_labels(
    request: Request,
    days: int = Query(90, ge=7, le=365),
    _: None = Depends(_check_rate_limit),
) -> BacktestResponse:
    cache_key = f"backtests:{days}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    rows = get_scores_since(days=days)
    summary = build_backtest_summary(rows)
    result = BacktestResponse(
        observations=summary["observations"],
        targets=summary["targets"],
        labels=[BacktestLabelSummary(**row) for row in summary["labels"]],
        examples=[BacktestObservation(**row) for row in summary["examples"]],
    )
    _cache_set(cache_key, result)
    return result


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    tags=["System"],
)
async def health() -> HealthResponse:
    try:
        rows = get_latest_scores()
        last_ts = max((r["computed_at"] for r in rows if r.get("computed_at")), default=None)
        return HealthResponse(status="ok", last_score_run=last_ts, subnet_count=len(rows))
    except Exception as exc:
        logger.warning("DB unavailable during health check: %s", exc)
        return HealthResponse(status="degraded", last_score_run=None, subnet_count=0)


@app.get(
    "/api/health",
    response_model=HealthResponse,
    summary="API health check",
    tags=["System"],
)
async def api_health() -> HealthResponse:
    return await health()
