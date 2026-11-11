"""Scoring (specs/scoring_spec.md), on synthetic positions and attempts (rolled back)."""

from __future__ import annotations

import os
from dataclasses import replace

import pytest
from sqlalchemy import func, insert, select

from chess_training.acceptance import AcceptanceSettings
from chess_training.db import attempts, position_moves, position_sources, positions
from chess_training.scoring import (
    NOT_ENOUGH,
    ScoringSettings,
    recompute_attempts,
    record_attempt,
    render,
    stats,
)

VERSION = "test-scoring"
ACC = AcceptanceSettings(G=5, L=6)


@pytest.fixture
def sc():
    return replace(ScoringSettings.from_config(), min_attempts=2, recent_window=3)


def add_position(conn, key, moves, *, phase="middlegame", side="w", name=None, puzzle=None):
    """moves: list of (uci, score_cp or None, score_mate or None). puzzle: list of themes."""
    pid = conn.execute(
        insert(positions)
        .values(fen=key + " 0 30", fen_key=key, side_to_move=side, phase=phase, opening_name=name)
        .returning(positions.c.id)
    ).scalar_one()
    conn.execute(
        insert(position_sources).values(
            position_id=pid,
            source="puzzle" if puzzle is not None else "opening",
            source_ref=f"ref-{key}",
            fullmove_number=30,
            moves_to_position=["e4"],
            puzzle_themes=puzzle,
        )
    )
    for uci, score_cp, score_mate in moves:
        conn.execute(
            insert(position_moves).values(
                position_id=pid,
                uci=uci,
                san=uci,
                score_cp=score_cp,
                score_mate=score_mate,
                depth=18,
                engine_version=VERSION,
            )
        )
    return pid


def rec(conn, pid, uci, sc, **kw):
    return record_attempt(
        conn, pid, uci, acceptance_settings=ACC, scoring_settings=sc, engine_version=VERSION, **kw
    )


def get_stats(conn, sc):
    return stats(conn, ACC, sc, engine_version=VERSION)


# ---------------------------------------------------------------- settings


def test_config_values():
    s = ScoringSettings.from_config()
    assert (s.recent_window, s.min_attempts, s.blunder_line) == (50, 10, 15)
    assert "fork" in s.motif and "middlegame" not in s.motif


@pytest.mark.parametrize(
    "size, label", [(1, "only-move"), (2, "2-4"), (4, "2-4"), (5, "5+"), (30, "5+")]
)
def test_difficulty_buckets(size, label):
    assert ScoringSettings.from_config().difficulty(size) == label


# ---------------------------------------------------------------- recording (§6, §7)


def test_record_attempt_judges_and_stores(conn, sc):
    pid = add_position(
        conn, "sc-1", [("a", 0, None), ("near", -100, None), ("far", -600, None)], side="b"
    )
    assert rec(conn, pid, "a", sc).kind == "acceptable"
    near = rec(conn, pid, "near", sc)
    assert near.kind == "close miss" and near.win_loss == pytest.approx(9.1, abs=0.1)
    assert rec(conn, pid, "far", sc).kind == "blunder"
    row = conn.execute(select(attempts).where(attempts.c.id == near.id)).one()
    assert (row.side, row.result, row.engine_version, row.mode) == (
        "b",
        "close miss",
        VERSION,
        "normal",
    )


def test_claim_correctness(conn, sc):
    only = add_position(conn, "sc-only", [("best", 200, None), ("x", 10, None)])
    many = add_position(conn, "sc-many", [("a", 20, None), ("b", 20, None)])
    assert rec(conn, only, "best", sc, claimed_only_move=True).claim_correct is True
    assert rec(conn, many, "a", sc, claimed_only_move=True).claim_correct is False
    assert rec(conn, many, "a", sc).claim_correct is None


def test_missed_mate_is_recorded_as_a_blunder(conn, sc):
    pid = add_position(conn, "sc-mate", [("m", None, 1), ("big", 900, None)])
    r = rec(conn, pid, "big", sc)
    assert r.kind == "blunder" and r.verdict_text == "Not acceptable (misses the mate)"


# ---------------------------------------------------------------- stats (§1–§5)


def test_not_enough_data_below_the_minimum(conn, sc):
    pid = add_position(conn, "sc-min", [("a", 0, None), ("b", -600, None)])
    rec(conn, pid, "a", sc)
    s = get_stats(conn, sc)
    assert s["overall"]["all_time"]["acceptable"] is None
    assert NOT_ENOUGH in render(s)
    rec(conn, pid, "b", sc)
    s = get_stats(conn, sc)
    assert s["overall"]["all_time"]["acceptable"] == 50.0
    assert s["overall"]["all_time"]["blunder"] == 50.0


def test_recent_is_the_last_n_attempts(conn, sc):
    pid = add_position(conn, "sc-recent", [("a", 0, None), ("b", -600, None)])
    for uci in ["b", "b", "a", "a", "a"]:  # recent window = 3: the last three are all good
        rec(conn, pid, uci, sc)
    s = get_stats(conn, sc)["overall"]
    assert s["all_time"]["acceptable"] == 60.0
    assert s["recent"]["acceptable"] == 100.0 and s["recent"]["attempts"] == 3


