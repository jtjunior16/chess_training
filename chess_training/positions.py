"""A few hand-picked sample positions until the Postgres position bank exists.

Each one is built from a move list (not a hand-typed FEN) so typos can't produce
an impossible position.
"""

from __future__ import annotations

from dataclasses import dataclass

import chess


@dataclass(frozen=True)
class SamplePosition:
    id: str
    description: str
    phase: str  # opening | middlegame | endgame (hand-labelled for now)
    opening: str | None
    fen: str


def _from_moves(san_moves: str, start_fen: str = chess.STARTING_FEN) -> str:
    board = chess.Board(start_fen)
    for san in san_moves.split():
        board.push_san(san)
    return board.fen()


SAMPLES: list[SamplePosition] = [
    SamplePosition(
        id="caro-kann-advance",
        description="Black to move after 3.e5. Several good moves exist.",
        phase="opening",
        opening="Caro-Kann Defense: Advance Variation",
        fen=_from_moves("e4 c6 d4 d5 e5"),
    ),
    SamplePosition(
        id="blackburne-shilling-trap",
        description="White just took on f7. Black has one move that wins.",
        phase="opening",
        opening="Italian Game: Blackburne Shilling Gambit",
        fen=_from_moves("e4 e5 Nf3 Nc6 Bc4 Nd4 Nxe5 Qg5 Nxf7"),
    ),
    SamplePosition(
        id="qgd-tartakower-quiet",
        description="A quiet middlegame with symmetrical pawns. No tactics.",
        phase="middlegame",
        opening="Queen's Gambit Declined: Tartakower Defense",
        fen=_from_moves(
            "d4 d5 c4 e6 Nc3 Nf6 Bg5 Be7 e3 O-O Nf3 h6 Bh4 b6 cxd5 Nxd5 Bxe7 Qxe7 Nxd5 exd5"
        ),
    ),
    SamplePosition(
        id="back-rank-mate",
        description="White to move and mate in one.",
        phase="endgame",
        opening=None,
        fen="6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1",
    ),
]

BY_ID = {p.id: p for p in SAMPLES}
