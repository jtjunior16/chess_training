# Status
_Last saved: 2026-11-06 17:53 · Overwritten by /project-format-toolkit:save-state at the end of each session._

## Where things stand
- Setup complete: app on Postgres 16 (Docker + Alembic), public repo at github.com/jtjunior16/chess_training, CI green.
- Gates on: pre-commit + commit-msg hooks, squash-only merges, main protected (PR + passing `checks` job required).
- Position sources and phase labelling decided (see README "Positions" and docs/decisions.md).
- No game code and no migrations yet.

## Unfinished work
- None.

## Next steps
1. Pick the stack: a web page or a desktop window for the board, plus python-chess (rules) and Stockfish (engine).
2. Design the first game feature (announce the plan first): show a position, the player makes a move, reveal the engine's top 3 moves.
3. Write the first Alembic migration for the position bank (FEN, phase, opening name, source, precomputed top-3 evals).

## Open questions
- Scoring thresholds for "made the position worse" are not decided yet.
