"""Position bank schema (migration 0001): constraints behave as specs/position_pipeline_spec.md §2.

Runs against the real database. Every test works inside a transaction that is rolled back,
so the local position bank is never touched. Locally: uv run --env-file .env pytest
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, insert, inspect, select, text
from sqlalchemy.exc import IntegrityError

from chess_training.db import attempts, metadata, position_moves, position_sources, positions

# Rows that no importer produces, so the tests never collide with an imported bank.
BARE_KINGS = "8/8/8/4k3/8/8/8/4K3 b - -"
TEST_REF = "test-only ref"


def add_position(conn, fen_key=BARE_KINGS, **kw):
    values = {
        "fen": fen_key + " 0 1",
        "fen_key": fen_key,
        "side_to_move": "b",
        "phase": "opening",
    } | kw
    return conn.execute(insert(positions).values(values).returning(positions.c.id)).scalar_one()


def add_source(conn, position_id, source_ref=TEST_REF, **kw):
    values = {
        "position_id": position_id,
        "source": "opening",
        "source_ref": source_ref,
        "fullmove_number": 1,
        "moves_to_position": ["e4"],
    } | kw
    conn.execute(insert(position_sources).values(values))


def add_move(conn, position_id, uci="e7e5", **kw):
    values = {
        "position_id": position_id,
        "uci": uci,
        "san": "e5",
        "score_cp": 20,
        "depth": 10,
        "engine_version": "sf_19",
    } | kw
    conn.execute(insert(position_moves).values(values))


def rejects(conn, fn, *args, **kw):
    """True if the database refuses the insert. A savepoint keeps the test's transaction usable."""
    try:
        with conn.begin_nested():
            fn(conn, *args, **kw)
    except IntegrityError:
        return True
    return False


def test_database_is_migrated_to_head(engine):
    with engine.connect() as c:
        tables = set(inspect(c).get_table_names())
    assert set(metadata.tables) <= tables, "Run: uv run --env-file .env alembic upgrade head"


def test_valid_rows_insert_with_defaults(conn):
    pid = add_position(conn)
    add_source(conn, pid)
    add_move(conn, pid)
    row = conn.execute(select(positions).where(positions.c.id == pid)).one()
    assert row.opening_names == []
    assert row.opening_name is None
    assert row.created_at is not None


def test_fen_key_is_unique(conn):
    add_position(conn)
    assert rejects(conn, add_position)


@pytest.mark.parametrize(
    "column, value",
    [("side_to_move", "x"), ("phase", "late"), ("pawn_fingerprint_version", 1)],
)
def test_position_checks(conn, column, value):
    # pawn_fingerprint_version without pawn_fingerprint breaks "filled together".
    assert rejects(conn, add_position, **{column: value})


def test_fingerprint_and_version_together(conn):
    add_position(conn, pawn_fingerprint={"files": []}, pawn_fingerprint_version=1)


def test_source_and_ref_are_unique(conn):
    pid = add_position(conn)
    add_source(conn, pid)
    assert rejects(conn, add_source, pid)  # same (opening, TEST_REF)
    add_source(conn, pid, source="puzzle", source_ref=TEST_REF)  # other source: fine


def test_source_must_be_known(conn):
    pid = add_position(conn)
    assert rejects(conn, add_source, pid, source="game")


@pytest.mark.parametrize(
    "scores",
    [{"score_cp": None, "score_mate": None}, {"score_cp": 20, "score_mate": 3}],
)
def test_move_has_exactly_one_score(conn, scores):
    pid = add_position(conn)
    assert rejects(conn, add_move, pid, **scores)
    add_move(conn, pid, score_cp=None, score_mate=-2)  # mate only: fine


def test_move_key_is_position_uci_engine(conn):
    pid = add_position(conn)
    add_move(conn, pid)
    assert rejects(conn, add_move, pid)  # same move, same engine
    add_move(conn, pid, engine_version="sf_20")  # newer engine side by side: fine


def test_deleting_a_position_removes_its_rows(conn):
    pid = add_position(conn)
    add_source(conn, pid)
    add_move(conn, pid)
    conn.execute(positions.delete().where(positions.c.id == pid))
    for table in (position_sources, position_moves):
        n = conn.execute(select(func.count()).select_from(table).where(table.c.position_id == pid))
        assert n.scalar_one() == 0


def test_rows_need_an_existing_position(conn):
    missing = conn.execute(text("SELECT coalesce(max(id), 0) + 1000 FROM positions")).scalar_one()
    assert rejects(conn, add_source, missing)
    assert rejects(conn, add_move, missing)


def test_puzzle_source_stores_opening_tags(conn):
    pid = add_position(conn)
    tags = ["Sicilian_Defense", "Sicilian_Defense_Najdorf_Variation"]
    add_source(conn, pid, source="puzzle", puzzle_opening_tags=tags)
    stored = conn.execute(
        select(position_sources.c.puzzle_opening_tags).where(position_sources.c.position_id == pid)
    ).scalar_one()
    assert stored == tags


def add_attempt(conn, position_id, **kw):
    values = {
        "position_id": position_id,
        "uci": "e7e5",
        "san": "e5",
        "mode": "normal",
        "side": "b",
        "claimed_only_move": False,
        "result": "acceptable",
        "win_loss": 0.0,
        "engine_version": "sf_19",
    } | kw
    return conn.execute(insert(attempts).values(values).returning(attempts.c.id)).scalar_one()


def test_attempt_inserts_with_defaults(conn):
    pid = add_position(conn)
    aid = add_attempt(conn, pid)
    row = conn.execute(select(attempts).where(attempts.c.id == aid)).one()
    assert row.challenge_repeat is False and row.played_at is not None


@pytest.mark.parametrize(
    "values",
    [
        {"mode": "blitz"},
        {"result": "inaccuracy"},
        {"side": "x"},
        {"win_loss": -1.0},
        {"mode": "normal", "challenge_repeat": True},  # repeats exist only in challenge mode
    ],
)
def test_attempt_checks(conn, values):
    pid = add_position(conn)
    assert rejects(conn, add_attempt, pid, **values)


def test_challenge_repeat_is_allowed_in_challenge_mode(conn):
    pid = add_position(conn)
    add_attempt(conn, pid, mode="challenge", challenge_repeat=True, result="blunder", win_loss=30)


def test_a_position_with_attempts_cannot_be_deleted(conn):
    pid = add_position(conn)
    add_attempt(conn, pid)
    try:
        with conn.begin_nested():
            conn.execute(positions.delete().where(positions.c.id == pid))
        deleted = True
    except IntegrityError:
        deleted = False
    assert not deleted
