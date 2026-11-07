"""Download the pinned Stockfish release into tools/stockfish/ and verify its checksum.

Usage: uv run python scripts/get_stockfish.py

The version, install path and expected SHA-256 of each release asset live in config.yaml
under `engine:`. Running this again is a no-op when the pinned version is already installed.
"""

from __future__ import annotations

import hashlib
import io
import platform
import stat
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from chess_training.config import engine_path, load_config  # noqa: E402

RELEASE_URL = "https://github.com/official-stockfish/Stockfish/releases/download/{version}/{asset}"


def asset_name() -> str:
    """Name of the release asset for this machine (universal builds pick CPU features)."""
    system = platform.system()
    machine = platform.machine().lower()
    if system == "Darwin":
        return "stockfish-macos-universal.tar.gz"
    arch = {"amd64": "x86-64", "x86_64": "x86-64", "arm64": "arm64", "aarch64": "arm64"}.get(
        machine
    )
    if system == "Windows" and arch:
        return f"stockfish-windows-{arch}-universal.zip"
    if system == "Linux" and arch:
        return f"stockfish-linux-{arch}-universal.tar.gz"
    raise SystemExit(f"No Stockfish build configured for {system}/{machine}.")


def extract_executable(archive: bytes, asset: str) -> bytes:
    """Return the bytes of the engine binary inside the release archive."""
    stem = asset.removesuffix(".zip").removesuffix(".tar.gz")
    if asset.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(archive)) as zf:
            name = next(n for n in zf.namelist() if Path(n).name.startswith(stem))
            return zf.read(name)
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tf:
        member = next(m for m in tf.getmembers() if m.isfile() and Path(m.name).name == stem)
        return tf.extractfile(member).read()


def main() -> None:
    cfg = load_config()["engine"]
    version = cfg["version"]
    target = engine_path()
    version_file = target.parent / "VERSION"

    if target.exists() and version_file.exists() and version_file.read_text().strip() == version:
        print(f"Stockfish {version} already installed at {target}")
        return

    asset = asset_name()
    expected = cfg["sha256"].get(asset)
    if not expected:
        raise SystemExit(f"No checksum for {asset} in config.yaml (engine.sha256). Add it first.")

    url = RELEASE_URL.format(version=version, asset=asset)
    print(f"Downloading {url}")
    with urllib.request.urlopen(url) as resp:  # noqa: S310 (fixed https URL)
        archive = resp.read()

    actual = hashlib.sha256(archive).hexdigest()
    if actual != expected:
        raise SystemExit(f"Checksum mismatch for {asset}: expected {expected}, got {actual}")

    binary = extract_executable(archive, asset)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Write to a temp file first so a failed run never leaves a half-written engine.
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as tmp:
        tmp.write(binary)
    tmp_path = Path(tmp.name)
    tmp_path.chmod(tmp_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    tmp_path.replace(target)
    version_file.write_text(version + "\n")
    print(f"Installed Stockfish {version} at {target} (sha256 verified)")


if __name__ == "__main__":
    main()
