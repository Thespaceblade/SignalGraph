"""Data storage utilities for raw archival and normalized Parquet/DuckDB."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import polars as pl

from signalgraph.ingestion.base import RawPayload


def ensure_dir(path: Path | str) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def utc_timestamp_slug(when: datetime | None = None) -> str:
    when = when or datetime.now(timezone.utc)
    return when.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def save_raw_payload(
    payload: RawPayload,
    raw_dir: Path | str,
    *,
    label: str | None = None,
) -> Path:
    """Persist an unchanged API payload as JSON under data/raw/.

    Layout:
        data/raw/{platform}/{endpoint_slug}/{timestamp}_{label}.json
    """
    raw_root = ensure_dir(Path(raw_dir) / payload.platform)
    endpoint_slug = payload.endpoint.strip("/").replace("/", "__") or "root"
    out_dir = ensure_dir(raw_root / endpoint_slug)
    slug = utc_timestamp_slug(payload.fetched_at)
    name = f"{slug}_{label}.json" if label else f"{slug}.json"
    path = out_dir / name
    path.write_text(json.dumps(payload.to_dict(), indent=2, default=str), encoding="utf-8")
    return path


def load_raw_payload(path: Path | str) -> dict[str, Any]:
    """Load a previously archived raw payload JSON file."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_parquet(frame: pl.DataFrame, path: Path | str) -> Path:
    path = Path(path)
    ensure_dir(path.parent)
    frame.write_parquet(path)
    return path


def read_parquet(path: Path | str) -> pl.DataFrame:
    return pl.read_parquet(path)


def write_normalized_dataset(
    frame: pl.DataFrame,
    normalized_dir: Path | str,
    *,
    name: str = "observations",
) -> Path:
    """Write normalized observations to Parquet."""
    out = Path(normalized_dir) / f"{name}.parquet"
    return write_parquet(frame, out)


def duckdb_query(sql: str, *, files: dict[str, Path | str] | None = None) -> pl.DataFrame:
    """Run a DuckDB SQL query, optionally registering Parquet files as views.

    Example:
        duckdb_query(
            "SELECT platform, count(*) AS n FROM obs GROUP BY 1",
            files={"obs": "data/normalized/observations.parquet"},
        )
    """
    con = duckdb.connect(database=":memory:")
    try:
        for view_name, file_path in (files or {}).items():
            con.execute(
                f"CREATE VIEW {view_name} AS SELECT * FROM read_parquet(?)",
                [str(file_path)],
            )
        result = con.execute(sql).pl()
        return result
    finally:
        con.close()


def parquet_to_duckdb_table(
    parquet_path: Path | str,
    db_path: Path | str,
    table_name: str = "observations",
) -> Path:
    """Load a Parquet file into a durable DuckDB database table."""
    db_path = Path(db_path)
    ensure_dir(db_path.parent)
    con = duckdb.connect(database=str(db_path))
    try:
        con.execute(
            f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM read_parquet(?)",
            [str(parquet_path)],
        )
    finally:
        con.close()
    return db_path
