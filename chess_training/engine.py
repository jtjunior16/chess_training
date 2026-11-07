"""Stockfish wrapper: top moves for a position, and the score of a specific move.

Scores are always from the point of view of the side to move in the position being analysed,
in centipawns (100 = one pawn). Mates are reported separately and converted to a large
centipawn value only when we need to subtract scores.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass

import chess
import chess.engine

from chess_training.config import engine_path, load_config

MATE_CP = 10_000  # centipawn stand-in for "mate" when computing differences


@dataclass(frozen=True)
class Score:
    cp: int | None  # centipawns, None when this is a forced mate
    mate: int | None  # moves to mate (+ = side to move mates, - = gets mated)

    @classmethod
    def from_pov(cls, pov: chess.engine.PovScore, turn: chess.Color) -> Score:
        s = pov.pov(turn)
        return cls(cp=s.score(), mate=s.mate())

    def as_cp(self) -> int:
        """Comparable number: mates become ±MATE_CP (sooner mates rank higher)."""
        if self.mate is None:
            return self.cp
        sign = 1 if self.mate > 0 else -1
        return sign * (MATE_CP - abs(self.mate))

    def to_dict(self) -> dict:
        return {"cp": self.cp, "mate": self.mate}


@dataclass(frozen=True)
class Line:
    move: chess.Move
    san: str
    score: Score
    pv_san: list[str]

    def to_dict(self) -> dict:
        return {
            "uci": self.move.uci(),
            "san": self.san,
            "score": self.score.to_dict(),
            "pv": self.pv_san,
        }


def _pv_to_san(board: chess.Board, pv: list[chess.Move], max_len: int = 6) -> list[str]:
    b = board.copy()
    out = []
    for m in pv[:max_len]:
        out.append(b.san(m))
        b.push(m)
    return out


class Engine:
    """One long-lived Stockfish process. Calls are serialised with a lock."""

    def __init__(self) -> None:
        cfg = load_config()["engine"]
        path = engine_path()
        if not path.exists():
            raise FileNotFoundError(
                f"Stockfish not found at {path}. Run: uv run python scripts/get_stockfish.py"
            )
        self._limit = chess.engine.Limit(depth=cfg["depth"])
        self._multipv = cfg["multipv"]
        self._lock = threading.Lock()
        self._engine = chess.engine.SimpleEngine.popen_uci(str(path))
        self._engine.configure({"Threads": cfg["threads"], "Hash": cfg["hash_mb"]})

    def top_moves(self, board: chess.Board, n: int | None = None) -> list[Line]:
        """The engine's best `n` moves (default: engine.multipv from config.yaml)."""
        n = n or self._multipv
        with self._lock:
            infos = self._engine.analyse(board, self._limit, multipv=n)
        lines = []
        for info in infos:
            pv = info.get("pv") or []
            if not pv:
                continue
            lines.append(
                Line(
                    move=pv[0],
                    san=board.san(pv[0]),
                    score=Score.from_pov(info["score"], board.turn),
                    pv_san=_pv_to_san(board, pv),
                )
            )
        return lines

    def score_move(self, board: chess.Board, move: chess.Move) -> Line:
        """Score one specific move by restricting the search to it."""
        with self._lock:
            info = self._engine.analyse(board, self._limit, root_moves=[move])
        pv = info.get("pv") or [move]
        return Line(
            move=move,
            san=board.san(move),
            score=Score.from_pov(info["score"], board.turn),
            pv_san=_pv_to_san(board, pv),
        )

    def close(self) -> None:
        with self._lock:
            self._engine.quit()
