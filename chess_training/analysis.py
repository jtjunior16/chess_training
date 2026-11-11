"""Batch engine analysis (specs/position_pipeline_spec.md §6).

Scores every legal move of every position in the bank with the pinned Stockfish, in two passes:
1. Quick pass: all legal moves at `analysis.quick_depth`, in one search with MultiPV set to the
   number of legal moves.
2. Deep pass: every move within `analysis.deep_margin` win-% points of the quick pass's best move
   is re-scored at `analysis.deep_depth`, in one search restricted to those moves.

Raw scores (from the mover's point of view) go into `position_moves`, with the depth each move
was finally scored at. Each worker is one Stockfish process with 1 thread, and the engine's hash
is cleared before every position (a new UCI game), so results don't depend on which worker
analysed what, or in which order.

Resumable: positions that already have scores for the current engine version are skipped. The
run order is a fixed shuffle (md5 of fen_key), so any first N positions mix sources and phases.

Usage:
    uv run --env-file .env python -m chess_training.analysis --limit 100   # timing report
    uv run --env-file .env python -m chess_training.analysis               # everything left
"""

from __future__ import annotations

import argparse
import multiprocessing as mp
import time
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

import chess
import chess.engine
import pandas as pd
from sqlalchemy import Connection, Engine, exists, func, select
from sqlalchemy.dialects.postgresql import insert

from chess_training.config import engine_path, load_config
from chess_training.db import get_engine, position_moves, position_sources, positions
from chess_training.winpct import win_pct

# ---------------------------------------------------------------- settings


@dataclass(frozen=True)
class AnalysisSettings:
    quick_depth: int
    deep_depth: int
    deep_margin: float
    workers: int
    engine_version: str
    threads: int
    hash_mb: int

    @classmethod
    def from_config(cls, cfg: dict | None = None) -> AnalysisSettings:
        cfg = cfg if cfg is not None else load_config()
        check_config(cfg)
        a, e = cfg["analysis"], cfg["engine"]
        return cls(
            quick_depth=int(a["quick_depth"]),
            deep_depth=int(a["deep_depth"]),
            deep_margin=float(a["deep_margin"]),
            workers=int(a["workers"]),
            engine_version=str(e["version"]),
            threads=int(e["threads"]),
            hash_mb=int(e["hash_mb"]),
        )


def check_config(cfg: dict) -> None:
    """Fail early on settings the spec forbids (§6)."""
    a, e, acc = cfg["analysis"], cfg["engine"], cfg["move_acceptance"]
    problems = []
    if int(a["deep_depth"]) != int(e["depth"]):
        problems.append(
            f"analysis.deep_depth ({a['deep_depth']}) must equal engine.depth ({e['depth']}), "
            "the live game's depth, so stored and live scores agree."
        )
    if float(a["deep_margin"]) < 2 * float(acc["L"]):
        problems.append(
            f"analysis.deep_margin ({a['deep_margin']}) must stay well above move_acceptance.L "
            f"({acc['L']}): at least 2 x L, or the quick pass could drop a borderline move."
        )
    if int(a["quick_depth"]) >= int(a["deep_depth"]):
        problems.append("analysis.quick_depth must be below analysis.deep_depth.")
    if int(e["threads"]) != 1:
        problems.append("engine.threads must be 1 for batch analysis (reproducible results).")
    if problems:
        raise ValueError("Invalid analysis settings in config.yaml:\n- " + "\n- ".join(problems))


# ---------------------------------------------------------------- scoring one position


@dataclass
class MoveScore:
    uci: str
    san: str
    score_cp: int | None
    score_mate: int | None
    depth: int

    @property
    def win(self) -> float:
        return win_pct(self.score_cp, self.score_mate)


@dataclass
class PositionResult:
    position_id: int
    moves: list[MoveScore]
    quick_s: float
    deep_s: float
    deep_count: int

    @property
    def total_s(self) -> float:
        return self.quick_s + self.deep_s


def _score(info: dict, turn: chess.Color) -> tuple[int | None, int | None]:
    s = info["score"].pov(turn)
    return s.score(), s.mate()


