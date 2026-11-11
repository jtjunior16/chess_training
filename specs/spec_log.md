# Spec log
_The history of each spec: when it was written, each time it was updated, and when it was built. Newest first within each spec. Add a row whenever a spec is added, changes, or moves to another status (draft → ready → in progress → done). The project has no deploy target, so "built" means merged to main._

_**Last revised** is the `Last revised` line at the top of each spec (ISO 8601 local time with UTC offset). It must match the spec file. A spec edit's row uses the same timestamp. Rows from before 2026-11-09 have dates only._

## Overview

| Spec | Created | Last revised | Status | Built |
|---|---|---|---|---|
| [challenge_mode_spec.md](challenge_mode_spec.md) | 2026-11-06 | 2026-11-11T13:20-08:00 | ready | not started (needs the position bank) |
| [position_pipeline_spec.md](position_pipeline_spec.md) | 2026-11-06 | 2026-11-11T12:21-08:00 | in progress | steps 1–5 of 6 (tables #9, phase labeller #10, opening importer #11, puzzle importer #13, batch analysis #16); full analysis run pending |
| [scoring_spec.md](scoring_spec.md) | 2026-11-11 | 2026-11-11T13:46-08:00 | ready | not started (needs move acceptance and a table for attempts) |
| [move_acceptance_spec.md](move_acceptance_spec.md) | 2026-11-06 | 2026-11-11T14:05-08:00 | in progress | rule, verdict and tuning report built (#22); the §8 display comes with pipeline step 6 |

## challenge_mode_spec.md

| Date | Event | Status after | PR |
|---|---|---|---|
| 2026-11-11T13:20-08:00 | Updated from the design chat (newer than the repo copy, so it replaced it). Pass/fail is decided: a move passes if it is in the acceptable set, the same function as normal mode's verdict (new §3). This replaces the "top 3 or ≤ 0.3 pawns" placeholder. | ready | #20 |
| 2026-11-09 | Added the `Last revised` line (2026-11-09T09:22-08:00, the time of the design chat's last content change). No other change. | ready | #8 |
| 2026-11-09 | Updated from the design chat: when to compute the pawn fingerprint (backfill when challenge mode is built), only Lichess motif and mate-pattern tags count as themes, a "similar" puzzle shares at least one motif tag (more shared tags rank higher), and matching treats each unique position as one. | ready | #7 |
| 2026-11-06 | Created: repeat queue, similar positions by pawn-structure fingerprint and puzzle theme. | ready | #4 |

## position_pipeline_spec.md

| Date | Event | Status after | PR |
|---|---|---|---|
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
| 2026-11-11T13:46-08:00 | **Status → ready** (from the design chat, newer than the 13:27 copy in main). Build now with the placeholders. Decided since 13:27: recent = the last 50 attempts per group, with groups under 10 attempts showing "not enough data yet" (§2); breakdowns by phase, opening family, side, difficulty and puzzle theme, with no source breakdown (§3); the "only good move" claim measured as claim accuracy and spotting rate (§4); challenge-mode repeats don't count (§5); misses split into close misses and blunders at `blunder_line` (§6); what each attempt records (§7). Open, with placeholders: `blunder_line` (15), the difficulty buckets, opening click-through, combined breakdowns, recomputing old attempts, the Stats page layout, and the claim in challenge mode. An intermediate 13:29 copy (adding §3) was reviewed but never committed; the design chat overwrote it before the commit. | ready | #21 |
| 2026-11-11T13:27-08:00 | Created in the design chat: progress is **accuracy %** (acceptable moves ÷ moves played), with no points, running score or streaks, each figure shown all-time and over a recent window. Imported by accident inside #20 (Claude's `git add -A` picked up the new file), so it wasn't logged then. | draft | #20 |

## move_acceptance_spec.md

| Date | Event | Status after | PR |
|---|---|---|---|
| 2026-11-11T14:05-08:00 | **Built:** the acceptable-set rule (§2, with forced mates per §7), the verdict on a move (§4, e.g. "Acceptable (7th of 12)") and the §6 tuning report, plus a blunder_line split and G × L grids (overall and openings only). First numbers on partial data: puzzles 99% only-move, openings 15% with a median of 8 acceptable moves, so G and L should be tuned on openings. The §8 display waits for pipeline step 6. | in progress | #22 |
| 2026-11-11T13:46-08:00 | **Status → ready** (from the design chat, newer than the 13:20 copy). Build now with the G and L placeholders. They are tuned in a later design chat from the §6 tuning report, run after the full analysis. Caching the set size is a performance detail to measure once built. | ready | #21 |
| 2026-11-11T13:20-08:00 | Updated from the design chat (newer than the repo copy, so it replaced it). Three open questions decided. Forced mates (new §7): when the best move forces mate, only moves that also force mate are acceptable, at any length. What the player sees (new §8): arrows for up to 3 acceptable moves, a verdict on the player's move, a count line, a "show all" toggle, and in only-move positions the 2nd-best move marked with what it loses. Challenge mode passes on the acceptable set (§4). Still open: G, L, and whether to cache the set size. | draft | #20 |
| 2026-11-09 | Added the `Last revised` line (2026-11-06T18:43-08:00, the time of the design chat's last content change). No other change. | draft | #8 |
| 2026-11-06 | Created: a gap-based acceptable-move rule in win %, replacing the fixed "top 3". G, L, mate handling and the challenge-mode pass rule are still open. | draft | #5 |

## Pending design decisions (snapshot, 2026-11-11T12:55-08:00, updated 2026-11-11T13:46-08:00)
_Every open question across the specs, for the design chat. In priority order. Each one runs on its stated placeholder until it is decided. Replace this snapshot when it goes out of date._

**Already settled today, so skip these:** opening ECO per source row, the 11 unplaced puzzle tags (not themes), the endgame rule (a side without a queen may have up to 3 pieces), from the design chat at 13:20, forced mates, challenge mode's pass rule and what the player sees after moving (move acceptance §7–§8, challenge mode §3); and at 13:46 the scoring spec's §1–§7 (accuracy %, the recent window, breakdowns, the claim figures, which attempts count, and close misses vs blunders), with scoring and move acceptance both marked ready. The position pipeline spec has no open questions left.

### 1. Move acceptance ([move_acceptance_spec.md](move_acceptance_spec.md), rule and tuning report **built** 14:04, G and L are placeholders)
Tuning aid: `python -m chess_training.acceptance_report`. On partial data, puzzles are about 99% only-move positions whatever G and L are, so tune on the **opening grid**: L sets the set size (median 5 / 8 / 11 for L = 4 / 6 / 7.5), and G sets the only-move share (23% at G = 3 down to about 10% at G = 8).
Batch analysis will have scored every legal move of all 12,715 bank positions by about 16:30 today. After that, the spec's §6 tuning report can show real acceptable-set sizes for any G and L.
| Question | Placeholder now |
|---|---|
| **G**, the break size between consecutive moves (win-% points) | 5 (`move_acceptance.G` in `config.yaml`) |
| **L**, the cap below the best move (win-% points) | 6. It must stay at or below 7.5, because the analysis deep pass covers moves within 15 of the best and checks deep_margin ≥ 2 × L |
| Cache the acceptable-set size per position, or compute it when needed? | Compute when needed |

Suggested approach: settle the *method* now (for example, "pick G and L so that X% of positions are only-move positions"), and pick the numbers once the tuning report has real data.

### 2. Scoring ([scoring_spec.md](scoring_spec.md), **ready** since 13:46: build with placeholders). Progress is accuracy %, not points
Needs real data (settle together with G and L):
| Question | Placeholder now |
|---|---|
| Value of `blunder_line` (close miss vs blunder) | 15 win-% points, and it must stay ≤ the analysis deep_margin (15) |
| Difficulty bucket boundaries | 1 / 2–4 / 5+ |

Small design choices (they don't block the build):
| Question | Placeholder now |
|---|---|
| Click through from an opening family to its variations? | No |
| Combined breakdowns (e.g. Caro-Kann as Black) | No |
| Recompute old attempts when G, L or blunder_line change? | Yes, from the stored move and scores |
| Where the figures are shown | One Stats page: overall, then one table per breakdown |
| Should a wrong or missed claim also fail a challenge position? | No |

**For the design chat to fix:** move acceptance's open-questions note says the tuning report runs after "the full analysis run (position pipeline step 6)". The full analysis run belongs to step 5. Step 6 is the game reading from the bank.

### 3. Challenge mode ([challenge_mode_spec.md](challenge_mode_spec.md), ready)
| Question | Placeholder now |
|---|---|
| Cap on run length (each failure adds 3 positions) | No cap. Max queue size is a config value, off by default |
| Order of the items added to the queue | The 2 similar positions first, then the repeat |
| Disguise repeats by flipping colours (middlegame and endgame only) | Off |
| What the 15 are sampled from | All phases, uniformly at random |
| Challenge length | 15 |

### 4. Needed for step 6 (the game reads from the bank), no spec yet
- **Choosing the next position:** random, by phase or opening, by difficulty (acceptable-set size), or something else. Placeholder if not decided: uniform random over bank positions that have legal moves.
- **What the game shows after a move:** decided in move acceptance §8. Still open: should it also show how the position arose (`moves_to_position`, the opening name, the puzzle's source game)?
- **Feedback after a bad move:** for example the refutation line. The bank stores scores but no lines (PVs). Showing lines would mean storing them, or running the engine live for that one move.
- **Promotion picker** (the board currently can't choose a promotion piece).
- Note, not a question: two bank positions are checkmates with no move to play (the ends of the named "Fool's Mate" and "Sea-Cadet Mate" lines). The game will skip them.

### 5. Later
- Defining "quiet" positions taken from real Lichess games (needs its own spec).
- Difficulty matching to the player.
- Accounts and stats.
- Re-analysing the bank after an engine upgrade.
- Extending openings past move 10.
- Hosting.
