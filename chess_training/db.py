"""Position bank tables (specs/position_pipeline_spec.md §2) and the database connection.

The schema itself is created by Alembic migrations in migrations/versions/. These table
definitions must match them; CI runs `alembic check` to catch any drift.
"""

from __future__ import annotations

import os

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    MetaData,
    PrimaryKeyConstraint,
    SmallInteger,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.engine import Engine

# Predictable constraint names, so migrations can refer to them.
metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_N_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)

PHASES = ("opening", "middlegame", "endgame")
SOURCES = ("opening", "puzzle")  # "game" is added later (spec §2)


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


positions = Table(
    "positions",
    metadata,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("fen", Text, nullable=False),  # as first seen
    # FEN without move counters; en passant square kept only when the capture is legal.
    Column("fen_key", Text, nullable=False, unique=True),
    Column("side_to_move", Text, nullable=False),
    Column("phase", Text, nullable=False),
    Column("opening_name", Text),  # primary name (spec §4); NULL when none
    Column(
        "opening_names",
        ARRAY(Text),
        nullable=False,
        server_default=text("'{}'::text[]"),
    ),
    # Placeholder type: the fingerprint's shape is defined when challenge mode is built
    # (spec §7, challenge_mode_spec §2). JSONB commits to nothing yet.
    Column("pawn_fingerprint", JSONB),
    Column("pawn_fingerprint_version", SmallInteger),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("side_to_move IN ('w', 'b')", name="side_to_move"),
    CheckConstraint(_in("phase", PHASES), name="phase"),
    CheckConstraint(
        "(pawn_fingerprint IS NULL) = (pawn_fingerprint_version IS NULL)",
        name="fingerprint_with_version",
    ),
)

position_sources = Table(
    "position_sources",
    metadata,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column(
        "position_id",
        BigInteger,
        ForeignKey("positions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column("source", Text, nullable=False),
    # Openings: the moves played to reach the position (decided 2026-11-09, option A).
    # Puzzles: the Lichess puzzle id.
    Column("source_ref", Text, nullable=False),
    Column("fullmove_number", Integer, nullable=False),
    # SAN moves leading here; the last element is the last move played.
    Column("moves_to_position", ARRAY(Text), nullable=False),
    Column("opening_eco", Text),
    Column("puzzle_rating", Integer),
    Column("puzzle_themes", ARRAY(Text)),
    Column("puzzle_popularity", Integer),
    Column("puzzle_nb_plays", Integer),
    # The opening of the game the puzzle came from (Lichess OpeningTags). Informational only:
    # never used for opening_name, which follows our own naming rule (spec §4). Migration 0002.
    Column("puzzle_opening_tags", ARRAY(Text)),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint(_in("source", SOURCES), name="source"),
    UniqueConstraint("source", "source_ref"),
)

position_moves = Table(
    "position_moves",
    metadata,
    Column(
        "position_id",
        BigInteger,
        ForeignKey("positions.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("uci", Text, nullable=False),
    Column("san", Text, nullable=False),
    # Raw score from the mover's point of view: exactly one of the two is set.
    Column("score_cp", Integer),
    Column("score_mate", Integer),
    Column("depth", SmallInteger, nullable=False),
    Column("engine_version", Text, nullable=False),
    Column("analysed_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    PrimaryKeyConstraint("position_id", "uci", "engine_version"),
    CheckConstraint("(score_cp IS NULL) <> (score_mate IS NULL)", name="one_score"),
)


def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Locally, run commands with: uv run --env-file .env ..."
        )
    return url


def get_engine() -> Engine:
    return create_engine(database_url())
