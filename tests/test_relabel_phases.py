"""Phase relabeller (specs/position_pipeline_spec.md §3), on the real database, rolled back."""

from __future__ import annotations

from dataclasses import replace

from sqlalchemy import insert, select

from chess_training.db import position_sources, positions
from chess_training.phase import PhaseSettings
from chess_training.relabel_phases import puzzle_phase_comparison, relabel

# R+B+N v R+B+N with pawns at move 30: endgame under the no-queen rule.
RBN = "r3kbn1/pppp4/8/8/8/8/PPPP4/R3KBN1 w - - 0 30"
# Full army at move 30, but on a named line: opening.
FULL = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 30"


def add(conn, fen, phase, source, ref):
    pid = conn.execute(
        insert(positions)
        .values(fen=fen, fen_key=fen.rsplit(" ", 2)[0] + " test", side_to_move="w", phase=phase)
        .returning(positions.c.id)
    ).scalar_one()
    conn.execute(
        insert(position_sources).values(
            position_id=pid,
            source=source,
            source_ref=ref,
            fullmove_number=30,
            moves_to_position=["e4"],
            puzzle_themes=["endgame", "fork"] if source == "puzzle" else None,
        )
    )
    return pid


def phase_of(conn, pid):
    return conn.execute(select(positions.c.phase).where(positions.c.id == pid)).scalar_one()


def test_relabel_applies_the_current_rule_and_is_idempotent(conn):
    # Rows inserted with deliberately wrong phases, so the relabeller has to fix them.
    rbn = add(conn, RBN, "middlegame", "puzzle", "test-rbn")
    named = add(conn, FULL, "middlegame", "opening", "test-full")
    # Same full army at move 30 from a puzzle only: no named line, so middlegame.
    unnamed = add(conn, FULL.replace("w KQkq", "b KQkq"), "opening", "puzzle", "test-unnamed")

    changes = relabel(conn)
    assert changes[("middlegame", "endgame")] >= 1
    assert changes[("middlegame", "opening")] >= 1
    assert changes[("opening", "middlegame")] >= 1
    assert phase_of(conn, rbn) == "endgame"
    assert phase_of(conn, named) == "opening"
    assert phase_of(conn, unnamed) == "middlegame"
    assert relabel(conn) == {}  # second run changes nothing

    table = puzzle_phase_comparison(conn)
    assert table.loc["endgame", "endgame"] >= 1


def test_old_rule_is_the_new_rule_with_the_no_queen_limit_at_2(conn):
    """Rollback path: setting the no-queen limit to 2 gives back the 2-piece rule exactly."""
    old = replace(PhaseSettings.from_config(), endgame_max_pieces_per_side_without_queen=2)
    rbn = add(conn, RBN, "endgame", "puzzle", "test-rbn-old")
    relabel(conn, old)
    assert phase_of(conn, rbn) == "middlegame"
