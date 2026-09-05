#!/usr/bin/env python3
"""Run baseline lead-lag research on a normalized Parquet dataset.

This script measures statistical relationships only. It does not claim alpha.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import polars as pl

from signalgraph.config import load_settings
from signalgraph.research.lead_lag import run_multiple_horizons
from signalgraph.research.returns import calculate_probability_change
from signalgraph.research.robustness import RobustnessChecklist
from signalgraph.utils.logging import setup_logging


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run lead-lag research scaffolding")
    p.add_argument("--source-market", required=True)
    p.add_argument("--target-market", required=True)
    p.add_argument(
        "--input",
        default=None,
        help="Normalized parquet path (default: data/normalized/observations.parquet)",
    )
    p.add_argument(
        "--horizons",
        default="1,5,15,30,60",
        help="Comma-separated lag steps (periods in the input series)",
    )
    p.add_argument("--price-col", default="yes_mid")
    return p.parse_args()


def main() -> None:
    setup_logging()
    args = parse_args()
    cfg = load_settings()
    input_path = Path(args.input) if args.input else ROOT / cfg.paths.normalized_dir / "observations.parquet"
    if not input_path.exists():
        raise SystemExit(
            f"Normalized dataset not found: {input_path}. "
            "Ingest and normalize data before running research."
        )

    frame = pl.read_parquet(input_path)
    frame = calculate_probability_change(frame, price_col=args.price_col)
    horizons = [int(x.strip()) for x in args.horizons.split(",") if x.strip()]
    results = run_multiple_horizons(
        frame,
        source_market=args.source_market,
        target_market=args.target_market,
        horizons=horizons,
    )
    print(results)

    checklist = RobustnessChecklist()
    checklist.run_all_stubs()
    print("\nRobustness checklist (stubs — not yet executed):")
    for name, done in checklist.completed.items():
        note = checklist.notes.get(name, "")
        print(f"  [{('x' if done else ' ')}] {name}: {note}")

    print(
        "\nReminder: p-values are not proof of economic alpha. "
        "Apply robustness controls and chronological validation before any backtest."
    )


if __name__ == "__main__":
    main()
