"""Configuration loading helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT = Path(__file__).resolve().parents[2]


class PathSettings(BaseModel):
    data_dir: str = "data"
    raw_dir: str = "data/raw"
    normalized_dir: str = "data/normalized"
    processed_dir: str = "data/processed"
    config_dir: str = "config"


class EnvSettings(BaseSettings):
    """Environment overrides (.env)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    signalgraph_primary_platform: str = "kalshi"
    kalshi_base_url: str = "https://api.elections.kalshi.com/trade-api/v2"
    kalshi_api_key_id: str | None = None
    kalshi_private_key_path: str | None = None
    polymarket_base_url: str = "https://gamma-api.polymarket.com"
    polymarket_clob_url: str = "https://clob.polymarket.com"
    signalgraph_data_dir: str = "data"
    signalgraph_raw_dir: str = "data/raw"
    signalgraph_normalized_dir: str = "data/normalized"
    signalgraph_processed_dir: str = "data/processed"
    signalgraph_http_timeout_seconds: float = 30.0
    signalgraph_http_max_retries: int = 3


class AppConfig(BaseModel):
    raw: dict[str, Any] = Field(default_factory=dict)
    paths: PathSettings = Field(default_factory=PathSettings)
    env: EnvSettings = Field(default_factory=EnvSettings)

    @property
    def root(self) -> Path:
        return ROOT


def load_yaml(path: Path | str) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def load_settings(path: Path | str | None = None) -> AppConfig:
    settings_path = Path(path) if path else ROOT / "config" / "settings.yaml"
    raw = load_yaml(settings_path) if settings_path.exists() else {}
    paths = PathSettings(**(raw.get("paths") or {}))
    env = EnvSettings()
    # Env overrides for paths when provided.
    paths = paths.model_copy(
        update={
            "data_dir": env.signalgraph_data_dir or paths.data_dir,
            "raw_dir": env.signalgraph_raw_dir or paths.raw_dir,
            "normalized_dir": env.signalgraph_normalized_dir or paths.normalized_dir,
            "processed_dir": env.signalgraph_processed_dir or paths.processed_dir,
        }
    )
    return AppConfig(raw=raw, paths=paths, env=env)
