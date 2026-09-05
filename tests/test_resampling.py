"""Tests for resampling forward-fill behavior."""

from datetime import datetime, timezone

import polars as pl
import pytest

from signalgraph.normalization.resample import (
    build_time_grid,
    forward_fill_to_grid,
    resample_observations,
)


def _obs_frame() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "platform": ["kalshi", "kalshi"],
            "market_id": ["M1", "M1"],
            "timestamp": [
                datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
                datetime(2024, 1, 1, 0, 2, tzinfo=timezone.utc),
            ],
            "yes_mid": [0.40, 0.60],
        }
    ).with_columns(pl.col("timestamp").cast(pl.Datetime(time_unit="us", time_zone="UTC")))


def test_forward_fill_propagates_last_known() -> None:
    obs = _obs_frame()
    grid = build_time_grid(
        datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        datetime(2024, 1, 1, 0, 3, tzinfo=timezone.utc),
        interval_minutes=1,
    )
    filled = forward_fill_to_grid(obs, grid, value_columns=["yes_mid"])
    values = filled.sort("timestamp")["yes_mid"].to_list()
    assert values == [0.40, 0.40, 0.60, 0.60]


def test_no_backward_fill() -> None:
    """Grid points before the first observation must remain null."""
    obs = pl.DataFrame(
        {
            "platform": ["kalshi"],
            "market_id": ["M1"],
            "timestamp": [datetime(2024, 1, 1, 0, 2, tzinfo=timezone.utc)],
            "yes_mid": [0.55],
        }
    ).with_columns(pl.col("timestamp").cast(pl.Datetime(time_unit="us", time_zone="UTC")))
    grid = build_time_grid(
        datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        datetime(2024, 1, 1, 0, 3, tzinfo=timezone.utc),
        interval_minutes=1,
    )
    filled = forward_fill_to_grid(obs, grid, value_columns=["yes_mid"])
    values = filled.sort("timestamp")["yes_mid"].to_list()
    assert values[0] is None
    assert values[1] is None
    assert values[2] == 0.55
    assert values[3] == 0.55


def test_future_price_never_appears_in_past() -> None:
    obs = _obs_frame()
    grid = build_time_grid(
        datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        datetime(2024, 1, 1, 0, 2, tzinfo=timezone.utc),
        interval_minutes=1,
    )
    filled = forward_fill_to_grid(obs, grid, value_columns=["yes_mid"])
    # At 00:01, only 0.40 is known — must not show 0.60.
    row = filled.filter(
        pl.col("timestamp") == datetime(2024, 1, 1, 0, 1, tzinfo=timezone.utc)
    )
    assert row["yes_mid"][0] == 0.40


def test_unsupported_interval_rejected() -> None:
    with pytest.raises(ValueError):
        build_time_grid(
            datetime(2024, 1, 1, tzinfo=timezone.utc),
            datetime(2024, 1, 1, 1, tzinfo=timezone.utc),
            interval_minutes=7,
        )


def test_resample_observations_smoke() -> None:
    obs = _obs_frame()
    out = resample_observations(obs, interval_minutes=1)
    assert out.height >= obs.height
    assert "yes_mid" in out.columns
