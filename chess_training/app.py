"""FastAPI app: serves the board page and the game API.

Run: uv run uvicorn chess_training.app:app --reload   then open http://localhost:8000
"""

from __future__ import annotations

import random
from contextlib import asynccontextmanager
from pathlib import Path

import chess
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from chess_training.engine import Engine
from chess_training.positions import BY_ID, SAMPLES

STATIC = Path(__file__).resolve().parents[1] / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.engine = Engine()
    try:
        yield
    finally:
        app.state.engine.close()


app = FastAPI(title="chess_training", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


def legal_dests(board: chess.Board) -> dict[str, list[str]]:
    """Legal moves as {from_square: [to_squares]}, the shape chessground expects."""
    dests: dict[str, list[str]] = {}
    for m in board.legal_moves:
        dests.setdefault(chess.square_name(m.from_square), [])
        to = chess.square_name(m.to_square)
        if to not in dests[chess.square_name(m.from_square)]:
            dests[chess.square_name(m.from_square)].append(to)
    return dests


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/api/position")
def get_position(id: str | None = None) -> dict:
    if id is not None and id not in BY_ID:
        raise HTTPException(404, f"Unknown position id: {id}")
    pos = BY_ID[id] if id else random.choice(SAMPLES)
    board = chess.Board(pos.fen)
    return {
        "id": pos.id,
        "fen": pos.fen,
        "turn": "white" if board.turn == chess.WHITE else "black",
        "phase": pos.phase,
        "opening": pos.opening,
        "description": pos.description,
        "dests": legal_dests(board),
    }


class MoveRequest(BaseModel):
    fen: str
    move: str  # UCI, e.g. "e2e4"; a missing promotion piece defaults to queen
    only_move: bool = False  # the player's "this is the only good move" claim


def parse_move(board: chess.Board, uci: str) -> chess.Move:
    try:
        move = chess.Move.from_uci(uci)
    except ValueError as exc:
        raise HTTPException(400, f"Not a UCI move: {uci}") from exc
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
def post_move(req: MoveRequest, request: Request) -> dict:
    try:
        board = chess.Board(req.fen)
    except ValueError as exc:
        raise HTTPException(400, "Invalid FEN") from exc
    if not board.is_valid():
        raise HTTPException(400, "Invalid FEN")
    move = parse_move(board, req.move)

    engine: Engine = request.app.state.engine
    top = engine.top_moves(board)
    # Reuse the top-line score when the player found one, so "loss" is exactly 0 for the best
    # move and identical scores aren't compared across two separate searches.
    player = next((line for line in top if line.move == move), None)
    in_top = player is not None
    if player is None:
        player = engine.score_move(board, move)

    best_cp = top[0].score.as_cp()
    loss_cp = max(0, best_cp - player.score.as_cp())
    gap_cp = best_cp - top[1].score.as_cp() if len(top) > 1 else None

    return {
        "player": player.to_dict(),
        "in_top": in_top,
        "rank": next((i + 1 for i, line in enumerate(top) if line.move == move), None),
        "top": [line.to_dict() for line in top],
        "loss_cp": loss_cp,
        # How far the best move is ahead of the 2nd best; a large gap suggests an "only move".
        # Thresholds for scoring are not decided yet, so we report the number only.
        "gap_cp": gap_cp,
        "only_move_claim": req.only_move,
    }
