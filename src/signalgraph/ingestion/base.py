"""Abstract interfaces for prediction-market data ingestion."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class RawPayload:
    """Immutable wrapper for an unchanged API response.

    Raw payloads must be persisted before any transformation.
    """

    platform: str
    endpoint: str
    fetched_at: datetime
    params: dict[str, Any] = field(default_factory=dict)
    data: Any = None
    status_code: int | None = None
    url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize for JSON/Parquet side-car metadata."""
        return {
            "platform": self.platform,
            "endpoint": self.endpoint,
            "fetched_at": self.fetched_at.astimezone(timezone.utc).isoformat(),
            "params": self.params,
            "status_code": self.status_code,
            "url": self.url,
            "data": self.data,
        }


class MarketDataClient(ABC):
    """Platform-agnostic read-only market data client interface.

    Implementations must:
    - Prefer public read-only endpoints when available.
    - Return raw API payloads unchanged for archival.
    - Document authentication requirements explicitly.
    - Avoid fabricating endpoints or response fields.
    """

    platform: str

    @abstractmethod
    def list_markets(self, **kwargs: Any) -> RawPayload:
        """List markets available on the platform."""

    @abstractmethod
    def get_market(self, market_id: str, **kwargs: Any) -> RawPayload:
        """Fetch a single market by platform-native identifier."""

    @abstractmethod
    def get_history(self, market_id: str, **kwargs: Any) -> RawPayload:
        """Fetch historical observations for a market.

        Implementations must document which history representation is returned
        (candlesticks, trades, snapshots) and any API limitations.
        """

    def close(self) -> None:
        """Release network resources. Override when holding a client session."""
        return None

    def __enter__(self) -> MarketDataClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
