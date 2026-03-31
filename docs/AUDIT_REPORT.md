# Audit Report

## Current architecture
- `scorer/run.py` orchestrates one daily snapshot run, collects on-chain data in `scorer/bittensor_client.py`, adds light GitHub enrichment, computes a single composite score in `scorer/composite.py`, and stores mostly final outputs in `scorer/database.py`.
- The current repo behaves like a ranking dashboard. It does not separate intrinsic quality, economic structure, reflexivity, fragility, or opportunity gap into distinct research layers.
- API and frontend still expose legacy dashboard fields rather than an analysis system.

## Data coverage
- Direct on-chain coverage: metagraph participation, coldkey stake concentration, incentive vector, validator permits, dTAO reserves, and a derived emission estimate.
- Off-chain coverage: GitHub commits and contributors.
- Missing persistent history for reserves, slippage probes, concentration, reflexivity, stress drawdowns, and regime changes.
- No explicit coverage for registration policy, immunity/dereg regime, validator weight informativeness over time, or bond dynamics over time.

## Feature coverage
- Current production features are first-order snapshot proxies: activity, validator count, distribution health, pool depth, APY, stake-per-emission, commits, contributors.
- No production feature family exists for reflexivity, stress robustness, or opportunity gap.
- Slippage, reserve sensitivity, crowding, validator dominance, disagreement informativeness, and scenario recomputation are absent in the old model.
- Multi-mechanism support is only partial and currently leaks a denominator bug into activity scoring.

## Scoring weaknesses
- Score leakage / double counting:
  - `undervalue` already includes activity and decentralization; `health` rewards both again.
  - `yield_q` rewards APY, pool depth, and stake-per-emission, which can all rise from the same capital-flow regime.
  - `stake_per_emission` and pool depth both reward capital absorption and can overrate reflexive inflows.
- Percentile normalization forces relative winners even in weak global regimes.
- Emission is still mostly treated as a positive quantity, not a distortion source that must be conditioned on quality.
- No hard caps exist for thin liquidity, concentration, or uninformative consensus.

## Missing alpha dimensions
- Earned vs reflexive vs fragile decomposition.
- Consensus informativeness, not just consensus participation.
- Stress behavior under outflows, liquidity shocks, validator removal, concentration shocks, and consensus perturbation.
- Opportunity gap between internal quality and market narrative.
- Persistence, acceleration, reversal risk, and regime change logic.

## Bug risks / implementation flaws
- `n_active_7d` is Yuma-filtered, but the old active ratio used `n_total` as denominator, penalizing multi-mechanism subnets.
- `market_cap_tao = tao_pool * 2` is an AMM TVL proxy mislabeled as market cap.
- `force_refresh` is parsed but not used.
- `get_github_coords(..., live_fetch=True)` inside every subnet fetch partially defeats the earlier batch identity warmup.
- Explainability is too thin for research: intermediate metrics are not persisted in a first-class way.

## Refactor priorities
1. Split collection, features, scoring, stress, labels, explainability, and storage into separate layers.
2. Fix multi-mechanism leakage and expose richer raw collector outputs.
3. Replace the single composite with axis-based scoring.
4. Persist analysis payloads and daily history so regime logic becomes possible.
5. Add hard rules and contradiction-based labels before further weight tuning.

## Quick wins
- Fix the Yuma denominator bug.
- Add constant-product slippage probes from existing reserve data.
- Persist analysis/debug payloads into `raw_data`.
- Cap scores when liquidity is too thin or concentration is too high.

## Structural redesign proposal
- `collectors/`: raw subnet snapshots and adapters.
- `features/`: direct/derived/history/simulated metrics.
- `regimes/`: hard rules and regime detectors.
- `stress/`: scenario simulations and fragility classification.
- `scoring/`: axis construction and total score composition.
- `labels/`: contradiction-based labeling.
- `explain/`: drivers, debug metrics, thesis output.
- `storage/`: history loading and persistence helpers.
- `backtests/`: forward proxies for persistence, deterioration, and score decay.
