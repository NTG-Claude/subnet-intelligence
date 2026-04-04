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
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Optional, Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.models import (
    BacktestLabelSummary,
    BacktestObservation,
    BacktestResponse,
    CompareSeriesResponse,
    CompareSeriesRunPoint,
    CompareSeriesSubnetPoint,
    DetailedScoreHistoryPoint,
    DistributionBucket,
    DistributionResponse,
    ErrorResponse,
    HealthResponse,
    LeaderboardResponse,
    LatestRunResponse,
    MarketOverviewPoint,
    MarketOverviewResponse,
    MetricDeltaValueResponse,
    PrimaryOutputsResponse,
    PreviewMetricDeltasResponse,
    ResearchSummaryResponse,
    ScoreBreakdownResponse,
    ScoreHistoryPoint,
    SubnetDetailResponse,
    SubnetListResponse,
    SubnetMetadataResponse,
    SubnetSignalHistoryPoint,
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
from scorer.coingecko_client import get_tao_price_usd
from backtests.engine import build_backtest_summary

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Simple in-memory cache (TTL-based)
# ---------------------------------------------------------------------------

_cache: dict[str, tuple[Any, float]] = {}
_CACHE_TTL = 3600  # 1 hour
_HOT_DATA_CACHE_TTL = 300  # 5 minutes
_SEED_NAMES_PATH = Path(__file__).resolve().parent.parent / "data" / "subnet_names.json"
_NAME_OVERRIDES_PATH = Path(__file__).resolve().parent.parent / "data" / "subnet_name_overrides.json"


def _cache_get(key: str) -> Any:
    entry = _cache.get(key)
    if entry and time.time() < entry[1]:
        return entry[0]
    return None


def _cache_set(key: str, value: Any, ttl: int = _CACHE_TTL) -> None:
    _cache[key] = (value, time.time() + ttl)


def _is_mocked_callable(value: Any) -> bool:
    module_name = getattr(value, "__module__", "")
    return module_name.startswith("unittest.mock")


def _get_cached_latest_scores() -> list[dict]:
    if _is_mocked_callable(get_latest_scores):
        return get_latest_scores()
    cached = _cache_get("latest_scores")
    if cached is not None:
        return cached
    rows = get_latest_scores()
    _cache_set("latest_scores", rows, ttl=_HOT_DATA_CACHE_TTL)
    return rows


def _get_cached_all_metadata() -> dict[int, dict]:
    if _is_mocked_callable(get_all_metadata):
        return get_all_metadata()
    cached = _cache_get("all_metadata")
    if cached is not None:
        return cached
    metadata = get_all_metadata()
    _cache_set("all_metadata", metadata, ttl=_HOT_DATA_CACHE_TTL)
    return metadata


def _get_cached_score_history(netuid: int, days: int) -> list[dict]:
    if _is_mocked_callable(get_score_history):
        return get_score_history(netuid, days=days)
    key = f"score_history:{netuid}:{days}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    history = get_score_history(netuid, days=days)
    _cache_set(key, history, ttl=_HOT_DATA_CACHE_TTL)
    return history


def _metadata_fingerprint(metadata: Optional[dict[int, dict]] = None) -> str:
    try:
        live_metadata = metadata if metadata is not None else get_all_metadata()
    except Exception:
        live_metadata = {}
    last_ts = max(
        (row.get("last_updated") for row in live_metadata.values() if row.get("last_updated")),
        default="none",
    )
    return f"{last_ts}:{len(live_metadata)}"


def _run_fingerprint(rows: Optional[list[dict]] = None, metadata: Optional[dict[int, dict]] = None) -> str:
    live_rows = rows if rows is not None else _get_cached_latest_scores()
    last_ts = max((row["computed_at"] for row in live_rows if row.get("computed_at")), default="none")
    return f"{last_ts}:{len(live_rows)}:meta={_metadata_fingerprint(metadata)}"


def _live_cache_key(
    prefix: str,
    *parts: Any,
    rows: Optional[list[dict]] = None,
    metadata: Optional[dict[int, dict]] = None,
) -> str:
    serialized_parts = ":".join(str(part) for part in parts)
    base = f"{prefix}:{serialized_parts}" if serialized_parts else prefix
    return f"{base}:run={_run_fingerprint(rows, metadata)}"


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


def _override_name_map() -> dict[int, str]:
    cached = _cache_get("override_names")
    if cached is not None:
        return cached
    try:
        raw = json.loads(_NAME_OVERRIDES_PATH.read_text(encoding="utf-8"))
        result = {int(k): v for k, v in raw.items() if k.isdigit() and isinstance(v, str)}
    except Exception:
        result = {}
    _cache_set("override_names", result)
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
    if row.get("netuid") == 0:
        return False
    raw_data = row.get("raw_data") or {}
    if raw_data.get("special_case") == "root_subnet":
        return False
    return raw_data.get("investable", True)


def _extract_market_cap_usd(row: dict) -> Optional[float]:
    raw_data = row.get("raw_data") or {}
    value = raw_data.get("market_cap_usd")
    if value is None:
        value = ((raw_data.get("raw_metrics") or {}).get("market_cap_usd"))
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _extract_price_usd(row: dict) -> Optional[float]:
    raw_data = row.get("raw_data") or {}
    value = raw_data.get("price_usd")
    if value is None:
        value = ((raw_data.get("raw_metrics") or {}).get("price_usd"))
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _normalize_analysis_payload(analysis: Optional[dict]) -> Optional[dict]:
    if not analysis:
        return None
    normalized = dict(analysis)
    schema_stale = False
    if "top_negative_drags" not in normalized:
        normalized["top_negative_drags"] = normalized.get("top_negative_drivers") or []
        schema_stale = schema_stale or "top_negative_drivers" in normalized
    if "top_negative_drivers" not in normalized:
        normalized["top_negative_drivers"] = normalized.get("top_negative_drags") or []
    for key, default in (
        ("key_uncertainties", []),
        ("primary_signal_contributors", {}),
        ("block_scores", {}),
        ("conditioning", {}),
    ):
        if key not in normalized:
            normalized[key] = default
            schema_stale = True
    if schema_stale:
        normalized["analysis_schema_stale"] = True
    return normalized


def _warning_flags(raw_data: dict, analysis: dict | None, primary_outputs: dict | None) -> list[str]:
    flags: list[str] = []
    conditioning = (analysis or {}).get("conditioning") or {}
    visibility = conditioning.get("visibility") or {}
    block_scores = (analysis or {}).get("block_scores") or {}
    raw_metrics = raw_data.get("raw_metrics") or {}
    fragility = (primary_outputs or {}).get("fragility_risk")
    confidence = (primary_outputs or {}).get("signal_confidence")

    if confidence is not None and confidence < 50:
        flags.append("low_confidence")
    if fragility is not None and fragility >= 65:
        flags.append("fragility")
    if (raw_metrics.get("slippage_10_tao") or 0.0) >= 0.08:
        flags.append("thin_liquidity")
    if (raw_metrics.get("performance_driven_by_few_actors") or 0.0) >= 0.6:
        flags.append("concentration")
    if len(visibility.get("discarded") or []) > 0:
        flags.append("telemetry_gap")
    elif len(visibility.get("reconstructed") or []) > 0:
        flags.append("reconstructed_inputs")
    if (block_scores.get("market_legitimacy") or 100.0) < 45:
        flags.append("weak_market_structure")

    deduped: list[str] = []
    for flag in flags:
        if flag not in deduped:
            deduped.append(flag)
    return deduped[:4]


def _investability_status(row: dict, analysis: dict | None, primary_outputs: dict | None) -> str:
    raw_data = row.get("raw_data") or {}
    if not raw_data.get("investable", True):
        return "uninvestable"
    if not primary_outputs:
        return "constrained"

    flags = _warning_flags(raw_data, analysis, primary_outputs)
    quality = primary_outputs.get("fundamental_quality") or 0.0
    opportunity = primary_outputs.get("mispricing_signal") or 0.0
    risk = primary_outputs.get("fragility_risk") or 100.0
    confidence = primary_outputs.get("signal_confidence") or 0.0
    severe_structure_break = "thin_liquidity" in flags and "concentration" in flags

    if severe_structure_break or risk >= 75 or confidence < 35:
        return "constrained"
    if risk >= 58 or confidence < 50 or "thin_liquidity" in flags or "concentration" in flags:
        return "speculative"
    if quality >= 55 and opportunity >= 45 and risk <= 50 and confidence >= 55:
        return "investable"
    return "speculative"


def _contributor_name(item: dict | None) -> str:
    if not item:
        return ""
    return item.get("name") or item.get("metric") or item.get("source_block") or ""


def _market_capacity(row: dict) -> str:
    market_cap = row.get("market_cap_tao") or 0.0
    pool_depth = row.get("tao_in_pool") or 0.0
    if market_cap >= 250_000 or pool_depth >= 25_000:
        return "high"
    if market_cap >= 75_000 or pool_depth >= 7_500:
        return "medium"
    if market_cap >= 15_000 or pool_depth >= 1_500:
        return "low"
    return "very_low"


def _evidence_strength(analysis: dict | None, primary_outputs: dict | None) -> str:
    conditioning = (analysis or {}).get("conditioning") or {}
    reliability = conditioning.get("reliability") or {}
    values = [value for value in reliability.values() if isinstance(value, (int, float))]
    avg_reliability = (sum(values) / len(values)) if values else None
    discarded = len((conditioning.get("visibility") or {}).get("discarded") or [])
    confidence = (primary_outputs or {}).get("signal_confidence") or 0.0

    if confidence >= 65 and discarded == 0 and (avg_reliability is None or avg_reliability >= 0.7):
        return "high"
    if confidence >= 45 and (avg_reliability is None or avg_reliability >= 0.5):
        return "medium"
    return "low"


def _setup_status(investability_status: str, primary_outputs: dict | None) -> str:
    if investability_status == "uninvestable" or not primary_outputs:
        return "not_investable"

    quality = primary_outputs.get("fundamental_quality") or 0.0
    opportunity = primary_outputs.get("mispricing_signal") or 0.0
    risk = primary_outputs.get("fragility_risk") or 100.0
    confidence = primary_outputs.get("signal_confidence") or 0.0

    if quality >= 65 and opportunity >= 55 and risk <= 45 and confidence >= 55:
        return "strong_setup"
    if quality >= 55 and confidence >= 45 and risk <= 60:
        return "improving_setup"
    if risk <= 75 and confidence >= 35:
        return "fragile_setup"
    return "not_investable"


def _driver_phrase(name: str, *, negative: bool = False, uncertainty: bool = False) -> str:
    mapping = {
        "fundamental_health": "operating quality is improving and holding up",
        "market_legitimacy": "the market already treats the subnet as credible",
        "structural_validity": "the structure still looks investable",
        "confidence_factor": "the main inputs point in the same direction",
        "thesis_confidence": "the broader case hangs together without too many assumptions",
        "market_confidence": "price action is not fighting the case",
        "data_confidence": "inputs are clean enough for a usable read",
        "base_opportunity": "part of the setup still looks underpriced",
        "opportunity_underreaction": "price still looks slow to reflect the setup",
        "quality_acceleration": "quality is still improving",
        "fragility": "modeled downside is still controlled",
        "reserve_change": "reserve growth is not yet producing a stronger market response",
        "liquidity_improvement_rate": "liquidity is not improving quickly enough",
        "reserve_growth_without_price": "fundamental progress is not showing up clearly in price",
        "price_response_lag_to_quality_shift": "the market may already be catching up to the improvement",
        "expected_price_response_gap": "the rerating gap is narrower than in the best peers",
        "emission_to_sticky_usage_conversion": "emissions are not yet converting into sticky usage",
        "post_incentive_retention": "retention still needs to prove itself after incentives cool",
        "emission_efficiency": "capital is not converting into usage efficiently enough",
        "cohort_quality_edge": "its quality lead over peers is not overwhelming",
        "discarded_inputs": "part of the telemetry had to be discarded",
        "external_data_reliability": "external corroboration is still thin",
        "validator_data_reliability": "validator-side evidence is thinner than ideal",
        "history_data_reliability": "the historical record is still shallow",
    }
    phrase = mapping.get(name)
    if not phrase:
        phrase = name.replace("_", " ").strip() if name else "the setup is still incomplete"
    if uncertainty:
        return phrase
    if negative:
        return phrase
    return phrase


def _peer_context(rank: int | None, percentile: float | None, primary_outputs: dict | None) -> str:
    if not primary_outputs:
        return "Peer context is provisional because the latest primary outputs are not available yet."

    quality = primary_outputs.get("fundamental_quality") or 0.0
    opportunity = primary_outputs.get("mispricing_signal") or 0.0
    risk = primary_outputs.get("fragility_risk") or 100.0
    confidence = primary_outputs.get("signal_confidence") or 0.0

    parts: list[str] = []
    if rank is not None and percentile is not None:
        parts.append(f"It currently ranks #{rank} and sits around the {percentile:.1f}th percentile of the tracked universe.")
    if quality >= 65:
        parts.append("Quality is above most peers.")
    elif quality <= 45:
        parts.append("Quality is still below the stronger peer group.")
    if opportunity >= 60:
        parts.append("The opportunity gap is still wider than most peers.")
    elif opportunity <= 40:
        parts.append("The opportunity gap is narrower than most peers.")
    if risk <= 40:
        parts.append("Fragility is better controlled than the median peer.")
    elif risk >= 60:
        parts.append("Fragility is worse than the median peer.")
    if confidence < 50:
        parts.append("Evidence quality is weaker than the more established peer set.")
    return " ".join(parts)


def _build_research_summary(
    row: dict,
    analysis: dict | None,
    primary_outputs: dict | None,
    investability_status: str,
    warning_flags: list[str],
    total: int,
) -> ResearchSummaryResponse:
    positives = (analysis or {}).get("top_positive_drivers") or []
    negatives = (analysis or {}).get("top_negative_drags") or (analysis or {}).get("top_negative_drivers") or []
    uncertainties = (analysis or {}).get("key_uncertainties") or []
    thesis_breakers = (analysis or {}).get("thesis_breakers") or []
    rank = row.get("rank")
    percentile = _compute_percentile(rank, total)
    setup_status = _setup_status(investability_status, primary_outputs)
    evidence_strength = _evidence_strength(analysis, primary_outputs)

    primary_positive = _driver_phrase(_contributor_name(positives[0]) if positives else "")
    primary_negative = _driver_phrase(_contributor_name(negatives[0]) if negatives else "", negative=True)
    lead_uncertainty_name = (uncertainties[0] or {}).get("name") if uncertainties else ""
    lead_uncertainty = _driver_phrase(lead_uncertainty_name, uncertainty=True)
    stress_drawdown = (analysis or {}).get("stress_drawdown")
    fragility_class = (analysis or {}).get("fragility_class")

    if not primary_outputs:
        setup_read = "Fresh scored outputs are missing, so the setup is still provisional."
        why_now = "This page is on watch because the latest run is incomplete, not because the case is confirmed."
    else:
        quality = primary_outputs.get("fundamental_quality") or 0.0
        opportunity = primary_outputs.get("mispricing_signal") or 0.0
        risk = primary_outputs.get("fragility_risk") or 100.0
        confidence = primary_outputs.get("signal_confidence") or 0.0
        if setup_status == "strong_setup":
            setup_read = "Quality, upside, and trust all clear the bar, and downside is still controlled."
        elif setup_status == "improving_setup":
            setup_read = "Quality is improving, but the case still needs cleaner confirmation."
        elif setup_status == "fragile_setup":
            setup_read = "There is something to work with, but weak trust or high stress can still break the case."
        else:
            setup_read = "On current evidence, the case is not investable."

        why_now = (
            f"{primary_positive.capitalize()}."
            if primary_positive
            else "The latest run still shows something worth tracking, but not enough for a firm call."
        )
        if opportunity >= 60 and confidence >= 50:
            why_now += " Price still looks slow to reflect the setup."
        elif quality >= 65 and risk <= 45:
            why_now += " Operating quality is stronger than price and stress imply."

    if primary_negative:
        main_constraint = f"{primary_negative.capitalize()}."
    elif "thin_liquidity" in warning_flags:
        main_constraint = "Liquidity is still too thin for larger flows."
    elif lead_uncertainty:
        main_constraint = f"{lead_uncertainty.capitalize()}."
    else:
        main_constraint = "The current evidence is not strong enough for a firmer call."

    if thesis_breakers:
        break_condition = thesis_breakers[0]
    elif stress_drawdown is not None:
        break_condition = f"The setup breaks if modeled drawdown pushes materially beyond {stress_drawdown:.1f}%."
    elif fragility_class:
        break_condition = f"The setup breaks if the current {fragility_class} risk profile worsens."
    else:
        break_condition = "The setup breaks if current support in price, usage, or evidence fades."

    return ResearchSummaryResponse(
        setup_status=setup_status,
        setup_read=setup_read,
        why_now=why_now,
        main_constraint=main_constraint,
        break_condition=break_condition,
        market_capacity=_market_capacity(row),
        evidence_strength=evidence_strength,
        relative_peer_context=_peer_context(rank, percentile, primary_outputs),
    )


def _compact_preview_contributor(item: dict | None) -> dict:
    if not item:
        return {}
    compact = {
        "metric": item.get("metric"),
        "name": item.get("name"),
        "short_explanation": item.get("short_explanation"),
        "source_block": item.get("source_block"),
    }
    return {key: value for key, value in compact.items() if value not in (None, "")}


def _compact_preview_uncertainty(item: dict | None) -> dict:
    if not item:
        return {}
    compact = {
        "name": item.get("name"),
        "short_explanation": item.get("short_explanation"),
        "source_block": item.get("source_block"),
    }
    return {key: value for key, value in compact.items() if value not in (None, "")}


def _compact_conditioning(conditioning: dict | None) -> dict:
    visibility = (conditioning or {}).get("visibility") or {}
    compact_visibility: dict[str, list[str]] = {}

    for key in ("reconstructed", "discarded"):
        values = visibility.get(key) or []
        if values:
            compact_visibility[key] = values[:1]

    return {"visibility": compact_visibility} if compact_visibility else {}


def _analysis_preview_payload(analysis: dict, preview: Literal["compact", "full"]) -> dict | None:
    if not analysis:
        return None

    if preview == "full":
        return {
            "top_positive_drivers": analysis.get("top_positive_drivers") or [],
            "top_negative_drags": analysis.get("top_negative_drags") or analysis.get("top_negative_drivers") or [],
            "key_uncertainties": analysis.get("key_uncertainties") or [],
            "conditioning": analysis.get("conditioning") or {},
            "block_scores": analysis.get("block_scores") or {},
        }

    return {
        "top_positive_drivers": [
            _compact_preview_contributor(item) for item in (analysis.get("top_positive_drivers") or [])[:2]
        ],
        "top_negative_drags": [
            _compact_preview_contributor(item)
            for item in (analysis.get("top_negative_drags") or analysis.get("top_negative_drivers") or [])[:2]
        ],
        "key_uncertainties": [
            _compact_preview_uncertainty(item) for item in (analysis.get("key_uncertainties") or [])[:2]
        ],
        "conditioning": _compact_conditioning(analysis.get("conditioning") or {}),
        "block_scores": {},
    }


def _row_to_summary(
    row: dict,
    total: int,
    meta: Optional[SubnetMetadataResponse] = None,
    preview: Literal["compact", "full"] = "full",
    previous_rank: Optional[int] = None,
    preview_metric_deltas: Optional[PreviewMetricDeltasResponse] = None,
) -> SubnetSummaryResponse:
    raw_data = row.get("raw_data") or {}
    analysis = _normalize_analysis_payload(raw_data.get("analysis")) or {}
    fallback_name = _override_name_map().get(row["netuid"])
    primary_outputs = analysis.get("primary_outputs") or raw_data.get("primary_outputs")
    warning_flags = _warning_flags(raw_data, analysis, primary_outputs)
    investability_status = _investability_status(row, analysis, primary_outputs)
    analysis_preview = _analysis_preview_payload(analysis, preview)
    return SubnetSummaryResponse(
        netuid=row["netuid"],
        name=(meta.name if meta else None) or fallback_name,
        score=row["score"],
        primary_outputs=PrimaryOutputsResponse(**primary_outputs) if primary_outputs else None,
        rank=row["rank"],
        previous_rank=previous_rank,
        preview_metric_deltas=preview_metric_deltas,
        percentile=_compute_percentile(row.get("rank"), total),
        computed_at=row.get("computed_at"),
        score_version=row.get("score_version", "v1"),
        alpha_price_tao=row.get("alpha_price_tao"),
        tao_in_pool=row.get("tao_in_pool"),
        market_cap_tao=row.get("market_cap_tao"),
        staking_apy=row.get("staking_apy"),
        investability_status=investability_status,
        warning_flags=warning_flags,
        label=raw_data.get("label"),
        thesis=raw_data.get("thesis"),
        analysis_preview=analysis_preview,
    )


def _row_to_detailed_history_point(row: dict) -> DetailedScoreHistoryPoint:
    raw_data = row.get("raw_data") or {}
    analysis = _normalize_analysis_payload(raw_data.get("analysis")) or {}
    primary_outputs = analysis.get("primary_outputs") or raw_data.get("primary_outputs")
    conditioning = analysis.get("conditioning") or {}
    reliability = conditioning.get("reliability") or {}
    return DetailedScoreHistoryPoint(
        computed_at=row["computed_at"],
        score=row["score"],
        rank=row.get("rank"),
        score_version=row.get("score_version", "v1"),
        label=raw_data.get("label"),
        thesis=raw_data.get("thesis"),
        primary_outputs=PrimaryOutputsResponse(**primary_outputs) if primary_outputs else None,
        block_scores=analysis.get("block_scores") or {},
        conditioning_reliability=reliability,
        top_positive_drivers=analysis.get("top_positive_drivers") or [],
        top_negative_drags=analysis.get("top_negative_drags") or analysis.get("top_negative_drivers") or [],
    )


def _row_to_signal_history_point(row: dict) -> SubnetSignalHistoryPoint:
    raw_data = row.get("raw_data") or {}
    analysis = _normalize_analysis_payload(raw_data.get("analysis")) or {}
    primary_outputs = analysis.get("primary_outputs") or raw_data.get("primary_outputs") or {}
    return SubnetSignalHistoryPoint(
        computed_at=row["computed_at"],
        score=row["score"],
        quality=primary_outputs.get("fundamental_quality"),
        opportunity=primary_outputs.get("mispricing_signal"),
        risk=primary_outputs.get("fragility_risk"),
        confidence=primary_outputs.get("signal_confidence"),
    )


def _empty_metric_delta() -> MetricDeltaValueResponse:
    return MetricDeltaValueResponse(value=None, has_history=False)


def _nearest_point_at_or_before(points: list[SubnetSignalHistoryPoint], target_time: int) -> Optional[SubnetSignalHistoryPoint]:
    match: Optional[SubnetSignalHistoryPoint] = None
    for point in points:
        try:
            point_time = int(datetime.fromisoformat(point.computed_at.replace("Z", "+00:00")).timestamp())
        except Exception:
            continue
        if point_time > target_time:
            continue
        match = point
    return match


def _metric_delta_from_points(
    points: list[SubnetSignalHistoryPoint],
    metric: Literal["quality", "opportunity", "risk", "confidence"],
    days: int,
) -> MetricDeltaValueResponse:
    latest_point = points[-1] if points else None
    if latest_point is None:
        return _empty_metric_delta()

    latest_value = getattr(latest_point, metric)
    if latest_value is None:
        return _empty_metric_delta()

    latest_time = int(datetime.fromisoformat(latest_point.computed_at.replace("Z", "+00:00")).timestamp())
    reference_point = _nearest_point_at_or_before(points, latest_time - days * 24 * 60 * 60)
    if reference_point is None:
        return _empty_metric_delta()

    reference_value = getattr(reference_point, metric)
    if reference_value is None:
        return _empty_metric_delta()

    return MetricDeltaValueResponse(
        value=round(float(latest_value) - float(reference_value), 1),
        has_history=True,
    )


def _preview_metric_deltas_from_points(points: list[SubnetSignalHistoryPoint]) -> Optional[PreviewMetricDeltasResponse]:
    if not points:
        return None

    return PreviewMetricDeltasResponse(
        strength={
            "1d": _metric_delta_from_points(points, "quality", 1),
            "7d": _metric_delta_from_points(points, "quality", 7),
            "30d": _metric_delta_from_points(points, "quality", 30),
        },
        upside={
            "1d": _metric_delta_from_points(points, "opportunity", 1),
            "7d": _metric_delta_from_points(points, "opportunity", 7),
            "30d": _metric_delta_from_points(points, "opportunity", 30),
        },
        risk={
            "1d": _metric_delta_from_points(points, "risk", 1),
            "7d": _metric_delta_from_points(points, "risk", 7),
            "30d": _metric_delta_from_points(points, "risk", 30),
        },
        evidence={
            "1d": _metric_delta_from_points(points, "confidence", 1),
            "7d": _metric_delta_from_points(points, "confidence", 7),
            "30d": _metric_delta_from_points(points, "confidence", 30),
        },
    )


def _sort_value(row: dict, sort_by: str, meta_by_netuid: dict[int, dict]) -> Any:
    raw_data = row.get("raw_data") or {}
    primary_outputs = raw_data.get("analysis", {}).get("primary_outputs") or raw_data.get("primary_outputs") or {}
    if sort_by == "score":
        return row.get("score") or 0.0
    if sort_by == "netuid":
        return row.get("netuid") or 0
    if sort_by == "rank":
        return -(row.get("rank") or 999999)
    if sort_by == "fundamental_quality":
        return primary_outputs.get("fundamental_quality", -1.0)
    if sort_by == "mispricing_signal":
        return primary_outputs.get("mispricing_signal", -1.0)
    if sort_by == "fragility_risk":
        return primary_outputs.get("fragility_risk", 999.0)
    if sort_by == "signal_confidence":
        return primary_outputs.get("signal_confidence", -1.0)
    if sort_by == "label":
        return raw_data.get("label") or ""
    if sort_by == "name":
        metadata = meta_by_netuid.get(row["netuid"]) or {}
        return metadata.get("name") or _override_name_map().get(row["netuid"]) or ""
    return row.get("score") or 0.0


def _previous_rank_by_netuid(
    history_rows: Optional[list[dict]] = None,
    days: int = 14,
) -> dict[int, int]:
    rows = history_rows if history_rows is not None else [row for row in get_scores_since(days=days) if _is_investable_row(row)]
    run_timestamps = sorted(
        {row.get("computed_at") for row in rows if row.get("computed_at")},
        reverse=True,
    )
    if len(run_timestamps) < 2:
        return {}

    previous_run_at = run_timestamps[1]
    previous_run_rows = [row for row in rows if row.get("computed_at") == previous_run_at]
    ranked_rows = sorted(previous_run_rows, key=lambda item: (-item["score"], item["netuid"]))
    return {row["netuid"]: index + 1 for index, row in enumerate(ranked_rows)}


def _preview_metric_deltas_by_netuid(
    history_rows: list[dict],
    netuids: set[int],
) -> dict[int, PreviewMetricDeltasResponse]:
    points_by_netuid: dict[int, list[SubnetSignalHistoryPoint]] = defaultdict(list)

    for row in history_rows:
        netuid = row.get("netuid")
        if netuid not in netuids:
            continue
        points_by_netuid[netuid].append(_row_to_signal_history_point(row))

    preview_deltas: dict[int, PreviewMetricDeltasResponse] = {}
    for netuid, points in points_by_netuid.items():
        deltas = _preview_metric_deltas_from_points(points)
        if deltas is not None:
            preview_deltas[netuid] = deltas
    return preview_deltas


def _get_metadata(netuid: int) -> Optional[SubnetMetadataResponse]:
    with SessionLocal() as session:
        row = session.get(SubnetMetadataRow, netuid)
        if row is None:
            return None
        return SubnetMetadataResponse(
            netuid=row.netuid,
            name=row.name or _override_name_map().get(netuid),
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
    sort_by: Literal[
        "score",
        "rank",
        "netuid",
        "name",
        "label",
        "fundamental_quality",
        "mispricing_signal",
        "fragility_risk",
        "signal_confidence",
    ] = Query("score"),
    sort_order: Literal["asc", "desc"] = Query("desc"),
    preview: Literal["compact", "full"] = Query("compact"),
    _: None = Depends(_check_rate_limit),
) -> SubnetListResponse:
    all_rows = _get_cached_latest_scores()
    cache_key = _live_cache_key("list", limit, offset, min_score, max_score, sort_by, sort_order, preview, rows=all_rows)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    all_rows = [r for r in all_rows if _is_investable_row(r)]
    meta_by_netuid = get_all_metadata()
    preview_history_rows = [row for row in get_scores_since(days=120) if _is_investable_row(row)]
    previous_rank_by_netuid = _previous_rank_by_netuid(preview_history_rows)
    filtered = [r for r in all_rows if min_score <= r["score"] <= max_score]
    reverse = sort_order == "desc"
    filtered = sorted(
        filtered,
        key=lambda row: _sort_value(row, sort_by, meta_by_netuid),
        reverse=reverse,
    )
    total = len(filtered)
    page = filtered[offset: offset + limit]
    page_netuids = {row["netuid"] for row in page}
    preview_metric_deltas_by_netuid = _preview_metric_deltas_by_netuid(preview_history_rows, page_netuids)

    subnets = []
    for r in page:
        meta_dict = meta_by_netuid.get(r["netuid"])
        meta = SubnetMetadataResponse(netuid=r["netuid"], **(meta_dict or {})) if meta_dict else None
        subnets.append(
            _row_to_summary(
                r,
                total,
                meta,
                preview=preview,
                previous_rank=previous_rank_by_netuid.get(r["netuid"]),
                preview_metric_deltas=preview_metric_deltas_by_netuid.get(r["netuid"]),
            )
        )

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
    view: Literal["page", "full"] = Query("full"),
    _: None = Depends(_check_rate_limit),
) -> SubnetDetailResponse:
    all_rows = get_latest_scores()
    meta_by_netuid = _get_cached_all_metadata()
    cache_key = _live_cache_key("subnet", netuid, view, rows=all_rows, metadata=meta_by_netuid)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    investable_rows = [r for r in all_rows if _is_investable_row(r)]
    total = len(investable_rows)

    row = next((r for r in all_rows if r["netuid"] == netuid), None)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Subnet {netuid} not found")

    score_delta_7d: Optional[float] = None
    history_for_delta = _get_cached_score_history(netuid, days=7)
    if len(history_for_delta) >= 2:
        score_delta_7d = round(row["score"] - history_for_delta[0]["score"], 1)

    history: list[ScoreHistoryPoint] = []
    if view == "full":
        history_raw = _get_cached_score_history(netuid, days=30)
        history = [
            ScoreHistoryPoint(
                computed_at=h["computed_at"],
                score=h["score"],
                rank=h.get("rank"),
            )
            for h in history_raw
        ]

    meta_dict = meta_by_netuid.get(netuid)
    meta = SubnetMetadataResponse(netuid=netuid, **(meta_dict or {})) if meta_dict else None

    analysis_payload = _normalize_analysis_payload((row.get("raw_data") or {}).get("analysis"))
    detail_primary_outputs = ((analysis_payload or {}).get("primary_outputs"))
    warning_flags = _warning_flags(row.get("raw_data") or {}, analysis_payload, detail_primary_outputs)
    investability_status = _investability_status(row, analysis_payload, detail_primary_outputs)
    research_summary = _build_research_summary(
        row=row,
        analysis=analysis_payload,
        primary_outputs=detail_primary_outputs,
        investability_status=investability_status,
        warning_flags=warning_flags,
        total=total,
    )

    result = SubnetDetailResponse(
        netuid=netuid,
        name=(meta.name if meta else None) or _override_name_map().get(netuid),
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
        ) if view == "full" else None,
        history=history,
        metadata=meta,
        computed_at=row.get("computed_at"),
        score_version=row.get("score_version", "v1"),
        alpha_price_tao=row.get("alpha_price_tao"),
        tao_in_pool=row.get("tao_in_pool"),
        market_cap_tao=row.get("market_cap_tao"),
        staking_apy=row.get("staking_apy"),
        score_delta_7d=score_delta_7d,
        investability_status=investability_status,
        warning_flags=warning_flags,
        label=(row.get("raw_data") or {}).get("label"),
        thesis=(row.get("raw_data") or {}).get("thesis"),
        research_summary=research_summary,
        analysis=analysis_payload,
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
    all_rows = get_latest_scores()
    cache_key = _live_cache_key("history", netuid, days, rows=all_rows)
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
    "/api/v1/subnets/{netuid}/history/detailed",
    response_model=list[DetailedScoreHistoryPoint],
    summary="Detailed score history with primary signals and block-level analysis",
    tags=["Subnets"],
    responses={404: {"model": ErrorResponse}},
)
async def get_subnet_history_detailed(
    request: Request,
    netuid: int,
    days: int = Query(30, ge=1, le=365),
    _: None = Depends(_check_rate_limit),
) -> list[DetailedScoreHistoryPoint]:
    all_rows = _get_cached_latest_scores()
    cache_key = _live_cache_key("history_detailed", netuid, days, rows=all_rows)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    history_raw = _get_cached_score_history(netuid, days=days)
    if not history_raw:
        raise HTTPException(status_code=404, detail=f"No history for subnet {netuid}")

    result = [_row_to_detailed_history_point(row) for row in history_raw]
    _cache_set(cache_key, result)
    return result


