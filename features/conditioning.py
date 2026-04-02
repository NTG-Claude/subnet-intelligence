import math
from dataclasses import replace
from datetime import datetime

from collectors.models import HistoricalFeaturePoint, RawSubnetSnapshot
from features.types import ConditionedSnapshot


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _log_scaled(value: float | int | None, scale: float) -> float:
    if value is None:
        return 0.0
    numeric = max(float(value), 0.0)
    if numeric <= 0.0:
        return 0.0
    return clamp01(math.log1p(numeric) / math.log1p(scale))


def _finite_number(value: object) -> float | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric):
        return None
    return numeric


def _register(visibility: dict[str, list[str]], bucket: str, name: str) -> None:
    if name not in visibility[bucket]:
        visibility[bucket].append(name)


def _bounded_numeric(
    visibility: dict[str, list[str]],
    name: str,
    value: object,
    *,
    floor: float | None = None,
    ceiling: float | None = None,
) -> float | None:
    numeric = _finite_number(value)
    if numeric is None:
        _register(visibility, "discarded", name)
        return None
    bounded = numeric
    if floor is not None:
        bounded = max(floor, bounded)
    if ceiling is not None:
        bounded = min(ceiling, bounded)
    _register(visibility, "original", name)
    if bounded != numeric:
        _register(visibility, "bounded", name)
    return bounded


def _bounded_list(
    visibility: dict[str, list[str]],
    name: str,
    values: list[object] | None,
    *,
    floor: float | None = None,
    ceiling: float | None = None,
) -> list[float]:
    clean: list[float] = []
    if not values:
        return clean
    for value in values:
        bounded = _bounded_numeric(visibility, name, value, floor=floor, ceiling=ceiling)
        if bounded is not None:
            clean.append(bounded)
    if len(clean) != len(values):
        _register(visibility, "discarded", name)
    return clean


