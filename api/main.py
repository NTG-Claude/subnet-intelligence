"""
api/main.py — FastAPI REST API for Subnet Intelligence.

Run with:
  uvicorn api.main:app --reload
  Docs: http://localhost:8000/docs
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.decorator import cache
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from api.models import (
    DistributionBucket,
    DistributionResponse,
    ErrorResponse,
    HealthResponse,
    LeaderboardResponse,
    LatestRunResponse,
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
    get_latest_scores,
    get_score_distribution,
    get_score_history,
    get_top_subnets,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    FastAPICache.init(InMemoryBackend(), prefix="subnet-intelligence")
    yield


app = FastAPI(
    title="Subnet Intelligence API",
    description="Automated Bittensor Subnet Scoring — public REST API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
    return len(get_latest_scores())


def _compute_percentile(rank: Optional[int], total: int) -> Optional[float]:
    if rank is None or total == 0:
        return None
    return round((1 - (rank - 1) / total) * 100, 1)


def _row_to_summary(row: dict, total: int) -> SubnetSummaryResponse:
    return SubnetSummaryResponse(
        netuid=row["netuid"],
        score=row["score"],
        rank=row["rank"],
        percentile=_compute_percentile(row.get("rank"), total),
        computed_at=row.get("computed_at"),
        score_version=row.get("score_version", "v1"),
    )


def _get_metadata(netuid: int) -> Optional[SubnetMetadataResponse]:
    with SessionLocal() as session:
        row = session.get(SubnetMetadataRow, netuid)
        if row is None:
            return None
        return SubnetMetadataResponse(
            netuid=row.netuid,
            name=row.name,
            github_url=row.github_url,
            website=row.website,
            first_seen=row.first_seen.isoformat() if row.first_seen else None,
            last_updated=row.last_updated.isoformat() if row.last_updated else None,
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get(
    "/api/v1/subnets",
    response_model=SubnetListResponse,
    summary="List all subnets with current scores",
    tags=["Subnets"],
)
@cache(expire=3600)
@limiter.limit("100/minute")
async def list_subnets(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    min_score: float = Query(0.0, ge=0, le=100),
    max_score: float = Query(100.0, ge=0, le=100),
) -> SubnetListResponse:
    all_rows = get_latest_scores()
    filtered = [
        r for r in all_rows
        if min_score <= r["score"] <= max_score
    ]
    total = len(filtered)
    page = filtered[offset: offset + limit]

    return SubnetListResponse(
        total=total,
        subnets=[_row_to_summary(r, total) for r in page],
    )


@app.get(
    "/api/v1/subnets/{netuid}",
    response_model=SubnetDetailResponse,
    summary="Subnet detail with breakdown and history",
    tags=["Subnets"],
    responses={404: {"model": ErrorResponse}},
)
@cache(expire=3600)
@limiter.limit("100/minute")
async def get_subnet(request: Request, netuid: int) -> SubnetDetailResponse:
    all_rows = get_latest_scores()
    total = len(all_rows)

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

    meta = _get_metadata(netuid)

    return SubnetDetailResponse(
        netuid=netuid,
        name=meta.name if meta else None,
        score=row["score"],
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
    )


@app.get(
    "/api/v1/subnets/{netuid}/history",
    response_model=list[ScoreHistoryPoint],
    summary="Score history for a subnet",
    tags=["Subnets"],
    responses={404: {"model": ErrorResponse}},
)
@cache(expire=3600)
@limiter.limit("100/minute")
async def get_subnet_history(
    request: Request,
    netuid: int,
    days: int = Query(30, ge=1, le=365),
) -> list[ScoreHistoryPoint]:
    history_raw = get_score_history(netuid, days=days)
    if not history_raw:
        raise HTTPException(status_code=404, detail=f"No history for subnet {netuid}")
    return [
        ScoreHistoryPoint(
            computed_at=h["computed_at"],
            score=h["score"],
            rank=h.get("rank"),
        )
        for h in history_raw
    ]


@app.get(
    "/api/v1/scores/latest",
    response_model=LatestRunResponse,
    summary="Timestamp and count of the most recent score run",
    tags=["Scores"],
)
@cache(expire=3600)
@limiter.limit("100/minute")
async def latest_run(request: Request) -> LatestRunResponse:
    rows = get_latest_scores()
    last_ts = max((r["computed_at"] for r in rows if r.get("computed_at")), default=None)
    return LatestRunResponse(last_score_run=last_ts, subnet_count=len(rows))


@app.get(
    "/api/v1/leaderboard",
    response_model=LeaderboardResponse,
    summary="Top 20 and bottom 5 subnets",
    tags=["Scores"],
)
@cache(expire=3600)
@limiter.limit("100/minute")
async def leaderboard(request: Request) -> LeaderboardResponse:
    all_rows = get_latest_scores()
    total = len(all_rows)
    top = [_row_to_summary(r, total) for r in all_rows[:20]]
    bottom = [_row_to_summary(r, total) for r in all_rows[-5:]]
    return LeaderboardResponse(top=top, bottom=bottom)


@app.get(
    "/api/v1/scores/distribution",
    response_model=DistributionResponse,
    summary="Score distribution histogram",
    tags=["Scores"],
)
@cache(expire=3600)
@limiter.limit("100/minute")
async def score_distribution(
    request: Request,
    buckets: int = Query(10, ge=2, le=20),
) -> DistributionResponse:
    dist = get_score_distribution(buckets=buckets)
    return DistributionResponse(
        buckets=[DistributionBucket(**b) for b in dist],
        total_subnets=_total_subnet_count(),
    )


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    tags=["System"],
)
async def health(request: Request) -> HealthResponse:
    rows = get_latest_scores()
    last_ts = max((r["computed_at"] for r in rows if r.get("computed_at")), default=None)
    return HealthResponse(
        status="ok",
        last_score_run=last_ts,
        subnet_count=len(rows),
    )
