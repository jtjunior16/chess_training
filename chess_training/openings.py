"""Opening importer (specs/position_pipeline_spec.md §4).

Replays every line of the pinned lichess-org/chess-openings TSVs and stores the position after
every half-move through move `openings.max_fullmove` (the starting position is skipped).

Naming: a position is named by what has actually happened on the board.
1. Exact match: if its `fen_key` is the end position of a named line (in any move order), it
   takes that line's name.
2. Otherwise it takes the name of the nearest named position on the path that led to it.
3. If several names apply (transpositions, or different named ancestors), `opening_name` is the
   most specific one (the longest line; ties go to the alphabetically first name) and
   `opening_names` lists all of them.

Sources: one `position_sources` row per sequence of moves (`source_ref` = PGN movetext so far,
decided 2026-11-09). Its `opening_eco` is the ECO of the line that names that path: the exactly
matching line, otherwise the nearest named ancestor (decided by the user, 2026-11-11).

Usage:
    uv run python scripts/get_openings.py              # download the pinned files
    uv run --env-file .env python -m chess_training.openings
"""

from __future__ import annotations

import csv
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

import chess
from sqlalchemy import Connection
from sqlalchemy.dialects.postgresql import insert

from chess_training.config import ROOT, load_config
from chess_training.db import get_engine, position_sources, positions
from chess_training.fen import fen_key
from chess_training.phase import PhaseSettings, label_phase

CHUNK = 1000  # rows per INSERT


@dataclass(frozen=True)
class Line:
    """One row of the openings TSV, replayed."""

    eco: str
    name: str
    sans: tuple[str, ...]

    @property
    def rank(self) -> tuple[int, str]:
        """Sort key for "most specific": longer lines first, then alphabetical by name."""
        return (-len(self.sans), self.name)


@dataclass
class SourceRow:
    source_ref: str
    fen_key: str
    fullmove_number: int
    moves_to_position: list[str]
    opening_eco: str | None


@dataclass
class PositionRow:
    fen: str  # as first seen
    fen_key: str
    side_to_move: str
    phase: str
    opening_name: str | None = None
    opening_names: list[str] = field(default_factory=list)


@dataclass
class OpeningImport:
    positions: dict[str, PositionRow]  # by fen_key
    sources: dict[str, SourceRow]  # by source_ref


def openings_dir() -> Path:
    cfg = load_config()
    return ROOT / cfg["data"]["raw_dir"] / cfg["openings"]["subdir"]


def read_lines(paths: Iterable[Path]) -> Iterator[tuple[str, str, str]]:
    """(eco, name, pgn) for every row of the given TSV files."""
    for path in paths:
        with path.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f, delimiter="\t"):
                yield row["eco"], row["name"], row["pgn"]


def parse_line(eco: str, name: str, pgn: str) -> Line:
    """Turn PGN movetext like "1. e4 c6 2. d4" into a Line of SAN moves (checked for legality)."""
    board = chess.Board()
    sans = []
    for token in pgn.split():
        if token.endswith("."):  # move numbers: "1." or "1..."
            continue
        move = board.parse_san(token)  # raises on an illegal or ambiguous move
        sans.append(board.san(move))
        board.push(move)
    return Line(eco=eco, name=name, sans=tuple(sans))


def movetext(sans: Iterable[str]) -> str:
    """PGN movetext for moves from the starting position: ("e4", "c6", "d4") -> "1. e4 c6 2. d4"."""
    parts = []
    for i, san in enumerate(sans):
        if i % 2 == 0:
            parts.append(f"{i // 2 + 1}.")
        parts.append(san)
    return " ".join(parts)


