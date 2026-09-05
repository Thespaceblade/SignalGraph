"""Explicit no-lookahead / no-leakage tests."""

from datetime import datetime, timedelta, timezone

import polars as pl
import pytest

from signalgraph.normalization.resample import build_time_grid, forward_fill_to_grid
from signalgraph.research.calibration import chronological_split
from signalgraph.research.lead_lag import build_lagged_features


def test_chronological_split_preserves_order() -> None:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    frame = pl.DataFrame(
        {
            "timestamp": [start + timedelta(minutes=i) for i in range(10)],
            "x": list(range(10)),
        }
    )
    split = chronological_split(
        frame, train_fraction=0.5, validation_fraction=0.2, test_fraction=0.3
    )
    assert split.train["timestamp"].max() <= split.validation["timestamp"].min()
    assert split.validation["timestamp"].max() <= split.test["timestamp"].min()


def test_lag_features_never_use_future_values() -> None:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    frame = pl.DataFrame(
        {
            "platform": ["kalshi"] * 5,
            "market_id": ["M"] * 5,
            "timestamp": [start + timedelta(minutes=i) for i in range(5)],
            "yes_mid": [0.1, 0.2, 0.3, 0.4, 0.5],
        }
    )
    out = build_lagged_features(frame, value_col="yes_mid", lags=[2])
    # At t=2 (0.3), lag-2 feature must be 0.1 — not anything from the future.
    assert out.sort("timestamp")["yes_mid_lag_2"].to_list() == [None, None, 0.1, 0.2, 0.3]


def test_resample_does_not_leak_future_into_earlier_bins() -> None:
    obs = pl.DataFrame(
        {
            "platform": ["kalshi", "kalshi"],
            "market_id": ["M", "M"],
            "timestamp": [
                datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
                datetime(2024, 1, 1, 0, 10, tzinfo=timezone.utc),
            ],
            "yes_mid": [0.2, 0.9],
        }
    ).with_columns(pl.col("timestamp").cast(pl.Datetime(time_unit="us", time_zone="UTC")))
    grid = build_time_grid(
        datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        datetime(2024, 1, 1, 0, 10, tzinfo=timezone.utc),
        interval_minutes=5,
    )
    filled = forward_fill_to_grid(obs, grid, value_columns=["yes_mid"])
    # 00:05 must still be 0.2; 0.9 only appears at/after 00:10.
    mid_by_ts = {
        row["timestamp"]: row["yes_mid"]
        for row in filled.select(["timestamp", "yes_mid"]).iter_rows(named=True)
    }
    assert mid_by_ts[datetime(2024, 1, 1, 0, 5, tzinfo=timezone.utc)] == 0.2
    assert mid_by_ts[datetime(2024, 1, 1, 0, 10, tzinfo=timezone.utc)] == 0.9
