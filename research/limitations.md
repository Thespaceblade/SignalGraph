# Limitations

Known limitations of the current SignalGraph setup:

## Data / API

- Kalshi candlestick API documents periods of 1, 60, and 1440 minutes only.
  5- and 15-minute research series are local resamples, not native exchange bars.
- Historical settled markets may require `/historical/...` endpoints after the
  cutoff returned by `/historical/cutoff`.
- Polymarket historical ingestion is unresolved scaffolding.
- Bid/ask availability and staleness vary by market and timestamp.

## Methods

- Midpoint prices are not executable; any mid-based signal needs bid/ask checks.
- Independent Bernoulli simulation is a baseline, not a realistic dependence model.
- OLS lead-lag ignores time-varying volatility and overlapping horizons' dependence.
- Multiple testing across pairs/horizons inflates false discovery risk.
- Backtest scaffolding does not model partial fills, queue position, or latency.

## Process

- No markets have been selected yet; no results exist to interpret.
- Configuration templates contain placeholder IDs that must be replaced.

Update this document as limitations are discovered during real analyses.
