"""Lead-lag feature and regression tests."""

from datetime import datetime, timedelta, timezone

import polars as pl
import pytest

from signalgraph.research.lead_lag import (
    build_lagged_features,
    run_lead_lag_regression,
    run_multiple_horizons,
)
from signalgraph.research.returns import calculate_probability_change


def _panel() -> pl.DataFrame:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows = []
    for i in range(20):
        ts = start + timedelta(minutes=i)
        rows.append(
            {
                "platform": "kalshi",
                "market_id": "A",
                "timestamp": ts,
                "yes_mid": 0.5 + 0.01 * i,
            }
        )
        rows.append(
            {
                "platform": "kalshi",
                "market_id": "B",
                "timestamp": ts,
                # B partially follows A's lagged level with idiosyncratic drift
                "yes_mid": 0.5 + 0.008 * max(i - 1, 0) + 0.001 * (i % 3),
            }
        )
    return pl.DataFrame(rows).with_columns(
        pl.col("timestamp").cast(pl.Datetime(time_unit="us", time_zone="UTC"))
    )


def test_probability_change() -> None:
    frame = calculate_probability_change(_panel())
    a = frame.filter(pl.col("market_id") == "A").sort("timestamp")
    assert a["prob_change"][0] is None
    assert pytest.approx(a["prob_change"][1], rel=1e-9) == 0.01


def test_lagged_features_reject_negative_lag() -> None:
    with pytest.raises(ValueError, match="look-ahead"):
        build_lagged_features(_panel(), value_col="yes_mid", lags=[-1])


def test_lagged_features_use_past_only() -> None:
    frame = build_lagged_features(_panel(), value_col="yes_mid", lags=[1])
    a = frame.filter(pl.col("market_id") == "A").sort("timestamp")
    assert a["yes_mid_lag_1"][0] is None
    assert a["yes_mid_lag_1"][1] == a["yes_mid"][0]


def test_lead_lag_regression_outputs_fields() -> None:
    frame = calculate_probability_change(_panel())
    result = run_lead_lag_regression(
        frame,
        source_market="A",
        target_market="B",
        lag=1,
        horizon=1,
    )
    assert result.observations > 0
    assert result.source_market == "A"
    assert result.target_market == "B"
    d = result.to_dict()
    for key in (
        "coefficient",
        "standard_error",
        "t_stat",
        "p_value",
        "r_squared",
        "observations",
    ):
        assert key in d


def test_multiple_horizons_frame() -> None:
    frame = calculate_probability_change(_panel())
    out = run_multiple_horizons(
        frame,
        source_market="A",
        target_market="B",
        horizons=[1, 2, 3],
    )
    assert out.height == 3
    assert set(out["horizon"].to_list()) == {1, 2, 3}
