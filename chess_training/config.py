"""Load non-secret project parameters from config.yaml."""

from __future__ import annotations

import sys
from functools import cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


@cache
def load_config() -> dict:
    with (ROOT / "config.yaml").open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def engine_path() -> Path:
    """Absolute path to the pinned Stockfish binary (adds .exe on Windows)."""
    path = ROOT / load_config()["engine"]["path"]
    if sys.platform == "win32":
        path = path.with_suffix(".exe")
    return path
