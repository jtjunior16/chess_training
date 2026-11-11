"""Download the pinned Lichess puzzle dump into data/raw/puzzles/ and verify its checksum.

Usage: uv run python scripts/get_puzzles.py

The URL and expected SHA-256 live in config.yaml under `puzzles:`. Lichess replaces the dump
monthly at the same URL, so a newer dump fails the check: re-pin it in config.yaml on purpose
(new sha256 and dump_date) rather than letting the sample change silently.
"""

from __future__ import annotations

import hashlib
import shutil
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from chess_training.config import load_config  # noqa: E402
from chess_training.puzzles import puzzles_path  # noqa: E402


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    cfg = load_config()["puzzles"]
    target = puzzles_path()
    expected = cfg["sha256"]
    if target.exists() and file_sha256(target) == expected:
        print(f"{target.name}: already present (sha256 verified)")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {cfg['url']} (about 300 MB)")
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as tmp:
        with urllib.request.urlopen(cfg["url"]) as resp:  # noqa: S310 (fixed https URL)
            shutil.copyfileobj(resp, tmp, 1 << 20)
    tmp_path = Path(tmp.name)
    actual = file_sha256(tmp_path)
    if actual != expected:
        tmp_path.unlink()
        raise SystemExit(
            f"Checksum mismatch: expected {expected}, got {actual}. Lichess has probably "
            "published a newer dump. To use it, set puzzles.sha256 and puzzles.dump_date in "
            "config.yaml (this changes the sample)."
        )
    tmp_path.replace(target)
    print(f"Saved {target} (sha256 verified)")


if __name__ == "__main__":
    main()
