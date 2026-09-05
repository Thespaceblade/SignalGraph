"""Chronological validation helpers. Never randomly shuffle time-series data."""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl


@dataclass(frozen=True)
class ChronologicalSplit:
    train: pl.DataFrame
    validation: pl.DataFrame
    test: pl.DataFrame


def chronological_split(
    frame: pl.DataFrame,
    *,
    timestamp_col: str = "timestamp",
    train_fraction: float = 0.6,
    validation_fraction: float = 0.2,
    test_fraction: float = 0.2,
) -> ChronologicalSplit:
    """Split a time-ordered frame into train/validation/test without shuffling.

    Fractions must sum to 1.0 (within floating tolerance).
    """
    total = train_fraction + validation_fraction + test_fraction
    if abs(total - 1.0) > 1e-9:
        raise ValueError(f"Split fractions must sum to 1.0; got {total}")
    if frame.is_empty():
        return ChronologicalSplit(frame, frame, frame)

    ordered = frame.sort(timestamp_col)
    n = ordered.height
    train_end = int(n * train_fraction)
    valid_end = train_end + int(n * validation_fraction)
    # Ensure test gets the remainder so all rows are used.
    train = ordered[:train_end]
    validation = ordered[train_end:valid_end]
    test = ordered[valid_end:]
    return ChronologicalSplit(train=train, validation=validation, test=test)
