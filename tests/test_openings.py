"""Opening importer (specs/position_pipeline_spec.md §4), on small hand-made TSV rows."""

from __future__ import annotations

import chess
import pytest
from sqlalchemy import select

from chess_training.db import position_sources, positions
from chess_training.fen import fen_key
from chess_training.openings import build_import, movetext, parse_line, write_import

CARO_KANN = [
    ("B00", "King's Pawn Game", "1. e4"),
    ("B10", "Caro-Kann Defense", "1. e4 c6"),
    ("B12", "Caro-Kann Defense: Advance Variation", "1. e4 c6 2. d4 d5 3. e5"),
    (
        "B12",
        "Caro-Kann Defense: Advance Variation, Short Variation",
        "1. e4 c6 2. d4 d5 3. e5 Bf5 4. Nf3 e6 5. Be2",
    ),
]


def key_after(*sans: str) -> str:
    board = chess.Board()
    for san in sans:
        board.push_san(san)
    return fen_key(board)


def build(rows, max_fullmove=10):
    return build_import(rows, max_fullmove=max_fullmove)


def test_movetext_round_trips_with_parse_line():
    line = parse_line("B12", "x", "1. e4 c6 2. d4 d5 3. e5")
    assert movetext(line.sans) == "1. e4 c6 2. d4 d5 3. e5"


def test_parse_line_rejects_illegal_moves():
    with pytest.raises(ValueError):
        parse_line("A00", "Broken", "1. e5")


def test_every_half_move_is_a_position_and_the_start_is_skipped():
    data = build(CARO_KANN)
    assert len(data.sources) == 9  # the longest line has 9 half-moves; the others share them
    assert fen_key(chess.Board()) not in data.positions
    sides = {p.side_to_move for p in data.positions.values()}
    assert sides == {"w", "b"}


def test_named_by_what_has_happened_not_by_longer_lines_through_it():
    data = build(CARO_KANN)
    assert data.positions[key_after("e4", "c6")].opening_name == "Caro-Kann Defense"
    # 2.d4 and 2...d5 have no line of their own: they keep the nearest named ancestor's name.
    assert data.positions[key_after("e4", "c6", "d4", "d5")].opening_name == "Caro-Kann Defense"
    advance = data.positions[key_after("e4", "c6", "d4", "d5", "e5")]
    assert advance.opening_name == "Caro-Kann Defense: Advance Variation"


def test_eco_follows_the_naming_line():
    data = build(CARO_KANN)
    assert data.sources["1. e4 c6"].opening_eco == "B10"
    assert data.sources["1. e4 c6 2. d4"].opening_eco == "B10"  # nearest named ancestor
    assert data.sources["1. e4 c6 2. d4 d5 3. e5"].opening_eco == "B12"  # exact match


def test_transposition_counts_as_an_exact_match():
    rows = [
        ("A00", "Line A", "1. Nf3 Nf6 2. d4"),
        ("A00", "Line B parent", "1. d4"),
        ("A00", "Line B", "1. d4 Nf6 2. Nf3 e6"),
    ]
    data = build(rows)
    # 1.d4 Nf6 2.Nf3 reaches Line A's end position by another move order.
    src = data.sources["1. d4 Nf6 2. Nf3"]
    assert src.fen_key == key_after("Nf3", "Nf6", "d4")
    assert src.opening_eco == "A00"
    assert data.positions[src.fen_key].opening_name == "Line A"
    # Two move orders, one position, two source rows.
    assert data.sources["1. Nf3 Nf6 2. d4"].fen_key == src.fen_key


def test_several_names_primary_is_the_longest_and_all_are_listed():
    rows = [
        ("C40", "Short name", "1. e4 e5 2. Nf3"),
        ("C44", "Longer name", "1. Nf3 Nf6 2. e4 Ng8 3. Nc3 e5 4. Nb1"),
    ]
    data = build(rows)
    pos = data.positions[key_after("e4", "e5", "Nf3")]
    assert pos.opening_name == "Longer name"
    assert pos.opening_names == ["Longer name", "Short name"]


def test_different_named_ancestors_are_all_listed():
    rows = [
        ("C00", "Parent one", "1. e4 e6"),
        ("D00", "Parent two", "1. d4 e6"),
        ("C01", "Child one", "1. e4 e6 2. d4 d5"),
        ("D01", "Child two", "1. d4 e6 2. e4 d5"),
    ]
    # Both children end on the same position, so it's an exact match for both.
    data = build(rows)
    pos = data.positions[key_after("e4", "e6", "d4", "d5")]
    assert pos.opening_names == ["Child one", "Child two"]
    assert pos.opening_name == "Child one"  # same length: alphabetical
    # 2.d4 / 2.e4 (no line of their own) reach the same position from different named parents.
    mid = data.positions[key_after("e4", "e6", "d4")]
    assert mid.opening_names == ["Parent one", "Parent two"]


def test_stops_after_black_s_last_allowed_move():
    data = build(CARO_KANN, max_fullmove=2)
    assert max(len(s.moves_to_position) for s in data.sources.values()) == 4
    assert "1. e4 c6 2. d4 d5" in data.sources
    assert "1. e4 c6 2. d4 d5 3. e5" not in data.sources


def test_source_row_details():
    data = build(CARO_KANN)
    src = data.sources["1. e4 c6 2. d4 d5 3. e5"]
    assert src.moves_to_position == ["e4", "c6", "d4", "d5", "e5"]
    assert src.fullmove_number == 3
    assert data.positions[src.fen_key].phase == "opening"


def snapshot(conn, keys):
    pos = conn.execute(
        select(
            positions.c.fen_key,
            positions.c.fen,
            positions.c.phase,
            positions.c.opening_name,
            positions.c.opening_names,
        )
        .where(positions.c.fen_key.in_(keys))
        .order_by(positions.c.fen_key)
    ).all()
    src = conn.execute(
        select(
            position_sources.c.source_ref,
            position_sources.c.position_id,
            position_sources.c.fullmove_number,
            position_sources.c.moves_to_position,
            position_sources.c.opening_eco,
        )
        .join(positions, positions.c.id == position_sources.c.position_id)
        .where(positions.c.fen_key.in_(keys), position_sources.c.source == "opening")
        .order_by(position_sources.c.source_ref)
    ).all()
    return pos, src


def test_writing_twice_changes_nothing(conn):
    data = build(CARO_KANN)
    keys = list(data.positions)
    assert write_import(conn, data) == {"positions": 9, "sources": 9}
    first = snapshot(conn, keys)
    write_import(conn, data)
    assert snapshot(conn, keys) == first
    pos, src = first
    assert len(pos) == 9
    assert {r.source_ref for r in src} >= set(data.sources)


def test_existing_position_keeps_its_first_seen_fen(conn):
    data = build(CARO_KANN)
    write_import(conn, data)
    key = key_after("e4", "c6")
    first_fen = data.positions[key].fen
    data.positions[key].fen = key + " 0 99"  # same board reached later by another source
    write_import(conn, data)
    stored = conn.execute(select(positions.c.fen).where(positions.c.fen_key == key)).scalar_one()
    assert stored == first_fen