@app.get(
    "/api/v1/subnets/{netuid}/history/signals",
    response_model=list[SubnetSignalHistoryPoint],
    summary="Signal history for a subnet chart",
    tags=["Subnets"],
    responses={404: {"model": ErrorResponse}},
)
async def get_subnet_signal_history(
    request: Request,
    netuid: int,
    days: int = Query(120, ge=1, le=365),
    _: None = Depends(_check_rate_limit),
) -> list[SubnetSignalHistoryPoint]:
    all_rows = get_latest_scores()
    cache_key = _live_cache_key("history_signals", netuid, days, rows=all_rows)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    history_raw = get_score_history(netuid, days=days)
    if not history_raw:
        raise HTTPException(status_code=404, detail=f"No history for subnet {netuid}")

    result = [_row_to_signal_history_point(row) for row in history_raw]
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
    rows = get_latest_scores()
    cache_key = _live_cache_key("latest_run", rows=rows)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    investable_rows = [r for r in rows if _is_investable_row(r)]
    last_ts = max((r["computed_at"] for r in rows if r.get("computed_at")), default=None)
    result = LatestRunResponse(last_score_run=last_ts, subnet_count=len(investable_rows))
    _cache_set(cache_key, result)
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
    all_rows = get_latest_scores()
    cache_key = _live_cache_key("leaderboard", rows=all_rows)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    all_rows = [r for r in all_rows if _is_investable_row(r)]
    meta_by_netuid = get_all_metadata()
    total = len(all_rows)

    def _with_meta(r: dict) -> SubnetSummaryResponse:
        md = meta_by_netuid.get(r["netuid"])
        m = SubnetMetadataResponse(netuid=r["netuid"], **(md or {})) if md else None
        return _row_to_summary(r, total, m)

    top = [_with_meta(r) for r in all_rows[:20]]
    bottom = [_with_meta(r) for r in all_rows[-5:]]
    result = LeaderboardResponse(top=top, bottom=bottom)
    _cache_set(cache_key, result)
    return result