def _sanitize_timestamp(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
    except ValueError:
        return None


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _external_repo_signals(snapshot: RawSubnetSnapshot) -> dict[str, float]:
    github = snapshot.github
    if github is None:
        return {
            "external_source_legitimacy": 0.0,
            "external_dev_recency": 0.0,
            "external_dev_continuity": 0.0,
            "external_dev_breadth": 0.0,
            "external_data_reliability": 0.0,
        }

    source_legitimacy = 0.0
    if github.github_url and github.owner and github.repo:
        if github.source_status in {"active_repo", "mapped_no_data"}:
            source_legitimacy = 1.0
        elif github.source_status == "fetch_failed":
            source_legitimacy = 0.35
        else:
            source_legitimacy = 0.7
    elif github.github_url:
        source_legitimacy = 0.5

    reference_time = _parse_iso_datetime(github.last_commit_at) or _parse_iso_datetime(github.last_push)
    if reference_time is None:
        dev_recency = 0.0
    else:
        age_days = max((datetime.now(reference_time.tzinfo) - reference_time).total_seconds() / 86400.0, 0.0)
        if age_days <= 14.0:
            dev_recency = 1.0
        elif age_days <= 45.0:
            dev_recency = 0.82
        elif age_days <= 90.0:
            dev_recency = 0.6
        elif age_days <= 180.0:
            dev_recency = 0.38
        elif age_days <= 365.0:
            dev_recency = 0.18
        else:
            dev_recency = 0.0

    dev_continuity = clamp01(
        0.20 * _log_scaled(github.commits_30d, 30.0)
        + 0.35 * _log_scaled(github.commits_90d, 90.0)
        + 0.45 * _log_scaled(github.commits_180d, 180.0)
    )
    dev_breadth = clamp01(
        0.20 * _log_scaled(github.contributors_30d, 4.0)
        + 0.35 * _log_scaled(github.contributors_90d, 8.0)
        + 0.45 * _log_scaled(github.contributors_180d, 12.0)
    )
    external_data_reliability = clamp01(
        0.30 * source_legitimacy
        + 0.25 * dev_recency
        + 0.30 * dev_continuity
        + 0.15 * dev_breadth
    )
    return {
        "external_source_legitimacy": source_legitimacy,
        "external_dev_recency": dev_recency,
        "external_dev_continuity": dev_continuity,
        "external_dev_breadth": dev_breadth,
        "external_data_reliability": external_data_reliability,
    }


def _sanitize_history(
    history: list[HistoricalFeaturePoint],
    visibility: dict[str, list[str]],
) -> list[HistoricalFeaturePoint]:
    clean: list[HistoricalFeaturePoint] = []
    for point in history:
        timestamp = _sanitize_timestamp(point.timestamp)
        if timestamp is None:
            _register(visibility, "discarded", "history.timestamp")
            continue
        concentration_proxy = _bounded_numeric(visibility, "history.concentration_proxy", point.concentration_proxy, floor=0.0, ceiling=1.0)
        liquidity_thinness = _bounded_numeric(visibility, "history.liquidity_thinness", point.liquidity_thinness, floor=0.0, ceiling=1.0)
        clean.append(
            replace(
                point,
                timestamp=timestamp,
                alpha_price_tao=_bounded_numeric(visibility, "history.alpha_price_tao", point.alpha_price_tao, floor=0.0),
                tao_in_pool=_bounded_numeric(visibility, "history.tao_in_pool", point.tao_in_pool, floor=0.0),
                emission_per_block_tao=_bounded_numeric(visibility, "history.emission_per_block_tao", point.emission_per_block_tao, floor=0.0),
                active_ratio=_bounded_numeric(visibility, "history.active_ratio", point.active_ratio, floor=0.0, ceiling=1.0),
                participation_breadth=_bounded_numeric(visibility, "history.participation_breadth", point.participation_breadth, floor=0.0, ceiling=1.0),
                validator_participation=_bounded_numeric(visibility, "history.validator_participation", point.validator_participation, floor=0.0, ceiling=1.0),
                incentive_distribution_quality=_bounded_numeric(visibility, "history.incentive_distribution_quality", point.incentive_distribution_quality, floor=0.0, ceiling=1.0),
                concentration_proxy=concentration_proxy,
                liquidity_thinness=liquidity_thinness,
                market_relevance_proxy=_bounded_numeric(visibility, "history.market_relevance_proxy", point.market_relevance_proxy, floor=0.0, ceiling=1.0),
                market_structure_floor=_bounded_numeric(visibility, "history.market_structure_floor", point.market_structure_floor, floor=0.0, ceiling=1.0),
                intrinsic_quality=_bounded_numeric(visibility, "history.intrinsic_quality", point.intrinsic_quality, floor=0.0, ceiling=1.0),
                economic_sustainability=_bounded_numeric(visibility, "history.economic_sustainability", point.economic_sustainability, floor=0.0, ceiling=1.0),
                reflexivity=_bounded_numeric(visibility, "history.reflexivity", point.reflexivity, floor=0.0, ceiling=1.0),
                stress_robustness=_bounded_numeric(visibility, "history.stress_robustness", point.stress_robustness, floor=0.0, ceiling=1.0),
                opportunity_gap=_bounded_numeric(visibility, "history.opportunity_gap", point.opportunity_gap, floor=-1.0, ceiling=1.0),
                fundamental_quality=_bounded_numeric(visibility, "history.fundamental_quality", point.fundamental_quality, floor=0.0, ceiling=1.0),
                mispricing_signal=_bounded_numeric(visibility, "history.mispricing_signal", point.mispricing_signal, floor=0.0, ceiling=1.0),
                fragility_risk=_bounded_numeric(visibility, "history.fragility_risk", point.fragility_risk, floor=0.0, ceiling=1.0),
                signal_confidence=_bounded_numeric(visibility, "history.signal_confidence", point.signal_confidence, floor=0.0, ceiling=1.0),
            )
        )
    return clean


def condition_snapshot(snapshot: RawSubnetSnapshot) -> ConditionedSnapshot:
    visibility = {
        "original": [],
        "bounded": [],
        "reconstructed": [],
        "discarded": [],
    }
    n_total = int(_bounded_numeric(visibility, "n_total", snapshot.n_total, floor=0.0) or 0.0)
    yuma_neurons = int(_bounded_numeric(visibility, "yuma_neurons", snapshot.yuma_neurons, floor=0.0) or 0.0)
    base_population = max(n_total, yuma_neurons, 1)
    n_validators = int(_bounded_numeric(visibility, "n_validators", snapshot.n_validators, floor=0.0, ceiling=float(base_population)) or 0.0)
    active_neurons = int(_bounded_numeric(visibility, "active_neurons_7d", snapshot.active_neurons_7d, floor=0.0, ceiling=float(base_population)) or 0.0)
    active_validators = _bounded_numeric(visibility, "active_validators_7d", snapshot.active_validators_7d, floor=0.0, ceiling=float(max(n_validators, 1)))
    unique_coldkeys = int(_bounded_numeric(visibility, "unique_coldkeys", snapshot.unique_coldkeys, floor=0.0, ceiling=float(max(base_population * 4, 1))) or 0.0)
    total_stake_tao = _bounded_numeric(visibility, "total_stake_tao", snapshot.total_stake_tao, floor=0.0) or 0.0
    tao_in_pool = _bounded_numeric(visibility, "tao_in_pool", snapshot.tao_in_pool, floor=0.0)
    alpha_in_pool = _bounded_numeric(visibility, "alpha_in_pool", snapshot.alpha_in_pool, floor=0.0)
    alpha_price_tao = _bounded_numeric(visibility, "alpha_price_tao", snapshot.alpha_price_tao, floor=0.0)
    if (alpha_price_tao is None or alpha_price_tao <= 0.0) and (tao_in_pool or 0.0) > 0.0 and (alpha_in_pool or 0.0) > 0.0:
        alpha_price_tao = safe_ratio(tao_in_pool or 0.0, max(alpha_in_pool or 0.0, 1e-9))
        _register(visibility, "reconstructed", "alpha_price_tao")
    elif (tao_in_pool or 0.0) > 0.0 and (alpha_in_pool or 0.0) > 0.0 and alpha_price_tao:
        implied = safe_ratio(tao_in_pool or 0.0, max(alpha_in_pool or 0.0, 1e-9))
        if implied > 0:
            ratio_gap = abs(alpha_price_tao - implied) / implied
            if ratio_gap > 0.4:
                alpha_price_tao = implied
                _register(visibility, "bounded", "alpha_price_tao")

    values = {
        "netuid": snapshot.netuid,
        "current_block": int(_bounded_numeric(visibility, "current_block", snapshot.current_block, floor=0.0) or 0.0),
        "n_total": n_total,
        "yuma_neurons": yuma_neurons,
        "active_neurons_7d": active_neurons,
        "active_validators_7d": None if active_validators is None else int(active_validators),
        "total_stake_tao": total_stake_tao,
        "unique_coldkeys": unique_coldkeys,
        "top3_stake_fraction": _bounded_numeric(visibility, "top3_stake_fraction", snapshot.top3_stake_fraction, floor=0.0, ceiling=1.0) or 0.0,
        "emission_per_block_tao": _bounded_numeric(visibility, "emission_per_block_tao", snapshot.emission_per_block_tao, floor=0.0) or 0.0,
        "incentive_scores": _bounded_list(visibility, "incentive_scores", snapshot.incentive_scores, floor=0.0),
        "n_validators": n_validators,
        "tao_in_pool": tao_in_pool or 0.0,
        "alpha_in_pool": alpha_in_pool or 0.0,
        "alpha_price_tao": alpha_price_tao or 0.0,
        "coldkey_stakes": _bounded_list(visibility, "coldkey_stakes", snapshot.coldkey_stakes, floor=0.0),
        "validator_stakes": _bounded_list(visibility, "validator_stakes", snapshot.validator_stakes, floor=0.0),
        "validator_weight_matrix": [
            _bounded_list(visibility, "validator_weight_matrix", row, floor=0.0, ceiling=1.0)
            for row in snapshot.validator_weight_matrix
            if row
        ],
        "validator_bond_matrix": [
            _bounded_list(visibility, "validator_bond_matrix", row, floor=0.0, ceiling=1.0)
            for row in snapshot.validator_bond_matrix
            if row
        ],
        "last_update_blocks": [
            int(block)
            for block in _bounded_list(
                visibility,
                "last_update_blocks",
                snapshot.last_update_blocks,
                floor=0.0,
                ceiling=float(max(snapshot.current_block, 0)),
            )
        ],
        "yuma_mask": list(snapshot.yuma_mask or []),
        "mechanism_ids": list(snapshot.mechanism_ids or []),
        "immunity_period": int(_bounded_numeric(visibility, "immunity_period", snapshot.immunity_period, floor=0.0) or 0.0),
        "registration_allowed": bool(snapshot.registration_allowed),
        "target_regs_per_interval": int(_bounded_numeric(visibility, "target_regs_per_interval", snapshot.target_regs_per_interval, floor=0.0) or 0.0),
        "min_burn": _bounded_numeric(visibility, "min_burn", snapshot.min_burn, floor=0.0) or 0.0,
        "max_burn": _bounded_numeric(visibility, "max_burn", snapshot.max_burn, floor=0.0) or 0.0,
        "difficulty": _bounded_numeric(visibility, "difficulty", snapshot.difficulty, floor=0.0) or 0.0,
        "github": snapshot.github,
        "history": _sanitize_history(snapshot.history or [], visibility),
    }

    market_inputs = [
        1.0 if values["tao_in_pool"] > 0 else 0.0,
        1.0 if values["alpha_in_pool"] > 0 else 0.0,
        1.0 if values["alpha_price_tao"] > 0 else 0.0,
    ]
    validator_inputs = [
        1.0 if values["n_validators"] > 0 else 0.0,
        1.0 if values["validator_stakes"] else 0.0,
        1.0 if values["validator_weight_matrix"] else 0.0,
    ]
    history_inputs = [
        1.0 if values["history"] else 0.0,
        clamp01(len(values["history"]) / 14.0),
        1.0 if any(point.alpha_price_tao is not None for point in values["history"]) else 0.0,
    ]
    external_signals = _external_repo_signals(snapshot)
    reliability = {
        "market_data_reliability": clamp01(sum(market_inputs) / len(market_inputs)),
        "validator_data_reliability": clamp01(sum(validator_inputs) / len(validator_inputs)),
        "history_data_reliability": clamp01(sum(history_inputs) / len(history_inputs)),
        **external_signals,
    }
    return ConditionedSnapshot(values=values, reliability=reliability, visibility=visibility)
