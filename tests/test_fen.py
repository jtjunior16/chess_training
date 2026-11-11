"""fen_key (specs/position_pipeline_spec.md §2)."""

from __future__ import annotations

import chess

from chess_training.fen import fen_key


def play(*sans: str) -> chess.Board:
    board = chess.Board()
    for san in sans:
        board.push_san(san)
    return board


def test_drops_move_counters():
    assert fen_key(play("e4")) == "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq -"


def test_same_board_same_key_whatever_the_move_count():
    # Knights out and back: same board as after 1.e4 e5, but later move counters.
    a = play("e4", "e5")
    b = play("e4", "e5", "Nf3", "Nf6", "Ng1", "Ng8")
    assert a.fen() != b.fen()
    assert fen_key(a) == fen_key(b)


def test_en_passant_square_only_when_the_capture_is_legal():
    # 1.e4: no black pawn can take on e3, so no en passant square.
    assert fen_key(play("e4")).endswith(" -")
    # 1.e4 Nf6 2.e5 d5: exd6 e.p. is legal, so d6 is kept.
    assert fen_key(play("e4", "Nf6", "e5", "d5")).endswith(" d6")
