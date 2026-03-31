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


def build_backtest_summary(rows: list[dict]) -> dict:
    by_netuid: dict[int, list[dict]] = defaultdict(list)
    for row in rows:
        by_netuid[row["netuid"]].append(row)

    observations: list[dict] = []
    label_stats: dict[str, list[dict]] = defaultdict(list)

    for netuid, history in by_netuid.items():
        ordered = sorted(history, key=lambda item: item["computed_at"] or "")
        for current, future in zip(ordered, ordered[1:]):
            observation = {
                "netuid": netuid,
                "start_at": current.get("computed_at"),
                "end_at": future.get("computed_at"),
                "label": _label(current),
                "score": current.get("score"),
                "future_score_change": future_score_decay(current.get("score"), future.get("score")),
                "future_return_proxy": future_return_proxy(current.get("alpha_price_tao"), future.get("alpha_price_tao")),
                "future_slippage_deterioration": future_slippage_deterioration(
                    _metric(current, ["raw_metrics", "slippage_10_tao"]),
                    _metric(future, ["raw_metrics", "slippage_10_tao"]),
                ),
                "future_concentration_increase": future_slippage_deterioration(
                    _metric(current, ["raw_metrics", "performance_driven_by_few_actors"]),
                    _metric(future, ["raw_metrics", "performance_driven_by_few_actors"]),
                ),
                "opportunity_gap": (_analysis(current).get("component_scores") or {}).get("opportunity_gap"),
                "stress_robustness": (_analysis(current).get("component_scores") or {}).get("stress_robustness"),
            }
            observations.append(observation)
            label_stats[observation["label"]].append(observation)

    def _avg(items: list[dict], key: str):
        vals = [item[key] for item in items if item.get(key) is not None]
        return round(fmean(vals), 4) if vals else None

    label_summary = []
    for label, items in sorted(label_stats.items(), key=lambda item: len(item[1]), reverse=True):
        label_summary.append(
            {
                "label": label,
                "observations": len(items),
                "avg_future_score_change": _avg(items, "future_score_change"),
                "avg_future_return_proxy": _avg(items, "future_return_proxy"),
                "avg_future_slippage_deterioration": _avg(items, "future_slippage_deterioration"),
                "avg_future_concentration_increase": _avg(items, "future_concentration_increase"),
            }
        )

    return {
        "observations": len(observations),
        "labels": label_summary,
        "examples": observations[:25],
    }
