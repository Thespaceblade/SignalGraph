"""Tests for normalized schema validation."""

from datetime import datetime, timezone

import polars as pl
import pytest
from pydantic import ValidationError

from signalgraph.normalization.schema import (
    MarketObservation,
    NormalizedFrame,
    validate_observation_frame,
)


def test_probability_validation_rejects_out_of_range() -> None:
    with pytest.raises(ValidationError):
        MarketObservation(
            platform="kalshi",
            market_id="M1",
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            yes_mid=1.5,
        )


def test_probability_validation_accepts_bounds() -> None:
    obs = MarketObservation(
        platform="kalshi",
        market_id="M1",
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        yes_bid=0.0,
        yes_ask=1.0,
        last_trade_price=0.42,
    )
    assert obs.yes_mid == 0.5


def test_bid_ask_ordering() -> None:
    with pytest.raises(ValidationError):
        MarketObservation(
            platform="kalshi",
            market_id="M1",
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            yes_bid=0.6,
            yes_ask=0.4,
        )


def test_timestamp_normalized_to_utc() -> None:
    obs = MarketObservation(
        platform="kalshi",
        market_id="M1",
        timestamp="2024-06-01T12:00:00+02:00",
        yes_mid=0.5,
    )
    assert obs.timestamp.tzinfo == timezone.utc
    assert obs.timestamp.hour == 10


def test_frame_rejects_duplicate_policy_and_validates() -> None:
    rows = [
        MarketObservation(
            platform="kalshi",
            market_id="M1",
            timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
            yes_mid=0.4,
        ),
        MarketObservation(
            platform="kalshi",
            market_id="M1",
            timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
            yes_mid=0.5,
        ),
        MarketObservation(
            platform="kalshi",
            market_id="M1",
            timestamp=datetime(2024, 1, 1, 0, 1, tzinfo=timezone.utc),
            yes_mid=0.55,
        ),
    ]
    frame = NormalizedFrame.from_observations(rows)
    assert frame.height == 2
    assert frame.sort("timestamp")["yes_mid"].to_list()[-1] == 0.55


def test_frame_detects_invalid_probabilities() -> None:
    frame = pl.DataFrame(
        {
            "platform": ["kalshi"],
            "market_id": ["M1"],
            "event_id": [None],
            "market_title": [None],
            "timestamp": [datetime(2024, 1, 1, tzinfo=timezone.utc)],
            "yes_bid": [None],
            "yes_ask": [None],
            "yes_mid": [1.2],
            "no_bid": [None],
            "no_ask": [None],
            "no_mid": [None],
            "last_trade_price": [None],
            "volume": [None],
            "open_interest": [None],
            "liquidity": [None],
            "time_to_resolution": [None],
            "resolved_outcome": [None],
        }
    )
    with pytest.raises(ValueError, match="outside"):
        validate_observation_frame(frame)
