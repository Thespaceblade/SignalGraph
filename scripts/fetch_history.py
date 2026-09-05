#!/usr/bin/env python3
"""Fetch historical candlesticks for specified markets and archive raw JSON.

Requires real market tickers. Does not fabricate data.

Example:
    uv run python scripts/fetch_history.py \\
        --ticker MARKET_TICKER \\
        --series-ticker SERIES \\
        --start-ts 1710000000 \\
        --end-ts 1711000000 \\
        --period-interval 1
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from signalgraph.config import load_settings
from signalgraph.ingestion.kalshi import KalshiClient
from signalgraph.relationships.grouping import load_market_groups
from signalgraph.storage import save_raw_payload
from signalgraph.utils.logging import setup_logging
from signalgraph.utils.time import to_unix_seconds


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fetch market history candlesticks")
    p.add_argument("--ticker", action="append", default=[], help="Market ticker (repeatable)")
    p.add_argument(
        "--from-group",
        default=None,
        help="Load tickers from config/market_groups.yaml group name",
    )
    p.add_argument("--series-ticker", default=None, help="Required for live candlesticks")
    p.add_argument("--start-ts", required=True, help="Unix seconds or ISO timestamp")
    p.add_argument("--end-ts", required=True, help="Unix seconds or ISO timestamp")
    p.add_argument(
        "--period-interval",
        type=int,
        default=1,
        choices=[1, 60, 1440],
        help="Kalshi candlestick period in minutes",
    )
    p.add_argument(
        "--use-historical",
        action="store_true",
        help="Use /historical/markets/{ticker}/candlesticks",
    )
    p.add_argument("--label", default="history")
    return p.parse_args()


def main() -> None:
    setup_logging()
    args = parse_args()
    cfg = load_settings()
    raw_dir = ROOT / cfg.paths.raw_dir

    tickers = list(args.ticker)
    if args.from_group:
        groups = load_market_groups(ROOT / "config" / "market_groups.yaml")
        if args.from_group not in groups:
            raise SystemExit(f"Unknown group: {args.from_group}")
        refs = groups[args.from_group].real_market_refs()
        tickers.extend(r.market_id for r in refs if r.platform == "kalshi")

    tickers = list(dict.fromkeys(tickers))
    if not tickers:
        raise SystemExit(
            "No tickers provided. Pass --ticker or populate a market group and "
            "use --from-group. Do not proceed with placeholder REPLACE_WITH_* ids."
        )

    start_ts = to_unix_seconds(args.start_ts)
    end_ts = to_unix_seconds(args.end_ts)

    with KalshiClient(
        base_url=cfg.env.kalshi_base_url,
        timeout_seconds=cfg.env.signalgraph_http_timeout_seconds,
        max_retries=cfg.env.signalgraph_http_max_retries,
    ) as client:
        for ticker in tickers:
            payload = client.get_history(
                ticker,
                series_ticker=args.series_ticker,
                start_ts=start_ts,
                end_ts=end_ts,
                period_interval=args.period_interval,
                use_historical=args.use_historical,
            )
            path = save_raw_payload(payload, raw_dir, label=f"{args.label}_{ticker}")
            candles = (
                payload.data.get("candlesticks", [])
                if isinstance(payload.data, dict)
                else []
            )
            print(f"{ticker}: archived {len(candles)} candlesticks -> {path}")


if __name__ == "__main__":
    main()
