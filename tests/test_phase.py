"""Phase labeller (specs/position_pipeline_spec.md §3)."""

from __future__ import annotations

from dataclasses import replace

import chess
import pytest

from chess_training.phase import PhaseSettings, label_phase, side_material

FULL = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 {move}"


def board(fen: str) -> chess.Board:
    return chess.Board(fen)


def test_settings_come_from_config_yaml():
    s = PhaseSettings.from_config()
    assert s.endgame_max_pieces_per_side == 2
    assert s.endgame_max_points_per_side == 8
    assert s.endgame_max_pieces_per_side_without_queen == 3
    assert s.opening_before_move == 12
    assert s.piece_values == {chess.QUEEN: 9, chess.ROOK: 5, chess.BISHOP: 3, chess.KNIGHT: 3}


@pytest.mark.parametrize(
    "fen, named, expected",
    [
        # Openings
        (chess.STARTING_FEN, False, "opening"),
        (FULL.format(move=11), False, "opening"),
        (FULL.format(move=15), True, "opening"),  # from a named line, any move number
        # Middlegames
        (FULL.format(move=12), False, "middlegame"),
        ("r2qkb2/pppp4/8/8/8/8/PPPP4/R2QKB2 w - - 0 30", False, "middlegame"),  # Q+R+B each
        ("r2qkb2/pppp4/8/8/8/8/PPPP4/R2QKN2 w - - 0 30", False, "middlegame"),  # Q+R+B v Q+R+N
        ("r3kbn1/pppp4/8/8/8/8/PPPP4/R2QKN2 w - - 0 30", False, "middlegame"),  # Q+R+N v R+B+N
        ("rr2kbn1/pppp4/8/8/8/8/PPPP4/RR2KBN1 w - - 0 30", False, "middlegame"),  # 4 v 4, no Q
        # Endgames by piece count (points over 8)
        ("3qk3/pppp4/8/8/8/8/PPPP4/3QK3 w - - 0 30", False, "endgame"),  # Q v Q
        ("r3k2r/pppp4/8/8/8/8/PPPP4/R3K2R w - - 0 30", False, "endgame"),  # R+R v R+R
        ("r2qk3/pppp4/8/8/8/8/PPPP4/R2QK3 w - - 0 30", False, "endgame"),  # Q+R v Q+R
        # Endgames by the no-queen limit (3 pieces, decided 2026-11-11), checked per side
        ("r3kbn1/pppp4/8/8/8/8/PPPP4/R3KBN1 w - - 0 30", False, "endgame"),  # R+B+N v R+B+N
        ("r3k3/pppp4/8/8/8/8/PPPP4/R3KBN1 w - - 0 30", False, "endgame"),  # R+B+N v R
        ("r3kbn1/pppp4/8/8/8/8/PPPP4/R2QK3 w - - 0 30", False, "endgame"),  # Q+R v R+B+N
        # Endgame by points
        ("r3kn2/pppp4/8/8/8/8/PPPP4/R3KB2 w - - 0 30", False, "endgame"),  # R+B v R+N
        # Endgame beats opening, even inside a named line
        ("r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 10", True, "endgame"),
        # Kings and pawns never count
        ("4k3/pppppppp/8/8/8/8/PPPPPPPP/4K3 w - - 0 5", False, "endgame"),
    ],
)
def test_label_phase(fen, named, expected):
    assert label_phase(board(fen), from_named_line=named) == expected


def test_side_material_counts_pieces_and_points():
    b = board("r2qkb2/pppp4/8/8/8/8/PPPP4/R3KBN1 w - - 0 30")
    s = PhaseSettings.from_config()
    assert side_material(b, chess.WHITE, s) == (3, 11)  # R+B+N
    assert side_material(b, chess.BLACK, s) == (3, 17)  # R+Q+B


def test_points_test_still_counts_when_piece_limit_is_lowered():
    s = replace(
        PhaseSettings.from_config(),
        endgame_max_pieces_per_side=1,
        endgame_max_pieces_per_side_without_queen=1,
    )
    rooks = board("r3k2r/pppp4/8/8/8/8/PPPP4/R3K2R w - - 0 30")
    rook_minor = board("r3kn2/pppp4/8/8/8/8/PPPP4/R3KB2 w - - 0 30")
    assert label_phase(rooks, settings=s) == "middlegame"  # 2 pieces, 10 points
    assert label_phase(rook_minor, settings=s) == "endgame"  # 2 pieces, 8 points


def test_opening_move_limit_is_configurable():
    s = replace(PhaseSettings.from_config(), opening_before_move=20)
    assert label_phase(board(FULL.format(move=15)), settings=s) == "opening"
