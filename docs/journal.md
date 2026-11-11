# Journal
_Newest first. Short entries as work happens: what was done, what was learned, what surprised us._

## 2026-11-11 (endgame rule without queens)
- The user settled both open questions from the puzzle importer: the unplaced tags are not themes (#14), and endgames now allow 3 pieces for a side without a queen, checked per side.
- Added `relabel_phases`, because the importers only label boards they add for the first time. It changed 298 positions (all middlegame → endgame), and a second run changed none.
- The remaining 702 disagreements with Lichess are queen positions (Q+R+R v Q+R+R, Q+R+B v Q+R+N, and so on). That's deliberate.

## 2026-11-11 (puzzle importer)
- Built position pipeline step 4: `chess_training/puzzles.py` and `scripts/get_puzzles.py`. It streams the 310 MB zstd dump (new dependency: `zstandard`; Python 3.13 has no built-in zstd), filters it to 4.48M puzzles, samples 5,000 and upserts them. The whole run takes about 45 seconds, and a second run adds nothing.
- None of the 5,000 sampled boards were already in the bank from openings.
- The 3200–3399 band has only 14 puzzles in the whole dump. Its share went to the other bands, as designed.
- The phase check found a real gap: Lichess calls about 1,000 sampled puzzles endgames that our rule calls middlegame. Most have 3 pieces against 3 or 2. Sent to the design chat. The rule is unchanged.
- The rollback in this PR is the safe two-step version: delete the puzzle source rows, then only the positions left with no source.

## 2026-11-11 (puzzle opening tags column)
- Planning the puzzle importer found that spec §5 asks to store `OpeningTags` but §2 has no column for them. Migration 0002 adds `position_sources.puzzle_opening_tags` (nullable, so no backfill).
- Also settled while planning (they go in with the importer PR): the 11 theme tags the spec doesn't place are not themes for now (placeholder, sent to the design chat), and the rating bands are filled so that final totals are even.

## 2026-11-11 (opening importer)
- Built position pipeline step 3: `chess_training/openings.py` (pure build step + idempotent upsert), `scripts/get_openings.py` (pinned commit, checksum-verified), and `chess_training/fen.py` (`fen_key`, which the puzzle importer will reuse). It imports 7,717 positions and 8,499 source rows in about 8 seconds. 125 positions have more than one name, and none are unnamed. All are labelled opening (no endgames by move 10).
- The user settled the ECO question: exact match line, otherwise nearest ancestor.
- The schema tests used the position after 1.e4, which now exists in a filled bank. They switched to a bare-kings position no importer produces. The DB fixtures moved into conftest.py so other tests can share them.

## 2026-11-09 (phase labeller)
- Built position pipeline step 2: `label_phase()` in `chess_training/phase.py`, with its numbers in the `phase:` section of `config.yaml` and 16 tests.
- Planning found three gaps in spec §3: opening vs endgame overlap, queen endings and double-rook endings. The user settled all three: endgame wins, plus a limit of 2 pieces per side.
- Learned: with a piece limit of 2, the 8-point test is redundant (three pieces are at least 9 points). Kept it so the config stays flexible.
- The user asked that questions restate any shorthand (like "step 2"), since it isn't obvious without scrolling back. Saved as a standing preference.

## 2026-11-09 (position bank tables)
- Built position pipeline step 1: migration 0001 with `positions`, `position_sources` and `position_moves`, table definitions in `chess_training/db.py`, and 14 schema tests that run inside rolled-back transactions, so local data is never touched. CI now also runs `alembic check` and a downgrade/upgrade round trip.
- Docker Desktop wouldn't start (`ERROR_NO_SYSTEM_RESOURCES`): committed memory was 24 of 29 GB, and WSL2 tries to reserve half the RAM (about 8 GB). A stuck `vmmem` process survived `wsl --shutdown --force`. Fixed with `~/.wslconfig` (memory=3GB, swap=1GB) and a reboot.
- gitleaks flagged a FEN stored in a variable named `START_KEY` as an API key (a false positive triggered by the word "KEY"). Renamed the variable rather than allow-listing it.
- Spotted a spec conflict: the opening `source_ref` (the line's PGN) would break the unique rule on (`source`, `source_ref`). The user chose to use the moves played so far.

## 2026-11-09 (spec timestamps)
- The user added a `Last revised` timestamp to all three specs. Added rules to CLAUDE.md for keeping it current and for comparing an incoming spec against the repo copy. The spec log overview now shows the full timestamp.
- move_acceptance_spec's timestamp (2026-11-06T18:43-08:00) is the time of its last content change, not today. Timestamps record when the content last changed, not when it was imported.

## 2026-11-09 (specs back from the design chat)
- The user brought back updated position pipeline and challenge mode specs. The pipeline spec is now ready, with all its open questions settled, so development can start with the step 1 migration whenever the user says go.
- Added `specs/spec_log.md` at the user's request, recording when each spec was created, updated and built.
- The branch-name guard hook reads everything after the new-branch flag up to the end of the command, so a branch-creation command chained with a semicolon gets blocked. Run branch creation as its own command.

## 2026-11-06 (specs and design workflow)
- Set up a design workflow: the user discusses design in a Claude Desktop chat and drops the resulting specs into `specs/`. Added the challenge mode spec (from the user), plus position pipeline and move acceptance specs (drafts).
- The user proposed replacing "top 3" with a statistical "acceptable moves" rule. Refined it into a gap-based cut on win % with a cap. Standard deviation collapses when many moves tie and lets slow chains drift, and win % makes a pawn matter less when the game is already decided.
- Learned: checking the numbers mattered. I had quoted +0.2 as 53.7% win (it's 51.8%), and a cap of L=10 would accept a −0.85 move when the best is +0.2. L=6 fits the user's own "+1.0 → +0.2 is a real loss" (7.3 points).
- Learned: the Lichess puzzle database (about 5M) is far too big to score every move of every puzzle, so puzzles will be sampled.
- Produced a prioritized list of open questions for the design chat (P1 blocks development).

## 2026-11-06 (game loop skeleton)
- Built the first playable version: FastAPI + python-chess + Stockfish 19, and a chessground board page. Shows a sample position, takes the player's move and the "only good move" checkbox, then shows the top 3 moves as arrows, the move's score and the pawns lost.
- Stockfish 19 ships "universal" builds per OS that pick CPU features themselves, so the download script needs no CPU detection. Our SHA-256 checksums matched GitHub's published digests.
- Depth 18 takes about a second per position on this machine. Sample check: Caro-Kann Advance top 3 within 0.16 (several fine moves); Blackburne Shilling trap Qxg2 +7.2 vs about −5 for anything else (a clear only move).
- FastAPI's TestClient warns that `httpx` is deprecated in favour of `httpx2`; harmless for now.
- Tests skip without Stockfish locally but fail in CI (CI=true), so a broken download step can't hide behind skipped tests.

## 2026-11-06 (position sources)
- Decided the position sources: generated named-opening lines (up to move 10, both sides), plus Lichess puzzles and quiet positions from real Lichess games.
- Learned: Lichess puzzles already carry phase and opening-name tags, but their opening puzzles are tactics, not theory. Most named opening lines end before move 10.
- Agreed on one phase rule for all sources (opening by move number or theory, endgame by material).

## 2026-11-06 (later)
- After a restart, Docker Desktop was running; Postgres 16 came up healthy, and Alembic connected (no migrations yet).
- Created the public repo, pushed the scaffold commit; the first CI run passed (lint, gitleaks, migrations on a fresh DB, tests).
- Turned on the gates: pre-commit + commit-msg hooks, squash-only merges with branch auto-delete, and main protection requiring the `checks` job (admins included, no force-pushes).

## 2026-11-06
- Scaffolded the project with project-format-toolkit v1.2.0 (app, Postgres, PR template C).
- Captured the initial game concept in README: top-3 engine moves, the "only good move" checkbox, and scoring non-top-3 moves that don't make the eval meaningfully worse.
- Alembic's patched `migrations/env.py` had a comment over ruff's 100-char limit; wrapped it.
- Docker Desktop was installed but not running, so `docker compose up` failed; the user is restarting the machine before the Postgres step.
- The guard hook blocks any shell command that mentions `.env`, including `git check-ignore`.