def deep_candidates(moves: Iterable[MoveScore], margin: float) -> list[str]:
    """UCI of every move within `margin` win-% points of the best one (the best included)."""
    moves = list(moves)
    if not moves:
        return []
    best = max(m.win for m in moves)
    return [m.uci for m in moves if best - m.win <= margin]


def analyse_position(
    engine: chess.engine.SimpleEngine,
    position_id: int,
    fen: str,
    settings: AnalysisSettings,
) -> PositionResult:
    board = chess.Board(fen)
    legal = list(board.legal_moves)
    if not legal:
        return PositionResult(position_id, [], 0.0, 0.0, 0)
    game = f"position-{position_id}"  # a new game id clears the hash: order-independent results

    t0 = time.perf_counter()
    infos = engine.analyse(
        board, chess.engine.Limit(depth=settings.quick_depth), multipv=len(legal), game=game
    )
    scored: dict[str, MoveScore] = {}
    for info in infos:
        pv = info.get("pv")
        if not pv:
            continue
        cp, mate = _score(info, board.turn)
        scored[pv[0].uci()] = MoveScore(
            pv[0].uci(), board.san(pv[0]), cp, mate, settings.quick_depth
        )
    for move in legal:  # safety net: score any move MultiPV didn't return on its own
        if move.uci() not in scored:
            info = engine.analyse(
                board,
                chess.engine.Limit(depth=settings.quick_depth),
                root_moves=[move],
                game=game,
            )
            cp, mate = _score(info, board.turn)
            scored[move.uci()] = MoveScore(
                move.uci(), board.san(move), cp, mate, settings.quick_depth
            )
    quick_s = time.perf_counter() - t0

    t1 = time.perf_counter()
    cands = deep_candidates(scored.values(), settings.deep_margin)
    infos = engine.analyse(
        board,
        chess.engine.Limit(depth=settings.deep_depth),
        multipv=len(cands),
        root_moves=[chess.Move.from_uci(u) for u in cands],
        game=game,
    )
    for info in infos:
        pv = info.get("pv")
        if not pv:
            continue
        cp, mate = _score(info, board.turn)
        m = scored[pv[0].uci()]
        m.score_cp, m.score_mate, m.depth = cp, mate, settings.deep_depth
    deep_s = time.perf_counter() - t1

    missing = [u for u in cands if scored[u].depth != settings.deep_depth]
    if missing:
        raise RuntimeError(f"Deep pass returned no score for {missing} in position {position_id}")
    return PositionResult(position_id, list(scored.values()), quick_s, deep_s, len(cands))


# ---------------------------------------------------------------- workers

_worker_engine: chess.engine.SimpleEngine | None = None
_worker_settings: AnalysisSettings | None = None


def open_engine(settings: AnalysisSettings) -> chess.engine.SimpleEngine:
    path = engine_path()
    if not path.exists():
        raise FileNotFoundError(f"Stockfish not found at {path}. Run scripts/get_stockfish.py")
    eng = chess.engine.SimpleEngine.popen_uci(str(path))
    eng.configure({"Threads": settings.threads, "Hash": settings.hash_mb})
    return eng


def _init_worker(settings: AnalysisSettings) -> None:
    global _worker_engine, _worker_settings
    _worker_settings = settings
    _worker_engine = open_engine(settings)


def _work(task: tuple[int, str]) -> PositionResult:
    return analyse_position(_worker_engine, task[0], task[1], _worker_settings)


def run_parallel(
    tasks: list[tuple[int, str]], settings: AnalysisSettings
) -> Iterator[PositionResult]:
    if settings.workers <= 1:
        eng = open_engine(settings)
        try:
            for pid, fen in tasks:
                yield analyse_position(eng, pid, fen, settings)
        finally:
            eng.quit()
        return
    ctx = mp.get_context("spawn")
    with ctx.Pool(settings.workers, initializer=_init_worker, initargs=(settings,)) as pool:
        yield from pool.imap_unordered(_work, tasks, chunksize=1)


# ---------------------------------------------------------------- database


def pending(conn: Connection, engine_version: str, limit: int | None = None) -> list[tuple]:
    """(id, fen) of positions without scores for this engine version, in the fixed shuffle."""
    done = exists().where(
        position_moves.c.position_id == positions.c.id,
        position_moves.c.engine_version == engine_version,
    )
    q = (
        select(positions.c.id, positions.c.fen)
        .where(~done)
        .order_by(func.md5(positions.c.fen_key), positions.c.id)
    )
    if limit:
        q = q.limit(limit)
    return [tuple(r) for r in conn.execute(q).all()]


