# Feature spec: Move acceptance (which moves are "OK" in a position)

**Last revised:** 2026-11-11T13:20-08:00

**Status: draft** (the design chat still needs to settle the open questions)

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

Why the gap, not standard deviation (the first idea): when many moves score the same, their standard deviation is close to 0, so a move 0.02 pawns lower would be rejected for engine noise. With only 1–2 accepted moves the standard deviation means very little. **G** is a fixed jump size, well above engine noise, so no separate noise floor is needed.

Why the cap: without it, a slow chain (+0.20, +0.15, +0.10, …) never has a big gap and keeps accepting worse moves.

### 3. Worked examples (G = 5, L = 6)
| Position | Scores | What happens | Acceptable |
|---|---|---|---|
| One great move | +2.0 (67.6%), the rest ≈ +0.1 (50.9%) | 16.7-point drop after move 1 > G | **1 move: an only-move position** |
| Many equal moves | 15 moves ≈ +0.2 (51.8%), next −0.5 (45.4%) | 6.4-point drop after move 15 > G | **15 moves** |
| Slow drift | +0.20, +0.15, +0.10, … (steps ≈ 0.5 points) | no big gap; the cap stops it at about −0.45 (best − 6) | moves down to ≈ −0.45 |

### 4. What the acceptable set is used for
- **Judging a move:** a move is OK if it's in the acceptable set.
- **Challenge mode pass/fail (decided 2026-11-11):** a move passes if it's in the acceptable set. Same function as normal mode's verdict. See [challenge_mode_spec.md](challenge_mode_spec.md) §3.
- **"Only move" positions:** a position is an only-move position when its acceptable set has exactly **1** move. This gives the "only good move" checkbox a correct answer that comes from the data.
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
- **Only-move positions also show the 2nd-best move** with a red/grey arrow, labelled with what it loses (e.g. "Nf3: −12 win-%"). It is the only arrow that ever points at a move that isn't acceptable, and its colour must make that obvious. Why (the user's decision): it lets the player ask "would I have wanted that move, and why is it bad?", which is the judgment the "only good move" claim is about.

Why: the user's decision. The old top 3 disagreed with the acceptable set: in an only-move position, moves 2 and 3 got arrows although they weren't acceptable; with many acceptable moves, a player's acceptable 7th-ranked move had no arrow and looked wrong. Arrows for every acceptable move (up to 15 or more) would clutter the board, hence the cap and the toggle.

## Open questions (do not decide. Use the placeholder and make it configurable)

| Question | Placeholder for now |
|---|---|
| Value of **G** (break size) | 5 win-% points. (+1.0 → +0.8, which you called minor, is 1.8 points.) |
| Value of **L** (cap below the best move) | 6 win-% points. Must stay below 7.3, the cost of +1.0 → +0.2, which you called a real loss. |
| Store the acceptable-set size per position (cached column), or compute it when needed? | Compute when needed. Add a cached column only if it's slow. |

## Out of scope for now
- Points for moves outside the acceptable set (graded by win-% loss). That's the scoring spec.
- Scoring the "only good move" claim (correct, wrong or missed claims). That's the scoring spec.
