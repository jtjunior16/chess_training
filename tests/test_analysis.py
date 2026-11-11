"""Batch engine analysis (specs/position_pipeline_spec.md §6) and the win-% curve."""

from __future__ import annotations

import copy
from dataclasses import replace

import chess
import pytest
from sqlalchemy import insert, select

from chess_training.analysis import (
    AnalysisSettings,
    MoveScore,
    analyse_position,
    check_config,
    deep_candidates,
    open_engine,
    pending,
    save,
)
from chess_training.config import load_config
from chess_training.db import position_moves, positions
from chess_training.winpct import win_pct, win_pct_from_cp

# ---------------------------------------------------------------- win %


@pytest.mark.parametrize(
    "cp, expected",
    [(0, 50.0), (-150, 36.5), (600, 90.1), (450, 84.0), (200, 67.6), (20, 51.8)],
)
def test_win_pct_matches_the_spec_examples(cp, expected):
    assert win_pct_from_cp(cp) == pytest.approx(expected, abs=0.1)


def test_mates_are_about_100_or_0():
    assert win_pct(None, 3) > 99.9
    assert win_pct(None, -2) < 0.1
    assert win_pct(None, 0) < 0.1  # side to move is mated
    with pytest.raises(ValueError):
        win_pct(None, None)


# ---------------------------------------------------------------- settings


def test_config_values_and_checks_pass():
    s = AnalysisSettings.from_config()
    assert (s.quick_depth, s.deep_depth, s.deep_margin) == (10, 18, 15)
    assert s.threads == 1


@pytest.mark.parametrize(
    "section, key, value, message",
    [
        ("analysis", "deep_depth", 16, "must equal engine.depth"),
        ("analysis", "deep_margin", 11, "at least 2 x L"),
        ("analysis", "quick_depth", 18, "below analysis.deep_depth"),
        ("engine", "threads", 2, "threads must be 1"),
    ],
)
def test_bad_config_fails(section, key, value, message):
    cfg = copy.deepcopy(load_config())
    cfg[section][key] = value
    with pytest.raises(ValueError, match=message):
        check_config(cfg)


# ---------------------------------------------------------------- deep-pass selection


def ms(uci, cp=None, mate=None):
    return MoveScore(uci, uci, cp, mate, 10)


def test_deep_candidates_are_within_the_margin_of_the_best():
    moves = [ms("a", 0), ms("b", -100), ms("c", -200), ms("d", -400)]
    # win%: a 50.0, b 40.9, c 32.4, d 18.7 -> within 15 of 50: a, b
    assert deep_candidates(moves, 15) == ["a", "b"]
    assert deep_candidates(moves, 100) == ["a", "b", "c", "d"]
    assert deep_candidates([], 15) == []


def test_a_mate_leaves_only_near_mates_for_the_deep_pass():
    moves = [ms("m", mate=2), ms("big", 900), ms("ok", 300)]
    # mate ~100, +9 ~96.5, +3 ~75.1
    assert deep_candidates(moves, 15) == ["m", "big"]


# ---------------------------------------------------------------- real Stockfish


@pytest.fixture(scope="module")
def sf(require_stockfish):
    settings = replace(AnalysisSettings.from_config(), quick_depth=6, deep_depth=10, workers=1)
    eng = open_engine(settings)
    yield eng, settings
    eng.quit()


def test_every_legal_move_is_scored_and_candidates_go_deep(sf):
    eng, settings = sf
    fen = "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3"
    result = analyse_position(eng, 1, fen, settings)
    legal = {m.uci() for m in chess.Board(fen).legal_moves}
    assert {m.uci for m in result.moves} == legal
    deep = [m for m in result.moves if m.depth == settings.deep_depth]
    assert len(deep) == result.deep_count >= 1
    assert all((m.score_cp is None) != (m.score_mate is None) for m in result.moves)
    best = max(result.moves, key=lambda m: m.win)
    assert best.depth == settings.deep_depth


def test_mate_in_one_is_found_and_stored_as_mate(sf):
    eng, settings = sf
    fen = "6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1"  # Ra8#
    result = analyse_position(eng, 2, fen, settings)
    mate = next(m for m in result.moves if m.uci == "a1a8")
    assert mate.score_mate == 1 and mate.score_cp is None


def test_same_position_same_scores(sf):
    eng, settings = sf
    fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
    a = analyse_position(eng, 3, fen, settings)
    analyse_position(eng, 4, "6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1", settings)  # something else
    b = analyse_position(eng, 3, fen, settings)
    key = lambda r: sorted((m.uci, m.score_cp, m.score_mate, m.depth) for m in r.moves)  # noqa: E731
    assert key(a) == key(b)


def test_no_legal_moves_gives_an_empty_result(sf):
    eng, settings = sf
    mated = "R5k1/5ppp/8/8/8/8/5PPP/6K1 b - - 1 1"
    assert analyse_position(eng, 5, mated, settings).moves == []


# ---------------------------------------------------------------- database


def test_saved_positions_are_no_longer_pending(conn, sf):
    eng, settings = sf
    fen = "4k3/8/8/8/8/8/4P3/4K3 w - - 0 60"
    pid = conn.execute(
        insert(positions)
        .values(
            fen=fen, fen_key="4k3/8/8/8/8/8/4P3/4K3 w - - test", side_to_move="w", phase="endgame"
        )
        .returning(positions.c.id)
    ).scalar_one()
    version = "test-engine"
    assert pid in {p for p, _ in pending(conn, version)}
    result = analyse_position(eng, pid, fen, settings)
    save(conn, result, version)
    save(conn, result, version)  # saving again updates in place
    rows = conn.execute(select(position_moves).where(position_moves.c.position_id == pid)).all()
    assert len(rows) == len(list(chess.Board(fen).legal_moves))
    assert pid not in {p for p, _ in pending(conn, version)}


def test_fresh_engine_gives_the_same_scores_as_a_used_one(sf):
    eng, settings = sf
    fen = "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3"
    used = analyse_position(eng, 6, fen, settings)
    fresh_engine = open_engine(settings)
    try:
        fresh = analyse_position(fresh_engine, 6, fen, settings)
    finally:
        fresh_engine.quit()
    key = lambda r: sorted((m.uci, m.score_cp, m.score_mate, m.depth) for m in r.moves)  # noqa: E731
    assert key(used) == key(fresh)


def test_terminal_positions_are_never_pending(conn):
    from chess_training.analysis import terminal_positions

    mated = "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3"  # Fool's Mate
    pid = conn.execute(
        insert(positions)
        .values(
            fen=mated,
            fen_key="fools-mate test",
            side_to_move="w",
            phase="opening",
        )
        .returning(positions.c.id)
    ).scalar_one()
    assert pid in terminal_positions(conn)
    assert pid not in {p for p, _ in pending(conn, "test-engine")}


def test_estimate_is_weighted_by_what_is_left():
    import pandas as pd

    from chess_training.analysis import estimate_hours

    done = pd.DataFrame(
        {"source": ["opening", "puzzle"], "phase": ["opening", "endgame"], "total_s": [10.0, 2.0]}
    )
    left = pd.DataFrame({"source": ["opening"] * 3, "phase": ["opening"] * 3})
    # 3 openings x 10 s of engine time, at 6 s wall per 12 s engine -> 15 s wall
    assert estimate_hours(done, 6.0, left) * 3600 == pytest.approx(15.0)
