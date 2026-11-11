"""Phase labeller: opening / middlegame / endgame (specs/position_pipeline_spec.md §3).

One rule for every source, checked in this order:
1. Endgame: every side passes at least one of these tests (checked per side):
   - at most `endgame_max_pieces_per_side` pieces;
   - at most `endgame_max_points_per_side` points of them;
   - no queen and at most `endgame_max_pieces_per_side_without_queen` pieces (decided
     2026-11-11: e.g. R+B+N without a queen is endgame material).
   Pieces are queens, rooks, bishops and knights; kings and pawns never count. Endgame is
   checked first, so it beats opening.
2. Opening: the position comes from a named opening line, or its move number is below
   `opening_before_move`.
3. Middlegame: everything else.

All numbers come from the `phase:` section of config.yaml.
"""

from __future__ import annotations

from dataclasses import dataclass

import chess

from chess_training.config import load_config

PIECE_NAMES = {
    chess.QUEEN: "queen",
    chess.ROOK: "rook",
    chess.BISHOP: "bishop",
    chess.KNIGHT: "knight",
}


@dataclass(frozen=True)
class PhaseSettings:
    opening_before_move: int
    endgame_max_pieces_per_side: int
    endgame_max_points_per_side: int
    endgame_max_pieces_per_side_without_queen: int
    piece_values: dict[int, int]  # python-chess piece type -> points

    @classmethod
    def from_config(cls, section: dict | None = None) -> PhaseSettings:
        s = section if section is not None else load_config()["phase"]
        values = s["piece_values"]
        return cls(
            opening_before_move=int(s["opening_before_move"]),
            endgame_max_pieces_per_side=int(s["endgame_max_pieces_per_side"]),
            endgame_max_points_per_side=int(s["endgame_max_points_per_side"]),
            endgame_max_pieces_per_side_without_queen=int(
                s["endgame_max_pieces_per_side_without_queen"]
            ),
            piece_values={pt: int(values[name]) for pt, name in PIECE_NAMES.items()},
        )


def side_material(
    board: chess.Board, color: chess.Color, settings: PhaseSettings
) -> tuple[int, int]:
    """(number of pieces, points) for one side, counting queens, rooks, bishops and knights."""
    pieces = points = 0
    for piece_type, value in settings.piece_values.items():
        n = len(board.pieces(piece_type, color))
        pieces += n
        points += n * value
    return pieces, points


def side_is_endgame_material(
    board: chess.Board, color: chess.Color, settings: PhaseSettings
) -> bool:
    pieces, points = side_material(board, color, settings)
    no_queen = not board.pieces(chess.QUEEN, color)
    return (
        pieces <= settings.endgame_max_pieces_per_side
        or points <= settings.endgame_max_points_per_side
        or (no_queen and pieces <= settings.endgame_max_pieces_per_side_without_queen)
    )


def is_endgame(board: chess.Board, settings: PhaseSettings) -> bool:
    return all(side_is_endgame_material(board, c, settings) for c in (chess.WHITE, chess.BLACK))


def label_phase(
    board: chess.Board,
    *,
    from_named_line: bool = False,
    settings: PhaseSettings | None = None,
) -> str:
    """Label a position "opening", "middlegame" or "endgame".

    `from_named_line`: True if any source of this position is a named opening line.
    """
    settings = settings or PhaseSettings.from_config()
    if is_endgame(board, settings):
        return "endgame"
    if from_named_line or board.fullmove_number < settings.opening_before_move:
        return "opening"
    return "middlegame"
