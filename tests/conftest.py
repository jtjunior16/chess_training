import os

import pytest

from chess_training.config import engine_path


@pytest.fixture(scope="session")
def require_stockfish():
    """Skip locally if Stockfish isn't downloaded; fail in CI, where it must be."""
    if not engine_path().exists():
        msg = "Stockfish missing. Run: uv run python scripts/get_stockfish.py"
        if os.environ.get("CI"):
            pytest.fail(msg)
        pytest.skip(msg)
