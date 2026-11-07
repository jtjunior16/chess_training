# Status
_Last saved: 2026-11-06 17:44 · Overwritten by /project-format-toolkit:save-state at the end of each session._

## Where things stand
- Setup complete: app on Postgres 16 (Docker + Alembic), public repo at github.com/jtjunior16/chess_training, CI green.
- Gates on: pre-commit + commit-msg hooks, squash-only merges, main protected (PR + passing `checks` job required).
- No game code and no migrations yet. The game concept is in README ("Game concept").

## Unfinished work
- None.

## Next steps
1. Design the first game feature (announce the plan first): show a position, the player makes a move, reveal the engine's top 3 moves. Decide the stack: UI framework, chess library (e.g. python-chess), and engine (e.g. Stockfish).
2. Write the first Alembic migration for the position bank (FEN + precomputed top-3 evals).

## Open questions
- Scoring thresholds for "made the position worse" are not decided yet.
- Where the positions come from (a puzzle database, the user's own games, or generated ones).
