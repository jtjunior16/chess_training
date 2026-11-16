# Status
_Last saved: 2026-11-16 11:50 · Overwritten by /project-format-toolkit:save-state at the end of each session._

## Where things stand
- The game plays from the position bank: `uv run --env-file .env uvicorn chess_training.app:app --reload`, then open http://localhost:8000 (`?id=<n>` for one position). A random bank position; after the move: the verdict, the count of acceptable moves, arrows for up to 3 of them, a "show all" toggle, and the 2nd-best move in red in only-move positions (move acceptance §8). No engine runs while playing. Attempts aren't recorded yet.
- Stack: FastAPI + python-chess, Postgres 16 in Docker, Stockfish 19 (pinned, `scripts/get_stockfish.py`) used only by the batch analysis, chessground 9.2.1 from a CDN. License GPL-3.0-or-later.
- Position bank: 7,717 opening and 5,000 puzzle positions. The full analysis finished on 2026-11-11: every position with legal moves (12,715) is scored. The 2 checkmate boards are never served.
- Specs in `specs/`: challenge mode = **ready**; position pipeline = **in progress** (step 6 part 1 of 3 built); move acceptance = **in progress** (everything built; G and L are placeholders); scoring = **in progress** (built; recording real moves and the Stats page are step 6 parts 2 and 3). `specs/spec_log.md` has the history.
- Design runs in a second Claude Code tab. It reads specs from main and writes new or updated specs only to `C:\Users\jtjun\code\chess_design_inbox\` (outside the repo). The dev tab imports them by file name on a `docs/` branch. The full-bank tuning report is there: `acceptance_report_2026-11-16.txt`.

## Unfinished work
- None.

## Next steps
1. Step 6 part 2: record each move in `attempts` (`scoring.record_attempt`).
2. Step 6 part 3: the Stats page (layout placeholder: overall, then one table per breakdown, all-time and recent).
3. When the design chat sends specs back: import them from the inbox, then update G, L, blunder_line and the difficulty buckets in `config.yaml` and run `python -m chess_training.scoring --recompute`.

## Open questions
In the design chat (agenda in priority order):
- **P2** (move_acceptance_spec): values of G and L. Tune them on the openings-only grid of the full-bank report.
- **P3** (scoring_spec): `blunder_line` (placeholder 15) and the difficulty buckets (placeholder 1 / 2–4 / 5+), settled with G and L. Small choices with placeholders: opening click-through, combined breakdowns, recomputing old attempts, the Stats page layout, the claim in challenge mode.
- **P4, built with placeholders now:** choosing the next position (uniform random), what the page shows before a move (phase and opening name only), promotion (always a queen).
- **P4, later:** defining quiet positions, showing how a position arose, feedback after a bad move, difficulty matching, challenge-mode leftovers, accounts and stats, re-analysing after engine upgrades, extending openings, hosting.
