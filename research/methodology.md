# Methodology

## Principles

1. Archive raw API responses before any transformation.
2. Normalize to a common UTC schema.
3. Use forward-fill only when aligning irregular observations to a grid.
4. Validate with chronological or walk-forward splits—never random shuffles.
5. Establish statistical relationships before any trading simulation.
6. Treat failed hypotheses as first-class results.

## Data

- **Primary source:** Kalshi public Trade API.
- **History representation:** candlesticks (`period_interval` ∈ {1, 60, 1440} minutes).
- **Local research intervals:** 1m / 5m / 15m / 1h via resampling.
- **Storage:** JSON (raw) → Parquet (normalized) → DuckDB (optional analytics).

## Lead-lag procedure

1. Compute `r_i,t = p_i,t - p_i,t-1` on mid (or documented price field).
2. Align related markets on a shared time grid.
3. Estimate OLS across horizons.
4. Inspect suspicious results (sparse data, stale quotes, tiny N).
5. Apply robustness checklist before interpretation.

## Synthetic aggregates

1. Define constituent set in `config/market_groups.yaml`.
2. Simulate aggregate outcomes (Monte Carlo).
3. Document correlation mode (`independent` baseline vs explicit correlation).
4. Compare to directly traded aggregate contract.
5. Study `D_t` dynamics—without assuming tradability.

## Backtests (later)

Only after a plausible signal survives controls:

- Execute at bid/ask, not mid.
- Include fees and configurable slippage.
- Chronological validation.
- Report gross and net metrics; stress thresholds without optimizing for vanity.

## What this document is not

This is not a claim that any signal exists. Update with concrete parameter
choices only when analyses are run.
