from features.normalization import clamp01


def build_confidence_components(
    raw: dict[str, float | None],
    normalized: dict[str, float],
    base_components: dict[str, float],
    opportunity_components: dict[str, float],
    fragility_components: dict[str, float],
) -> dict[str, float]:
    proxy_reliance = clamp01(raw.get("proxy_reliance_penalty") or 0.0)
    signal_fabrication_risk = normalized.get("signal_fabrication_risk", 0.0)
    market_structure_floor = normalized.get("market_structure_floor", base_components.get("market_relevance", 0.0))
    evidence_depth = clamp01(
        0.52 * normalized.get("history_depth_score", 0.0)
        + 0.34 * normalized.get("data_coverage", 0.0)
        + 0.14 * (1.0 - proxy_reliance)
    )
    evidence_consistency = clamp01(
        0.38 * (1.0 - normalized.get("consensus_signal_gap", 0.0))
        + 0.38 * normalized.get("confidence_thesis_coherence", 0.0)
        + 0.24 * (1.0 - signal_fabrication_risk)
    )
    telemetry_quality = clamp01(
        0.30 * normalized.get("update_freshness", 0.0)
        + 0.28 * normalized.get("market_data_reliability", 0.0)
        + 0.22 * normalized.get("validator_data_reliability", 0.0)
        + 0.20 * normalized.get("history_data_reliability", 0.0)
    )
    data_confidence = clamp01(
        0.40 * evidence_depth
        + 0.30 * evidence_consistency
        + 0.24 * telemetry_quality
        + 0.06 * normalized.get("external_data_reliability", 0.0)
    )
    market_confidence = clamp01(
        0.30 * base_components.get("market_relevance", 0.0)
        + 0.32 * base_components.get("liquidity_health", 0.0)
        + 0.24 * base_components.get("concentration_health", 0.0)
        + 0.16 * normalized.get("market_data_reliability", 0.0)
    )
    # External dev / GitHub style signals stay corroborative rather than
    # thesis-defining. The confidence stack should still stand on onchain
    # evidence, market structure, and coherence when external proxies are thin.
    thesis_confidence = clamp01(
        0.30 * evidence_consistency
        + 0.24 * opportunity_components.get("uncrowded_participation", 0.0)
        + 0.14 * opportunity_components.get("fair_value_gap_light", 0.0)
        + 0.16 * (1.0 - fragility_components.get("reversal_risk", 0.0))
        + 0.06 * normalized.get("external_source_legitimacy", 0.0)
        + 0.05 * normalized.get("external_dev_recency", 0.0)
        + 0.05 * normalized.get("external_dev_continuity", 0.0)
    )
    evidence_confidence = clamp01(
        0.40 * data_confidence
        + 0.30 * market_confidence
        + 0.30 * thesis_confidence
    )
    evidence_penalty = clamp01(
        0.34 * (1.0 - evidence_depth)
        + 0.22 * (1.0 - telemetry_quality)
        + 0.18 * proxy_reliance
        + 0.16 * signal_fabrication_risk
        + 0.10 * max(0.0, 0.58 - market_structure_floor) / 0.58
    )
    evidence_floor = clamp01(
        0.60 * data_confidence
        + 0.25 * normalized.get("history_depth_score", 0.0)
        + 0.15 * normalized.get("data_coverage", 0.0)
        - 0.18 * proxy_reliance
        - 0.12 * signal_fabrication_risk
    )
    return {
        "evidence_depth": evidence_depth,
        "evidence_consistency": evidence_consistency,
        "telemetry_quality": telemetry_quality,
        "data_confidence": data_confidence,
        "market_confidence": market_confidence,
        "thesis_confidence": thesis_confidence,
        "evidence_confidence": evidence_confidence,
        "evidence_penalty": evidence_penalty,
        "evidence_floor": evidence_floor,
    }
