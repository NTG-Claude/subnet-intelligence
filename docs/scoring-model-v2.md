# Scoring Model V2

## Current Chain Before V2

1. Collector snapshots flowed directly into `compute_raw_features()`.
2. `features/metrics.py` mixed raw measurements, proto-components, confidence orchestration, and penalty cascades.
3. `normalize_features()` both normalized inputs and built final thesis logic.
4. Explainability mostly reflected metric weights, not explicit block-level contributions.

## Main Problems Identified

- Bad or incomplete telemetry reached downstream formulas too early.
- Several risks were penalized multiple times through overlapping heuristics.
- Relative percentile strength could flatter weak subnets in weak cohorts.
- Confidence logic and mispricing logic were entangled.

## V2 Runtime Shape

1. Collector Output
2. Data Conditioning Layer
3. Raw Features Layer
4. Base Components Layer
5. Core Blocks Layer
6. Primary Signals Layer
7. Ranking Layer
8. Explainability Layer

## Explicit Signal Dependency Chain

### Before

`RawSubnetSnapshot`
-> `compute_raw_features()`
-> raw metrics plus embedded proto-thesis heuristics
-> `normalize_features()`
-> weighted metric outputs
-> confidence and penalty cascades
-> primary signals
-> ranking / labels / explainability

### After

`RawSubnetSnapshot`
-> `condition_snapshot()` in `features/conditioning.py`
-> canonicalized and bounded runtime inputs plus reliability metadata
-> `compute_raw_features()` in `features/model_v2.py`
-> raw features only
-> `normalize_features()` in `features/model_v2.py`
-> absolute-plus-relative normalization
-> base components
-> core blocks
-> primary signals
-> ranking helpers
-> explainability contributors and uncertainties

## Data Conditioning

`features/conditioning.py` now:

- validates impossible values
- canonicalizes list, count, ratio, and history inputs
- bounds extreme or negative values
- reconstructs `alpha_price_tao` conservatively from reserves when needed
- emits reliability markers:
  - `market_data_reliability`
  - `validator_data_reliability`
  - `history_data_reliability`
  - `external_data_reliability`
- preserves missingness visibility with `original`, `bounded`, `reconstructed`, and `discarded`

### How Conditioning Is Bound Into The Model

- `compute_raw_features()` no longer reads collector payloads directly.
- It now starts from `ConditionedSnapshot.values`.
- Reliability markers from conditioning feed directly into confidence features and the `evidence_confidence` block.
- Visibility markers remain attached to `FeatureBundle.conditioned` and are exposed through explanation output.

## Base Components

- Quality:
  - `participation_health`
  - `validator_health`
  - `liquidity_health`
  - `concentration_health`
  - `market_relevance`
- Opportunity:
  - `quality_momentum`
  - `reserve_momentum`
  - `price_lag`
  - `uncrowded_participation`
  - `fair_value_gap_light`
- Fragility:
  - `crowding_level`
  - `concentration_risk`
  - `thin_liquidity_risk`
  - `reversal_risk`
  - `weak_market_structure`
- Confidence:
  - `evidence_depth`
  - `evidence_consistency`
  - `telemetry_quality`
  - `data_confidence`
  - `market_confidence`
  - `thesis_confidence`

## Core Blocks

- `fundamental_health`
- `opportunity_underreaction`
- `fragility`
- `evidence_confidence`
- `market_legitimacy`

## Primary Signals

- `fundamental_quality`
  - mainly `fundamental_health`
  - small `market_legitimacy` lift
  - small structural penalty for extreme concentration or illiquidity
- `mispricing_signal`
  - `base_opportunity * confidence_factor * structural_validity_factor - small_penalties`
- `fragility_risk`
  - directly from `fragility`
- `signal_confidence`
  - controlled aggregation of `data_confidence`, `market_confidence`, and `thesis_confidence`

## Ranking Layer

The ranking layer remains separate from `mispricing_signal`.

It now leans on:

- `fundamental_quality`
- `mispricing_signal`
- `signal_confidence`
- `resilience`
- `market_relevance`
- `confidence_adjusted_thesis_strength` as a bounded helper

History stabilization, bounded drift, telemetry-gap fallback, and stress integration are still preserved through the existing scoring engine.

## Removed, Merged, or Demoted Legacy Metrics

- Demoted from final signal orchestration to compatibility/debug:
  - `signal_fabrication_risk`
  - `proxy_reliance_penalty`
  - `low_evidence_high_conviction`
- Merged into cleaner V2 paths:
  - `crowding_proxy` -> `crowding_level` plus small penalty path
  - `overreaction_score` -> small penalty path
  - `mispricing_structural_drag` -> `structural_validity_factor`
  - `crowded_repricing_discount` -> bounded crowding penalty
  - `confidence_adjusted_thesis_strength` -> ranking helper only

## Explainability Migration

Existing explanation fields remain available, but V2 adds:

- `block_scores`
- `primary_signal_contributors`
- `top_negative_drags`
- `key_uncertainties`
- `conditioning`

These are derived from real component/block contributions rather than free-text templates alone.

### API / Explanation Migration Note

No primary signal names changed.

Existing explanation consumers can continue using:

- `primary_outputs`
- `component_scores`
- `why_mispriced`
- `risk_drivers`
- `confidence_rationale`

New machine-readable fields are additive:

- `block_scores`
- `primary_signal_contributors`
- `top_negative_drags`
- `key_uncertainties`
- `conditioning`
