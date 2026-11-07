# Status
_Last saved: 2026-11-06 18:15 · Overwritten by /project-format-toolkit:save-state at the end of each session._

## Where things stand
- Playable skeleton: `uv run uvicorn chess_training.app:app --reload`, then open http://localhost:8000. Four hardcoded sample positions; shows the top 3 moves (arrows), the player's score and the pawns lost. No points yet.
- Stack: FastAPI + python-chess + Stockfish 19 (pinned, downloaded by scripts/get_stockfish.py into tools/) + chessground 9.2.1 from a CDN. License GPL-3.0-or-later.
- Postgres 16 is running locally but has no tables yet. CI downloads the same Stockfish and runs the engine and API tests.

## Unfinished work
- None.

## Next steps
1. Position bank: first Alembic migration (`data:` PR) for positions (FEN, phase, opening name, source, precomputed top-3 moves and scores, engine version), and point the app at it instead of positions.py.
2. Importer for opening positions from lichess-org/chess-openings (up to move 10, both sides) with the phase rule in config.yaml.
3. Decide the scoring thresholds (pawn-loss bands, "only move" gap) and add points.
4. Importers for Lichess puzzles and quiet real-game positions.

## Open questions
- Scoring thresholds for "made the position worse" and for what counts as an "only move" (the API already reports `loss_cp` and `gap_cp`).
- Promotions auto-queen for now; add a piece picker later?
