#!/usr/bin/env python3
"""Normalize archived Kalshi candlestick JSON into Parquet observations.

Reads raw payloads from data/raw/, writes data/normalized/observations.parquet.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from signalgraph.config import load_settings
from signalgraph.normalization.schema import (
    NormalizedFrame,
    kalshi_candlesticks_to_observations,
    validate_observation_frame,
)
from signalgraph.storage import write_normalized_dataset
from signalgraph.utils.logging import setup_logging


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Normalize raw market history to Parquet")
    p.add_argument(
        "--raw-glob",
        default="**/*.json",
        help="Glob under data/raw to select payload files",
    )
    p.add_argument("--output-name", default="observations")
    return p.parse_args()


def main() -> None:
    setup_logging()
    args = parse_args()
    cfg = load_settings()
    raw_root = ROOT / cfg.paths.raw_dir
    out_dir = ROOT / cfg.paths.normalized_dir

    files = sorted(raw_root.glob(args.raw_glob))
    if not files:
        raise SystemExit(f"No raw JSON files found under {raw_root} matching {args.raw_glob}")

    all_obs = []
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        data = payload.get("data") or {}
        if not isinstance(data, dict):
            continue
        candlesticks = data.get("candlesticks")
        if not candlesticks:
            continue
        market_id = data.get("ticker")
        if not market_id:
            # Fall back to label embedded in filename if present.
            market_id = path.stem
        all_obs.extend(
            kalshi_candlesticks_to_observations(
                candlesticks=candlesticks,
                market_id=str(market_id),
            )
        )

    if not all_obs:
        raise SystemExit(
            "No candlestick payloads found to normalize. "
            "Run scripts/fetch_history.py first."
        )

    frame = validate_observation_frame(NormalizedFrame.from_observations(all_obs))
    out = write_normalized_dataset(frame, out_dir, name=args.output_name)
    print(f"Wrote {frame.height} observations -> {out}")


if __name__ == "__main__":
    main()
