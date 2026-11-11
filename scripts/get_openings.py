"""Download the pinned lichess-org/chess-openings TSV files into data/raw/openings/.

Usage: uv run python scripts/get_openings.py

The commit and the expected SHA-256 of each file live in config.yaml under `openings:`.
Files that are already present with the right checksum are not downloaded again.
"""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from chess_training.config import load_config  # noqa: E402
from chess_training.openings import openings_dir  # noqa: E402

RAW_URL = "https://raw.githubusercontent.com/{repo}/{commit}/{name}"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    cfg = load_config()["openings"]
    target_dir = openings_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    for name, expected in cfg["sha256"].items():
        target = target_dir / name
        if target.exists() and sha256(target.read_bytes()) == expected:
            print(f"{name}: already present (sha256 verified)")
            continue
        url = RAW_URL.format(repo=cfg["repo"], commit=cfg["commit"], name=name)
        print(f"Downloading {url}")
        with urllib.request.urlopen(url) as resp:  # noqa: S310 (fixed https URL)
            data = resp.read()
        actual = sha256(data)
        if actual != expected:
            raise SystemExit(f"Checksum mismatch for {name}: expected {expected}, got {actual}")
        target.write_bytes(data)
        print(f"{name}: saved to {target} (sha256 verified)")


if __name__ == "__main__":
    main()
