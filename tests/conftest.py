import os

import pytest
from sqlalchemy import create_engine

from chess_training.config import engine_path


@pytest.fixture(scope="session")
def require_stockfish():
    """Skip locally if Stockfish isn't downloaded; fail in CI, where it must be."""
    if not engine_path().exists():
        msg = "Stockfish missing. Run: uv run python scripts/get_stockfish.py"
        if os.environ.get("CI"):
            pytest.fail(msg)
        pytest.skip(msg)


@pytest.fixture(scope="session")
def engine():
    """The real database. Skip locally if DATABASE_URL isn't set; fail in CI, where it must be."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        msg = "DATABASE_URL not set. Run: uv run --env-file .env pytest"
        if os.environ.get("CI"):
            pytest.fail(msg)
        pytest.skip(msg)
    eng = create_engine(url)
    yield eng
    eng.dispose()


@pytest.fixture
def conn(engine):
    """A connection inside a transaction that is always rolled back, so local data is untouched."""
    with engine.connect() as c:
        outer = c.begin()
        try:
            yield c
        finally:
            outer.rollback()
