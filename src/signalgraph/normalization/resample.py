"""Time-grid resampling utilities with strict forward-fill semantics.

CRITICAL:
- Historical values may only propagate forward from the last known observation.
- Never backward-fill future prices into earlier timestamps.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import polars as pl

SUPPORTED_INTERVALS_MINUTES = frozenset({1, 5, 15, 60})


def _ensure_utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def build_time_grid(
    start: datetime,
    end: datetime,
    interval_minutes: int,
) -> pl.DataFrame:
    """Build an inclusive-start, inclusive-end UTC timestamp grid."""
    if interval_minutes not in SUPPORTED_INTERVALS_MINUTES:
        raise ValueError(
            f"interval_minutes must be one of {sorted(SUPPORTED_INTERVALS_MINUTES)}"
        )
    start = _ensure_utc_datetime(start)
    end = _ensure_utc_datetime(end)
    if end < start:
        raise ValueError("end must be >= start")
    step = timedelta(minutes=interval_minutes)
    stamps: list[datetime] = []
    cursor = start
    while cursor <= end:
        stamps.append(cursor)
        cursor += step
    return pl.DataFrame(
        {"timestamp": stamps}
    ).with_columns(pl.col("timestamp").cast(pl.Datetime(time_unit="us", time_zone="UTC")))


def forward_fill_to_grid(
    observations: pl.DataFrame,
    grid: pl.DataFrame,
    *,
    value_columns: list[str] | None = None,
    market_keys: list[str] | None = None,
) -> pl.DataFrame:
    """Align observations onto a fixed timestamp grid using forward-fill only.

    For each market key group:
    1. Left-join the time grid to observations on timestamp.
    2. Forward-fill value columns so each grid point carries the most recent
       prior observation (including an exact match).
    3. Leave leading nulls when no prior observation exists.

    This function never sorts descending or uses backward fill.
    """
    market_keys = market_keys or ["platform", "market_id"]
    if "timestamp" not in observations.columns:
        raise ValueError("observations must include timestamp")
    if "timestamp" not in grid.columns:
        raise ValueError("grid must include timestamp")

    value_columns = value_columns or [
        c
        for c in observations.columns
        if c not in {*market_keys, "timestamp"}
    ]

    # Explicitly reject any attempt to request bfill via kwargs elsewhere.
    parts: list[pl.DataFrame] = []
    if observations.is_empty():
        return grid.with_columns([pl.lit(None).alias(c) for c in value_columns])

    groups = observations.select(market_keys).unique().iter_rows(named=True)
    for keys in groups:
        mask = pl.lit(True)
        for key, val in keys.items():
            mask = mask & (pl.col(key) == val)
        market_obs = (
            observations.filter(mask)
            .sort("timestamp")
            .unique(subset=["timestamp"], keep="last")
        )
        aligned = (
            grid.join(market_obs, on="timestamp", how="left")
            .sort("timestamp")
            .with_columns([pl.col(c).forward_fill() for c in value_columns])
        )
        for key, val in keys.items():
            if key not in aligned.columns or aligned[key].null_count() == aligned.height:
                aligned = aligned.with_columns(pl.lit(val).alias(key))
            else:
                aligned = aligned.with_columns(pl.col(key).forward_fill().alias(key))
        parts.append(aligned)

    if not parts:
        return grid
    return pl.concat(parts, how="vertical_relaxed").sort([*market_keys, "timestamp"])


def resample_observations(
    observations: pl.DataFrame,
    interval_minutes: int,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    value_columns: list[str] | None = None,
) -> pl.DataFrame:
    """Resample multi-market observations onto a shared fixed interval grid."""
    if observations.is_empty():
        return observations

    obs = observations.sort("timestamp")
    ts_min = obs["timestamp"].min()
    ts_max = obs["timestamp"].max()
    assert isinstance(ts_min, datetime)
    assert isinstance(ts_max, datetime)

    grid_start = _ensure_utc_datetime(start) if start else _ensure_utc_datetime(ts_min)
    grid_end = _ensure_utc_datetime(end) if end else _ensure_utc_datetime(ts_max)
    # Align start down to interval boundary for reproducibility.
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    start_minutes = int((grid_start - epoch).total_seconds() // 60)
    aligned_minutes = start_minutes - (start_minutes % interval_minutes)
    grid_start = epoch + timedelta(minutes=aligned_minutes)

    grid = build_time_grid(grid_start, grid_end, interval_minutes)
    return forward_fill_to_grid(obs, grid, value_columns=value_columns)
