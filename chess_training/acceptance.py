"""Move acceptance: which moves are "OK" in a position (specs/move_acceptance_spec.md).

Everything here works from stored scores (`position_moves`) and never runs the engine, so
changing G or L only means recomputing (spec §5).

The rule (§2): sort the moves by win %, best first. The best move is always acceptable. Walk
down the list; a move is acceptable while it is at most G below the move above it (no break)
and at most L below the best move (cap). Stop at the first move that fails either test.

Forced mates (§7): if the best move forces mate, the acceptable set is exactly the moves that
also force mate, at any length. G and L don't apply.

G and L are placeholders in config.yaml (`move_acceptance:`) until tuned from the §6 report.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import Connection, select

from chess_training.config import load_config
from chess_training.db import position_moves
from chess_training.winpct import win_pct


@dataclass(frozen=True)
class AcceptanceSettings:
    G: float
    L: float

    @classmethod
    def from_config(cls, section: dict | None = None) -> AcceptanceSettings:
        s = section if section is not None else load_config()["move_acceptance"]
        return cls(G=float(s["G"]), L=float(s["L"]))


@dataclass(frozen=True)
class ScoredMove:
    uci: str
    san: str
    score_cp: int | None
    score_mate: int | None

    @property
    def win(self) -> float:
        return win_pct(self.score_cp, self.score_mate)

    @property
    def forces_mate(self) -> bool:
        return self.score_mate is not None and self.score_mate > 0

    def strength(self) -> tuple:
        """Sort key, higher = better: forced mates first (sooner first), then by centipawns,
        then being mated (later first). Ties are broken by UCI so the order is stable."""
        if self.forces_mate:
            return (2, -self.score_mate)
        if self.score_mate is not None:  # gets mated (mate <= 0)
            return (0, -self.score_mate)
        return (1, self.score_cp)


@dataclass(frozen=True)
class Acceptance:
    """The ranked moves of one position and its acceptable set."""

    ranked: tuple[ScoredMove, ...]  # every legal move, best first
    size: int  # how many of `ranked` (from the top) are acceptable
    forced_mate: bool  # the best move forces mate (§7 applied)

    @property
    def acceptable(self) -> tuple[ScoredMove, ...]:
        return self.ranked[: self.size]

    @property
    def only_move(self) -> bool:
        return self.size == 1

    @property
    def best(self) -> ScoredMove:
        return self.ranked[0]


def rank(moves: Iterable[ScoredMove]) -> tuple[ScoredMove, ...]:
    moves = list(moves)
    moves.sort(key=lambda m: m.uci)
    moves.sort(key=lambda m: m.strength(), reverse=True)
    return tuple(moves)


def acceptable_set(moves: Iterable[ScoredMove], settings: AcceptanceSettings) -> Acceptance:
    ranked = rank(moves)
    if not ranked:
        raise ValueError("A position with no scored moves has no acceptable set")
    if ranked[0].forces_mate:  # §7: exactly the mating moves, at any length
        size = sum(1 for m in ranked if m.forces_mate)
        return Acceptance(ranked, size, forced_mate=True)
    wins = [m.win for m in ranked]
    size = 1
    for i in range(1, len(ranked)):
        if wins[i - 1] - wins[i] > settings.G or wins[0] - wins[i] > settings.L:
            break
        size += 1
    return Acceptance(ranked, size, forced_mate=False)


@dataclass(frozen=True)
class Verdict:
    """What the game tells the player about one move (spec §4, §8)."""

    uci: str
    san: str
    acceptable: bool
    rank: int  # 1 = best, among all legal moves
    acceptable_count: int  # size of the acceptable set
    legal_count: int
    win_loss: float  # win-% points below the best move (0 for the best move)
    only_move: bool  # the position is an only-move position
    forced_mate: bool  # the best move forces mate

    def text(self) -> str:
        """e.g. "Acceptable (7th of 12)", "Not acceptable (lost 9 win-%)", or, when the best
        move mates and this one doesn't, "Not acceptable (misses the mate)"."""
        if self.acceptable:
            return f"Acceptable ({_ordinal(self.rank)} of {self.acceptable_count})"
        if self.forced_mate:
            # Win % can't express this (a +25 move is about 100 win-% too): say what happened.
            return "Not acceptable (misses the mate)"
        return f"Not acceptable (lost {self.win_loss:.0f} win-%)"


def _ordinal(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def judge(acceptance: Acceptance, uci: str) -> Verdict:
    """The verdict on the move `uci`. Normal mode and challenge mode both use this."""
    for i, m in enumerate(acceptance.ranked):
        if m.uci == uci:
            return Verdict(
                uci=m.uci,
                san=m.san,
                acceptable=i < acceptance.size,
                rank=i + 1,
                acceptable_count=acceptance.size,
                legal_count=len(acceptance.ranked),
                win_loss=max(0.0, acceptance.best.win - m.win),
                only_move=acceptance.only_move,
                forced_mate=acceptance.forced_mate,
            )
    raise ValueError(f"{uci} is not a scored move in this position")


def load_moves(conn: Connection, position_id: int, engine_version: str) -> list[ScoredMove]:
    rows = conn.execute(
        select(
            position_moves.c.uci,
            position_moves.c.san,
            position_moves.c.score_cp,
            position_moves.c.score_mate,
        ).where(
            position_moves.c.position_id == position_id,
            position_moves.c.engine_version == engine_version,
        )
    ).all()
    return [ScoredMove(*r) for r in rows]


def for_position(
    conn: Connection,
    position_id: int,
    settings: AcceptanceSettings | None = None,
    engine_version: str | None = None,
) -> Acceptance:
    """The acceptable set of a bank position, from its stored scores."""
    settings = settings or AcceptanceSettings.from_config()
    engine_version = engine_version or load_config()["engine"]["version"]
    return acceptable_set(load_moves(conn, position_id, engine_version), settings)
