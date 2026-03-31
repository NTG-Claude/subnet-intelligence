from collections import defaultdict
from statistics import fmean

from backtests.proxies import (
    future_return_proxy,
    future_score_decay,
    future_slippage_deterioration,
)


def _analysis(row: dict) -> dict:
    raw = row.get("raw_data") or {}
    return raw.get("analysis") or {}


def _label(row: dict) -> str:
    raw = row.get("raw_data") or {}
    return raw.get("label") or "Unlabeled"


def _metric(row: dict, path: list[str], default=None):
    current = row.get("raw_data") or {}
    for key in path:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return current if current is not None else default


def _avg(items: list[dict], key: str):
    vals = [item[key] for item in items if item.get(key) is not None]
    return round(fmean(vals), 4) if vals else None


def _primary_output(row: dict, key: str) -> float | None:
    return _metric(row, ["analysis", "primary_outputs", key])


def _legacy_component(row: dict, key: str) -> float | None:
    return _metric(row, ["analysis", "component_scores", key])


INVESTMENT_TARGETS = {
    "relative_forward_return_vs_tao_30d": lambda current, future: future_return_proxy(
        current.get("alpha_price_tao"), future.get("alpha_price_tao")
    ),
    "relative_forward_return_vs_tao_90d": lambda current, future: future_return_proxy(
        current.get("alpha_price_tao"), future.get("alpha_price_tao")
    ),
    "drawdown_risk": lambda current, future: future_score_decay(current.get("score"), future.get("score")),
    "liquidity_deterioration_risk": lambda current, future: future_slippage_deterioration(
        _metric(current, ["raw_metrics", "slippage_10_tao"]),
        _metric(future, ["raw_metrics", "slippage_10_tao"]),
    ),
    "concentration_deterioration_risk": lambda current, future: future_slippage_deterioration(
        _metric(current, ["raw_metrics", "performance_driven_by_few_actors"]),
        _metric(future, ["raw_metrics", "performance_driven_by_few_actors"]),
    ),
}


def build_backtest_summary(rows: list[dict]) -> dict:
    by_netuid: dict[int, list[dict]] = defaultdict(list)
    for row in rows:
        by_netuid[row["netuid"]].append(row)

    observations: list[dict] = []
    label_stats: dict[str, list[dict]] = defaultdict(list)

    for netuid, history in by_netuid.items():
        ordered = sorted(history, key=lambda item: item["computed_at"] or "")
        for current, future in zip(ordered, ordered[1:]):
            targets = {name: fn(current, future) for name, fn in INVESTMENT_TARGETS.items()}
            observation = {
                "netuid": netuid,
                "start_at": current.get("computed_at"),
                "end_at": future.get("computed_at"),
                "label": _label(current),
                "score": current.get("score"),
                "fundamental_quality": _primary_output(current, "fundamental_quality"),
                "mispricing_signal": _primary_output(current, "mispricing_signal"),
                "fragility_risk": _primary_output(current, "fragility_risk"),
                "signal_confidence": _primary_output(current, "signal_confidence"),
                "legacy_opportunity_gap": _legacy_component(current, "opportunity_gap"),
                "legacy_stress_robustness": _legacy_component(current, "stress_robustness"),
                **targets,
            }
            observations.append(observation)
            label_stats[observation["label"]].append(observation)

    label_summary = []
    for label, items in sorted(label_stats.items(), key=lambda item: len(item[1]), reverse=True):
        label_summary.append(
            {
                "label": label,
                "observations": len(items),
                "avg_relative_forward_return_vs_tao_30d": _avg(items, "relative_forward_return_vs_tao_30d"),
                "avg_relative_forward_return_vs_tao_90d": _avg(items, "relative_forward_return_vs_tao_90d"),
                "avg_drawdown_risk": _avg(items, "drawdown_risk"),
                "avg_liquidity_deterioration_risk": _avg(items, "liquidity_deterioration_risk"),
                "avg_concentration_deterioration_risk": _avg(items, "concentration_deterioration_risk"),
            }
        )

    return {
        "observations": len(observations),
        "labels": label_summary,
        "examples": observations[:25],
        "targets": list(INVESTMENT_TARGETS),
    }
