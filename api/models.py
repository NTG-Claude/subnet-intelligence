"""
API response models (Pydantic).
"""

from typing import Optional
from pydantic import BaseModel, Field


class ScoreBreakdownResponse(BaseModel):
    capital_score: float
    activity_score: float
    efficiency_score: float
    health_score: float
    dev_score: float


class PrimaryOutputsResponse(BaseModel):
    fundamental_quality: float
    mispricing_signal: float
    fragility_risk: float
    signal_confidence: float


class ResearchSummaryResponse(BaseModel):
    setup_status: str
    setup_read: str
    why_now: str
    main_constraint: str
    break_condition: str
    market_capacity: str
    evidence_strength: str
    relative_peer_context: str


class SubnetSummaryResponse(BaseModel):
    netuid: int
    name: Optional[str] = None
    score: float
    primary_outputs: Optional[PrimaryOutputsResponse] = None
    rank: Optional[int] = None
    percentile: Optional[float] = None  # 0-100
    computed_at: Optional[str] = None
    score_version: str = "v1"
    # dTAO market data
    alpha_price_tao: Optional[float] = None
    tao_in_pool: Optional[float] = None
    market_cap_tao: Optional[float] = None
    staking_apy: Optional[float] = None
    investability_status: Optional[str] = None
    warning_flags: list[str] = Field(default_factory=list)
    label: Optional[str] = Field(
        default=None,
        description="Deprecated compatibility field. Product surfaces should prefer thesis and V2 explanation data.",
        json_schema_extra={"deprecated": True},
    )
    thesis: Optional[str] = None
    analysis_preview: Optional[dict] = None


class SubnetMetadataResponse(BaseModel):
    netuid: int
    name: Optional[str] = None
    github_url: Optional[str] = None
    website: Optional[str] = None
    first_seen: Optional[str] = None
    last_updated: Optional[str] = None


class ScoreHistoryPoint(BaseModel):
    computed_at: str
    score: float
    rank: Optional[int] = None


class DetailedScoreHistoryPoint(BaseModel):
    computed_at: str
    score: float
    rank: Optional[int] = None
    score_version: str = "v1"
    label: Optional[str] = None
    thesis: Optional[str] = None
    primary_outputs: Optional[PrimaryOutputsResponse] = None
    block_scores: dict = Field(default_factory=dict)
    conditioning_reliability: dict = Field(default_factory=dict)
    top_positive_drivers: list[dict] = Field(default_factory=list)
    top_negative_drags: list[dict] = Field(default_factory=list)


class SubnetSignalHistoryPoint(BaseModel):
    computed_at: str
    score: float
    quality: Optional[float] = None
    opportunity: Optional[float] = None
    risk: Optional[float] = None
    confidence: Optional[float] = None


class CompareSeriesSubnetPoint(BaseModel):
    netuid: int
    name: Optional[str] = None
    score: float
    fundamental_quality: Optional[float] = None
    mispricing_signal: Optional[float] = None
    fragility_risk: Optional[float] = None
    signal_confidence: Optional[float] = None


class CompareSeriesRunPoint(BaseModel):
    computed_at: str
    subnets: list[CompareSeriesSubnetPoint]


class CompareSeriesResponse(BaseModel):
    runs: list[CompareSeriesRunPoint]
    total_subnets: int


class MarketOverviewPoint(BaseModel):
    computed_at: str
    total_market_cap_tao: float
    subnet_count: int


class MarketOverviewResponse(BaseModel):
    current_market_cap_tao: float
    current_market_cap_usd: Optional[float] = None
    tao_price_usd: Optional[float] = None
    change_pct_vs_previous_run: Optional[float] = None
    current_subnet_count: int
    points: list[MarketOverviewPoint]


class SubnetDetailResponse(BaseModel):
    netuid: int
    name: Optional[str] = None
    score: float
    primary_outputs: Optional[PrimaryOutputsResponse] = None
    rank: Optional[int] = None
    percentile: Optional[float] = None
    breakdown: Optional[ScoreBreakdownResponse] = None
    history: list[ScoreHistoryPoint] = Field(default_factory=list)
    metadata: Optional[SubnetMetadataResponse] = None
    computed_at: Optional[str] = None
    score_version: str = "v1"
    # dTAO market data
    alpha_price_tao: Optional[float] = None
    tao_in_pool: Optional[float] = None
    market_cap_tao: Optional[float] = None
    staking_apy: Optional[float] = None
    score_delta_7d: Optional[float] = None
    investability_status: Optional[str] = None
    warning_flags: list[str] = Field(default_factory=list)
    label: Optional[str] = Field(
        default=None,
        description="Deprecated compatibility field. Product surfaces should prefer thesis and V2 explanation data.",
        json_schema_extra={"deprecated": True},
    )
    thesis: Optional[str] = None
    research_summary: Optional[ResearchSummaryResponse] = None
    analysis: Optional[dict] = None


class SubnetListResponse(BaseModel):
    total: int
    subnets: list[SubnetSummaryResponse]


class LatestRunResponse(BaseModel):
    last_score_run: Optional[str] = None
    subnet_count: int


class LeaderboardResponse(BaseModel):
    top: list[SubnetSummaryResponse]
    bottom: list[SubnetSummaryResponse]


class DistributionBucket(BaseModel):
    range_start: float
    range_end: float
    count: int


class DistributionResponse(BaseModel):
    buckets: list[DistributionBucket]
    total_subnets: int


class HealthResponse(BaseModel):
    status: str
    last_score_run: Optional[str] = None
    subnet_count: int


class ErrorResponse(BaseModel):
    detail: str


class BacktestLabelSummary(BaseModel):
    label: str
    observations: int
    avg_relative_forward_return_vs_tao_30d: Optional[float] = None
    avg_relative_forward_return_vs_tao_90d: Optional[float] = None
    avg_drawdown_risk: Optional[float] = None
    avg_liquidity_deterioration_risk: Optional[float] = None
    avg_concentration_deterioration_risk: Optional[float] = None


class BacktestObservation(BaseModel):
    netuid: int
    start_at: Optional[str] = None
    end_at: Optional[str] = None
    label: str
    score: Optional[float] = None
    fundamental_quality: Optional[float] = None
    mispricing_signal: Optional[float] = None
    fragility_risk: Optional[float] = None
    signal_confidence: Optional[float] = None
    relative_forward_return_vs_tao_30d: Optional[float] = None
    relative_forward_return_vs_tao_90d: Optional[float] = None
    drawdown_risk: Optional[float] = None
    liquidity_deterioration_risk: Optional[float] = None
    concentration_deterioration_risk: Optional[float] = None
    legacy_opportunity_gap: Optional[float] = None
    legacy_stress_robustness: Optional[float] = None


class BacktestResponse(BaseModel):
    observations: int
    targets: list[str]
    labels: list[BacktestLabelSummary]
    examples: list[BacktestObservation]
