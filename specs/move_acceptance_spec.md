# Feature spec: Move acceptance (which moves are "OK" in a position)

**Last revised:** 2026-11-16T12:45-08:00

**Status: in progress** (2026-11-11: the rule (§2, §7), the verdict (§4) and the tuning report (§6) are built in `chess_training/acceptance.py` and `acceptance_report.py`. The §8 display is built in `chess_training/game.py` and the board page (2026-11-16, position pipeline step 6). G and L were decided on 2026-11-16 (§9): set both to 5 in `config.yaml`)

> For Claude Code. Implement what's under **Decided**. Do **not** pick answers for anything under **Open questions**: use the stated placeholder, make it easy to change, and flag it. Record each decision in the project's decision log (Question → Choice → Why).
>
> Depends on: [position_pipeline_spec.md](position_pipeline_spec.md) step 5 (every legal move scored and stored).

## Summary
Replace the fixed "top 3" with an **acceptable set** of moves that depends on each position's own spread of scores. If one move is far better than everything else, only that move is acceptable. If 15 moves are all about equal, all 15 are. The top 3 stays as something to *show* the player, not the rule for *judging* a move.

## Decided

### 1. Measure in winning chances, not pawns
Convert every engine score to a win percentage, using the curve Lichess uses for accuracy:

```
win% = 50 + 50 · (2 / (1 + e^(−0.00368208 · cp)) − 1)
```

Mates count as cp = ±10,000, so win% ≈ 100 or 0. All thresholds below are in **win-% points**.

Why: the same pawn loss matters less when the position is already decided. 0.0 → −1.5 costs 13.5 points (50 → 36.5), while +6.0 → +4.5 costs only 6 (90.1 → 84.0).

