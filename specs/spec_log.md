# Spec log
_The history of each spec: when it was written, each time it was updated, and when it was built. Newest first within each spec. Add a row whenever a spec is added, changes, or moves to another status (draft → ready → in progress → done). The project has no deploy target, so "built" means merged to main._

## Overview

| Spec | Created | Last updated | Status | Built |
|---|---|---|---|---|
| [challenge_mode_spec.md](challenge_mode_spec.md) | 2026-11-06 | 2026-11-09 | ready | not started (needs the position bank) |
| [position_pipeline_spec.md](position_pipeline_spec.md) | 2026-11-06 | 2026-11-09 | ready | not started |
| [move_acceptance_spec.md](move_acceptance_spec.md) | 2026-11-06 | 2026-11-06 | draft | not started |

## challenge_mode_spec.md

| Date | Event | Status after | PR |
|---|---|---|---|
| 2026-11-09 | Updated from the design chat: when to compute the pawn fingerprint (backfill when challenge mode is built), only Lichess motif and mate-pattern tags count as themes, a "similar" puzzle shares at least one motif tag (more shared tags rank higher), and matching treats each unique position as one. | ready | #7 |
| 2026-11-06 | Created: repeat queue, similar positions by pawn-structure fingerprint and puzzle theme. | ready | #4 |

## position_pipeline_spec.md

| Date | Event | Status after | PR |
|---|---|---|---|
| 2026-11-09 | Updated from the design chat, settling every open question: one row per unique position plus a `position_sources` table, opening names based on the moves actually played (primary name plus a list of all names), a filtered puzzle sample of 5,000 with at least 30 per motif theme, two-pass engine scoring (depth 10, then depth 18 near the best move), and the fingerprint filled in later. | ready | #7 |
| 2026-11-06 | Created: build order, tables, phase labeller, opening and puzzle importers, batch analysis. Five open questions left with placeholders. | draft | #5 |

## move_acceptance_spec.md

| Date | Event | Status after | PR |
|---|---|---|---|
| 2026-11-06 | Created: a gap-based acceptable-move rule in win %, replacing the fixed "top 3". G, L, mate handling and the challenge-mode pass rule are still open. | draft | #5 |
