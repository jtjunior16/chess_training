# Feature spec: Scoring (how the player's progress is measured)

**Last revised:** 2026-11-16T12:45-08:00

**Status: in progress** (2026-11-11: §1–§7 are built in `chess_training/scoring.py`: the attempts table (migration 0003), recording, the figures, recomputing, a text report and `/api/stats`. The Stats page and recording real moves come with the game reading from the bank (position pipeline step 6). 2026-11-16: `blunder_line` = 15 (§6) and the difficulty buckets 1 / 2–4 / 5–9 / 10+ (§3) are decided, and the "only good move" claim is removed (§4); the other placeholders under **Open questions** still apply)

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
- **Minimum:** a group with fewer than **10** counted attempts shows "not enough data yet" instead of a percentage. This applies to all-time and recent figures. Config value `scoring.min_attempts: 10`.

Why: the user's decisions. All-time accuracy barely moves after a few hundred positions and hides improvement; recent accuracy shows the current level. Counting attempts rather than days means a break from practice doesn't empty the window, and every group is compared like with like. The minimum stops tiny groups (e.g. "Pin: 100%" after 2 puzzles) from showing fake strengths and weaknesses.

### 3. Breakdowns (decided 2026-11-11)
Accuracy is shown overall and split by:

| Breakdown | Groups | Example |
|---|---|---|
| **Phase** | opening / middlegame / endgame (the position's phase label) | Endgame 51% |
| **Opening family** | the part of the primary opening name before the colon, e.g. "Caro-Kann Defense" for "Caro-Kann Defense: Advance Variation". Only for positions with an opening name. | Caro-Kann Defense 41% |
| **Side** | the colour the player moved with (White / Black) | As Black 58% |
| **Difficulty** | by acceptable-set size: only-move (1), 2–4, 5–9, 10+ (boundaries decided 2026-11-16, below) | Only-move 38% |
| **Puzzle theme** | motif and mate-pattern tags only (the theme list in [position_pipeline_spec.md](position_pipeline_spec.md) §5). A puzzle with several tags counts towards each of them. Only for puzzle positions. | Pin 45% |

**No source breakdown** (openings vs puzzles): it mostly repeats phase.

Why: the user's decision. Phase and opening find weak areas, which is the project's goal. Side matters because openings are practised from both colours. Difficulty shows how the player handles hard positions, which replaces the earlier idea of more points for harder positions. Puzzle themes show which tactics are missed, using the same tags as challenge mode. Opening families rather than full names, because thousands of full names would leave a few attempts each and the percentages would be noise.

**Difficulty buckets: 1 / 2–4 / 5–9 / 10+ (decided 2026-11-16).** Four buckets by acceptable-set size, under the current G and L. The boundaries stay a config value (`scoring.difficulty_buckets`, the upper ends of the first three buckets: 1, 4, 9).

Share of bank positions per bucket at G = L = 5 (computed in the design chat):

| Phase | 1 | 2–4 | 5–9 | 10+ |
|---|---|---|---|---|
| Openings (7,871) | 16% | 26% | 22% | 36% |
| Middlegame + endgame (all puzzles, 4,844) | 99% | 1% | 0% | 0% |
| Whole bank | 48% | 16% | 14% | 23% |

Options considered: 1 / 2–4 / 5+ (the old placeholder; 59% of openings in one 5+ bucket) and 1 / 2–9 / 10+.

Why: the user's decision. For openings, the useful question is whether the player does worse as the choice narrows, and three opening buckets (hard 2–4, moderate 5–9, easy 10+) show that. The 10+ bucket keeps the flat positions, where almost any sensible move is acceptable (e.g. bank #4671, 1.e4 e5 2.Nf3 Nc6, 13 acceptable moves), from hiding the rest. With `min_attempts` = 10, four buckets still fill up quickly. Note: the only-move bucket is almost all puzzles and the others almost all openings, so this breakdown partly repeats phase. Separating them would need a combined breakdown (see **Open questions**).

### 4. The "only good move" claim: removed (decided 2026-11-16)
There is **no "only good move" checkbox** and no claim figures. This replaces the 2026-11-11 decision, which had the player tick a box when they thought a position had exactly one acceptable move, and measured claim accuracy (correct claims ÷ claims) and a spotting rate (correct claims ÷ only-move positions seen).

Remove it everywhere: the checkbox on the board page (both modes), the claim figures in the text report and `/api/stats`, and the claim from what an attempt records (§7). Whether the `attempts.claimed_only_move` column is dropped by a migration or left in place unused is a build choice for Claude Code (flag it).

What stays: the **only-move position** itself (an acceptable set of exactly 1, [move_acceptance_spec.md](move_acceptance_spec.md) §4). It is the difficulty bucket "1" (§3), and after the move it still shows the 2nd-best move's red arrow (move acceptance §8).

Why: the user's decision. Every middlegame and endgame position in the bank is a puzzle, and 99% of puzzles are only-move positions at G = L = 5, so in those phases the answer is almost always "tick it" and the box tests nothing. It still carried information in openings (16% only-move), but the user chose to remove it everywhere rather than show it only in openings: a simpler page, and a box that came and went would tell the player whether the position is a puzzle. How the player does in only-move positions is still shown by the difficulty breakdown's "1" row.

### 5. Which attempts count (decided 2026-11-11)
Every attempt counts towards accuracy, in both modes, **except a challenge-mode repeat**: the same failed position coming back later in the same run. In challenge mode, the 2 similar positions added after a failure still count (they're different positions), and so does the first attempt at every position. In normal mode, seeing a position again counts as a new attempt.

The repeat is still stored with the attempt history (marked as a challenge repeat); it's only left out of the figures.

Why: the user's decision. A challenge repeat comes minutes after the player saw the answer, so it tests memory rather than understanding, and counting it would inflate accuracy exactly in the player's weak areas. A normal-mode revisit usually comes much later and is a fair re-test. Counting only the first attempt at each position ever was rejected: recent accuracy could then never show that a once-failed position has been learned.

### 6. Close misses and blunders (decided 2026-11-11)
A move that isn't acceptable is one of two kinds, by how far its win % is below the best move's:
- **Close miss:** at most **blunder_line** win-% points below the best move.
- **Blunder:** more than **blunder_line** below the best move.
- **When the best move forces mate** (see [move_acceptance_spec.md](move_acceptance_spec.md) §7), a move that doesn't mate is **always a blunder**, however big its score and wherever `blunder_line` is (decided 2026-11-11, the user). Its win-% loss is still measured from the mate's win % (≈100) and stored.
  - Why: under win % a big non-mating move (+8 ≈ 95%) is only about 5 points below a mate (≈100), so it would count as a close miss. But missing a forced mate is exactly the tactic the player failed to see.

Every accuracy figure is shown as three shares that add up to 100%, e.g. "Endgame: 51% acceptable · 30% close misses · 19% blunders", with the all-time/recent split (§2) and the breakdowns (§3). `blunder_line` lives in `config.yaml`.

Why: the user's decision. It tells two weaknesses apart: mostly close misses means the judgment is nearly there, mostly blunders means tactics are being missed. An average loss was rejected because one blunder would hide many close misses. It also answers the project overview's open question about "fine / inaccurate / bad".

**Value of `blunder_line`: 15 win-% points (decided 2026-11-16).** With L (Max Below Best) = 5 ([move_acceptance_spec.md](move_acceptance_spec.md) §9), a close miss loses more than 5 and at most 15 win-%, and a blunder loses more than 15. Near an equal position that's a close miss between about 0.55 and 1.7 pawns, and a blunder beyond about 1.7 pawns (or a dropped piece). `blunder_line` must stay ≤ `analysis.deep_margin` (15).

What the stored scores show (G = L = 5, computed in the design chat; no real attempts yet):
- **Puzzles (every middlegame and endgame position in the bank):** every non-acceptable move loses more than 20 win-%, so all misses there are blunders whatever `blunder_line` is. The close-miss share only shows up in openings.
- **Openings, among the engine's top 10 moves** (the ones a player is likely to try): 64% of non-acceptable moves are close misses at 15, against 56% at 12.5 and 46% at 10.
- **Example, bank #4671 (1.e4 e5 2.Nf3 Nc6, White to move):** h4, Qe2, b3, Na3, Ng1 and Rg1 (−0.27 to −0.95) are close misses; b4 (−1.37), Ke2, g4 and the moves that drop a piece are blunders.

Options considered: 10 (a blunder beyond about 1.1 pawns; roughly where Lichess's analysis starts calling a move a mistake, as recalled in the design chat), and three kinds instead of two (close miss 5–10, mistake 10–15, blunder over 15), which would change the two-way split above.

Why: the user's decision. A blunder should mean a clear loss (about a pawn and a half or more, or a dropped piece), which keeps "tactics are being missed" apart from "judgment is nearly there". At 10, a passive move like 3.Rg1 (about −0.95) would count as a blunder. It is also where the analysis's full-depth scoring ends (deep_margin), so every close-miss/blunder call rests on depth-18 scores, and it matches the line where Lichess starts calling a move a blunder (as recalled in the design chat, not checked against Lichess's code).

### 7. What each attempt must record (follows from §1–6)
Store every attempt, including challenge repeats, with at least: the position, the move played, the time, the mode (normal / challenge), whether it was a challenge repeat (§5), the side the player moved with, and the result (acceptable / close miss / blunder) with the win-% loss. Phase, opening family, difficulty and themes can be looked up from the position. Store the result at the time of the attempt; if G, L or blunder_line change later, whether old attempts are recomputed is an open question.

### Built 2026-11-11 (details settled while building, Claude's, flagged to the user)
- **Difficulty and only-move** use each position's acceptable set under the *current* G and L, computed when the figures are made. The stored result is recomputed with `python -m chess_training.scoring --recompute` (the placeholder answer below).
- ~~**Minimum for the claim figures**~~ and ~~**recent claim figures**~~: removed with the claim (§4, 2026-11-16).
- **Figures are served as JSON at `/api/stats`** and printed by `python -m chess_training.scoring`. The Stats page itself waits for step 6's UI work.

## Open questions (do not decide. Use the placeholder and make it configurable)

> **To decide later.** The spec was marked ready with these still open (the user's decision, 2026-11-11). Two kinds:
> - **Need real data:** none left. `blunder_line` (§6) and the difficulty buckets (§3) were decided on 2026-11-16, after G and L ([move_acceptance_spec.md](move_acceptance_spec.md) §9).
> - **Small design choices:** opening click-through, combined breakdowns, recomputing old attempts, and the Stats page layout. (The claim in challenge mode went with the claim, §4.) Build with the placeholders; any of these can be revisited in the design chat without blocking the build.

| Question | Placeholder for now |
|---|---|
| Click through from an opening family to its variations (full names)? | No. |
| Combined breakdowns (e.g. Caro-Kann as Black) | No: each breakdown on its own. |
| If G, L or blunder_line are retuned, recompute old attempts' results? | Yes: recompute from the stored move and the position's stored scores, so all figures use the current rule. |
| Where the figures are shown | One Stats page: overall, then one table per breakdown (§3), each row with all-time and recent. |

## Out of scope for now
- Player accounts. Until they exist, attempts are stored for the one local player.
- A rating system (see §1).