### 2. The acceptable set: cut at the first big gap
1. Sort all legal moves by win%, best first: w₁ ≥ w₂ ≥ … ≥ wₙ.
2. The best move is always acceptable.
3. Walk down the list. Move *i* is acceptable if **both**:
   - **no break:** wᵢ₋₁ − wᵢ ≤ **G** (it's not separated from the move above it by a big drop), and
   - **cap:** w₁ − wᵢ ≤ **L** (it's not too far below the best move).
4. Stop at the first move that fails either test. It and every move below it are not acceptable.

**Names (2026-11-16):** in text and on screen, call **G "Max Single Drop"** (the biggest drop allowed between two neighbouring moves in the sorted list) and **L "Max Below Best"** (how far below the best move a move may score). Write them as "G (Max Single Drop)" and "L (Max Below Best)". Whether to rename the config keys is under **Open questions**.

Why the gap, not standard deviation (the first idea): when many moves score the same, their standard deviation is close to 0, so a move 0.02 pawns lower would be rejected for engine noise. With only 1–2 accepted moves the standard deviation means very little. **G** is a fixed jump size, well above engine noise, so no separate noise floor is needed.

Why the cap: without it, a slow chain (+0.20, +0.15, +0.10, …) never has a big gap and keeps accepting worse moves.

### 3. Worked examples (G = L = 5, the values decided in §9)
| Position | Scores | What happens | Acceptable |
|---|---|---|---|
| One great move | +2.0 (67.6%), the rest ≈ +0.1 (50.9%) | 16.7 points below the best > L | **1 move: an only-move position** |
| Many equal moves | 15 moves ≈ +0.2 (51.8%), next −0.5 (45.4%) | 6.4 points below the best after move 15 > L | **15 moves** |
| Slow drift | +0.20, +0.15, +0.10, … (steps ≈ 0.5 points) | no big gap; the cap stops it at about −0.35 (best − 5) | moves down to ≈ −0.35 |
| Real bank position #4671 (1.e4 e5 2.Nf3 Nc6, White to move) | Bb5 +0.30 (52.8%) … c4 −0.24 (47.8%), h4 −0.27 (47.5%) | the biggest drop is 1.5; the cap stops it between c4 (4.96 below) and h4 (5.2 below) | **13 moves**, including a3, a4 and h3 |

### 4. What the acceptable set is used for
- **Judging a move:** a move is OK if it's in the acceptable set.
- **Challenge mode pass/fail (decided 2026-11-11):** a move passes if it's in the acceptable set. Same function as normal mode's verdict. See [challenge_mode_spec.md](challenge_mode_spec.md) §3.
- **"Only move" positions:** a position is an only-move position when its acceptable set has exactly **1** move. It is the hardest difficulty bucket ([scoring_spec.md](scoring_spec.md) §3) and gets the 2nd-best arrow after the move (§8). (Until 2026-11-16 it also gave the "only good move" checkbox its answer; the checkbox was removed, see scoring_spec.md §4.)
- **Difficulty:** the size of the acceptable set (1 = hard, many = easy), usable later for choosing positions.

### 5. Computed from stored scores, re-runnable
The acceptable set is computed from the raw per-move scores in `position_moves`. It never calls the engine. Changing G or L means recomputing, not re-analysing. G and L live in `config.yaml`.

### 6. Tuning report
A command that computes acceptable sets for the whole bank and prints:
- the distribution of acceptable-set sizes, split by phase and source (opening / puzzle)
- the share of only-move positions per phase and source
- a few example positions per set size
- the positions where the best move is a forced mate (§7), and the positions where every move gets mated

Use it to tune G and L with real data before awarding points.

Built 2026-11-11 as `python -m chess_training.acceptance_report`. It only covers positions with stored scores, so it runs while the analysis is going. Additions while building (Claude's, flagged to the user):
- how non-acceptable moves split around `scoring.blunder_line` (scoring spec §6 asked for this);
- a G × L grid (G 3/4/5/6/8 × L 4/6/7.5) of only-move share and median set size, both for all positions and for **opening positions only**. Puzzles are about 99% only-move positions whatever G and L are, so the opening grid is the one that shows what G and L change.

First run on partial data (4,604 of 12,715 positions, G = 5, L = 6):
- **Puzzles:** 99% are only-move positions, and every non-acceptable move is a blunder (more than 15 win-% lost).
- **Openings:** 15–16% are only-move positions, the median set size is 8, and a third of non-acceptable moves are close misses.
- **Opening grid:** L drives the set size (median 5 / 8 / 11 for L = 4 / 6 / 7.5), and G drives the only-move share (23% at G = 3 down to 9–12% at G = 8).

### 7. Forced mates (decided 2026-11-11)
If the best move forces mate (`score_mate` > 0 from the mover's point of view), the acceptable set is **exactly the moves that also force mate, at any length**. G and L don't apply. Every move that doesn't force mate is not acceptable, however big its score.

- Mate in 9 instead of mate in 2 is acceptable.
- +8 (or any non-mating score) when a mate exists is **not** acceptable: it misses the mate.
- If exactly one move forces mate, it's an only-move position (§4). A mate in 1 with two mating moves has an acceptable set of 2.
- Use `score_mate`, not win%: under win% a mate (≈100) and +8 (≈95) are 5 points apart, right at G, so the result would depend on where G happens to sit.
- The losing side (every move gets mated) has no special case: all moves are ≈0% and all are acceptable. The tuning report lists these positions (§6).

Why: the user's decision. A slower forced mate still wins by force; a big non-mating win lets the mate go, which defeats the point of a mate puzzle.

### 8. What the player sees after moving (decided 2026-11-11)
This replaces the project's original "show the top 3 arrows" display.
- **Arrows only for acceptable moves, at most 3** (the best ones). Apart from the only-move case below, an arrow never points at a move that isn't acceptable.
- **A verdict on the player's move**, always shown, e.g. "Acceptable (7th of 12)" or "Not acceptable (lost 9 win-%)". This covers an acceptable move that has no arrow.
- **The count line**, e.g. "12 moves were acceptable here".
- **A "show all" toggle** that draws arrows for the whole acceptable set.
- **Only-move positions also show the 2nd-best move** with a red/grey arrow, labelled with what it loses (e.g. "Nf3: −12 win-%"). It is the only arrow that ever points at a move that isn't acceptable, and its colour must make that obvious. Why (the user's decision): it lets the player ask "would I have wanted that move, and why is it bad?", which is the judgment an only-move position tests. (The "only good move" checkbox this was first tied to was removed on 2026-11-16; the arrow stays.)

Why: the user's decision. The old top 3 disagreed with the acceptable set: in an only-move position, moves 2 and 3 got arrows although they weren't acceptable; with many acceptable moves, a player's acceptable 7th-ranked move had no arrow and looked wrong. Arrows for every acceptable move (up to 15 or more) would clutter the board, hence the cap and the toggle.

**Built 2026-11-16** (`chess_training/game.py`, `static/app.js`). The cap is `game.max_arrows: 3` in `config.yaml`. Details settled while building (Claude, flagged in the PR):
- Arrows: green, blue and yellow for acceptable moves 1–3; "show all" adds the rest in pale green; the 2nd-best move in an only-move position is red. The toggle appears only when the set is larger than the cap.
- When the best move forces mate and the 2nd-best doesn't, its label reads "h5: misses the mate" instead of a win-% loss, the same as the verdict (a +3.78 move is still about 80 win-%).

### 9. Values of G and L (decided 2026-11-16)
**G (Max Single Drop) = 5** and **L (Max Below Best) = 5** win-% points. Set both in `config.yaml` (`move_acceptance.G: 5`, `move_acceptance.L: 5`).

What this means:
- **A move is acceptable if it loses at most 5 win-% compared with the best move.** Near an equal position that's about half a pawn (about 0.55 pawns); at +3 it's about 0.7 pawns; at +5 about 1 pawn.
- **G has no effect while G ≥ L.** A move that comes after a drop of more than G is already more than G below the best move, so the cap stops the list first. The gap test is kept in the code, so a later G below L is only a config change.
- **Only-move position = the 2nd-best move is more than 5 below the best.** On the Lichess scale, which uses the same win-% curve, a drop of 5 points or more is an inaccuracy (as recalled in the design chat, not checked against Lichess's code).
- L = 5 meets the limit L ≤ deep_margin / 2 = 7.5 (position pipeline §6) and stays below 7.3, the cost of +1.0 → +0.2, which the user called a real loss.

Full-bank figures at G = L = 5 (12,715 positions; computed in the design chat from the stored scores):
- **Openings** (7,712 positions whose best move doesn't force mate): 14% only-move, median acceptable-set size 6 (middle half of positions: 2–13), 37% with 10 or more acceptable moves.
- **Puzzles:** unchanged, about 99% only-move whatever G and L are. Every middlegame and endgame position in the bank comes from a puzzle.

Options considered (opening figures):

| Option | Only-move | Median size | 10+ acceptable |
|---|---|---|---|
| **G = L = 5 (chosen)** | 14% | 6 | 37% |
| G = 3, L = 5 (a gap test that does something) | 23% | 6 | 37% |
| G = 4, L = 6 | 17% | 8 | 45% |
| G = 5, L = 6 (the old placeholder) | 14% | 8 | 45% |
| G ≥ L, L = 3 (about a third of a pawn) | 23% | 3 | 14% |

Why: the user's decision, after real opening examples. One threshold is easy to explain, and the same loss always gets the same verdict. With G = 3, a position would count as only-move when the 2nd-best move loses just 3.3 points (about 0.33 pawns), hard for a person to see, and a 4-point loss would be acceptable after a slow slide but not after one jump. L = 3 was considered (the user's instinct was "only moves that keep a positive score", which in #4671 means ranks 1–7, matched by L ≈ 2.8). It was not chosen: "stays positive" is a different, absolute rule that would need a different L in every position, and its line at 0.00 is engine noise (d3 +0.01 against a4 −0.01). The cost of L = 5: in quiet openings the engine sees little difference between moves, so moves like 3.a3 or an early queen move are acceptable as long as they lose less than about half a pawn. Choosing positions with smaller acceptable sets more often is the place to make practice harder (see the position-choice question), not a tighter L.

## Open questions (do not decide. Use the placeholder and make it configurable)

> **To decide later.** G and L were decided on 2026-11-16 (§9). The caching question is a performance detail: measure it now that it's built, and report back.

| Question | Placeholder for now |
|---|---|
| Rename the config keys `G` and `L` to descriptive names (e.g. `max_single_drop`, `max_below_best`)? | Keep the keys `G` and `L`; add the descriptive names as comments in `config.yaml`, and use them in text and on screen (§2). |
| Store the acceptable-set size per position (cached column), or compute it when needed? | Compute when needed. Add a cached column only if it's slow. |

## Out of scope for now
- Points for moves outside the acceptable set (graded by win-% loss). That's the scoring spec.
