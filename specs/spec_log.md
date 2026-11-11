# Spec log
_The history of each spec: when it was written, each time it was updated, and when it was built. Newest first within each spec. Add a row whenever a spec is added, changes, or moves to another status (draft → ready → in progress → done). The project has no deploy target, so "built" means merged to main._

_**Last revised** is the `Last revised` line at the top of each spec (ISO 8601 local time with UTC offset). It must match the spec file. A spec edit's row uses the same timestamp. Rows from before 2026-11-09 have dates only._

## Overview

| Spec | Created | Last revised | Status | Built |
|---|---|---|---|---|
| [challenge_mode_spec.md](challenge_mode_spec.md) | 2026-11-06 | 2026-11-09T09:22-08:00 | ready | not started (needs the position bank) |
| [position_pipeline_spec.md](position_pipeline_spec.md) | 2026-11-06 | 2026-11-11T12:21-08:00 | in progress | steps 1–5 of 6 (tables #9, phase labeller #10, opening importer #11, puzzle importer #13, batch analysis #16); full analysis run pending |
| [move_acceptance_spec.md](move_acceptance_spec.md) | 2026-11-06 | 2026-11-06T18:43-08:00 | draft | not started |

## challenge_mode_spec.md

| Date | Event | Status after | PR |
|---|---|---|---|
| 2026-11-09 | Added the `Last revised` line (2026-11-09T09:22-08:00, the time of the design chat's last content change). No other change. | ready | #8 |
| 2026-11-09 | Updated from the design chat: when to compute the pawn fingerprint (backfill when challenge mode is built), only Lichess motif and mate-pattern tags count as themes, a "similar" puzzle shares at least one motif tag (more shared tags rank higher), and matching treats each unique position as one. | ready | #7 |
| 2026-11-06 | Created: repeat queue, similar positions by pawn-structure fingerprint and puzzle theme. | ready | #4 |

## position_pipeline_spec.md

| Date | Event | Status after | PR |
|---|---|---|---|
| 2026-11-11T12:21-08:00 | Batch analysis can be stopped with Ctrl+C and resumed, so the full run can be done in short sessions (the user's request). §6 note added. | in progress | #17 |
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

## move_acceptance_spec.md

| Date | Event | Status after | PR |
|---|---|---|---|
| 2026-11-09 | Added the `Last revised` line (2026-11-06T18:43-08:00, the time of the design chat's last content change). No other change. | draft | #8 |
| 2026-11-06 | Created: a gap-based acceptable-move rule in win %, replacing the fixed "top 3". G, L, mate handling and the challenge-mode pass rule are still open. | draft | #5 |
