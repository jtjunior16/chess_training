# Feature spec: Scoring (how the player's progress is measured)

**Last revised:** 2026-11-11T13:27-08:00

**Status: draft** (the design chat is still settling the open questions)

> For Claude Code. Implement what's under **Decided**. Do **not** pick answers for anything under **Open questions**: use the stated placeholder, make it easy to change, and flag it. Record each decision in the project's decision log (Question → Choice → Why).
>
> Depends on: [move_acceptance_spec.md](move_acceptance_spec.md) (the acceptable set decides whether each move is acceptable).

## Summary
Progress is measured as **accuracy %**: the share of moves that were in the position's acceptable set, broken down by phase, opening and other groupings. There are no points, no running score and no streaks. Each figure is shown both **all-time** and over a **recent** window.

## Decided

### 1. Accuracy %, not points (decided 2026-11-11)
- **Accuracy** = acceptable moves ÷ moves played, for any group of attempts.
- It is shown broken down by phase and by opening (the full list of breakdowns is an open question below).
- **No running score, no points per move, no streaks.**

Why: the user's decision. The game tests understanding, and accuracy shows it directly, split the way the project's goal needs (finding weak phases and openings). A running score only grows, so it shows effort rather than skill. Streaks were rejected because missing a hard position, which is exactly what the player should practise, then feels bad. A rating (like Lichess puzzle ratings) was set aside: with one local player and no accounts, there's no crowd to learn position ratings from, and opening positions have no ratings. It could be reconsidered with player accounts.

### 2. All-time and recent (decided 2026-11-11)
Every accuracy figure is shown twice: **all-time** and **recent** (a window of the latest attempts in that group; size is an open question).

Why: the user's decision. All-time accuracy barely moves after a few hundred positions and hides improvement; recent accuracy shows the current level.

## Open questions (do not decide. Use the placeholder and make it configurable)

| Question | Placeholder for now |
|---|---|
| Which breakdowns are shown (phase, opening, side, source, difficulty, puzzle theme…), and at what opening granularity? | Phase and opening family (the part of the name before the colon). |
| Size of the recent window | The last 50 attempts in each group. Config value. |
| Which attempts count (repeats of the same position, challenge-mode attempts)? | Every attempt counts, in both modes. |
| How the "only good move" claim is measured | Not measured yet. |
| Also show the average win-% lost on non-acceptable moves? | No. |

## Out of scope for now
- Player accounts. Until they exist, attempts are stored for the one local player.
- A rating system (see §1).