def build_import(
    rows: Iterable[tuple[str, str, str]],
    *,
    max_fullmove: int,
    phase_settings: PhaseSettings | None = None,
) -> OpeningImport:
    """Work out every position and source row from (eco, name, pgn) rows. Pure: no database."""
    phase_settings = phase_settings or PhaseSettings.from_config()
    lines = [parse_line(*r) for r in rows]
    max_plies = 2 * max_fullmove

    # Named lines by the key of their end position. Matching on the position, not the moves,
    # means a transposition counts as an exact match.
    ends: dict[str, list[Line]] = {}
    for line in lines:
        board = chess.Board()
        for san in line.sans:
            board.push_san(san)
        ends.setdefault(fen_key(board), []).append(line)
    for named in ends.values():
        named.sort(key=lambda ln: ln.rank)

    # Walk every line ply by ply. Each distinct move sequence is visited once; its naming line is
    # the exact match at that position, otherwise the one inherited from the sequence before it.
    path_namer: dict[tuple[str, ...], Line | None] = {(): None}
    names_at: dict[str, set[Line]] = {}  # fen_key -> every line that names it on some path
    result = OpeningImport(positions={}, sources={})

    for line in lines:
        board = chess.Board()
        for ply, san in enumerate(line.sans[:max_plies], start=1):
            board.push_san(san)
            path = line.sans[:ply]
            if path in path_namer:
                continue
            key = fen_key(board)
            exact = ends.get(key)
            namer = exact[0] if exact else path_namer[path[:-1]]
            path_namer[path] = namer

            names = names_at.setdefault(key, set())
            if exact:
                names.update(exact)
            elif namer:
                names.add(namer)

            ref = movetext(path)
            result.sources[ref] = SourceRow(
                source_ref=ref,
                fen_key=key,
                fullmove_number=board.fullmove_number,
                moves_to_position=list(path),
                opening_eco=namer.eco if namer else None,
            )
            if key not in result.positions:
                result.positions[key] = PositionRow(
                    fen=board.fen(en_passant="legal"),
                    fen_key=key,
                    side_to_move="w" if board.turn == chess.WHITE else "b",
                    # Every position here comes from a named opening line (spec §3).
                    phase=label_phase(board, from_named_line=True, settings=phase_settings),
                )

    for key, pos in result.positions.items():
        named = sorted(names_at.get(key, ()), key=lambda ln: ln.rank)
        if named:
            pos.opening_name = named[0].name
            pos.opening_names = sorted({ln.name for ln in named})
    return result


def _chunks(items: list, size: int = CHUNK) -> Iterator[list]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def write_import(conn: Connection, data: OpeningImport) -> dict[str, int]:
    """Upsert the import. Running it twice leaves the database unchanged.

    An existing position keeps its first-seen `fen`; its phase and names are refreshed.
    """
    ids: dict[str, int] = {}
    pos_rows = [vars(p) for p in data.positions.values()]
    for chunk in _chunks(pos_rows):
        stmt = insert(positions).values(chunk)
        stmt = stmt.on_conflict_do_update(
            index_elements=[positions.c.fen_key],
            set_={
                "phase": stmt.excluded.phase,
                "opening_name": stmt.excluded.opening_name,
                "opening_names": stmt.excluded.opening_names,
            },
        ).returning(positions.c.id, positions.c.fen_key)
        ids.update({k: i for i, k in conn.execute(stmt)})

    src_rows = [
        {
            "position_id": ids[s.fen_key],
            "source": "opening",
            "source_ref": s.source_ref,
            "fullmove_number": s.fullmove_number,
            "moves_to_position": s.moves_to_position,
            "opening_eco": s.opening_eco,
        }
        for s in data.sources.values()
    ]
    for chunk in _chunks(src_rows):
        stmt = insert(position_sources).values(chunk)
        stmt = stmt.on_conflict_do_update(
            index_elements=[position_sources.c.source, position_sources.c.source_ref],
            set_={
                c: stmt.excluded[c]
                for c in ("position_id", "fullmove_number", "moves_to_position", "opening_eco")
            },
        )
        conn.execute(stmt)
    return {"positions": len(pos_rows), "sources": len(src_rows)}


def main() -> None:
    cfg = load_config()["openings"]
    folder = openings_dir()
    paths = [folder / name for name in cfg["sha256"]]
    missing = [p.name for p in paths if not p.exists()]
    if missing:
        raise SystemExit(
            f"Missing {', '.join(missing)} in {folder}. Run: uv run python scripts/get_openings.py"
        )
    data = build_import(read_lines(paths), max_fullmove=int(cfg["max_fullmove"]))
    with get_engine().begin() as conn:
        counts = write_import(conn, data)
    phases: dict[str, int] = {}
    for p in data.positions.values():
        phases[p.phase] = phases.get(p.phase, 0) + 1
    unnamed = sum(1 for p in data.positions.values() if not p.opening_name)
    print(
        f"Imported {counts['positions']} positions and {counts['sources']} opening sources "
        f"(commit {cfg['commit'][:7]}). Phases: {phases}. Unnamed: {unnamed}."
    )


if __name__ == "__main__":
    main()
