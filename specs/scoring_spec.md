# Feature spec: Scoring (how the player's progress is measured)

**Last revised:** 2026-11-11T13:46-08:00

**Status: ready** (decided 2026-11-11: build now with the placeholders under **Open questions**; they're decided later, see the note there)

> For Claude Code. Implement what's under **Decided**. Do **not** pick answers for anything under **Open questions**: use the stated placeholder, make it easy to change, and flag it. Record each decision in the project's decision log (Question → Choice → Why).
>
> Depends on: [move_acceptance_spec.md](move_acceptance_spec.md) (the acceptable set decides whether each move is acceptable).

## Summary
Progress is measured as **accuracy %**: the share of moves that were in the position's acceptable set, broken down by phase, opening and other groupings. There are no points, no running score and no streaks. Each figure is shown both **all-time** and over a **recent** window.

## Decided

### 1. Accuracy %, not points (decided 2026-11-11)
- **Accuracy** = acceptable moves ÷ moves played, for any group of attempts.
- It is shown overall and broken down as in §3.
- **No running score, no points per move, no streaks.**

Why: the user's decision. The game tests understanding, and accuracy shows it directly, split the way the project's goal needs (finding weak phases and openings). A running score only grows, so it shows effort rather than skill. Streaks were rejected because missing a hard position, which is exactly what the player should practise, then feels bad. A rating (like Lichess puzzle ratings) was set aside: with one local player and no accounts, there's no crowd to learn position ratings from, and opening positions have no ratings. It could be reconsidered with player accounts.

### 2. All-time and recent (decided 2026-11-11)
Every accuracy figure is shown twice: **all-time** and **recent**.
- **Recent** = the last **50 attempts in that group** (e.g. the last 50 endgame attempts, the last 50 Caro-Kann Defense attempts), counted in attempts, not days. Config value `scoring.recent_window: 50`.
- **Minimum:** a group with fewer than **10** counted attempts shows "not enough data yet" instead of a percentage. This applies to all-time and recent figures, and to the claim figures (§4, counting claims or only-move positions seen). Config value `scoring.min_attempts: 10`.

Why: the user's decisions. All-time accuracy barely moves after a few hundred positions and hides improvement; recent accuracy shows the current level. Counting attempts rather than days means a break from practice doesn't empty the window, and every group is compared like with like. The minimum stops tiny groups (e.g. "Pin: 100%" after 2 puzzles) from showing fake strengths and weaknesses.

### 3. Breakdowns (decided 2026-11-11)
Accuracy is shown overall and split by:

| Breakdown | Groups | Example |
|---|---|---|
| **Phase** | opening / middlegame / endgame (the position's phase label) | Endgame 51% |
| **Opening family** | the part of the primary opening name before the colon, e.g. "Caro-Kann Defense" for "Caro-Kann Defense: Advance Variation". Only for positions with an opening name. | Caro-Kann Defense 41% |
| **Side** | the colour the player moved with (White / Black) | As Black 58% |
| **Difficulty** | by acceptable-set size: only-move (1), 2–4, 5+ (boundaries are an open question) | Only-move 38% |
| **Puzzle theme** | motif and mate-pattern tags only (the theme list in [position_pipeline_spec.md](position_pipeline_spec.md) §5). A puzzle with several tags counts towards each of them. Only for puzzle positions. | Pin 45% |

**No source breakdown** (openings vs puzzles): it mostly repeats phase.

Why: the user's decision. Phase and opening find weak areas, which is the project's goal. Side matters because openings are practised from both colours. Difficulty shows how the player handles hard positions, which replaces the earlier idea of more points for harder positions. Puzzle themes show which tactics are missed, using the same tags as challenge mode. Opening families rather than full names, because thousands of full names would leave a few attempts each and the percentages would be noise.

### 4. The "only good move" claim (decided 2026-11-11)
The claim is about the **position** (is it an only-move position, i.e. an acceptable set of exactly 1?), not about the player's move. It is measured separately from move accuracy. Each attempt falls into one of four cases:

| | Only-move position | Not an only-move position |
|---|---|---|
| **Claimed** | correct claim | wrong claim |
| **Not claimed** | missed | correctly left blank |

Two figures are shown:
- **Claim accuracy:** correct claims ÷ all claims. "When you claimed, you were right 70% of the time." Shown as "no claims yet" when there are none.
- **Spotting rate:** correct claims ÷ only-move positions seen. "You spotted 45% of only-move positions."

Both get the all-time and recent treatment (§2) and the breakdowns (§3), e.g. "You spotted 30% of only-move endgame positions."

Why: the user's decision. Most positions aren't only-move positions, so one figure over all four cases would be dominated by "correctly left blank" and look high even for a player who never claims. The two figures catch opposite habits: claiming too often lowers claim accuracy, claiming too rarely lowers the spotting rate.

### 5. Which attempts count (decided 2026-11-11)
Every attempt counts towards accuracy and the claim figures, in both modes, **except a challenge-mode repeat**: the same failed position coming back later in the same run. In challenge mode, the 2 similar positions added after a failure still count (they're different positions), and so does the first attempt at every position. In normal mode, seeing a position again counts as a new attempt.

The repeat is still stored with the attempt history (marked as a challenge repeat); it's only left out of the figures.

Why: the user's decision. A challenge repeat comes minutes after the player saw the answer, so it tests memory rather than understanding, and counting it would inflate accuracy exactly in the player's weak areas. A normal-mode revisit usually comes much later and is a fair re-test. Counting only the first attempt at each position ever was rejected: recent accuracy could then never show that a once-failed position has been learned.

### 6. Close misses and blunders (decided 2026-11-11)
A move that isn't acceptable is one of two kinds, by how far its win % is below the best move's:
- **Close miss:** at most **blunder_line** win-% points below the best move.
- **Blunder:** more than **blunder_line** below the best move.
- When the best move forces mate (see [move_acceptance_spec.md](move_acceptance_spec.md) §7), a non-mating move is measured the same way, from the mate's win % (≈100).

Every accuracy figure is shown as three shares that add up to 100%, e.g. "Endgame: 51% acceptable · 30% close misses · 19% blunders", with the all-time/recent split (§2) and the breakdowns (§3). `blunder_line` lives in `config.yaml`.

Why: the user's decision. It tells two weaknesses apart: mostly close misses means the judgment is nearly there, mostly blunders means tactics are being missed. An average loss was rejected because one blunder would hide many close misses. It also answers the project overview's open question about "fine / inaccurate / bad".

### 7. What each attempt must record (follows from §1–6)
Store every attempt, including challenge repeats, with at least: the position, the move played, the time, the mode (normal / challenge), whether it was a challenge repeat (§5), the side the player moved with, whether the claim box was ticked, and the result (acceptable / close miss / blunder) with the win-% loss. Phase, opening family, difficulty and themes can be looked up from the position. Store the result at the time of the attempt; if G, L or blunder_line change later, whether old attempts are recomputed is an open question.

## Open questions (do not decide. Use the placeholder and make it configurable)

> **To decide later.** The spec was marked ready with these still open (the user's decision, 2026-11-11). Two kinds:
> - **Need real data:** the value of `blunder_line` and the difficulty bucket boundaries. Settle them together with G and L ([move_acceptance_spec.md](move_acceptance_spec.md)), once the tuning report and some real attempts exist. If the tuning report can also show how non-acceptable moves split around `blunder_line`, that helps.
> - **Small design choices:** opening click-through, combined breakdowns, recomputing old attempts, the Stats page layout, and the claim in challenge mode. Build with the placeholders; any of these can be revisited in the design chat without blocking the build.

| Question | Placeholder for now |
|---|---|
| Click through from an opening family to its variations (full names)? | No. |
| Difficulty bucket boundaries (depend on G and L, still being tuned) | 1 / 2–4 / 5+. Config value. |
| Combined breakdowns (e.g. Caro-Kann as Black) | No: each breakdown on its own. |
| If G, L or blunder_line are retuned, recompute old attempts' results? | Yes: recompute from the stored move and the position's stored scores, so all figures use the current rule. |
| Where the figures are shown | One Stats page: overall, then one table per breakdown (§3), each row with all-time and recent. |
| Should a wrong or missed claim also fail a challenge-mode position? | No: challenge mode judges only the move ([challenge_mode_spec.md](challenge_mode_spec.md) §3). |
| Value of **blunder_line** (where a close miss ends and a blunder begins, §6) | 15 win-% points, the same as the analysis's deep_margin: moves further below the best are only scored at depth 10, so their exact loss is less precise anyway. Keep blunder_line ≤ deep_margin. |

## Out of scope for now
- Player accounts. Until they exist, attempts are stored for the one local player.
- A rating system (see §1).
