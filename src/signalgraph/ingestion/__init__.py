"""Ingestion clients for prediction-market platforms."""

from signalgraph.ingestion.base import MarketDataClient, RawPayload
from signalgraph.ingestion.kalshi import KalshiClient
from signalgraph.ingestion.polymarket import PolymarketClient

__all__ = [
    "MarketDataClient",
    "RawPayload",
    "KalshiClient",
    "PolymarketClient",
]
