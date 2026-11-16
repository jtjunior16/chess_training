"""The game, played from the position bank (position pipeline step 6, move acceptance §8).

Every score comes from `position_moves`, so no engine runs while the player plays (pipeline
spec §6): the verdict and the arrows always agree with the stored acceptable set.

- `playable_ids()` / `pick_position_id()`: which bank positions can be served, and the next one.
  A position is playable when it has stored scores for the current engine version. That leaves
  out the 2 boards with no legal moves (the checkmates ending "Fool's Mate" and "Sea-Cadet
  Mate"), which analysis skips; the positions one move earlier, with the mate to find, stay in.
- `position_payload()`: what the page shows before the move.
- `move_result()`: what the page shows after it (§8): the verdict, the count line, arrows for at
  most `max_arrows` acceptable moves, the whole set for "show all", and in only-move positions
  the 2nd-best move with what it loses.

PLACEHOLDERS (open in the design chat, STATUS.md P4; config.yaml `game:`):
- choosing the next position: uniformly random over every playable position;
- what the page says about a position: phase and opening name only (puzzle themes stay hidden,
  they would give the answer away);
- promotion: always to a queen (in app.py).
"""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass

import chess
from sqlalchemy import Connection, select

from chess_training.acceptance import Acceptance, ScoredMove, judge
from chess_training.config import load_config
from chess_training.db import position_moves, positions

POSITION_CHOICES = ("random",)


@dataclass(frozen=True)
class GameSettings:
    position_choice: str
    max_arrows: int

    @classmethod
    def from_config(cls, section: dict | None = None) -> GameSettings:
        s = section if section is not None else load_config()["game"]
        choice = str(s["position_choice"])
        if choice not in POSITION_CHOICES:
            raise ValueError(f"game.position_choice must be one of {POSITION_CHOICES}: {choice}")
        return cls(position_choice=choice, max_arrows=int(s["max_arrows"]))


# ---------------------------------------------------------------- choosing a position


def playable_ids(conn: Connection, engine_version: str) -> list[int]:
    """Ids of bank positions with stored scores for `engine_version`, in id order."""
    return list(
        conn.execute(
            select(position_moves.c.position_id)
            .where(position_moves.c.engine_version == engine_version)
            .distinct()
            .order_by(position_moves.c.position_id)
        ).scalars()
    )


def pick_position_id(ids: list[int], settings: GameSettings, rng: random.Random) -> int:
    """The next position. Placeholder rule: uniformly random (STATUS.md P4)."""
    if not ids:
        raise LookupError("No playable positions: run the analysis first")
    return rng.choice(ids)


def is_playable(conn: Connection, position_id: int, engine_version: str) -> bool:
    return (
        conn.execute(
            select(position_moves.c.position_id)
            .where(
                position_moves.c.position_id == position_id,
                position_moves.c.engine_version == engine_version,
            )
            .limit(1)
        ).first()
        is not None
    )


# ---------------------------------------------------------------- before the move


def legal_dests(board: chess.Board) -> dict[str, list[str]]:
    """Legal moves as {from_square: [to_squares]}, the shape chessground expects."""
    dests: dict[str, list[str]] = {}
    for m in board.legal_moves:
        to = dests.setdefault(chess.square_name(m.from_square), [])
        if chess.square_name(m.to_square) not in to:
            to.append(chess.square_name(m.to_square))
    return dests


def load_position(conn: Connection, position_id: int):
    """The position's row (id, fen, phase, opening_name), or None."""
    return conn.execute(
        select(positions.c.id, positions.c.fen, positions.c.phase, positions.c.opening_name).where(
            positions.c.id == position_id
        )
    ).first()


def position_payload(row) -> dict:
    board = chess.Board(row.fen)
    return {
        "id": row.id,
        "fen": row.fen,
        "turn": "white" if board.turn == chess.WHITE else "black",
        "phase": row.phase,
        "opening": row.opening_name,  # None for puzzles
        "dests": legal_dests(board),
    }


# ---------------------------------------------------------------- after the move


def _move(m: ScoredMove) -> dict:
    return {"uci": m.uci, "san": m.san, "score_cp": m.score_cp, "score_mate": m.score_mate}


def count_text(size: int) -> str:
    return f"{size} move{'' if size == 1 else 's'} {'was' if size == 1 else 'were'} acceptable here"


def move_result(acc: Acceptance, uci: str, settings: GameSettings) -> dict:
    """What the page shows after the player's move (move acceptance §8)."""
    verdict = judge(acc, uci)
    player = next(m for m in acc.ranked if m.uci == verdict.uci)
    second = None
    if acc.only_move and len(acc.ranked) > 1:
        s = acc.ranked[1]
        loss = max(0.0, acc.best.win - s.win)
        # As in the verdict: when the best move mates and this one doesn't, win % can't show
        # the loss (a +8 move is about 95 win-%), so say what happened.
        misses_mate = acc.forced_mate and not s.forces_mate
        second = {
            **_move(s),
            "win_loss": loss,
            "label": f"{s.san}: misses the mate" if misses_mate else f"{s.san}: −{loss:.1f} win-%",
        }
    return {
        "verdict": {**asdict(verdict), "text": verdict.text()},
        "player": _move(player),
        "count_text": count_text(acc.size),
        "arrows": [_move(m) for m in acc.acceptable[: settings.max_arrows]],
        "acceptable": [_move(m) for m in acc.acceptable],  # for the "show all" toggle
        "second_best": second,  # only in only-move positions
    }
