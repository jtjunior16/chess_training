"""FastAPI app: serves the board page and the game API.

The game plays positions from the bank and judges moves from their stored scores, so no
engine runs while the player plays (specs/position_pipeline_spec.md §6, step 6).

Run: uv run --env-file .env uvicorn chess_training.app:app --reload   then open http://localhost:8000
"""

from __future__ import annotations

import random
from collections.abc import Iterator
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Annotated

import chess
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import Connection
from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError

from chess_training.acceptance import AcceptanceSettings, acceptable_set, load_moves
from chess_training.config import load_config
from chess_training.game import (
    GameSettings,
    is_playable,
    load_position,
    move_result,
    pick_position_id,
    playable_ids,
    position_payload,
)
from chess_training.scoring import stats as scoring_stats

STATIC = Path(__file__).resolve().parents[1] / "static"

app = FastAPI(title="chess_training")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.exception_handler(OperationalError)
@app.exception_handler(InterfaceError)
def _database_error(request: Request, exc: DBAPIError) -> JSONResponse:
    """The database is down or unreachable. Other database errors (a constraint violation, a
    bad query) are bugs and stay 500s, so they don't look like an outage."""
    return JSONResponse(
        status_code=503, content={"detail": f"Database unavailable: {type(exc).__name__}"}
    )


@cache
def _db():
    """One SQLAlchemy engine (and connection pool) for the app, created on first use."""
    from chess_training.db import get_engine

    return get_engine()


def get_conn() -> Iterator[Connection]:
    """A database connection for one request. Tests override this with a rolled-back one."""
    try:
        engine = _db()
    except RuntimeError as exc:  # DATABASE_URL not set
        raise HTTPException(503, str(exc)) from exc
    with engine.connect() as conn:
        yield conn


@dataclass(frozen=True)
class GameConfig:
    acceptance: AcceptanceSettings
    game: GameSettings
    engine_version: str


@cache
def _game_config() -> GameConfig:
    return GameConfig(
        acceptance=AcceptanceSettings.from_config(),
        game=GameSettings.from_config(),
        engine_version=load_config()["engine"]["version"],
    )


def get_game_config() -> GameConfig:
    """The settings the game runs with. Tests override this to use their own engine version."""
    return _game_config()


DbConn = Annotated[Connection, Depends(get_conn)]
Config = Annotated[GameConfig, Depends(get_game_config)]

_rng = random.Random()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/api/position")
def get_position(conn: DbConn, cfg: Config, id: int | None = None) -> dict:
    picked = id is None
    if picked:
        # Lists every playable id (~90 ms on the full bank). Fine locally; cache it if the
        # bank or the traffic grows.
        try:
            id = pick_position_id(playable_ids(conn, cfg.engine_version), cfg.game, _rng)
        except LookupError as exc:
            raise HTTPException(503, str(exc)) from exc
    row = load_position(conn, id)
    if row is None:
        raise HTTPException(404, f"Unknown position id: {id}")
    if not picked and not is_playable(conn, id, cfg.engine_version):
        raise HTTPException(404, f"Position {id} has no stored scores (or no legal moves)")
    return position_payload(row)


class MoveRequest(BaseModel):
    position_id: int
    move: str  # UCI, e.g. "e2e4"; a missing promotion piece defaults to queen
    only_move: bool = False  # the player's "this is the only good move" claim


def parse_move(board: chess.Board, uci: str) -> chess.Move:
    try:
        move = chess.Move.from_uci(uci)
    except ValueError as exc:
        raise HTTPException(400, f"Not a UCI move: {uci}") from exc
    # PLACEHOLDER (STATUS.md P4, promotion picker): a promotion without a piece is a queen.
    if (
        move.promotion is None
        and board.piece_type_at(move.from_square) == chess.PAWN
        and chess.square_rank(move.to_square) in (0, 7)
    ):
        move = chess.Move(move.from_square, move.to_square, promotion=chess.QUEEN)
    if move not in board.legal_moves:
        raise HTTPException(400, f"Illegal move in this position: {uci}")
    return move


@app.post("/api/move")
def post_move(
    req: MoveRequest,
    conn: DbConn,
    cfg: Config,
) -> dict:
    row = load_position(conn, req.position_id)
    if row is None:
        raise HTTPException(404, f"Unknown position id: {req.position_id}")
    move = parse_move(chess.Board(row.fen), req.move)
    moves = load_moves(conn, req.position_id, cfg.engine_version)
    if not moves:
        raise HTTPException(404, f"Position {req.position_id} has no stored scores")
    acc = acceptable_set(moves, cfg.acceptance)
    try:
        result = move_result(acc, move.uci(), cfg.game)
    except ValueError as exc:  # a legal move without a stored score: the analysis is incomplete
        raise HTTPException(409, str(exc)) from exc
    return {**result, "only_move_claim": req.only_move}


@app.get("/api/stats")
def get_stats(conn: DbConn) -> dict:
    """The player's accuracy figures (specs/scoring_spec.md). Needs the database."""
    return scoring_stats(conn)
