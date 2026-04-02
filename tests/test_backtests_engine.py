from backtests.engine import build_backtest_summary


def test_backtest_summary_exposes_investment_targets_and_primary_outputs():
    rows = [
        {
            "netuid": 11,
            "score": 68.0,
            "alpha_price_tao": 1.0,
            "computed_at": "2026-03-01T00:00:00+00:00",
            "raw_data": {
                "label": "Compounding Quality",
                "analysis": {
                    "primary_outputs": {
                        "fundamental_quality": 72.0,
                        "mispricing_signal": 61.0,
                        "fragility_risk": 24.0,
                        "signal_confidence": 78.0,
                    },
                    "component_scores": {
                        "opportunity_gap": 18.0,
                        "stress_robustness": 71.0,
                    },
                },
                "raw_metrics": {
                    "slippage_10_tao": 0.10,
                    "performance_driven_by_few_actors": 0.20,
                },
            },
        },
        {
            "netuid": 11,
            "score": 72.0,
            "alpha_price_tao": 1.15,
            "computed_at": "2026-04-01T00:00:00+00:00",
            "raw_data": {
                "label": "Compounding Quality",
                "analysis": {
                    "primary_outputs": {
                        "fundamental_quality": 75.0,
                        "mispricing_signal": 66.0,
                        "fragility_risk": 26.0,
                        "signal_confidence": 80.0,
                    },
                    "component_scores": {
                        "opportunity_gap": 20.0,
                        "stress_robustness": 73.0,
                    },
                },
                "raw_metrics": {
                    "slippage_10_tao": 0.12,
                    "performance_driven_by_few_actors": 0.24,
                },
            },
        },
    ]

    summary = build_backtest_summary(rows)

    assert summary["observations"] == 1
    assert "relative_forward_return_vs_tao_30d" in summary["targets"]
    assert "drawdown_risk" in summary["targets"]
    example = summary["examples"][0]
    assert example["fundamental_quality"] == 72.0
    assert example["mispricing_signal"] == 61.0
    assert example["fragility_risk"] == 24.0
    assert example["signal_confidence"] == 78.0
    assert example["relative_forward_return_vs_tao_30d"] is not None
    assert summary["labels"][0]["avg_liquidity_deterioration_risk"] is not None
