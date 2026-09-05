# SignalGraph
Quantitative Information Flow Across Prediction Markets

SignalGraph is a quantitative research framework for studying information
propagation and probabilistic consistency across related prediction markets. It
analyzes lead-lag relationships, constructs synthetic probabilities from
constituent markets, and tests whether temporary cross-market dislocations
predict future price convergence.

This is **not** a generic stock predictor, election tip sheet, or AI trading bot.

## Motivation

When multiple prediction markets relate to the same underlying event—or to
logically connected outcomes—temporary inconsistencies and delayed information
propagation may appear. SignalGraph provides infrastructure to measure whether
those dislocations are informative, spurious, or explained by microstructure.

## Research question

When related prediction markets temporarily disagree, does that disagreement
predict subsequent price convergence—after accounting for liquidity, spreads,
volume, and other confounders?

## Architecture

```
config/           Settings and market relationship groups
data/             Raw → normalized → processed datasets
src/signalgraph/  Reusable library (ingestion, research, simulation, backtest)
scripts/          CLI entry points for fetch / normalize / research
notebooks/        Exploration templates (no fabricated results)
tests/            Unit tests including no-lookahead guards
research/         Hypotheses, methodology, findings, limitations
frontend/         Placeholder only
```

Initial data source: **Kalshi** (public market data; no auth required for listing
and candlesticks). Polymarket is scaffolded for later addition.

## Data pipeline

1. Pull market metadata / history via platform clients.
2. Archive **raw** JSON unchanged under `data/raw/`.
3. Normalize into a common UTC timestamped schema (Parquet).
4. Optionally resample onto fixed grids with **forward-fill only**.
5. Join related markets via `config/market_groups.yaml`.

## Research methodology

1. Explore probability paths and liquidity qualitatively.
2. Measure lead-lag: does `r_A,t` predict `r_B,t+k`?
3. Build synthetic aggregates (Monte Carlo) where mathematically valid.
4. Define dislocation `D_t = P_synthetic,t - P_direct,t`.
5. Test whether `D_t` predicts convergence.
6. Apply robustness controls (spread, liquidity, volume, etc.).
7. Only then consider a realistic bid/ask backtest.
8. Validate chronologically or walk-forward—never shuffle time.

## Running locally

Requirements: Python 3.12+, [uv](https://github.com/astral-sh/uv).

```bash
# Install
uv sync --extra dev

# Copy environment template (optional; public Kalshi reads work without keys)
cp .env.example .env

# Run tests
make test
# or: uv run pytest

# Fetch public Kalshi market metadata
uv run python scripts/fetch_markets.py --limit 20 --status open

# After choosing real tickers, fetch history (example placeholders):
uv run python scripts/fetch_history.py \
  --ticker YOUR_MARKET_TICKER \
  --series-ticker YOUR_SERIES \
  --start-ts 1710000000 \
  --end-ts 1711000000 \
  --period-interval 1

# Normalize archived candlesticks
uv run python scripts/normalize_data.py

# Lead-lag scaffolding (requires normalized parquet)
uv run python scripts/run_research.py \
  --source-market TICKER_A \
  --target-market TICKER_B
```

## Current status

| Component | Status |
|-----------|--------|
| Repo structure, config, docs | Ready |
| Kalshi public list/market/candlestick client | Working |
| Raw JSON archival + Parquet/DuckDB helpers | Working |
| Normalized schema + validation | Working |
| Forward-fill resampling | Working |
| Market group YAML parsing | Working |
| Lead-lag / OLS research helpers | Working (needs real data) |
| Monte Carlo synthetic probability | Working (baseline independence) |
| Robustness controls | Scaffolding (TODO stubs) |
| Backtest engine (bid/ask, costs, metrics) | Scaffolding (no strategy claims) |
| Polymarket historical ingestion | Scaffolding |
| ML models | Deferred interface only |
| Frontend | Placeholder README |

## Research principles

- Avoid look-ahead bias.
- Preserve raw data.
- Prefer reproducibility via scripts/config.
- No fake alpha / curve-fitting for pretty charts.
- Time-series validation only.
- Separate research from execution.
- Failed hypotheses are valid results.

## Roadmap

1. Select ~10 related markets; ingest and plot.
2. Estimate lead-lag baselines with chronological splits.
3. Implement robustness controls with real data.
4. Prototype synthetic aggregates with explicit correlation assumptions.
5. Backtest only if a plausible signal survives controls.
6. Optionally add Polymarket once historical API requirements are confirmed.
7. Optional UI later.

## Disclaimer

SignalGraph is **research software**. It is not investment advice, not a
brokerage product, and not a guarantee of tradable edge. Prediction markets
involve substantial risk. Past statistical relationships—if any—may not persist.
Do not trade based on this repository without independent due diligence.
