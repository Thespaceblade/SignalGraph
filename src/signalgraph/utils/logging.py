"""Logging setup."""

from __future__ import annotations

import logging
import sys


def setup_logging(level: str = "INFO", fmt: str | None = None) -> None:
    fmt = fmt or "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(level)
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt))
    root.addHandler(handler)
    root.setLevel(level)
