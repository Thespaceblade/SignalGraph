"""Normalized prediction-market observation schema.

All platforms map into this common representation. Fields unavailable from a
source may be null. Timestamps are always UTC.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

import polars as pl
from pydantic import BaseModel, Field, field_validator, model_validator

Platform = Literal["kalshi", "polymarket", "other"]

NORMALIZED_COLUMNS: list[str] = [
    "platform",
    "market_id",
    "event_id",
    "market_title",
    "timestamp",
    "yes_bid",
    "yes_ask",
    "yes_mid",
    "no_bid",
    "no_ask",
    "no_mid",
    "last_trade_price",
    "volume",
    "open_interest",
    "liquidity",
    "time_to_resolution",
    "resolved_outcome",
]


class MarketObservation(BaseModel):
    """Single timestamped observation for one market on one platform."""

    platform: Platform
    market_id: str = Field(..., min_length=1)
    event_id: str | None = None
    market_title: str | None = None
    timestamp: datetime
    yes_bid: float | None = None
    yes_ask: float | None = None
    yes_mid: float | None = None
    no_bid: float | None = None
    no_ask: float | None = None
    no_mid: float | None = None
    last_trade_price: float | None = None
    volume: float | None = None
    open_interest: float | None = None
    liquidity: float | None = None
    time_to_resolution: float | None = Field(
        default=None,
        description="Seconds until expected resolution, if known.",
    )
    resolved_outcome: str | None = None

    @field_validator("timestamp", mode="before")
    @classmethod
    def _ensure_utc(cls, value: Any) -> datetime:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc)
        if isinstance(value, str):
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        elif isinstance(value, datetime):
            dt = value
        else:
            raise TypeError(f"Unsupported timestamp type: {type(value)}")
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    @field_validator(
        "yes_bid",
        "yes_ask",
        "yes_mid",
        "no_bid",
        "no_ask",
        "no_mid",
        "last_trade_price",
        mode="after",
    )
    @classmethod
    def _probability_bounds(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"Probability-like field must be in [0, 1]; got {value}")
        return value

    @model_validator(mode="after")
    def _bid_ask_and_mids(self) -> MarketObservation:
        for side in ("yes", "no"):
            bid = getattr(self, f"{side}_bid")
            ask = getattr(self, f"{side}_ask")
            if bid is not None and ask is not None and bid > ask:
                raise ValueError(f"{side}_bid ({bid}) > {side}_ask ({ask})")
            mid = getattr(self, f"{side}_mid")
            if mid is None and bid is not None and ask is not None:
                object.__setattr__(self, f"{side}_mid", (bid + ask) / 2.0)
        return self


class NormalizedFrame:
    """Helpers for building and validating Polars frames of observations."""

    @staticmethod
    def empty() -> pl.DataFrame:
        schema: dict[str, Any] = {
            "platform": pl.Utf8,
            "market_id": pl.Utf8,
            "event_id": pl.Utf8,
            "market_title": pl.Utf8,
            "timestamp": pl.Datetime(time_unit="us", time_zone="UTC"),
            "yes_bid": pl.Float64,
            "yes_ask": pl.Float64,
            "yes_mid": pl.Float64,
            "no_bid": pl.Float64,
            "no_ask": pl.Float64,
            "no_mid": pl.Float64,
            "last_trade_price": pl.Float64,
            "volume": pl.Float64,
            "open_interest": pl.Float64,
            "liquidity": pl.Float64,
            "time_to_resolution": pl.Float64,
            "resolved_outcome": pl.Utf8,
        }
        return pl.DataFrame(schema=schema)

    @staticmethod
    def from_observations(observations: list[MarketObservation]) -> pl.DataFrame:
        if not observations:
            return NormalizedFrame.empty()
        rows = [obs.model_dump() for obs in observations]
        frame = pl.DataFrame(rows).with_columns(
            pl.col("timestamp").cast(pl.Datetime(time_unit="us", time_zone="UTC"))
        )
        return validate_observation_frame(frame)


def validate_observation_frame(
    frame: pl.DataFrame,
    *,
    drop_duplicates: bool = True,
    require_sorted: bool = False,
) -> pl.DataFrame:
    """Validate a normalized observation DataFrame.

    Checks:
    - required columns present
    - probability fields in [0, 1]
    - bid <= ask when both present
    - optional duplicate removal on (platform, market_id, timestamp)
    - optional sort check / enforcement
    """
    missing = [c for c in NORMALIZED_COLUMNS if c not in frame.columns]
    if missing:
        raise ValueError(f"Normalized frame missing columns: {missing}")

    out = frame.select(NORMALIZED_COLUMNS)

    prob_cols = [
        "yes_bid",
        "yes_ask",
        "yes_mid",
        "no_bid",
        "no_ask",
        "no_mid",
        "last_trade_price",
    ]
    for col in prob_cols:
        invalid = out.filter(
            pl.col(col).is_not_null() & ((pl.col(col) < 0.0) | (pl.col(col) > 1.0))
        )
        if invalid.height > 0:
            raise ValueError(f"Values outside [0, 1] in column {col}")

    for side in ("yes", "no"):
        crossed = out.filter(
            pl.col(f"{side}_bid").is_not_null()
            & pl.col(f"{side}_ask").is_not_null()
            & (pl.col(f"{side}_bid") > pl.col(f"{side}_ask"))
        )
        if crossed.height > 0:
            raise ValueError(f"Found {crossed.height} rows with {side}_bid > {side}_ask")

    if drop_duplicates:
        out = out.unique(subset=["platform", "market_id", "timestamp"], keep="last")

    out = out.sort(["platform", "market_id", "timestamp"])

    if require_sorted:
        # After sort this is true; kept as an explicit contract for callers.
        grouped = out.group_by(["platform", "market_id"], maintain_order=True).agg(
            pl.col("timestamp").is_sorted().alias("is_sorted")
        )
        if grouped.filter(~pl.col("is_sorted")).height > 0:
            raise ValueError("Timestamps are not sorted within platform/market groups")

    return out


def _parse_dollars(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value != "":
        return float(value)
    return None


def kalshi_candlesticks_to_observations(
    *,
    candlesticks: list[dict[str, Any]],
    market_id: str,
    event_id: str | None = None,
    market_title: str | None = None,
) -> list[MarketObservation]:
    """Map Kalshi candlestick objects to normalized observations.

    Uses period-end close bid/ask dollars when present. last_trade_price uses
    price.close_dollars when a trade occurred in the period.
    """
    observations: list[MarketObservation] = []
    for candle in candlesticks:
        yes_bid = _parse_dollars((candle.get("yes_bid") or {}).get("close_dollars"))
        yes_ask = _parse_dollars((candle.get("yes_ask") or {}).get("close_dollars"))
        price = candle.get("price") or {}
        last_trade = _parse_dollars(price.get("close_dollars"))
        volume = _parse_dollars(candle.get("volume_fp"))
        open_interest = _parse_dollars(candle.get("open_interest_fp"))
        # NO side inferred from binary complementarity when YES quotes exist.
        no_bid = (1.0 - yes_ask) if yes_ask is not None else None
        no_ask = (1.0 - yes_bid) if yes_bid is not None else None
        observations.append(
            MarketObservation(
                platform="kalshi",
                market_id=market_id,
                event_id=event_id,
                market_title=market_title,
                timestamp=candle["end_period_ts"],
                yes_bid=yes_bid,
                yes_ask=yes_ask,
                no_bid=no_bid,
                no_ask=no_ask,
                last_trade_price=last_trade,
                volume=volume,
                open_interest=open_interest,
            )
        )
    return observations


def kalshi_market_snapshot_to_observation(market: dict[str, Any]) -> MarketObservation:
    """Map a Kalshi /markets object snapshot to one observation."""
    yes_bid = _parse_dollars(market.get("yes_bid_dollars"))
    yes_ask = _parse_dollars(market.get("yes_ask_dollars"))
    no_bid = _parse_dollars(market.get("no_bid_dollars"))
    no_ask = _parse_dollars(market.get("no_ask_dollars"))
    ts_raw = market.get("updated_time") or market.get("created_time")
    if ts_raw is None:
        raise ValueError("Kalshi market snapshot missing updated_time/created_time")
    return MarketObservation(
        platform="kalshi",
        market_id=market["ticker"],
        event_id=market.get("event_ticker"),
        market_title=market.get("title"),
        timestamp=ts_raw,
        yes_bid=yes_bid,
        yes_ask=yes_ask,
        no_bid=no_bid,
        no_ask=no_ask,
        last_trade_price=_parse_dollars(market.get("last_price_dollars")),
        volume=_parse_dollars(market.get("volume_fp")),
        open_interest=_parse_dollars(market.get("open_interest_fp")),
        liquidity=_parse_dollars(market.get("liquidity_dollars")),
        resolved_outcome=market.get("result") or None,
    )