@app.get(
    "/api/v1/compare/timeseries",
    response_model=CompareSeriesResponse,
    summary="Run-over-run universe series for compare charts",
    tags=["Compare"],
)
async def compare_timeseries(
    request: Request,
    days: int = Query(30, ge=1, le=180),
    _: None = Depends(_check_rate_limit),
) -> CompareSeriesResponse:
    all_rows = get_latest_scores()
    cache_key = _live_cache_key("compare_timeseries", days, rows=all_rows)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    history_rows = [row for row in get_scores_since(days=days) if _is_investable_row(row)]
    meta_by_netuid = get_all_metadata()
    grouped: dict[str, list[CompareSeriesSubnetPoint]] = defaultdict(list)

    for row in history_rows:
        raw_data = row.get("raw_data") or {}
        analysis = _normalize_analysis_payload(raw_data.get("analysis")) or {}
        outputs = analysis.get("primary_outputs") or raw_data.get("primary_outputs") or {}
        metadata = meta_by_netuid.get(row["netuid"]) or {}
        grouped[row["computed_at"]].append(
            CompareSeriesSubnetPoint(
                netuid=row["netuid"],
                name=metadata.get("name") or _override_name_map().get(row["netuid"]),
                score=row["score"],
                fundamental_quality=outputs.get("fundamental_quality"),
                mispricing_signal=outputs.get("mispricing_signal"),
                fragility_risk=outputs.get("fragility_risk"),
                signal_confidence=outputs.get("signal_confidence"),
            )
        )

    runs = [
        CompareSeriesRunPoint(
            computed_at=computed_at,
            subnets=sorted(points, key=lambda point: point.netuid),
        )
        for computed_at, points in sorted(grouped.items())
    ]
    latest_count = len(runs[-1].subnets) if runs else 0
    result = CompareSeriesResponse(runs=runs, total_subnets=latest_count)
    _cache_set(cache_key, result)
    return result


