# Journal
_Newest first. Short entries as work happens: what was done, what was learned, what surprised us._

## 2026-11-11 (move acceptance)
- Built the acceptable-set rule, the verdict and the tuning report while the analysis runs. They read stored scores only. Nothing touched `analysis.py` or the engine config, so a replacement worker can't load changed code.
- First report (4,604 positions): **puzzles are 99% only-move positions** and their wrong moves are all blunders. **Openings are 15% only-move**, with a median of 8 acceptable moves and a third close misses. G and L only really matter for openings, so the report gained an openings-only G × L grid. There, L drives the set size (5 / 8 / 11) and G drives the only-move share (23% → about 10%).
- The report runs in about 9 s on 4,600 positions.
- Review follow-up: a non-mating move in a mate position read "lost 0 win-%" and counted as a close miss. Its verdict now says "misses the mate", and the user decided that a missed mate is always a blunder (`miss_kind()`, scoring §6).

## 2026-11-11 (design chat round: move acceptance, challenge mode, scoring)
- The design chat sent updated move_acceptance and challenge_mode specs (forced mates, the pass rule, what the player sees after a move), merged in #20, and a new scoring spec: accuracy %, no points.
- Mistake, twice:
  - The commit for #20 used `git add -A`, which swept in the design chat's brand-new `scoring_spec.md` (13:27 draft), unreviewed and unlogged.
  - Then the 13:29 copy was reviewed, but the design chat overwrote it with 13:46 (status ready, §4–§7 added) before the commit. So #21's first records described a version that was never in git. The pr-reviewer caught it, and #21 now matches 13:46.
  - Lessons: stage spec imports by file name, never with `git add -A`. Just before committing, check each staged spec's `Last revised` against the one reviewed (`git show :specs/<file> | head -3`).
- Checked the scoring spec against the bank: there are 149 opening families over 7,717 named positions (about 50 each), so that breakdown isn't too thin. The 5,000 puzzle positions have no opening name and appear only in the other breakdowns. Attempts aren't stored yet, so building this spec needs a migration.

## 2026-11-11 (stop and resume the analysis)
- The user wants to run the 4–5 hour analysis in short sessions. It was already resumable, but Ctrl+C with 10 worker processes on Windows could leave a mess (tracebacks, a hang, orphaned Stockfish processes).
- Now: workers ignore Ctrl+C, Stockfish runs in its own process group, and the main process catches Ctrl+C (and Ctrl+Break), terminates the pool and prints "Stopped. … X of 12,715 done. Run the same command again to continue."
- Tested on this machine with a real Ctrl+Break after 25 s: it exited in 5 s with code 0, no stockfish.exe was left, the 17 positions finished were saved, and a restart carried on (167 → 172).
- The time estimate from a short session runs high (6.9 h from a 30 s session), because it includes starting 10 engines.

## 2026-11-11 (batch analysis)
- Built position pipeline step 5: `chess_training/analysis.py` (two-pass Stockfish scoring, 10 parallel workers, resumable) and `chess_training/winpct.py`.
- Timing on the first 100 positions: 98 s wall time. 50 more took 56 s. The review pointed out that the simple estimate (3.4 h) ignored the bank's mix: 61% openings, against 55% in the sample. Weighted by what is left, it's about 4–5 hours. Opening positions average 13.5 s, because about 14 of their 32 moves stay within 15 win-% of the best and get the depth-18 pass. Puzzles average 1–3 s, with about 2 moves sent deep.
- Spot check: after 1.e4 e5 2.f4 d5 (Falkbeer), the stored best moves are exd5 −0.19 and Nf3 −0.21, both at depth 18.
- The 150 analysed positions stay in the bank. The full run skips them.
- Two bank positions have no legal moves: the mates that end "Fool's Mate" and "Sea-Cadet Mate". Analysis now skips and reports them. Before the fix they would have stayed pending forever. Step 6 must not serve them.
- Review fixes before the long run: store the depth Stockfish actually reached, log a failed position and carry on, weight the estimate by the remaining mix, and test that a fresh engine gives the same scores as a used one.

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
