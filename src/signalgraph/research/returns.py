"""Probability change (return-like) transforms for prediction markets."""

from __future__ import annotations

import polars as pl


def calculate_probability_change(
    frame: pl.DataFrame,
    *,
    price_col: str = "yes_mid",
    group_cols: list[str] | None = None,
    output_col: str = "prob_change",
) -> pl.DataFrame:
    """Compute r_i,t = p_i,t - p_i,t-1 within each market.

    Uses simple differences of implied probabilities. Does not assume
    log-returns are appropriate for bounded probabilities.
    """
    group_cols = group_cols or ["platform", "market_id"]
    required = {*group_cols, "timestamp", price_col}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing columns for probability change: {sorted(missing)}")

    return (
        frame.sort([*group_cols, "timestamp"])
        .with_columns(
            (pl.col(price_col) - pl.col(price_col).shift(1).over(group_cols)).alias(output_col)
        )
    )
