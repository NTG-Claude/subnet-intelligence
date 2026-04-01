# Contributing

## Runtime Architecture

The current scoring runtime is V2-first. Treat this pipeline as the source of truth:

`conditioning -> raw features -> base components -> core blocks -> primary signals -> ranking -> explanation`

The main flow lives in:

- `features/conditioning.py`
- `features/model_v2.py`
- `features/components_*.py`
- `scoring/engine.py`
- `explain/engine.py`

Legacy axes and legacy-history projections still exist only as compatibility layers for a few downstream surfaces such as stress, labels, and persisted responses. Do not add new product logic on top of `AxisScores` or old V1 composite paths.

## Where To Add Logic

### 1. Conditioning

If the change is about repairing, bounding, or visibility/reliability of raw inputs, update `features/conditioning.py`.

Keep conditioning responsibilities limited to:

- preserving usable source values,
- bounding malformed inputs,
- reconstructing missing values only when the rule is explicit,
- recording `reliability` and `visibility`.

### 2. Raw Features

If the change is about deriving telemetry, cohort-relative signals, or history-aware measurements, update `features/model_v2.py`.

Raw features should:

- remain typed and deterministic,
- avoid network access,
- write stable V2 inputs to `bundle.raw`,
- avoid adding temporary compatibility aliases unless there is a verified downstream need.

### 3. Base Components

If the change belongs to a reusable building block, update the component modules:

- `features/components_quality.py`
- `features/components_opportunity.py`
- `features/components_fragility.py`
- `features/components_confidence.py`

Base components should be interpretable sub-scores, not product labels or leaderboard policy.

### 4. Core Blocks And Primary Signals

If the change affects the model’s actual investment view, update `features/model_v2.py` where V2 core blocks, contributions, ranking artifacts, and `PrimarySignals` are assembled.

Prefer:

- `bundle.base_components`
- `bundle.core_blocks`
- `bundle.contributions`
- `bundle.ranking`
- `bundle.primary_signals`

Avoid introducing new logic that depends on legacy axis names when a V2 block or contribution already exists.

### 5. Ranking

If the change affects ordering or score stabilization, update `scoring/engine.py`.

Ranking should be driven primarily by:

- `bundle.primary_signals`
- `bundle.core_blocks`
- `bundle.ranking`

History blending and telemetry-gap fallbacks are allowed, but they should remain explicit compatibility behavior around the V2 runtime rather than replacing it.

### 6. Explanation

If the change affects narratives or drivers, update `explain/engine.py`.

Explanations should prefer:

- V2 contributions,
- V2 core blocks,
- conditioned reliability and visibility,
- direct primary-signal rationale.

Metric-by-metric axis sorting should only be fallback context, not the main explanation source.

## Compatibility Guidance

Before removing any field from `bundle.raw`:

1. Check `scoring/`, `regimes/`, `labels/`, `explain/`, `api/`, `frontend/`, and `tests/`.
2. If the field is only used by tests or an internal compatibility shim, migrate those callers first.
3. Keep only the smallest compatibility surface needed to avoid accidental API regressions.

When compatibility is required:

- prefer reading from V2 blocks/components first,
- fall back to raw aliases only when necessary,
- document the reason in code with a short comment.

## Tests

Add or update tests in the area you changed:

- `tests/test_scoring_model_v2.py` for V2 bundle assembly, conditioning, and explanation behavior
- `tests/test_feature_normalization.py` for raw-feature and component interactions
- `tests/test_scoring_engine.py` for ranking, drift caps, and history fallbacks
- `tests/test_regimes_and_labels.py` for hard-rule and label integration

Minimum expectations:

- no new dependencies,
- typed code,
- deterministic tests,
- `pytest` should pass before merging.
