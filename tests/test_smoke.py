"""Smoke tests: the scaffold is intact. Replace or extend with real tests."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_env_example_lists_no_values():
    """.env.example must hold key names only (universal-rules §5)."""
    for line in (ROOT / ".env.example").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            assert value == "", f"{key} has a value in .env.example; values belong in .env"


def test_config_exists():
    assert (ROOT / "config.yaml").is_file()
