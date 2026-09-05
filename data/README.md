# Data directory

This directory stores research datasets for SignalGraph.

## Layout

- `raw/` — **unchanged** API responses (JSON). Always archive here first.
- `normalized/` — platform-agnostic observation tables (Parquet).
- `processed/` — derived research artifacts (resampled panels, feature matrices).

## Rules

1. Never modify files under `raw/` after download.
2. All timestamps in normalized/processed data are UTC.
3. Do not commit large market datasets or secrets.
4. Prefer Parquet for columnar storage; DuckDB for local SQL analytics.

## Tomorrow's first workflow

1. Choose ~10 related markets and record them in `config/market_groups.yaml`.
2. `uv run python scripts/fetch_markets.py ...`
3. `uv run python scripts/fetch_history.py --ticker ... --start-ts ... --end-ts ...`
4. `uv run python scripts/normalize_data.py`
5. Open `notebooks/01_market_exploration.ipynb` and plot probability paths.

Do not skip to ML or trading.
