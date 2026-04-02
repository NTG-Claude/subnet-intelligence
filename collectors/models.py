from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RepoActivitySnapshot:
    github_url: Optional[str] = None
    owner: Optional[str] = None
    repo: Optional[str] = None
    source_status: str = "unavailable"
    fetched_at: Optional[str] = None
    commits_30d: int = 0
    contributors_30d: int = 0
    stars: int = 0
    forks: int = 0
    open_issues: int = 0
    last_push: Optional[str] = None


@dataclass
class HistoricalFeaturePoint:
    timestamp: str
    alpha_price_tao: Optional[float] = None
    tao_in_pool: Optional[float] = None
    emission_per_block_tao: Optional[float] = None
    active_ratio: Optional[float] = None
    participation_breadth: Optional[float] = None
    validator_participation: Optional[float] = None
    incentive_distribution_quality: Optional[float] = None
    concentration_proxy: Optional[float] = None
    liquidity_thinness: Optional[float] = None
    market_relevance_proxy: Optional[float] = None
    market_structure_floor: Optional[float] = None
    intrinsic_quality: Optional[float] = None
    economic_sustainability: Optional[float] = None
    reflexivity: Optional[float] = None
    stress_robustness: Optional[float] = None
    opportunity_gap: Optional[float] = None
    fundamental_quality: Optional[float] = None
    mispricing_signal: Optional[float] = None
    fragility_risk: Optional[float] = None
    signal_confidence: Optional[float] = None


@dataclass
class RawSubnetSnapshot:
    netuid: int
    current_block: int
    n_total: int = 0
    yuma_neurons: int = 0
    active_neurons_7d: int = 0
    active_validators_7d: Optional[int] = None
    total_stake_tao: float = 0.0
    unique_coldkeys: int = 0
    top3_stake_fraction: float = 1.0
    emission_per_block_tao: float = 0.0
    incentive_scores: list[float] = field(default_factory=list)
    n_validators: int = 0
    tao_in_pool: float = 0.0
    alpha_in_pool: float = 0.0
    alpha_price_tao: float = 0.0
    coldkey_stakes: list[float] = field(default_factory=list)
    validator_stakes: list[float] = field(default_factory=list)
    validator_weight_matrix: list[list[float]] = field(default_factory=list)
    validator_bond_matrix: list[list[float]] = field(default_factory=list)
    last_update_blocks: list[int] = field(default_factory=list)
    yuma_mask: list[bool] = field(default_factory=list)
    mechanism_ids: list[int] = field(default_factory=list)
    immunity_period: int = 0
    registration_allowed: bool = False
    target_regs_per_interval: int = 0
    min_burn: float = 0.0
    max_burn: float = 0.0
    difficulty: float = 0.0
    github: Optional[RepoActivitySnapshot] = None
    history: list[HistoricalFeaturePoint] = field(default_factory=list)
