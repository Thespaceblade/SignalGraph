#!/usr/bin/env python3
"""Fetch market metadata from the configured primary platform.

Archives raw API responses under data/raw/ before any transformation.

Example:
    uv run python scripts/fetch_markets.py --series-ticker KXHIGHNY --status open
    uv run python scripts/fetch_markets.py --limit 50
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from signalgraph.config import load_settings
from signalgraph.ingestion.kalshi import KalshiClient
from signalgraph.storage import save_raw_payload
from signalgraph.utils.logging import setup_logging


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fetch prediction-market metadata")
    p.add_argument("--platform", default=None, help="kalshi (default) | polymarket")
    p.add_argument("--series-ticker", default=None)
    p.add_argument("--event-ticker", default=None)
    p.add_argument("--status", default=None, help="e.g. open, closed, settled")
    p.add_argument("--limit", type=int, default=100)
    p.add_argument("--label", default="markets")
    return p.parse_args()


def main() -> None:
    setup_logging()
    args = parse_args()
    cfg = load_settings()
    platform = (args.platform or cfg.env.signalgraph_primary_platform).lower()
    raw_dir = ROOT / cfg.paths.raw_dir

    if platform != "kalshi":
        raise SystemExit(
            f"Initial source is Kalshi. Platform {platform!r} is scaffolding only."
        )

    with KalshiClient(
        base_url=cfg.env.kalshi_base_url,
        timeout_seconds=cfg.env.signalgraph_http_timeout_seconds,
        max_retries=cfg.env.signalgraph_http_max_retries,
    ) as client:
        payload = client.list_markets(
            limit=args.limit,
            series_ticker=args.series_ticker,
            event_ticker=args.event_ticker,
            status=args.status,
        )
        path = save_raw_payload(payload, raw_dir, label=args.label)
        n = len(payload.data.get("markets", [])) if isinstance(payload.data, dict) else "?"
        print(f"Saved raw markets payload ({n} markets) -> {path}")


if __name__ == "__main__":
    main()
