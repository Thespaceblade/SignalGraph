"""Polymarket client scaffolding.

This module intentionally does not invent undocumented endpoints or claim
complete historical coverage. Polymarket data access involves multiple
services (e.g. Gamma API for market metadata, CLOB for order books/prices).
Exact historical reconstruction requirements are unresolved and must be
verified against current Polymarket documentation before research use.

Status: scaffolding only. Kalshi is the initial production source.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from signalgraph.ingestion.base import MarketDataClient, RawPayload

logger = logging.getLogger(__name__)

DEFAULT_GAMMA_URL = "https://gamma-api.polymarket.com"
DEFAULT_CLOB_URL = "https://clob.polymarket.com"


class PolymarketClient(MarketDataClient):
    """Scaffolding client for Polymarket public metadata endpoints.

    Only implements cautious, commonly documented metadata fetches.
    Historical price series ingestion is NOT implemented until requirements
    are confirmed — calling get_history raises NotImplementedError with
    guidance rather than fabricating an API contract.
    """

    platform = "polymarket"

    def __init__(
        self,
        base_url: str = DEFAULT_GAMMA_URL,
        clob_url: str = DEFAULT_CLOB_URL,
        timeout_seconds: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.clob_url = clob_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._owns_client = client is None
        self._client = client or httpx.Client(
            timeout=timeout_seconds,
            headers={"Accept": "application/json", "User-Agent": "signalgraph/0.1"},
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def _get(self, url: str, params: dict[str, Any] | None = None) -> RawPayload:
        params = {k: v for k, v in (params or {}).items() if v is not None}
        response = self._client.get(url, params=params)
        response.raise_for_status()
        return RawPayload(
            platform=self.platform,
            endpoint=url,
            fetched_at=datetime.now(timezone.utc),
            params=params,
            data=response.json(),
            status_code=response.status_code,
            url=str(response.url),
        )

    def list_markets(self, **kwargs: Any) -> RawPayload:
        """GET {gamma}/markets — metadata listing (verify filters against docs)."""
        return self._get(f"{self.base_url}/markets", params=kwargs)

    def get_market(self, market_id: str, **kwargs: Any) -> RawPayload:
        """GET {gamma}/markets/{id} — single market metadata."""
        return self._get(f"{self.base_url}/markets/{market_id}", params=kwargs or None)

    def get_history(self, market_id: str, **kwargs: Any) -> RawPayload:
        """Historical prices are not yet implemented for Polymarket.

        Unresolved requirements:
        - Confirm the authoritative historical prices endpoint (CLOB prices-history
          vs other services) and its auth/rate-limit constraints.
        - Confirm timestamp granularity and whether bid/ask are available or only
          last trade / mid approximations.
        - Define raw archival format for reproducibility.
        """
        raise NotImplementedError(
            "Polymarket historical ingestion is scaffolding only. "
            "Confirm the documented historical prices API, then implement "
            "get_history without inventing endpoints. Kalshi is the initial source."
        )
