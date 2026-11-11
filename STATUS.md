# Status
_Last saved: 2026-11-11 11:31 · Overwritten by /project-format-toolkit:save-state at the end of each session._

## Where things stand
- Playable skeleton: `uv run uvicorn chess_training.app:app --reload`, then open http://localhost:8000. Four hardcoded sample positions; shows the top 3 moves (arrows), the player's score and the pawns lost. No points yet.
- Stack: FastAPI + python-chess + Stockfish 19 (pinned, downloaded by `scripts/get_stockfish.py` into tools/) + chessground 9.2.1 from a CDN. License GPL-3.0-or-later. Postgres 16 runs locally in Docker. The position bank (migrations 0001–0002) holds 7,717 opening positions and 5,000 puzzle positions. The README lists the commands that fill it.
- Design lives in `specs/`: challenge mode = **ready** (needs the position bank), position pipeline = **in progress** (steps 1–4 of 6 done: the tables, the phase labeller, and the opening and puzzle importers), move acceptance = **draft**. `specs/spec_log.md` records when each spec was created, updated and built. CLAUDE.md: build only what a spec marks Decided, and never settle its Open questions while coding.
- The user takes open questions to a separate design chat (Claude Desktop) and brings answers back as updated spec files.

## Unfinished work
- None.

## Next steps
1. Position pipeline step 5 of 6: batch engine analysis (spec §6). It scores every legal move of all 12,717 positions in two passes (depth 10, then depth 18 near the best), times the first 100 and reports the cost before the full run.
2. Then: the game reads from the bank → move acceptance.

## Open questions
Sent to the design chat in priority order:
- ~~P1~~ settled in the design chat on 2026-11-09 (see specs/position_pipeline_spec.md §7).
- ~~ECO code for shared opening source rows~~ settled by the user on 2026-11-11: the exactly matching line, otherwise the nearest named ancestor (spec §4).
- ~~Unplaced Lichess tags~~ settled by the user on 2026-11-11: not themes.
- ~~Endgame threshold vs Lichess~~ settled by the user on 2026-11-11: a side without a queen may have up to 3 pieces, checked per side (spec §3).
- **P2, before points** (move_acceptance_spec): values of G and L, mate handling, showing the accepted set vs the top 3, challenge mode's pass rule.
- **P3, no spec yet** (scoring): points for acceptable moves and for moves outside the set, scoring the "only good move" claim, the overall points system.
- **P4, later**: defining quiet positions, choosing the next position, showing how a position arose, feedback after a bad move, difficulty matching, promotion picker, challenge-mode leftovers, accounts and stats, re-analysing after engine upgrades, extending openings, hosting.
