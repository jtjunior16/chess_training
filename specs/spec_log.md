# Spec log
_The history of each spec: when it was written, each time it was updated, and when it was built. Newest first within each spec. Add a row whenever a spec is added, changes, or moves to another status (draft → ready → in progress → done). The project has no deploy target, so "built" means merged to main._

_**Last revised** is the `Last revised` line at the top of each spec (ISO 8601 local time with UTC offset). It must match the spec file. A spec edit's row uses the same timestamp. Rows from before 2026-11-09 have dates only._

## Overview

| Spec | Created | Last revised | Status | Built |
|---|---|---|---|---|
| [challenge_mode_spec.md](challenge_mode_spec.md) | 2026-11-06 | 2026-11-16T12:45-08:00 | ready | not started (the position bank is ready) |
| [position_pipeline_spec.md](position_pipeline_spec.md) | 2026-11-06 | 2026-11-16T11:42-08:00 | in progress | steps 1–5 of 6 (tables #9, phase labeller #10, opening importer #11, puzzle importer #13, batch analysis #16); full analysis run done; step 6 part 1 of 3 (the game reads from the bank, #26) |
| [scoring_spec.md](scoring_spec.md) | 2026-11-11 | 2026-11-16T12:45-08:00 | in progress | §1–§7 built (attempts table #24, scoring #25); blunder_line and four buckets in config.yaml (#29); the claim removed (#30) and its column dropped (migration 0004, #31); the Stats page and real recording come with pipeline step 6 |
| [move_acceptance_spec.md](move_acceptance_spec.md) | 2026-11-06 | 2026-11-16T12:45-08:00 | in progress | rule, verdict and tuning report built (#22); the §8 display (#26); G = L = 5 in config.yaml (§9, #29) |

## challenge_mode_spec.md

| Date | Event | Status after | PR |
|---|---|---|---|
| 2026-11-16T13:02-08:00 | Checkbox removal (§2, §3) built for the shared board page, which challenge mode will use. Challenge mode itself is not built. | ready | #30 |
| 2026-11-16T12:45-08:00 | Updated from the design chat (newer than the repo copy, so it replaced it). The "only good move" checkbox is removed from challenge mode too (§2 step 3, §3). Pass/fail is unchanged. | ready | #27 |
| 2026-11-11T13:20-08:00 | Updated from the design chat (newer than the repo copy, so it replaced it). Pass/fail is decided: a move passes if it is in the acceptable set, the same function as normal mode's verdict (new §3). This replaces the "top 3 or ≤ 0.3 pawns" placeholder. | ready | #20 |
| 2026-11-09 | Added the `Last revised` line (2026-11-09T09:22-08:00, the time of the design chat's last content change). No other change. | ready | #8 |
| 2026-11-09 | Updated from the design chat: when to compute the pawn fingerprint (backfill when challenge mode is built), only Lichess motif and mate-pattern tags count as themes, a "similar" puzzle shares at least one motif tag (more shared tags rank higher), and matching treats each unique position as one. | ready | #7 |
| 2026-11-06 | Created: repeat queue, similar positions by pawn-structure fingerprint and puzzle theme. | ready | #4 |

## position_pipeline_spec.md

| Date | Event | Status after | PR |
|---|---|---|---|
| 2026-11-16T11:42-08:00 | **Built step 6, part 1 of 3:** the game reads from the bank (`chess_training/game.py`); the hardcoded positions and the live engine are removed. Only positions with stored scores are served, so the two checkmate boards are left out and the positions one move before them are played. Also recorded: the full analysis run finished on 2026-11-11 (12,715 positions). Step 6 is split into 3 PRs: this one, recording attempts, the Stats page. | in progress | #26 |
| 2026-11-11T12:21-08:00 | Batch analysis can be stopped with Ctrl+C and resumed, so the full run can be done in short sessions (the user's request). §6 note added. | in progress | #18 |
| 2026-11-11T12:03-08:00 | **Built step 5:** batch engine analysis (`chess_training/analysis.py`, `chess_training/winpct.py`). The first 150 positions took 154 s with 10 workers; weighted by the bank's mix, the full bank is estimated at about 4–5 hours. Two checkmate positions (the ends of the named Fool's Mate and Sea-Cadet Mate lines) are skipped. Opening positions are the costly ones (about 14 moves per position get the deep pass). §6 revised with the details approved in the build plan: deep_margin ≥ 2 × L, the hash cleared per position, a fixed shuffled run order. | in progress | #16 |
| 2026-11-11T11:42-08:00 | Open question settled by the user: §3's endgame rule gains a per-side "no queen, at most 3 pieces" test. Built with a relabeller (`chess_training/relabel_phases.py`) that moved 298 positions from middlegame to endgame. The Lichess endgame disagreement fell from 1,000 to 702 puzzles, almost all with queens on. No open questions remain. | in progress | #15 |
| 2026-11-11T11:39-08:00 | Open question settled by the user: the 11 Lichess tags the spec didn't place (advancedPawn, attackingF2F7, castling, enPassant, exposedKing, kingsideAttack, queensideAttack, promotion, underPromotion, collinearMove, defensiveMove) are **not** themes. No code change: it was already the placeholder. | in progress | #14 |
| 2026-11-11T11:29-08:00 | **Built step 4:** the puzzle importer (`chess_training/puzzles.py`, `scripts/get_puzzles.py`). It samples 5,000 of 4.48M filtered puzzles from the 2026-11-01 dump, pinned by checksum. §5 revised with the user's decisions: final band totals as even as possible; the 11 unplaced theme tags are not themes for now (placeholder). Two new open questions: the unplaced tags, and our endgame threshold against Lichess's, which disagree on 1,000 puzzles. | in progress | #13 |
| 2026-11-11T11:22-08:00 | Updated while planning step 4: `position_sources` gets a `puzzle_opening_tags` column (migration 0002) for Lichess's `OpeningTags`, which §5 asked to store but §2 had no column for. The user chose a new column. | in progress | #12 |
| 2026-11-11T11:07-08:00 | **Built step 3:** the opening importer (`chess_training/openings.py`, `scripts/get_openings.py`), with the source pinned to lichess-org/chess-openings commit 3ba6b20. It imports 7,717 positions and 8,499 source rows. Spec §4 revised: the user decided that `opening_eco` is the ECO of the exactly matching line, otherwise the nearest named ancestor. Also recorded: "up to move 10" includes Black's 10th move, and equal-length names are broken alphabetically. | in progress | #11 |
| 2026-11-09T10:59-08:00 | **Built step 2:** the phase labeller (`chess_training/phase.py`). Spec §3 revised with the user's decisions: endgame is checked first and beats opening, and a side with at most 2 pieces counts towards an endgame as well as one with at most 8 points. | in progress | #10 |
| 2026-11-09T10:04-08:00 | **Built step 1:** the `positions`, `position_sources` and `position_moves` tables (migration 0001). Spec revised: an opening's `source_ref` is the moves played to reach the position (user's decision, option A), because the full line's PGN would break the unique rule. | in progress | #9 |
| 2026-11-09 | Added the `Last revised` line (2026-11-09T09:22-08:00, the time of the design chat's last content change). No other change. | ready | #8 |
| 2026-11-09 | Updated from the design chat, settling every open question: one row per unique position plus a `position_sources` table, opening names based on the moves actually played (primary name plus a list of all names), a filtered puzzle sample of 5,000 with at least 30 per motif theme, two-pass engine scoring (depth 10, then depth 18 near the best move), and the fingerprint filled in later. | ready | #7 |
| 2026-11-06 | Created: build order, tables, phase labeller, opening and puzzle importers, batch analysis. Five open questions left with placeholders. | draft | #5 |

## scoring_spec.md

| Date | Event | Status after | PR |
|---|---|---|---|
| 2026-11-16T13:05-08:00 | **Built §7 (claim column dropped):** migration 0004 drops `attempts.claimed_only_move` (Claude's call, which the spec left open). The table had 0 rows, so nothing was lost. Downgrade re-adds it as NOT NULL default false. | in progress | #31 |
| 2026-11-16T13:02-08:00 | **Built §4 (claim removed):** the claim figures are gone from `/api/stats` and the text report, and `record_attempt()` no longer takes a claim. Until migration 0004 drops `attempts.claimed_only_move`, it writes false. | in progress | #30 |
| 2026-11-16T12:57-08:00 | **Built §3 and §6 values:** `scoring.difficulty_buckets: [1, 4, 9]` (four buckets, no code change needed) and `blunder_line: 15` marked decided in `config.yaml`. Recomputing stored attempts changed 0 (none exist yet). | in progress | #29 |
| 2026-11-16T12:45-08:00 | Updated from the design chat (newer than the repo copy, so it replaced it). Decided by the user: `blunder_line` = 15 (§6); difficulty buckets 1 / 2–4 / 5–9 / 10+ (§3, config `[1, 4, 9]`); the "only good move" claim is removed with its figures (§4, §7), replacing the 2026-11-11 claim decision. Whether `attempts.claimed_only_move` is dropped is left to Claude Code. No data-dependent questions remain. | in progress | #27 |
| 2026-11-11T14:26-08:00 | **Built §1–§7:** the `attempts` table (migration 0003, #24), plus `record_attempt()`, the figures (acceptable / close miss / blunder shares, all-time and recent, minimum 10, five breakdowns, claim accuracy and spotting rate, repeats left out), `recompute_attempts()`, a text report and `/api/stats` (#25). Nothing records real moves yet. That and the Stats page come with pipeline step 6. | in progress | #25 |
| 2026-11-11T14:16-08:00 | Decided by the user (a question found while building move acceptance): when the best move forces mate, a move that doesn't mate is **always a blunder** (§6), even though win % puts +8 only about 5 points below a mate. Built as `acceptance.miss_kind()`, which the tuning report uses now and scoring will use. | ready | #23 |
| 2026-11-11T13:46-08:00 | **Status → ready** (from the design chat, newer than the 13:27 copy in main). Build now with the placeholders. Decided since 13:27: recent = the last 50 attempts per group, with groups under 10 attempts showing "not enough data yet" (§2); breakdowns by phase, opening family, side, difficulty and puzzle theme, with no source breakdown (§3); the "only good move" claim measured as claim accuracy and spotting rate (§4); challenge-mode repeats don't count (§5); misses split into close misses and blunders at `blunder_line` (§6); what each attempt records (§7). Open, with placeholders: `blunder_line` (15), the difficulty buckets, opening click-through, combined breakdowns, recomputing old attempts, the Stats page layout, and the claim in challenge mode. An intermediate 13:29 copy (adding §3) was reviewed but never committed; the design chat overwrote it before the commit. | ready | #21 |
| 2026-11-11T13:27-08:00 | Created in the design chat: progress is **accuracy %** (acceptable moves ÷ moves played), with no points, running score or streaks, each figure shown all-time and over a recent window. Imported by accident inside #20 (Claude's `git add -A` picked up the new file), so it wasn't logged then. | draft | #20 |

## move_acceptance_spec.md

| Date | Event | Status after | PR |
|---|---|---|---|
| 2026-11-16T13:14-08:00 | Built a display change the user asked for: win-% losses in the verdict (§4) and the 2nd-best label (§8) show one decimal ("lost 5.2 win-%"), so a loss just over L doesn't read as "lost 5". The spec's examples still use whole numbers; the design chat may want to update them. | in progress | #33 |
| 2026-11-16T13:02-08:00 | **Built §4 and §8 (checkbox removed):** the board page has no "only good move" checkbox and no "You said…" line, and `/api/move` no longer takes `only_move`. The 2nd-best red arrow stays. | in progress | #30 |
| 2026-11-16T12:57-08:00 | **Built §9:** `move_acceptance.L: 5` (G stays 5), with Max Single Drop and Max Below Best as comments; the tuning report and the scoring text report use the names. The report reproduces §9's figures: openings 14% only-move, median size 6, 37% with 10+. | in progress | #29 |
| 2026-11-16T12:45-08:00 | Updated from the design chat (newer than the repo copy, which it was based on, so it replaced it). Decided by the user: **G = L = 5** (new §9, with the full-bank figures and options considered); G is called "Max Single Drop" and L "Max Below Best" in text and on screen (§2). New open question: rename the config keys (placeholder: keep `G` and `L`, names as comments). The checkbox mentions in §4 and §8 are gone. Caching question, measured by Claude Code on 2026-11-16: building a position's acceptable set takes 0.69 ms per move (median over 300 bank positions, max 2.6 ms), so "compute when needed" holds. | in progress | #27 |
| 2026-11-16T11:42-08:00 | **Built §8:** what the player sees after moving: the verdict, the count line, arrows for at most 3 acceptable moves, a "show all" toggle, and in only-move positions the 2nd-best move in red with its loss ("misses the mate" when the best move mates). G and L are still placeholders; the full-bank tuning report is ready for the design chat. | in progress | #26 |
| 2026-11-11T14:05-08:00 | **Built:** the acceptable-set rule (§2, with forced mates per §7), the verdict on a move (§4, e.g. "Acceptable (7th of 12)") and the §6 tuning report, plus a blunder_line split and G × L grids (overall and openings only). First numbers on partial data: puzzles 99% only-move, openings 15% with a median of 8 acceptable moves, so G and L should be tuned on openings. The §8 display waits for pipeline step 6. | in progress | #22 |
| 2026-11-11T13:46-08:00 | **Status → ready** (from the design chat, newer than the 13:20 copy). Build now with the G and L placeholders. They are tuned in a later design chat from the §6 tuning report, run after the full analysis. Caching the set size is a performance detail to measure once built. | ready | #21 |
| 2026-11-11T13:20-08:00 | Updated from the design chat (newer than the repo copy, so it replaced it). Three open questions decided. Forced mates (new §7): when the best move forces mate, only moves that also force mate are acceptable, at any length. What the player sees (new §8): arrows for up to 3 acceptable moves, a verdict on the player's move, a count line, a "show all" toggle, and in only-move positions the 2nd-best move marked with what it loses. Challenge mode passes on the acceptable set (§4). Still open: G, L, and whether to cache the set size. | draft | #20 |
| 2026-11-09 | Added the `Last revised` line (2026-11-06T18:43-08:00, the time of the design chat's last content change). No other change. | draft | #8 |
| 2026-11-06 | Created: a gap-based acceptable-move rule in win %, replacing the fixed "top 3". G, L, mate handling and the challenge-mode pass rule are still open. | draft | #5 |

## Pending design decisions (snapshot, 2026-11-16T12:51-08:00)
_Every open question across the specs, for the design chat. In priority order. Each one runs on its stated placeholder until it is decided. Replace this snapshot when it goes out of date._

**Settled on 2026-11-16 (design chat):** G = L = 5, with the names "Max Single Drop" and "Max Below Best"; `blunder_line` = 15; difficulty buckets 1 / 2–4 / 5–9 / 10+; the "only good move" checkbox removed everywhere. Every earlier question settled on 2026-11-09 and 2026-11-11 is in the history above.

### 1. Needed for step 6 (the game reads from the bank; being worked on in the design chat now)
| Question | Placeholder now |
|---|---|
| Choosing the next position | Uniformly random over every playable bank position (`game.position_choice: random`), about 61% openings |
| What the page shows before the move | The phase and the opening name only; puzzle theme tags hidden |
| Promotion picker | Always a queen |

Also open: showing how a position arose (`moves_to_position`, the opening name, the puzzle's source game), and feedback after a bad move (the bank stores no lines, so a refutation needs stored lines or one live engine call).

### 2. Move acceptance ([move_acceptance_spec.md](move_acceptance_spec.md))
| Question | Placeholder now |
|---|---|
| Rename the config keys `G` and `L` (e.g. `max_single_drop`, `max_below_best`)? | Keep `G` and `L`, names as comments |
| Cache the acceptable-set size per position? | Compute when needed (measured: 0.69 ms per move) |

### 3. Scoring ([scoring_spec.md](scoring_spec.md)), small design choices
| Question | Placeholder now |
|---|---|
| Click through from an opening family to its variations? | No |
| Combined breakdowns (e.g. Caro-Kann as Black; would separate the only-move bucket from phase) | No |
| Recompute old attempts when G, L or blunder_line change? | Yes, from the stored move and scores |
| Where the figures are shown | One Stats page: overall, then one table per breakdown |

### 4. Challenge mode ([challenge_mode_spec.md](challenge_mode_spec.md), ready)
| Question | Placeholder now |
|---|---|
| Cap on run length (each failure adds 3 positions) | No cap. Max queue size is a config value, off by default |
| Order of the items added to the queue | The 2 similar positions first, then the repeat |
| Disguise repeats by flipping colours (middlegame and endgame only) | Off |
| What the 15 are sampled from | All phases, uniformly at random |
| Challenge length | 15 |

### 5. Later
- Defining "quiet" positions taken from real Lichess games (needs its own spec).
- Difficulty matching to the player.
- Accounts and stats.
- Re-analysing the bank after an engine upgrade.
- Extending openings past move 10.
- Hosting.