def save(conn: Connection, result: PositionResult, engine_version: str) -> None:
    if not result.moves:
        return
    rows = [
        {
            "position_id": result.position_id,
            "uci": m.uci,
            "san": m.san,
            "score_cp": m.score_cp,
            "score_mate": m.score_mate,
            "depth": m.depth,
            "engine_version": engine_version,
        }
        for m in result.moves
    ]
    stmt = insert(position_moves).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[
            position_moves.c.position_id,
            position_moves.c.uci,
            position_moves.c.engine_version,
        ],
        set_={
            c: stmt.excluded[c] for c in ("san", "score_cp", "score_mate", "depth", "analysed_at")
        },
    )
    conn.execute(stmt)


def position_labels(conn: Connection, ids: list[int]) -> pd.DataFrame:
    """Source (opening / puzzle / both) and phase for the given positions."""
    rows = conn.execute(
        select(positions.c.id, positions.c.phase, position_sources.c.source)
        .join(position_sources, position_sources.c.position_id == positions.c.id)
        .where(positions.c.id.in_(ids))
    ).all()
    df = pd.DataFrame(rows, columns=["id", "phase", "source"])
    src = df.groupby("id")["source"].agg(lambda s: s.iloc[0] if s.nunique() == 1 else "both")
    return df.drop_duplicates("id").set_index("id")[["phase"]].join(src)


# ---------------------------------------------------------------- run + report


def run(db: Engine, settings: AnalysisSettings, limit: int | None = None) -> pd.DataFrame:
    """Analyse pending positions; each result is committed as soon as it arrives."""
    with db.connect() as conn:
        tasks = pending(conn, settings.engine_version, limit)
    records = []
    for result in run_parallel(tasks, settings):
        with db.begin() as conn:
            save(conn, result, settings.engine_version)
        records.append(
            {
                "id": result.position_id,
                "total_s": result.total_s,
                "quick_s": result.quick_s,
                "deep_s": result.deep_s,
                "legal_moves": len(result.moves),
                "deep_moves": result.deep_count,
            }
        )
    return pd.DataFrame(records)


def report(stats: pd.DataFrame, labels: pd.DataFrame, wall_s: float, remaining: int, workers: int):
    df = stats.set_index("id").join(labels)
    cols = ["total_s", "quick_s", "deep_s", "legal_moves", "deep_moves"]
    lines = [
        f"Analysed {len(df)} positions in {wall_s:.0f} s wall time with {workers} workers.",
        "",
        "Per position, mean (by source and phase):",
        df.groupby(["source", "phase"])[cols]
        .mean()
        .round(2)
        .assign(n=df.groupby(["source", "phase"]).size())
        .to_string(),
        "",
        "Per position, overall: mean / median / max",
    ]
    for c in cols:
        lines.append(f"  {c:<12} {df[c].mean():8.2f} {df[c].median():8.2f} {df[c].max():8.2f}")
    if len(df):
        per_pos_wall = wall_s / len(df)
        est_h = per_pos_wall * remaining / 3600
        lines += [
            "",
            f"Remaining positions: {remaining:,}. At {per_pos_wall:.2f} s wall time per position "
            f"(this run's throughput), the rest takes about {est_h:.1f} hours.",
        ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--limit", type=int, help="analyse at most this many positions")
    parser.add_argument("--workers", type=int, help="override analysis.workers")
    args = parser.parse_args()
    settings = AnalysisSettings.from_config()
    if args.workers:
        settings = AnalysisSettings(**{**settings.__dict__, "workers": args.workers})
    db = get_engine()
    t0 = time.perf_counter()
    stats = run(db, settings, args.limit)
    wall = time.perf_counter() - t0
    if stats.empty:
        print("Nothing to analyse: every position has scores for", settings.engine_version)
        return
    with db.connect() as conn:
        labels = position_labels(conn, stats["id"].tolist())
        remaining = len(pending(conn, settings.engine_version))
    print(report(stats, labels, wall, remaining, settings.workers))


if __name__ == "__main__":
    main()
