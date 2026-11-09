# Spec log
_The history of each spec: when it was written, each time it was updated, and when it was built. Newest first within each spec. Add a row whenever a spec is added, changes, or moves to another status (draft → ready → in progress → done). The project has no deploy target, so "built" means merged to main._

_**Last revised** is the `Last revised` line at the top of each spec (ISO 8601 local time with UTC offset). It must match the spec file. A spec edit's row uses the same timestamp. Rows from before 2026-11-09 have dates only._

## Overview

| Spec | Created | Last revised | Status | Built |
|---|---|---|---|---|
| [challenge_mode_spec.md](challenge_mode_spec.md) | 2026-11-06 | 2026-11-09T09:22-08:00 | ready | not started (needs the position bank) |
| [position_pipeline_spec.md](position_pipeline_spec.md) | 2026-11-06 | 2026-11-09T10:04-08:00 | in progress | step 1 of 6 (tables, #9) |
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
| 2026-11-09T10:04-08:00 | **Built step 1:** the `positions`, `position_sources` and `position_moves` tables (migration 0001). Spec revised: an opening's `source_ref` is the moves played to reach the position (user's decision, option A), because the full line's PGN would break the unique rule. | in progress | #9 |
| 2026-11-09 | Added the `Last revised` line (2026-11-09T09:22-08:00, the time of the design chat's last content change). No other change. | ready | #8 |
| 2026-11-09 | Updated from the design chat, settling every open question: one row per unique position plus a `position_sources` table, opening names based on the moves actually played (primary name plus a list of all names), a filtered puzzle sample of 5,000 with at least 30 per motif theme, two-pass engine scoring (depth 10, then depth 18 near the best move), and the fingerprint filled in later. | ready | #7 |
| 2026-11-06 | Created: build order, tables, phase labeller, opening and puzzle importers, batch analysis. Five open questions left with placeholders. | draft | #5 |

## move_acceptance_spec.md

| Date | Event | Status after | PR |
|---|---|---|---|
| 2026-11-09 | Added the `Last revised` line (2026-11-06T18:43-08:00, the time of the design chat's last content change). No other change. | draft | #8 |
| 2026-11-06 | Created: a gap-based acceptable-move rule in win %, replacing the fixed "top 3". G, L, mate handling and the challenge-mode pass rule are still open. | draft | #5 |
