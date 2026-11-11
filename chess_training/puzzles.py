"""Puzzle importer (specs/position_pipeline_spec.md §5).

Streams the pinned Lichess puzzle dump, applies the quality filter, draws a seeded sample and
writes it into the position bank.

Sample (all numbers in the `puzzles:` section of config.yaml):
1. Quality filter: drop puzzles with NbPlays < min_nb_plays or Popularity < min_popularity.
2. Theme floor: every motif theme gets at least `theme_floor` puzzles, rarest theme first. A
   puzzle with several motif themes counts towards each. A theme with too few puzzles gets all
   of them, and the report says so.
3. Rating bands: the rest of the `sample_size` slots fill `rating_band_width`-point bands so the
   final totals (floor picks included) are as even as possible (decided by the user,
   2026-11-11). A band with too few puzzles takes all it has; the others share its slots.
4. Everything random uses one numpy Generator seeded with `seed`, over candidates sorted by
   PuzzleId, so the same dump and settings always give the same sample.

The training position is the FEN *after* the first move in `Moves` (the opponent's move), and
that move is stored as the last move played.

Usage:
    uv run python scripts/get_puzzles.py               # download the pinned dump
    uv run --env-file .env python -m chess_training.puzzles
"""

from __future__ import annotations

import io
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

import chess
import numpy as np
import pandas as pd
import zstandard
from sqlalchemy import Connection, select
from sqlalchemy.dialects.postgresql import insert

from chess_training.config import ROOT, load_config
from chess_training.db import get_engine, position_sources, positions
from chess_training.fen import fen_key
from chess_training.phase import PhaseSettings, label_phase

COLUMNS = ["PuzzleId", "FEN", "Moves", "Rating", "Popularity", "NbPlays", "Themes", "OpeningTags"]
LICHESS_PHASES = ("opening", "middlegame", "endgame")
CHUNK = 1000  # rows per INSERT


@dataclass(frozen=True)
class SampleSettings:
    min_nb_plays: int
    min_popularity: int
    sample_size: int
    theme_floor: int
    rating_band_width: int
    seed: int
    motif: frozenset[str]
    not_theme: frozenset[str]
    unplaced: frozenset[str]  # placeholder: treated as not themes

    @classmethod
    def from_config(cls, section: dict | None = None) -> SampleSettings:
        s = section if section is not None else load_config()["puzzles"]
        t = s["themes"]
        return cls(
            min_nb_plays=int(s["min_nb_plays"]),
            min_popularity=int(s["min_popularity"]),
            sample_size=int(s["sample_size"]),
            theme_floor=int(s["theme_floor"]),
            rating_band_width=int(s["rating_band_width"]),
            seed=int(s["seed"]),
            motif=frozenset(t["motif"]),
            not_theme=frozenset(t["not_theme"]),
            unplaced=frozenset(t.get("unplaced") or ()),
        )

    @property
    def known_tags(self) -> frozenset[str]:
        return self.motif | self.not_theme | self.unplaced


@dataclass
class Sample:
    rows: pd.DataFrame  # the chosen puzzles, sorted by PuzzleId
    candidates: int  # puzzles left after the quality filter
    short_themes: dict[str, int]  # motif themes with fewer than theme_floor candidates
    unknown_tags: Counter  # tags in the candidates that no theme list mentions


def puzzles_path() -> Path:
    cfg = load_config()
    return ROOT / cfg["data"]["raw_dir"] / cfg["puzzles"]["subdir"] / cfg["puzzles"]["file"]


# ---------------------------------------------------------------- reading


def read_chunks(path: Path, chunksize: int = 500_000) -> Iterator[pd.DataFrame]:
    """Stream the zstd-compressed CSV without writing it to disk uncompressed."""
    with path.open("rb") as raw:
        reader = zstandard.ZstdDecompressor().stream_reader(raw)
        text = io.TextIOWrapper(reader, encoding="utf-8", newline="")
        yield from pd.read_csv(
            text,
            usecols=COLUMNS,
            dtype={c: "string" for c in ("PuzzleId", "FEN", "Moves", "Themes", "OpeningTags")},
            chunksize=chunksize,
        )


def quality_filter(chunks: Iterable[pd.DataFrame], settings: SampleSettings) -> pd.DataFrame:
    kept = [
        c[(c["NbPlays"] >= settings.min_nb_plays) & (c["Popularity"] >= settings.min_popularity)]
        for c in chunks
    ]
    df = pd.concat(kept, ignore_index=True) if kept else pd.DataFrame(columns=COLUMNS)
    df["Themes"] = df["Themes"].fillna("")
    return df.sort_values("PuzzleId", kind="stable").reset_index(drop=True)


# ---------------------------------------------------------------- sampling


def motif_themes(themes: str, motif: frozenset[str]) -> list[str]:
    return [t for t in themes.split() if t in motif]


