# Status
_Last saved: 2026-11-06 18:50 · Overwritten by /project-format-toolkit:save-state at the end of each session._

## Where things stand
- Playable skeleton: `uv run uvicorn chess_training.app:app --reload`, then open http://localhost:8000. Four hardcoded sample positions; shows the top 3 moves (arrows), the player's score and the pawns lost. No points yet.
- Stack: FastAPI + python-chess + Stockfish 19 (pinned, downloaded by scripts/get_stockfish.py into tools/) + chessground 9.2.1 from a CDN. License GPL-3.0-or-later.
- Postgres 16 is running locally but has no tables yet. CI downloads the same Stockfish and runs the engine and API tests.

## Unfinished work
- None.

## Next steps
Paused by the user: no development until they say so. When resuming, follow `specs/` (statuses: challenge mode = ready; position pipeline and move acceptance = draft).
1. Design chat: settle the open questions in specs/position_pipeline_spec.md and specs/move_acceptance_spec.md (puzzle sample size, analysis depth, G and L).
2. Position pipeline step 1: the `data:` migration for `positions` + `position_moves`.
3. Then phase labeller → opening importer → puzzle importer → batch analysis → game reads from the bank.

## Open questions
- Values of G and L for the acceptable-move rule (draft spec); points for moves outside the acceptable set; scoring of the "only good move" claim.
- Promotions auto-queen for now; add a piece picker later?
