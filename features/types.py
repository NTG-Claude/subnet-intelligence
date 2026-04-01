from dataclasses import dataclass, field


@dataclass
class FeatureMetric:
    name: str
    value: float | None
    normalized: float
    category: str
    axis: str
    weight: float
    higher_is_better: bool = True

    @property
    def contribution(self) -> float:
        centered = self.normalized if self.higher_is_better else (1.0 - self.normalized)
        return centered * self.weight


@dataclass
class AxisScores:
    intrinsic_quality: float
    economic_sustainability: float
    reflexivity: float
    stress_robustness: float
    opportunity_gap: float


@dataclass
class PrimarySignals:
    fundamental_quality: float
    mispricing_signal: float
    fragility_risk: float
    signal_confidence: float


@dataclass
class ConditionedSnapshot:
    values: dict[str, object] = field(default_factory=dict)
    reliability: dict[str, float] = field(default_factory=dict)
    visibility: dict[str, list[str]] = field(
        default_factory=lambda: {
            "original": [],
            "bounded": [],
            "reconstructed": [],
            "discarded": [],
        }
    )


@dataclass
class FeatureBundle:
    raw: dict[str, float | None]
    metrics: dict[str, FeatureMetric] = field(default_factory=dict)
    axes: AxisScores | None = None
    primary_signals: PrimarySignals | None = None
    conditioned: ConditionedSnapshot | None = None
    base_components: dict[str, float] = field(default_factory=dict)
    core_blocks: dict[str, float] = field(default_factory=dict)
    ranking: dict[str, float] = field(default_factory=dict)
    contributions: dict[str, list[dict]] = field(default_factory=dict)
