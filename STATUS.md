# Status
_Last saved: 2026-11-11 11:31 · Overwritten by /project-format-toolkit:save-state at the end of each session._

## Where things stand
- Playable skeleton: `uv run uvicorn chess_training.app:app --reload`, then open http://localhost:8000. Four hardcoded sample positions; shows the top 3 moves (arrows), the player's score and the pawns lost. No points yet.
- Stack: FastAPI + python-chess + Stockfish 19 (pinned, downloaded by `scripts/get_stockfish.py` into tools/) + chessground 9.2.1 from a CDN. License GPL-3.0-or-later. Postgres 16 runs locally in Docker. The position bank (migrations 0001–0002) holds 7,717 opening positions and 5,000 puzzle positions. The README lists the commands that fill it.
- Design lives in `specs/`: challenge mode = **ready** (needs the position bank), position pipeline = **in progress** (steps 1–5 of 6 done: the tables, the phase labeller, the opening and puzzle importers, and batch analysis. The full analysis run is pending: 172 of 12,715 positions are scored), move acceptance = **in progress** (rule, verdict and tuning report built; the §8 display comes with step 6), scoring = **in progress** (built; recording real moves and the Stats page come with step 6). `specs/spec_log.md` records when each spec was created, updated and built. CLAUDE.md: build only what a spec marks Decided, and never settle its Open questions while coding.
- The user takes open questions to a separate design chat (Claude Desktop) and brings answers back as updated spec files.

## Unfinished work
- None.

## Next steps
1. Full analysis run: `uv run --env-file .env python -m chess_training.analysis` (about 4–5 hours in total, uses 10 of 12 cores). It can run in sessions of any length: Ctrl+C stops it cleanly, and the same command continues.
2. Then: re-run `python -m chess_training.acceptance_report` on the full bank for the design chat to tune G and L (tune on the opening grid), then position pipeline step 6 (the game reads from the bank: verdicts and arrows, recording attempts, the Stats page) (the game reads from the bank; it must skip the 2 checkmate positions that end the Fool's Mate and Sea-Cadet Mate lines) → move acceptance (G and L are placeholders in `config.yaml`).

## Open questions
Sent to the design chat in priority order:
- ~~P1~~ settled in the design chat on 2026-11-09 (see specs/position_pipeline_spec.md §7).
- ~~ECO code for shared opening source rows~~ settled by the user on 2026-11-11: the exactly matching line, otherwise the nearest named ancestor (spec §4).
- ~~Unplaced Lichess tags~~ settled by the user on 2026-11-11: not themes.
- ~~Endgame threshold vs Lichess~~ settled by the user on 2026-11-11: a side without a queen may have up to 3 pieces, checked per side (spec §3).
- **P2** (move_acceptance_spec, now ready): values of G and L, to tune in a later design chat from the §6 tuning report once the analysis finishes. Mate handling, the display and challenge mode's pass rule were settled in the design chat on 2026-11-11 (§7, §8; challenge mode §3).
- **P3** (scoring_spec, ready since 2026-11-11T13:46): progress is accuracy %, with no points. Needs real data: `blunder_line` (placeholder 15) and the difficulty buckets, settled with G and L. Small choices with placeholders: opening click-through, combined breakdowns, recomputing old attempts, the Stats page layout, and the claim in challenge mode.
- **P4, later**: defining quiet positions, choosing the next position, showing how a position arose, feedback after a bad move, difficulty matching, promotion picker, challenge-mode leftovers, accounts and stats, re-analysing after engine upgrades, extending openings, hosting.
