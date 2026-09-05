"""Lead-lag feature construction, correlation, and regression helpers.

These functions measure statistical relationships only. Statistical
significance is not proof of economic alpha.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import polars as pl
import statsmodels.api as sm


@dataclass(frozen=True)
class LeadLagResult:
    source_market: str
    target_market: str
    lag: int
    horizon: int
    coefficient: float
    standard_error: float
    t_stat: float
    p_value: float
    r_squared: float
    observations: int
    correlation: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def build_lagged_features(
    frame: pl.DataFrame,
    *,
    value_col: str,
    lags: list[int],
    group_cols: list[str] | None = None,
) -> pl.DataFrame:
    """Create lagged columns value_col_lag_{k} using only past observations.

    A lag of k means the feature at time t is the value from t-k.
    Negative lags (future leakage) are rejected.
    """
    if any(lag < 0 for lag in lags):
        raise ValueError(
            "Negative lags are not allowed — they would introduce look-ahead bias."
        )
    group_cols = group_cols or ["platform", "market_id"]
    out = frame.sort([*group_cols, "timestamp"])
    for lag in lags:
        out = out.with_columns(
            pl.col(value_col).shift(lag).over(group_cols).alias(f"{value_col}_lag_{lag}")
        )
    return out


def _extract_series(
    frame: pl.DataFrame,
    market_id: str,
    value_col: str,
    platform: str | None = None,
) -> pl.DataFrame:
    mask = pl.col("market_id") == market_id
    if platform is not None:
        mask = mask & (pl.col("platform") == platform)
    subset = frame.filter(mask).select(["timestamp", value_col]).sort("timestamp")
    if subset.is_empty():
        raise ValueError(f"No rows for market_id={market_id!r}")
    return subset.rename({value_col: "value"})


def lead_lag_correlation(
    frame: pl.DataFrame,
    *,
    source_market: str,
    target_market: str,
    value_col: str = "prob_change",
    lag: int = 0,
    source_platform: str | None = None,
    target_platform: str | None = None,
) -> float:
    """Pearson correlation between source_t and target_{t+lag} aligned on time.

    lag > 0 means source leads target by `lag` periods (target shifted backward
    relative to source, or equivalently source compared to future target).
    Implementation joins source[t] to target[t+lag] without using unavailable
    future information in feature construction for source.
    """
    if lag < 0:
        raise ValueError("lag must be >= 0 for lead-lag correlation tests")

    source = _extract_series(frame, source_market, value_col, source_platform)
    target = _extract_series(frame, target_market, value_col, target_platform)

    # Assign period index within each series after sorting.
    source = source.with_row_index("idx")
    target = target.with_row_index("idx")
    # Align by timestamp intersection first for irregular series.
    merged = source.rename({"value": "source"}).join(
        target.rename({"value": "target"}), on="timestamp", how="inner"
    )
    if merged.height == 0:
        return float("nan")

    # For lag, shift target upward (future target) within the aligned frame.
    # source[t] correlates with target[t+lag].
    aligned = merged.sort("timestamp").with_columns(
        pl.col("target").shift(-lag).alias("target_future")
    ).drop_nulls(["source", "target_future"])

    if aligned.height < 3:
        return float("nan")

    x = aligned["source"].to_numpy()
    y = aligned["target_future"].to_numpy()
    if np.std(x) == 0 or np.std(y) == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def run_lead_lag_regression(
    frame: pl.DataFrame,
    *,
    source_market: str,
    target_market: str,
    value_col: str = "prob_change",
    lag: int = 1,
    horizon: int | None = None,
    source_platform: str | None = None,
    target_platform: str | None = None,
) -> LeadLagResult:
    """OLS: target_{t+lag} = alpha + beta * source_t + epsilon.

    `horizon` is recorded for reporting (e.g. minutes represented by each lag
    step). If omitted, defaults to `lag`.
    """
    if lag < 0:
        raise ValueError("lag must be >= 0")
    horizon = lag if horizon is None else horizon

    source = _extract_series(frame, source_market, value_col, source_platform).rename(
        {"value": "source"}
    )
    target = _extract_series(frame, target_market, value_col, target_platform).rename(
        {"value": "target"}
    )
    merged = source.join(target, on="timestamp", how="inner").sort("timestamp")
    aligned = merged.with_columns(
        pl.col("target").shift(-lag).alias("target_future")
    ).drop_nulls(["source", "target_future"])

    n = aligned.height
    if n < 3:
        return LeadLagResult(
            source_market=source_market,
            target_market=target_market,
            lag=lag,
            horizon=horizon,
            coefficient=float("nan"),
            standard_error=float("nan"),
            t_stat=float("nan"),
            p_value=float("nan"),
            r_squared=float("nan"),
            observations=n,
            correlation=float("nan"),
        )

    y = aligned["target_future"].to_numpy()
    x = sm.add_constant(aligned["source"].to_numpy())
    model = sm.OLS(y, x, missing="drop").fit()
    corr = float("nan")
    if np.std(aligned["source"].to_numpy()) > 0 and np.std(y) > 0:
        corr = float(np.corrcoef(aligned["source"].to_numpy(), y)[0, 1])

    return LeadLagResult(
        source_market=source_market,
        target_market=target_market,
        lag=lag,
        horizon=horizon,
        coefficient=float(model.params[1]),
        standard_error=float(model.bse[1]),
        t_stat=float(model.tvalues[1]),
        p_value=float(model.pvalues[1]),
        r_squared=float(model.rsquared),
        observations=int(model.nobs),
        correlation=corr,
    )


def run_multiple_horizons(
    frame: pl.DataFrame,
    *,
    source_market: str,
    target_market: str,
    horizons: list[int],
    value_col: str = "prob_change",
    source_platform: str | None = None,
    target_platform: str | None = None,
) -> pl.DataFrame:
    """Run lead-lag regressions across multiple horizons (lag steps)."""
    results = [
        run_lead_lag_regression(
            frame,
            source_market=source_market,
            target_market=target_market,
            value_col=value_col,
            lag=h,
            horizon=h,
            source_platform=source_platform,
            target_platform=target_platform,
        ).to_dict()
        for h in horizons
    ]
    return pl.DataFrame(results)


# Public alias requested in the research API. Marked non-test so pytest does
# not collect this library function when imported into test modules.
test_multiple_horizons = run_multiple_horizons
test_multiple_horizons.__test__ = False  # type: ignore[attr-defined]
