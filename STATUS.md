# Status
_Last saved: 2026-11-11 11:05 · Overwritten by /project-format-toolkit:save-state at the end of each session._

## Where things stand
- Playable skeleton: `uv run uvicorn chess_training.app:app --reload`, then open http://localhost:8000. Four hardcoded sample positions; shows the top 3 moves (arrows), the player's score and the pawns lost. No points yet.
- Stack: FastAPI + python-chess + Stockfish 19 (pinned, downloaded by `scripts/get_stockfish.py` into tools/) + chessground 9.2.1 from a CDN. License GPL-3.0-or-later. Postgres 16 runs locally in Docker. The position bank (migration 0001) holds 7,717 opening positions (`uv run --env-file .env python -m chess_training.openings`).
- Design lives in `specs/`: challenge mode = **ready** (needs the position bank), position pipeline = **in progress** (steps 1–3 of 6 done: the tables, the phase labeller and the opening importer), move acceptance = **draft**. `specs/spec_log.md` records when each spec was created, updated and built. CLAUDE.md: build only what a spec marks Decided, and never settle its Open questions while coding.
- The user takes open questions to a separate design chat (Claude Desktop) and brings answers back as updated spec files.

## Unfinished work
- None.

## Next steps
1. Position pipeline step 4 of 6: the puzzle importer (spec §5): a 5,000-puzzle sample, and a comparison of our phase labels with Lichess's puzzle tags. It will reuse `chess_training/fen.py`.
2. Then: batch analysis (scores every legal move) → the game reads from the bank → move acceptance.

## Open questions
Sent to the design chat in priority order:
- ~~P1~~ settled in the design chat on 2026-11-09 (see specs/position_pipeline_spec.md §7).
- ~~ECO code for shared opening source rows~~ settled by the user on 2026-11-11: the exactly matching line, otherwise the nearest named ancestor (spec §4).
- **P2, before points** (move_acceptance_spec): values of G and L, mate handling, showing the accepted set vs the top 3, challenge mode's pass rule.
- **P3, no spec yet** (scoring): points for acceptable moves and for moves outside the set, scoring the "only good move" claim, the overall points system.
- **P4, later**: defining quiet positions, choosing the next position, showing how a position arose, feedback after a bad move, difficulty matching, promotion picker, challenge-mode leftovers, accounts and stats, re-analysing after engine upgrades, extending openings, hosting.
