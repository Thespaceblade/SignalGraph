"""Smoke test against the live Kalshi public API (network)."""

import os

import httpx
import pytest

from signalgraph.ingestion.kalshi import KalshiClient


@pytest.mark.skipif(
    os.environ.get("SIGNALGRAPH_SKIP_NETWORK", "").lower() in {"1", "true", "yes"},
    reason="Network tests disabled via SIGNALGRAPH_SKIP_NETWORK",
)
def test_kalshi_list_markets_public() -> None:
    try:
        with KalshiClient(max_retries=2) as client:
            payload = client.list_markets(limit=2, status="open")
    except httpx.HTTPStatusError as exc:
        if exc.response is not None and exc.response.status_code == 429:
            pytest.skip("Kalshi API rate limited (429); public endpoint otherwise verified.")
        raise
    assert payload.status_code == 200
    assert isinstance(payload.data, dict)
    assert "markets" in payload.data
    assert isinstance(payload.data["markets"], list)
