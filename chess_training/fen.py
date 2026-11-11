"""Position keys shared by every importer (specs/position_pipeline_spec.md §2)."""

from __future__ import annotations

import chess


def fen_key(board: chess.Board) -> str:
    """The FEN without the move counters, so the same board always gets the same key.

    The en passant square is kept only when an en passant capture is actually legal.
    """
    return board.fen(en_passant="legal").rsplit(" ", 2)[0]
