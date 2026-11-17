# Status
_Last saved: 2026-11-16 21:39 · Overwritten by /project-format-toolkit:save-state at the end of each session._

## Where things stand
- The game plays from the position bank: `uv run --env-file .env uvicorn chess_training.app:app --reload`, then open http://localhost:8000 (`?id=<n>` for one position). A random bank position; after the move: the verdict, the count of acceptable moves, arrows for up to 3 of them, a "show all" toggle, and the 2nd-best move in red in only-move positions (move acceptance §8). No engine runs while playing, and there is no "only good move" checkbox. Win-% losses show one decimal ("lost 5.2 win-%"). Attempts aren't recorded yet.
- Stack: FastAPI + python-chess, Postgres 16 in Docker, Stockfish 19 (pinned, `scripts/get_stockfish.py`) used only by the batch analysis, chessground 9.2.1 from a CDN. License GPL-3.0-or-later.
- Position bank: 7,717 opening and 5,000 puzzle positions. The full analysis finished on 2026-11-11: every position with legal moves (12,715) is scored. The 2 checkmate boards are never served.
- Specs in `specs/`: challenge mode = **ready**; position pipeline = **in progress** (step 6 part 1 of 3 built); move acceptance = **in progress** (everything built; G = L = 5 decided and in `config.yaml`); scoring = **in progress** (built, with blunder_line 15 and four difficulty buckets; the "only good move" claim removed, its column dropped by migration 0004; recording real moves and the Stats page are step 6 parts 2 and 3). `specs/spec_log.md` has the history.
- Design runs in a second Claude Code tab. It reads specs from main and writes new or updated specs only to `../chess_design_inbox/` (a folder next to the repo, outside it). The dev tab imports them by file name on a `docs/` branch. The full-bank tuning report is there: `acceptance_report_2026-11-16.txt`.

## Unfinished work
- None.

## Next steps
1. Step 6 part 2: record each move in `attempts` (`scoring.record_attempt`).
2. Step 6 part 3: the Stats page (layout placeholder: overall, then one table per breakdown, all-time and recent).
3. When the design chat sends specs back (it is working on choosing the next position): import them from the inbox on a `docs/` branch.

## Open questions
In the design chat (agenda in priority order):
- ~~P2~~ settled in the design chat on 2026-11-16: G (Max Single Drop) = L (Max Below Best) = 5 (move acceptance §9). Still open there: renaming the config keys (placeholder: keep `G` and `L`, names as comments) and caching the set size (placeholder: compute when needed; measured 0.69 ms per move).
- **P3** (scoring_spec): the data-dependent parts were settled on 2026-11-16: `blunder_line` = 15, difficulty buckets 1 / 2–4 / 5–9 / 10+, and the "only good move" claim removed. Small choices with placeholders: opening click-through, combined breakdowns, recomputing old attempts, the Stats page layout.
- **P4, built with placeholders now:** choosing the next position (uniform random), what the page shows before a move (phase and opening name only), promotion (always a queen).
- **P4, later:** defining quiet positions, showing how a position arose, feedback after a bad move, difficulty matching, challenge-mode leftovers, accounts and stats, re-analysing after engine upgrades, extending openings, hosting.
