"""Kalshi Trade API client for public market data.

Public market listing, market detail, orderbook, and candlestick endpoints
do not require authentication per Kalshi documentation:

    https://docs.kalshi.com/getting_started/quick_start_market_data.md

Base URLs (production):
    https://api.elections.kalshi.com/trade-api/v2
    https://external-api.kalshi.com/trade-api/v2

Historical partition:
    Settled markets older than the cutoff must use /historical/... endpoints.
    See https://docs.kalshi.com/getting_started/historical_data.md

Unresolved / authenticated capabilities (not implemented here):
    - Private portfolio / order endpoints (require API key + RSA signing)
    - Authenticated WebSocket streams
    - Any endpoint not confirmed in public docs
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from signalgraph.ingestion.base import MarketDataClient, RawPayload

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
VALID_CANDLESTICK_PERIODS = frozenset({1, 60, 1440})


class KalshiClient(MarketDataClient):
    """Read-only Kalshi client wrapping documented public REST endpoints."""

    platform = "kalshi"

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self._owns_client = client is None
        self._client = client or httpx.Client(
            base_url=self.base_url,
            timeout=timeout_seconds,
            headers={"Accept": "application/json", "User-Agent": "signalgraph/0.1"},
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def _get(self, path: str, params: dict[str, Any] | None = None) -> RawPayload:
        """Perform GET and wrap the unchanged JSON body as a RawPayload."""
        params = {k: v for k, v in (params or {}).items() if v is not None}
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self._client.get(path, params=params)
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else min(2**attempt, 30)
                    logger.warning(
                        "Kalshi rate limited on %s; sleeping %.1fs (attempt %s/%s)",
                        path,
                        delay,
                        attempt,
                        self.max_retries,
                    )
                    time.sleep(delay)
                response.raise_for_status()
                return RawPayload(
                    platform=self.platform,
                    endpoint=path,
                    fetched_at=datetime.now(timezone.utc),
                    params=params,
                    data=response.json(),
                    status_code=response.status_code,
                    url=str(response.url),
                )
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                logger.warning(
                    "Kalshi GET %s failed (attempt %s/%s): %s",
                    path,
                    attempt,
                    self.max_retries,
                    exc,
                )
                if attempt < self.max_retries:
                    # Retry 429 and transient transport errors; stop on other 4xx.
                    if isinstance(exc, httpx.HTTPStatusError):
                        code = exc.response.status_code if exc.response is not None else None
                        if code == 429:
                            continue
                        if code is not None and 400 <= code < 500:
                            break
                    time.sleep(min(2**attempt, 10))
        assert last_error is not None
        raise last_error

    def list_markets(
        self,
        *,
        limit: int = 100,
        cursor: str | None = None,
        event_ticker: str | None = None,
        series_ticker: str | None = None,
        status: str | None = None,
        tickers: str | None = None,
        **kwargs: Any,
    ) -> RawPayload:
        """GET /markets — public market listing with cursor pagination."""
        params: dict[str, Any] = {
            "limit": limit,
            "cursor": cursor,
            "event_ticker": event_ticker,
            "series_ticker": series_ticker,
            "status": status,
            "tickers": tickers,
            **kwargs,
        }
        return self._get("/markets", params=params)

    def iter_markets(self, *, page_limit: int = 200, **filters: Any) -> list[dict[str, Any]]:
        """Paginate through /markets and return concatenated market objects.

        Returns market dicts extracted from raw responses. The raw pages
        themselves should be archived separately via list_markets when
        reproducibility of exact API responses is required.
        """
        markets: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            payload = self.list_markets(limit=page_limit, cursor=cursor, **filters)
            page = payload.data.get("markets", []) if isinstance(payload.data, dict) else []
            markets.extend(page)
            cursor = payload.data.get("cursor") if isinstance(payload.data, dict) else None
            if not cursor or not page:
                break
        return markets

    def get_market(self, market_id: str, **kwargs: Any) -> RawPayload:
        """GET /markets/{ticker}."""
        return self._get(f"/markets/{market_id}", params=kwargs or None)

    def get_event(self, event_ticker: str, **kwargs: Any) -> RawPayload:
        """GET /events/{event_ticker}."""
        return self._get(f"/events/{event_ticker}", params=kwargs or None)

    def get_series(self, series_ticker: str, **kwargs: Any) -> RawPayload:
        """GET /series/{series_ticker}."""
        return self._get(f"/series/{series_ticker}", params=kwargs or None)

    def get_orderbook(self, market_id: str, **kwargs: Any) -> RawPayload:
        """GET /markets/{ticker}/orderbook."""
        return self._get(f"/markets/{market_id}/orderbook", params=kwargs or None)

    def get_historical_cutoff(self) -> RawPayload:
        """GET /historical/cutoff — boundary between live and archived data."""
        return self._get("/historical/cutoff")

    def get_candlesticks(
        self,
        *,
        series_ticker: str,
        ticker: str,
        start_ts: int,
        end_ts: int,
        period_interval: int = 1,
        include_latest_before_start: bool | None = None,
    ) -> RawPayload:
        """GET /series/{series_ticker}/markets/{ticker}/candlesticks.

        period_interval must be one of {1, 60, 1440} per Kalshi docs.
        For settled markets older than the historical cutoff, use
        get_historical_candlesticks instead.
        """
        if period_interval not in VALID_CANDLESTICK_PERIODS:
            raise ValueError(
                f"Kalshi candlestick period_interval must be one of "
                f"{sorted(VALID_CANDLESTICK_PERIODS)}; got {period_interval}. "
                "Use local resampling for 5m/15m research series."
            )
        params: dict[str, Any] = {
            "start_ts": start_ts,
            "end_ts": end_ts,
            "period_interval": period_interval,
        }
        if include_latest_before_start is not None:
            params["include_latest_before_start"] = include_latest_before_start
        path = f"/series/{series_ticker}/markets/{ticker}/candlesticks"
        return self._get(path, params=params)

    def get_historical_candlesticks(
        self,
        *,
        ticker: str,
        start_ts: int,
        end_ts: int,
        period_interval: int = 1,
    ) -> RawPayload:
        """GET /historical/markets/{ticker}/candlesticks for archived markets."""
        if period_interval not in VALID_CANDLESTICK_PERIODS:
            raise ValueError(
                f"Kalshi candlestick period_interval must be one of "
                f"{sorted(VALID_CANDLESTICK_PERIODS)}; got {period_interval}."
            )
        return self._get(
            f"/historical/markets/{ticker}/candlesticks",
            params={
                "start_ts": start_ts,
                "end_ts": end_ts,
                "period_interval": period_interval,
            },
        )

    def get_history(
        self,
        market_id: str,
        *,
        series_ticker: str | None = None,
        start_ts: int | None = None,
        end_ts: int | None = None,
        period_interval: int = 1,
        use_historical: bool = False,
        **kwargs: Any,
    ) -> RawPayload:
        """Fetch candlestick history for a market.

        Requires start_ts and end_ts (Unix seconds).
        Live path requires series_ticker.
        Set use_historical=True for archived settled markets.
        """
        if start_ts is None or end_ts is None:
            raise ValueError("get_history requires start_ts and end_ts (Unix seconds).")
        if use_historical:
            return self.get_historical_candlesticks(
                ticker=market_id,
                start_ts=start_ts,
                end_ts=end_ts,
                period_interval=period_interval,
            )
        if not series_ticker:
            # Attempt to resolve series_ticker from market detail.
            detail = self.get_market(market_id)
            market = detail.data.get("market", {}) if isinstance(detail.data, dict) else {}
            series_ticker = market.get("series_ticker") or _series_from_ticker(market_id)
            if not series_ticker:
                raise ValueError(
                    "series_ticker is required for live candlesticks and could not be "
                    "resolved from market detail. Pass series_ticker explicitly."
                )
        return self.get_candlesticks(
            series_ticker=series_ticker,
            ticker=market_id,
            start_ts=start_ts,
            end_ts=end_ts,
            period_interval=period_interval,
            **kwargs,
        )


def _series_from_ticker(ticker: str) -> str | None:
    """Best-effort series ticker extraction.

    Kalshi market tickers often look like SERIES-EVENT-OUTCOME.
    This heuristic is not guaranteed; prefer the series_ticker field
    from market detail when available.
    """
    if "-" not in ticker:
        return None
    return ticker.split("-", 1)[0]
