"""Recompute the phase label of every position in the bank (specs/position_pipeline_spec.md §3).

The importers label a board only when they first add it, so after a change to the phase rule or
its numbers in config.yaml, run this once:

    uv run --env-file .env python -m chess_training.relabel_phases

A position counts as "from a named line" if it has an opening source. The move number comes
from its stored FEN (the FEN as first seen). Prints how many labels changed, then compares our
labels with Lichess's phase tags for puzzle positions. Running it twice changes nothing.
"""

from __future__ import annotations

from collections import Counter

import chess
import pandas as pd
from sqlalchemy import Connection, bindparam, exists, select, update

from chess_training.db import get_engine, position_sources, positions
from chess_training.phase import PhaseSettings, label_phase
from chess_training.puzzles import lichess_phase


def relabel(conn: Connection, settings: PhaseSettings | None = None) -> Counter:
    """Update every position whose label differs from the current rule.

    Returns a Counter of (old, new) label pairs for the rows that changed.
    """
    settings = settings or PhaseSettings.from_config()
    has_opening = exists().where(
        position_sources.c.position_id == positions.c.id,
        position_sources.c.source == "opening",
    )
    rows = conn.execute(
        select(positions.c.id, positions.c.fen, positions.c.phase, has_opening.label("named"))
    ).all()
    changes: Counter = Counter()
    updates = []
    for r in rows:
        new = label_phase(chess.Board(r.fen), from_named_line=r.named, settings=settings)
        if new != r.phase:
            changes[(r.phase, new)] += 1
            updates.append({"pid": r.id, "new_phase": new})
    if updates:
        conn.execute(
            update(positions)
            .where(positions.c.id == bindparam("pid"))
            .values(phase=bindparam("new_phase")),
            updates,
        )
    return changes


def puzzle_phase_comparison(conn: Connection) -> pd.DataFrame:
    """Our phase (rows) against Lichess's phase tag (columns), over every puzzle source."""
    rows = conn.execute(
        select(positions.c.phase, position_sources.c.puzzle_themes)
        .join(positions, positions.c.id == position_sources.c.position_id)
        .where(position_sources.c.source == "puzzle")
    ).all()
    return pd.crosstab(
        pd.Series([r.phase for r in rows], name="ours"),
        pd.Series([lichess_phase(" ".join(r.puzzle_themes or [])) for r in rows], name="lichess"),
    )


def main() -> None:
    with get_engine().begin() as conn:
        changes = relabel(conn)
        table = puzzle_phase_comparison(conn)
    total = sum(changes.values())
    print(f"Relabelled {total:,} positions.")
    for (old, new), n in sorted(changes.items()):
        print(f"  {old} -> {new}: {n:,}")
    if not table.empty:
        print("\nPuzzle positions, ours (rows) vs Lichess tags (columns):")
        print(table.to_string())


if __name__ == "__main__":
    main()