def even_band_targets(selected: dict[int, int], available: dict[int, int], total: int) -> dict:
    """How many more to take per band so final totals are as even as possible.

    `selected`: already chosen per band (floor picks). `available`: unchosen candidates per band.
    Water-filling: raise a common level until the slots run out; a band never drops below what it
    already has and never takes more than it has available. Leftover slots (when the level can't
    rise by a whole step for every band) go to the lowest bands first, by band number.
    """
    bands = sorted(set(selected) | set(available))
    have = {b: selected.get(b, 0) for b in bands}
    cap = {b: have[b] + available.get(b, 0) for b in bands}
    slots = total - sum(have.values())
    if slots <= 0:
        return dict.fromkeys(bands, 0)
    final = dict(have)
    level = min(have.values()) if bands else 0
    while slots > 0:
        growable = [b for b in bands if final[b] <= level and final[b] < cap[b]]
        if not growable:
            if all(final[b] >= cap[b] for b in bands):
                break  # every band exhausted
            level += 1
            continue
        if len(growable) <= slots:
            for b in growable:
                final[b] += 1
            slots -= len(growable)
            level += 1
        else:
            for b in sorted(growable, key=lambda b: (final[b], b))[:slots]:
                final[b] += 1
            slots = 0
    return {b: final[b] - have[b] for b in bands}