def test_challenge_repeats_are_stored_but_not_counted(conn, sc):
    pid = add_position(conn, "sc-repeat", [("a", 0, None), ("b", -600, None)])
    rec(conn, pid, "b", sc, mode="challenge")
    rec(conn, pid, "a", sc, mode="challenge", challenge_repeat=True)
    rec(conn, pid, "b", sc)
    s = get_stats(conn, sc)["overall"]["all_time"]
    assert s["attempts"] == 2 and s["blunder"] == 100.0
    n = conn.execute(
        select(func.count()).select_from(attempts).where(attempts.c.position_id == pid)
    ).scalar_one()
    assert n == 3


def test_claim_accuracy_and_spotting_rate(conn, sc):
    only = add_position(conn, "sc-c-only", [("best", 200, None), ("x", 10, None)])
    many = add_position(conn, "sc-c-many", [("a", 20, None), ("b", 20, None)])
    rec(conn, only, "best", sc, claimed_only_move=True)  # correct claim
    rec(conn, only, "best", sc)  # missed
    rec(conn, many, "a", sc, claimed_only_move=True)  # wrong claim
    rec(conn, many, "a", sc)  # correctly left blank
    f = get_stats(conn, sc)["overall"]["all_time"]
    assert (f["claims"], f["claim_accuracy"]) == (2, 50.0)
    assert (f["only_move_seen"], f["spotting_rate"]) == (2, 50.0)


def test_breakdowns(conn, sc):
    caro = add_position(
        conn,
        "sc-caro",
        [("a", 0, None), ("b", -600, None)],
        phase="opening",
        side="b",
        name="Caro-Kann Defense: Advance Variation",
    )
    caro2 = add_position(
        conn,
        "sc-caro2",
        [("a", 0, None), ("b", -600, None)],
        phase="opening",
        side="w",
        name="Caro-Kann Defense",
    )
    puz = add_position(
        conn,
        "sc-puz",
        [("a", 300, None), ("b", -300, None)],
        phase="endgame",
        puzzle=["endgame", "fork", "pin", "short"],
    )
    for pid, uci in [(caro, "a"), (caro2, "b"), (puz, "a"), (puz, "a")]:
        rec(conn, pid, uci, sc)
    b = get_stats(conn, sc)["breakdowns"]
    assert b["opening family"]["Caro-Kann Defense"]["all_time"]["attempts"] == 2
    assert b["opening family"]["Caro-Kann Defense"]["all_time"]["acceptable"] == 50.0
    assert set(b["puzzle theme"]) == {"fork", "pin"}  # motif tags only, each counted
    assert b["puzzle theme"]["fork"]["all_time"]["attempts"] == 2
    assert set(b["side"]) == {"White", "Black"}
    assert set(b["phase"]) == {"opening", "endgame"}
    assert set(b["difficulty"]) == {"only-move"}


# ---------------------------------------------------------------- recompute (§7 placeholder)


def test_recompute_after_g_changes(conn, sc):
    # 0 vs -100 cp is a 9.1 win-% gap: not acceptable at G = 5, acceptable at G = 10, L = 10.
    pid = add_position(conn, "sc-recompute", [("a", 0, None), ("b", -100, None)])
    aid = rec(conn, pid, "b", sc).id
    assert recompute_attempts(conn, ACC, sc, engine_version=VERSION) == (0, 0)
    loose = AcceptanceSettings(G=10, L=10)
    assert recompute_attempts(conn, loose, sc, engine_version=VERSION) == (1, 0)
    assert conn.execute(select(attempts.c.result).where(attempts.c.id == aid)).scalar_one() == (
        "acceptable"
    )


# ---------------------------------------------------------------- API


def test_stats_endpoint_returns_the_structure():
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set")
    from chess_training.app import get_stats as endpoint

    s = endpoint()
    assert set(s) == {"overall", "breakdowns", "settings", "skipped_unscored"}
    assert set(s["breakdowns"]) == {"phase", "opening family", "side", "difficulty", "puzzle theme"}


def test_recompute_after_blunder_line_changes(conn, sc):
    pid = add_position(conn, "sc-bl", [("a", 0, None), ("near", -100, None)])  # 9.1 below
    aid = rec(conn, pid, "near", sc).id
    strict = replace(sc, blunder_line=5)
    assert recompute_attempts(conn, ACC, strict, engine_version=VERSION) == (1, 0)
    assert conn.execute(select(attempts.c.result).where(attempts.c.id == aid)).scalar_one() == (
        "blunder"
    )


def test_unscored_positions_are_skipped_not_fatal(conn, sc):
    pid = add_position(conn, "sc-upgrade", [("a", 0, None), ("b", -600, None)])
    rec(conn, pid, "a", sc)
    rec(conn, pid, "b", sc)
    # A new engine version with no scores for this position yet (e.g. after an upgrade):
    s = stats(conn, ACC, sc, engine_version="not-analysed-yet")
    assert s["skipped_unscored"] >= 2
    assert "Skipped" in render(s)
    changed, skipped = recompute_attempts(conn, ACC, sc, engine_version="not-analysed-yet")
    assert skipped >= 2


def test_difficulty_buckets_through_stats(conn, sc):
    two = add_position(conn, "sc-two", [("a", 20, None), ("b", 20, None), ("c", -600, None)])
    six = add_position(conn, "sc-six", [(f"m{i}", 20, None) for i in range(6)])
    rec(conn, two, "a", sc)
    rec(conn, six, "m0", sc)
    assert set(get_stats(conn, sc)["breakdowns"]["difficulty"]) == {"2-4", "5+"}