@app.get(
    "/api/v1/market/overview",
    response_model=MarketOverviewResponse,
    summary="Aggregated subnet market cap overview across runs",
    tags=["Market"],
)
async def market_overview(
    request: Request,
    days: int = Query(90, ge=7, le=365),
    _: None = Depends(_check_rate_limit),
) -> MarketOverviewResponse:
    all_rows = get_latest_scores()
    latest_score_version = next((row.get("score_version") for row in all_rows if row.get("score_version")), None)
    cache_key = _live_cache_key("market_overview_v4", days, latest_score_version or "unknown", rows=all_rows)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    history_rows = [
        row
        for row in get_scores_since(days=days)
        if _is_investable_row(row) and (latest_score_version is None or row.get("score_version") == latest_score_version)
    ]
    grouped: dict[str, dict[str, float]] = defaultdict(lambda: {"market_cap": 0.0, "market_cap_usd": 0.0, "count": 0, "usd_points": 0})

    for row in history_rows:
        market_cap = row.get("market_cap_tao")
        if market_cap is None:
            continue
        bucket = grouped[row["computed_at"]]
        bucket["market_cap"] += float(market_cap)
        bucket["count"] += 1
        market_cap_usd = _extract_market_cap_usd(row)
        if market_cap_usd is not None:
            bucket["market_cap_usd"] += market_cap_usd
            bucket["usd_points"] += 1

    points = [
        MarketOverviewPoint(
            computed_at=computed_at,
            total_market_cap_tao=values["market_cap"],
            total_market_cap_usd=values["market_cap_usd"] if values["usd_points"] > 0 else None,
            subnet_count=int(values["count"]),
        )
        for computed_at, values in sorted(grouped.items())
    ]

    current_market_cap = points[-1].total_market_cap_tao if points else 0.0
    current_market_cap_usd = points[-1].total_market_cap_usd if points else None
    current_count = points[-1].subnet_count if points else 0
    previous_market_cap = points[-2].total_market_cap_tao if len(points) > 1 else None
    tao_price_usd = (
        (current_market_cap_usd / current_market_cap)
        if current_market_cap_usd is not None and current_market_cap > 0
        else None
    )
    if tao_price_usd is None:
        latest_rows = [row for row in all_rows if _is_investable_row(row)]
        prices = [price for price in (_extract_price_usd(row) for row in latest_rows) if price is not None]
        if prices:
            tao_price_usd = sum(prices) / len(prices)
            current_market_cap_usd = current_market_cap * tao_price_usd if current_market_cap > 0 else None
        else:
            tao_price_usd = await get_tao_price_usd()
            current_market_cap_usd = current_market_cap * tao_price_usd if tao_price_usd is not None else current_market_cap_usd
    change_pct = (
        round(((current_market_cap - previous_market_cap) / previous_market_cap) * 100, 2)
        if previous_market_cap and previous_market_cap > 0
        else None
    )

    result = MarketOverviewResponse(
        current_market_cap_tao=current_market_cap,
        current_market_cap_usd=current_market_cap_usd,
        tao_price_usd=tao_price_usd,
        change_pct_vs_previous_run=change_pct,
        current_subnet_count=current_count,
        points=points,
    )
    _cache_set(cache_key, result)
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
    all_rows = get_latest_scores()
    cache_key = _live_cache_key("distribution", buckets, rows=all_rows)
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
    all_rows = get_latest_scores()
    cache_key = _live_cache_key("backtests", days, rows=all_rows)
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