def draw_sample(df: pd.DataFrame, settings: SampleSettings) -> Sample:
    """Theme floor first, then even rating bands. `df` must be sorted by PuzzleId."""
    rng = np.random.default_rng(settings.seed)
    motifs = df["Themes"].map(lambda s: motif_themes(s, settings.motif))
    chosen: set[int] = set()
    have_theme: Counter = Counter()

    def take(indices: Iterable[int]) -> None:
        for i in indices:
            chosen.add(int(i))
            have_theme.update(motifs.iat[int(i)])

    # 1. Theme floor, rarest theme first.
    by_theme: dict[str, list[int]] = {}
    for i, ts in enumerate(motifs):
        for t in ts:
            by_theme.setdefault(t, []).append(i)
    counts = {t: len(by_theme.get(t, [])) for t in settings.motif}
    short = {t: n for t, n in counts.items() if n < settings.theme_floor}
    for theme in sorted(settings.motif, key=lambda t: (counts[t], t)):
        need = settings.theme_floor - have_theme[theme]
        if need <= 0:
            continue
        pool = np.array([i for i in by_theme.get(theme, []) if i not in chosen], dtype=np.int64)
        if len(pool) <= need:
            take(pool)
        else:
            take(rng.choice(pool, size=need, replace=False))
    if len(chosen) > settings.sample_size:
        raise ValueError(
            f"The theme floor alone needs {len(chosen)} puzzles, more than sample_size "
            f"{settings.sample_size}. Lower puzzles.theme_floor or raise puzzles.sample_size."
        )

    # 2. Rating bands, topped up so final totals are as even as possible.
    band = (df["Rating"] // settings.rating_band_width).astype(int).to_numpy()
    chosen_mask = np.zeros(len(df), dtype=bool)
    chosen_mask[list(chosen)] = True
    selected = Counter(band[chosen_mask].tolist())
    available = Counter(band[~chosen_mask].tolist())
    targets = even_band_targets(dict(selected), dict(available), settings.sample_size)
    for b in sorted(targets):
        n = targets[b]
        if n <= 0:
            continue
        pool = np.flatnonzero((band == b) & ~chosen_mask)
        take(pool if len(pool) <= n else rng.choice(pool, size=n, replace=False))

    known = settings.known_tags
    unknown = Counter(t for s in df["Themes"] for t in s.split() if t not in known)
    rows = df.iloc[sorted(chosen)].reset_index(drop=True)
    return Sample(rows=rows, candidates=len(df), short_themes=short, unknown_tags=unknown)


# ---------------------------------------------------------------- positions


def training_position(fen: str, moves: str) -> tuple[chess.Board, str]:
    """The board after the opponent's first move, and that move in SAN."""
    board = chess.Board(fen)
    first = chess.Move.from_uci(moves.split()[0])
    if first not in board.legal_moves:
        raise ValueError(f"First move {first.uci()} is illegal in {fen}")
    san = board.san(first)
    board.push(first)
    return board, san


def split_tags(value) -> list[str] | None:
    if value is None or pd.isna(value) or not str(value).strip():
        return None
    return str(value).split()


def write_sample(
    conn: Connection, sample: Sample, phase_settings: PhaseSettings | None = None
) -> dict[str, int]:
    """Upsert the sample. Running it twice leaves the database unchanged.

    A board that is already in the bank (e.g. from openings) keeps its row, phase and names; the
    puzzle only adds its source row. New boards are labelled without the named-line test.
    """
    phase_settings = phase_settings or PhaseSettings.from_config()
    new_positions: dict[str, dict] = {}
    sources = []
    for r in sample.rows.itertuples(index=False):
        board, san = training_position(r.FEN, r.Moves)
        key = fen_key(board)
        new_positions.setdefault(
            key,
            {
                "fen": board.fen(en_passant="legal"),
                "fen_key": key,
                "side_to_move": "w" if board.turn == chess.WHITE else "b",
                "phase": label_phase(board, from_named_line=False, settings=phase_settings),
            },
        )
        sources.append(
            {
                "fen_key": key,
                "source": "puzzle",
                "source_ref": r.PuzzleId,
                "fullmove_number": board.fullmove_number,
                "moves_to_position": [san],
                "puzzle_rating": int(r.Rating),
                "puzzle_themes": str(r.Themes).split(),
                "puzzle_popularity": int(r.Popularity),
                "puzzle_nb_plays": int(r.NbPlays),
                "puzzle_opening_tags": split_tags(r.OpeningTags),
            }
        )

    rows = list(new_positions.values())
    inserted = 0
    for i in range(0, len(rows), CHUNK):
        stmt = insert(positions).values(rows[i : i + CHUNK]).on_conflict_do_nothing()
        inserted += len(conn.execute(stmt.returning(positions.c.id)).all())
    ids = dict(
        conn.execute(
            select(positions.c.fen_key, positions.c.id).where(
                positions.c.fen_key.in_(list(new_positions))
            )
        ).all()
    )
    for s in sources:
        s["position_id"] = ids[s.pop("fen_key")]
    updatable = [c for c in sources[0] if c not in ("source", "source_ref")] if sources else []
    for i in range(0, len(sources), CHUNK):
        stmt = insert(position_sources).values(sources[i : i + CHUNK])
        stmt = stmt.on_conflict_do_update(
            index_elements=[position_sources.c.source, position_sources.c.source_ref],
            set_={c: stmt.excluded[c] for c in updatable},
        )
        conn.execute(stmt)
    return {"sources": len(sources), "positions": len(rows), "new_positions": inserted}


# ---------------------------------------------------------------- report


def lichess_phase(themes: str) -> str:
    tags = set(themes.split())
    found = [p for p in LICHESS_PHASES if p in tags]
    return found[0] if len(found) == 1 else ("none" if not found else "several")


def phase_comparison(conn: Connection, sample: Sample) -> pd.DataFrame:
    """Our phase label (rows) against Lichess's phase tag (columns), for the sampled puzzles."""
    refs = sample.rows["PuzzleId"].tolist()
    ours = dict(
        conn.execute(
            select(position_sources.c.source_ref, positions.c.phase)
            .join(positions, positions.c.id == position_sources.c.position_id)
            .where(position_sources.c.source == "puzzle", position_sources.c.source_ref.in_(refs))
        ).all()
    )
    theirs = sample.rows.set_index("PuzzleId")["Themes"].map(lichess_phase)
    table = pd.crosstab(
        pd.Series([ours[r] for r in refs], name="ours"),
        pd.Series(theirs.loc[refs].to_numpy(), name="lichess"),
    )
    return table


def report(sample: Sample, settings: SampleSettings, counts: dict, phases: pd.DataFrame) -> str:
    rows = sample.rows
    theme_counts = Counter(t for s in rows["Themes"] for t in motif_themes(s, settings.motif))
    bands = (rows["Rating"] // settings.rating_band_width * settings.rating_band_width).astype(int)
    lines = [
        f"Candidates after the quality filter: {sample.candidates:,}",
        f"Sampled {len(rows):,} puzzles (seed {settings.seed}): {counts['sources']:,} sources, "
        f"{counts['positions']:,} positions, {counts['new_positions']:,} of them new to the bank.",
        "",
        "Motif themes in the sample (floor " + str(settings.theme_floor) + "):",
    ]
    for t in sorted(settings.motif, key=lambda t: (theme_counts[t], t)):
        flag = (
            "  << fewer than the floor in the whole filtered set"
            if t in sample.short_themes
            else ""
        )
        lines.append(f"  {t:<20} {theme_counts[t]:>5}{flag}")
    lines += ["", f"Rating bands ({settings.rating_band_width} points):"]
    for b, n in bands.value_counts().sort_index().items():
        lines.append(f"  {b:>4}-{b + settings.rating_band_width - 1:<4} {n:>5}")
    lines += ["", "Phase labels: ours (rows) vs Lichess tags (columns):", phases.to_string()]
    if sample.unknown_tags:
        lines += ["", "Tags in the data that no theme list in config.yaml mentions (FLAG):"]
        lines += [f"  {t}: {n:,}" for t, n in sample.unknown_tags.most_common()]
    return "\n".join(lines)


def main() -> None:
    settings = SampleSettings.from_config()
    path = puzzles_path()
    if not path.exists():
        raise SystemExit(f"Missing {path}. Run: uv run python scripts/get_puzzles.py")
    df = quality_filter(read_chunks(path), settings)
    sample = draw_sample(df, settings)
    with get_engine().begin() as conn:
        counts = write_sample(conn, sample)
        phases = phase_comparison(conn, sample)
    print(report(sample, settings, counts, phases))


if __name__ == "__main__":
    main()
