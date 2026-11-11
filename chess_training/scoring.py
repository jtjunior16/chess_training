"""Scoring: the player's progress as accuracy % (specs/scoring_spec.md).

- `record_attempt()` judges a move against the position's acceptable set and stores it in
  `attempts` (§7): acceptable, close miss or blunder, with the win-% loss.
- `stats()` computes the figures (§1–§6):
  - accuracy as three shares (acceptable / close miss / blunder);
  - shown all-time and over the last `recent_window` attempts in each group;
  - groups below `min_attempts` show "not enough data yet";
  - broken down by phase, opening family, side, difficulty and puzzle theme;
  - the "only good move" claim as claim accuracy and spotting rate;
  - challenge-mode repeats are left out.
- `recompute_attempts()` re-judges stored attempts after G, L or blunder_line change (§7; the
  spec's placeholder answer is to recompute).

All numbers come from config.yaml (`scoring:`). Difficulty and only-move use each position's
acceptable set under the current G and L.

Usage: uv run --env-file .env python -m chess_training.scoring            # print the stats
       uv run --env-file .env python -m chess_training.scoring --recompute
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from sqlalchemy import Connection, insert, select, update

from chess_training.acceptance import (
    ACCEPTABLE,
    BLUNDER,
    CLOSE_MISS,
    Acceptance,
    AcceptanceSettings,
    acceptable_set,
    judge,
    load_moves,
    miss_kind,
)
from chess_training.config import load_config
from chess_training.db import attempts, get_engine, position_sources, positions

BREAKDOWNS = ("phase", "opening family", "side", "difficulty", "puzzle theme")
SIDE_NAMES = {"w": "White", "b": "Black"}
NOT_ENOUGH = "not enough data yet"


@dataclass(frozen=True)
class ScoringSettings:
    recent_window: int
    min_attempts: int
    blunder_line: float
    difficulty_buckets: tuple[int, ...]  # upper bounds, e.g. (1, 4) -> "1", "2-4", "5+"
    motif: frozenset[str]

    @classmethod
    def from_config(cls, cfg: dict | None = None) -> ScoringSettings:
        cfg = cfg if cfg is not None else load_config()
        s = cfg["scoring"]
        return cls(
            recent_window=int(s["recent_window"]),
            min_attempts=int(s["min_attempts"]),
            blunder_line=float(s["blunder_line"]),
            difficulty_buckets=tuple(int(b) for b in s["difficulty_buckets"]),
            motif=frozenset(cfg["puzzles"]["themes"]["motif"]),
        )

    def difficulty(self, size: int) -> str:
        lo = 1
        for hi in self.difficulty_buckets:
            if size <= hi:
                return str(hi) if lo == hi else f"{lo}-{hi}"
            lo = hi + 1
        return f"{lo}+"


def _settings(acc, sc):
    return acc or AcceptanceSettings.from_config(), sc or ScoringSettings.from_config()


def _acceptance(conn: Connection, position_id: int, acc: AcceptanceSettings, version: str):
    moves = load_moves(conn, position_id, version)
    if not moves:
        raise ValueError(f"Position {position_id} has no stored scores for {version}")
    return acceptable_set(moves, acc)


# ---------------------------------------------------------------- recording


@dataclass(frozen=True)
class AttemptResult:
    id: int
    kind: str  # acceptable / close miss / blunder
    verdict_text: str
    win_loss: float
    only_move: bool  # the position is an only-move position (the claim's right answer)
    claim_correct: bool | None  # None if the player didn't claim


def record_attempt(
    conn: Connection,
    position_id: int,
    uci: str,
    *,
    mode: str = "normal",
    challenge_repeat: bool = False,
    claimed_only_move: bool = False,
    acceptance_settings: AcceptanceSettings | None = None,
    scoring_settings: ScoringSettings | None = None,
    engine_version: str | None = None,
) -> AttemptResult:
    """Judge `uci` in a bank position and store the attempt (scoring §7)."""
    acc_s, sc_s = _settings(acceptance_settings, scoring_settings)
    version = engine_version or load_config()["engine"]["version"]
    acc = _acceptance(conn, position_id, acc_s, version)
    verdict = judge(acc, uci)
    kind = miss_kind(acc, uci, sc_s.blunder_line)
    side = conn.execute(
        select(positions.c.side_to_move).where(positions.c.id == position_id)
    ).scalar_one()
    aid = conn.execute(
        insert(attempts)
        .values(
            position_id=position_id,
            uci=verdict.uci,
            san=verdict.san,
            mode=mode,
            challenge_repeat=challenge_repeat,
            side=side,
            claimed_only_move=claimed_only_move,
            result=kind,
            win_loss=verdict.win_loss,
            engine_version=version,
        )
        .returning(attempts.c.id)
    ).scalar_one()
    return AttemptResult(
        id=aid,
        kind=kind,
        verdict_text=verdict.text(),
        win_loss=verdict.win_loss,
        only_move=acc.only_move,
        claim_correct=(claimed_only_move == acc.only_move) if claimed_only_move else None,
    )


def recompute_attempts(
    conn: Connection,
    acceptance_settings: AcceptanceSettings | None = None,
    scoring_settings: ScoringSettings | None = None,
    engine_version: str | None = None,
) -> int:
    """Re-judge every stored attempt with the current rule and scores. Returns rows changed."""
    acc_s, sc_s = _settings(acceptance_settings, scoring_settings)
    version = engine_version or load_config()["engine"]["version"]
    rows = conn.execute(
        select(
            attempts.c.id,
            attempts.c.position_id,
            attempts.c.uci,
            attempts.c.result,
            attempts.c.win_loss,
            attempts.c.engine_version,
        )
    ).all()
    cache: dict[int, Acceptance] = {}
    changed = 0
    for r in rows:
        if r.position_id not in cache:
            cache[r.position_id] = _acceptance(conn, r.position_id, acc_s, version)
        acc = cache[r.position_id]
        kind = miss_kind(acc, r.uci, sc_s.blunder_line)
        loss = judge(acc, r.uci).win_loss
        if (kind, round(loss, 6), version) != (r.result, round(r.win_loss, 6), r.engine_version):
            conn.execute(
                update(attempts)
                .where(attempts.c.id == r.id)
                .values(result=kind, win_loss=loss, engine_version=version)
            )
            changed += 1
    return changed


# ---------------------------------------------------------------- stats


@dataclass(frozen=True)
class Figures:
    """Accuracy and claim figures for one group over one window of attempts."""

    attempts: int
    acceptable: float | None  # shares in %, None when attempts < min_attempts
    close_miss: float | None
    blunder: float | None
    claims: int
    claim_accuracy: float | None  # correct claims / claims, None below min_attempts claims
    only_move_seen: int
    spotting_rate: float | None  # correct claims / only-move positions seen

    def to_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass(frozen=True)
class _Row:
    result: str
    claimed: bool
    only_move: bool
    groups: dict[str, tuple[str, ...]]  # breakdown -> the groups this attempt belongs to


def _pct(part: int, whole: int, enough: bool) -> float | None:
    return round(100 * part / whole, 1) if enough and whole else None


def figures(rows: list[_Row], min_attempts: int) -> Figures:
    n = len(rows)
    enough = n >= min_attempts
    counts = {k: sum(1 for r in rows if r.result == k) for k in (ACCEPTABLE, CLOSE_MISS, BLUNDER)}
    claims = [r for r in rows if r.claimed]
    only = [r for r in rows if r.only_move]
    correct = sum(1 for r in claims if r.only_move)
    return Figures(
        attempts=n,
        acceptable=_pct(counts[ACCEPTABLE], n, enough),
        close_miss=_pct(counts[CLOSE_MISS], n, enough),
        blunder=_pct(counts[BLUNDER], n, enough),
        claims=len(claims),
        claim_accuracy=_pct(correct, len(claims), len(claims) >= min_attempts),
        only_move_seen=len(only),
        spotting_rate=_pct(correct, len(only), len(only) >= min_attempts),
    )


def _group_figures(rows: list[_Row], settings: ScoringSettings) -> dict:
    return {
        "all_time": figures(rows, settings.min_attempts).to_dict(),
        "recent": figures(rows[-settings.recent_window :], settings.min_attempts).to_dict(),
    }


def load_rows(
    conn: Connection,
    acc_s: AcceptanceSettings,
    sc_s: ScoringSettings,
    engine_version: str,
) -> list[_Row]:
    """Counted attempts (challenge repeats left out, §5), oldest first, with their groups."""
    q = (
        select(
            attempts.c.position_id,
            attempts.c.result,
            attempts.c.claimed_only_move,
            attempts.c.side,
            positions.c.phase,
            positions.c.opening_name,
        )
        .join(positions, positions.c.id == attempts.c.position_id)
        .where(~attempts.c.challenge_repeat)
        .order_by(attempts.c.played_at, attempts.c.id)
    )
    raw = conn.execute(q).all()
    ids = sorted({r.position_id for r in raw})
    themes: dict[int, set[str]] = {pid: set() for pid in ids}
    if ids:
        for pid, tags in conn.execute(
            select(position_sources.c.position_id, position_sources.c.puzzle_themes).where(
                position_sources.c.position_id.in_(ids), position_sources.c.source == "puzzle"
            )
        ):
            themes[pid].update(t for t in (tags or []) if t in sc_s.motif)
    sizes = {pid: _acceptance(conn, pid, acc_s, engine_version).size for pid in ids}
    rows = []
    for r in raw:
        family = r.opening_name.split(":")[0].strip() if r.opening_name else None
        rows.append(
            _Row(
                result=r.result,
                claimed=r.claimed_only_move,
                only_move=sizes[r.position_id] == 1,
                groups={
                    "phase": (r.phase,),
                    "opening family": (family,) if family else (),
                    "side": (SIDE_NAMES[r.side],),
                    "difficulty": (sc_s.difficulty(sizes[r.position_id]),),
                    "puzzle theme": tuple(sorted(themes[r.position_id])),
                },
            )
        )
    return rows


def stats(
    conn: Connection,
    acceptance_settings: AcceptanceSettings | None = None,
    scoring_settings: ScoringSettings | None = None,
    engine_version: str | None = None,
) -> dict:
    """{"overall": {...}, "breakdowns": {breakdown: {group: {...}}}, "settings": {...}}.

    Each {...} holds "all_time" and "recent" Figures as dicts. A share is None when its group
    has fewer than min_attempts attempts (shown as "not enough data yet").
    """
    acc_s, sc_s = _settings(acceptance_settings, scoring_settings)
    version = engine_version or load_config()["engine"]["version"]
    rows = load_rows(conn, acc_s, sc_s, version)
    breakdowns: dict[str, dict] = {}
    for b in BREAKDOWNS:
        members: dict[str, list[_Row]] = {}
        for r in rows:
            for g in r.groups[b]:
                members.setdefault(g, []).append(r)
        breakdowns[b] = {g: _group_figures(rs, sc_s) for g, rs in sorted(members.items())}
    return {
        "overall": _group_figures(rows, sc_s),
        "breakdowns": breakdowns,
        "settings": {
            "G": acc_s.G,
            "L": acc_s.L,
            "blunder_line": sc_s.blunder_line,
            "recent_window": sc_s.recent_window,
            "min_attempts": sc_s.min_attempts,
        },
    }


# ---------------------------------------------------------------- text output


def _fmt(f: dict) -> str:
    if f["acceptable"] is None:
        acc = f"{NOT_ENOUGH} ({f['attempts']})"
    else:
        acc = (
            f"{f['acceptable']:.0f}% acceptable · {f['close_miss']:.0f}% close misses · "
            f"{f['blunder']:.0f}% blunders ({f['attempts']})"
        )
    claim = (
        "no claims yet"
        if f["claims"] == 0
        else (
            f"claims right {f['claim_accuracy']:.0f}%"
            if f["claim_accuracy"] is not None
            else f"claims: {NOT_ENOUGH}"
        )
    )
    spot = (
        f"spotted {f['spotting_rate']:.0f}%"
        if f["spotting_rate"] is not None
        else f"spotting: {NOT_ENOUGH}"
    )
    return f"{acc}; {claim}; {spot}"


def render(s: dict) -> str:
    st = s["settings"]
    lines = [
        f"Accuracy (G = {st['G']:g}, L = {st['L']:g}, blunder_line = {st['blunder_line']:g}; "
        f"recent = last {st['recent_window']} attempts; at least {st['min_attempts']} needed)",
        "",
        f"Overall, all-time: {_fmt(s['overall']['all_time'])}",
        f"Overall, recent:   {_fmt(s['overall']['recent'])}",
    ]
    for b, groups in s["breakdowns"].items():
        lines += ["", f"By {b}:"]
        if not groups:
            lines.append("  (no attempts yet)")
        for g, f in groups.items():
            lines.append(f"  {g}")
            lines.append(f"    all-time: {_fmt(f['all_time'])}")
            lines.append(f"    recent:   {_fmt(f['recent'])}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--recompute", action="store_true", help="re-judge stored attempts with the current rule"
    )
    args = parser.parse_args()
    db = get_engine()
    if args.recompute:
        with db.begin() as conn:
            print(f"Recomputed: {recompute_attempts(conn)} attempts changed.")
    with db.connect() as conn:
        print(render(stats(conn)))


if __name__ == "__main__":
    main()
