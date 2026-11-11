"""Tuning report for move acceptance (specs/move_acceptance_spec.md §6).

Computes the acceptable set of every fully scored bank position from the stored scores and
prints:
- the distribution of acceptable-set sizes, by phase and by source (opening / puzzle)
- the share of only-move positions, by phase and by source
- a few example positions per set size
- positions where the best move forces mate, and positions where every move gets mated
- how the non-acceptable moves split around `scoring.blunder_line` (scoring_spec §6)
- a small G/L grid: only-move share and median set size for nearby values, to help tuning

Usage: uv run --env-file .env python -m chess_training.acceptance_report [--examples 3]

Only positions with stored scores are included, so it can run while the analysis is going.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace

import chess
import pandas as pd
from sqlalchemy import Connection, select

from chess_training.acceptance import (
    Acceptance,
    AcceptanceSettings,
    ScoredMove,
    acceptable_set,
)
from chess_training.config import load_config
from chess_training.db import get_engine, position_moves, position_sources, positions

SIZE_BUCKETS = [(1, 1, "1"), (2, 2, "2"), (3, 4, "3-4"), (5, 9, "5-9"), (10, 10_000, "10+")]
GRID_G = (3, 4, 5, 6, 8)
GRID_L = (4, 6, 7.5)


@dataclass
class BankPosition:
    id: int
    fen: str
    phase: str
    source: str  # opening / puzzle / both
    label: str  # opening name or puzzle id, for examples
    moves: list[ScoredMove]


def load_bank(conn: Connection, engine_version: str) -> list[BankPosition]:
    rows = conn.execute(
        select(
            position_moves.c.position_id,
            position_moves.c.uci,
            position_moves.c.san,
            position_moves.c.score_cp,
            position_moves.c.score_mate,
        ).where(position_moves.c.engine_version == engine_version)
    ).all()
    moves: dict[int, list[ScoredMove]] = {}
    for pid, uci, san, cp, mate in rows:
        moves.setdefault(pid, []).append(ScoredMove(uci, san, cp, mate))
    if not moves:
        return []
    meta = conn.execute(
        select(
            positions.c.id,
            positions.c.fen,
            positions.c.phase,
            positions.c.opening_name,
            position_sources.c.source,
            position_sources.c.source_ref,
        )
        .join(position_sources, position_sources.c.position_id == positions.c.id)
        .where(positions.c.id.in_(list(moves)))
        .order_by(positions.c.id, position_sources.c.source, position_sources.c.source_ref)
    ).all()
    info: dict[int, dict] = {}
    for pid, fen, phase, name, source, ref in meta:
        d = info.setdefault(pid, {"fen": fen, "phase": phase, "sources": set(), "label": None})
        d["sources"].add(source)
        if d["label"] is None:
            d["label"] = name if source == "opening" and name else f"puzzle {ref}"
    bank = []
    for pid in sorted(moves):
        d = info[pid]
        source = d["sources"].pop() if len(d["sources"]) == 1 else "both"
        bank.append(BankPosition(pid, d["fen"], d["phase"], source, d["label"], moves[pid]))
    return bank


def bucket(size: int) -> str:
    return next(name for lo, hi, name in SIZE_BUCKETS if lo <= size <= hi)


def summarise(bank: list[BankPosition], settings: AcceptanceSettings, blunder_line: float):
    """One row per position, plus the non-acceptable move losses."""
    rows, losses = [], []
    results: dict[int, Acceptance] = {}
    for p in bank:
        acc = acceptable_set(p.moves, settings)
        results[p.id] = acc
        all_mated = all(m.score_mate is not None and m.score_mate <= 0 for m in acc.ranked)
        rows.append(
            {
                "id": p.id,
                "phase": p.phase,
                "source": p.source,
                "size": acc.size,
                "bucket": bucket(acc.size),
                "only_move": acc.only_move,
                "forced_mate": acc.forced_mate,
                "all_mated": all_mated,
            }
        )
        best = acc.best.win
        for m in acc.ranked[acc.size :]:
            loss = best - m.win
            losses.append(
                {
                    "phase": p.phase,
                    "kind": "close miss" if loss <= blunder_line else "blunder",
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(losses, columns=["phase", "kind"]), results


def _share_table(df: pd.DataFrame, by: str) -> str:
    order = [name for _, _, name in SIZE_BUCKETS]
    t = pd.crosstab(df[by], df["bucket"], normalize="index").reindex(columns=order, fill_value=0)
    t = (t * 100).round(0).astype(int).astype(str) + "%"
    t["positions"] = df.groupby(by).size()
    t["median size"] = df.groupby(by)["size"].median()
    return t.to_string()


def grid(bank: list[BankPosition], base: AcceptanceSettings, title: str = "all positions") -> str:
    if not bank:
        return f"G/L grid ({title}): no positions."
    lines = [f"only-move share / median set size, {title}, for G (rows) x L (columns):"]
    header = "  G\\L " + "".join(f"{lv:>14}" for lv in GRID_L)
    lines.append(header)
    for g in GRID_G:
        cells = []
        for lv in GRID_L:
            s = replace(base, G=float(g), L=float(lv))
            sizes = [acceptable_set(p.moves, s).size for p in bank]
            only = sum(1 for n in sizes if n == 1) / len(sizes) * 100
            median = pd.Series(sizes).median()
            cells.append(f"{only:6.0f}% / {median:>4.0f}")
        mark = "  <- current G" if g == base.G else ""
        lines.append(f"  {g:>3} " + "".join(f"{c:>14}" for c in cells) + mark)
    lines.append(f"  (current L = {base.L:g}; L must stay <= deep_margin / 2)")
    return "\n".join(lines)


def report(
    bank: list[BankPosition],
    settings: AcceptanceSettings,
    blunder_line: float,
    examples: int,
    total_positions: int,
) -> str:
    if not bank:
        return "No scored positions yet. Run: python -m chess_training.analysis"
    df, losses, results = summarise(bank, settings, blunder_line)
    by_id = {p.id: p for p in bank}
    lines = [
        f"Move acceptance tuning report: G = {settings.G:g}, L = {settings.L:g} (placeholders), "
        f"blunder_line = {blunder_line:g}",
        f"Positions with stored scores: {len(df):,} of {total_positions:,}"
        + ("" if len(df) == total_positions else " (analysis still running: partial data)"),
        "",
        "Acceptable-set size, share of positions, by phase:",
        _share_table(df, "phase"),
        "",
        "... by source:",
        _share_table(df, "source"),
        "",
        "Only-move positions (acceptable set of exactly 1):",
        f"  overall {df['only_move'].mean() * 100:.0f}%",
    ]
    for col in ("phase", "source"):
        shares = (df.groupby(col)["only_move"].mean() * 100).round(0).astype(int)
        lines.append(f"  by {col}: " + ", ".join(f"{k} {v}%" for k, v in shares.items()))

    fm, am = df[df["forced_mate"]], df[df["all_mated"]]
    lines += [
        "",
        f"Best move forces mate (sec. 7): {len(fm):,} positions "
        f"({', '.join(f'{k} {v}' for k, v in fm['source'].value_counts().items()) or 'none'}). "
        f"Of these, {int(fm['only_move'].sum()):,} have exactly one mating move.",
        f"Every move gets mated (losing side, all acceptable): {len(am):,} positions.",
    ]
    if not losses.empty:
        t = pd.crosstab(losses["phase"], losses["kind"], normalize="index")
        t = (t * 100).round(0).astype(int).astype(str) + "%"
        t["moves"] = losses.groupby("phase").size()
        lines += [
            "",
            f"Non-acceptable moves around blunder_line ({blunder_line:g} win-% below the best):",
            t.to_string(),
        ]

    lines += ["", f"Examples ({examples} per set size, lowest position ids):"]
    for _, _, name in SIZE_BUCKETS:
        ids = df.loc[df["bucket"] == name, "id"].head(examples).tolist()
        for pid in ids:
            p, acc = by_id[pid], results[pid]
            shown = ", ".join(m.san for m in acc.acceptable[:8])
            more = f" (+{acc.size - 8} more)" if acc.size > 8 else ""
            nxt = acc.ranked[acc.size] if acc.size < len(acc.ranked) else None
            after = (
                f"; next {nxt.san} -{acc.best.win - nxt.win:.1f} win-%" if nxt is not None else ""
            )
            lines.append(
                f"  [{name}] #{pid} {p.phase}, {p.label}: {shown}{more}{after}\n        {p.fen}"
            )

    # Puzzles are nearly all only-move positions whatever G and L are, so they swamp the
    # overall grid; the opening grid is the one that shows what G and L change.
    openings = [p for p in bank if p.source in ("opening", "both")]
    lines += ["", grid(bank, settings), "", grid(openings, settings, "opening positions only")]
    return "\n".join(lines)


def scorable_positions(conn: Connection) -> int:
    """Positions that can ever be scored (checkmate and stalemate positions can't)."""
    fens = conn.execute(select(positions.c.fen)).scalars()
    return sum(1 for fen in fens if any(chess.Board(fen).legal_moves))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--examples", type=int, default=3, help="examples per set size")
    args = parser.parse_args()
    cfg = load_config()
    settings = AcceptanceSettings.from_config()
    blunder_line = float(cfg["scoring"]["blunder_line"])
    with get_engine().connect() as conn:
        bank = load_bank(conn, cfg["engine"]["version"])
        total = scorable_positions(conn)
    print(report(bank, settings, blunder_line, args.examples, total))


if __name__ == "__main__":
    main()
