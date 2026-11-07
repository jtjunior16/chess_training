# Feature spec: Challenge mode

> For Claude Code. This spec comes from the design chat. Implement what's under **Decided**. Do **not** pick answers for anything under **Open questions**: use the stated placeholder, make it easy to change, and flag it. Record each decision below in the project's decision log (Question → Choice → Why).

## Summary
A "Challenge mode" button starts a run of 15 randomly sampled positions. Each move is a pass or a fail. Failing a position sends it back to the end of the queue along with 2 *similar* positions, so the player practises their weak spots before the run ends. The challenge is complete when the queue is empty, meaning every position in it, including the added ones, has been passed.

## Decided

### 1. Flow
1. The player clicks **Challenge mode**.
2. The app samples **15 positions** at random from the position bank and puts them in a queue.
3. The app shows the next position from the front of the queue. The player moves (the "only good move" claim works as in normal mode).
4. The move is judged **pass** or **fail** (see Open questions for the rule).
5. **Pass:** the position is done. Go to the next one.
6. **Fail:** append to the **end** of the queue:
   - the same position again (the *repeat*), and
   - **2 similar positions** (see section 2).
7. Repeats and similar positions follow the same rules. Failing any of them appends its own repeat + 2 similar positions.
8. A repeat only has to be passed **once** to count as done.
9. When the queue is empty, the challenge is passed. Show a summary (positions seen, first-try passes, failures).

Why: placing repeats at the end puts other positions in between, which clears short-term memory. The player has to re-solve the position with chess thinking instead of remembering the answer.

### 2. Similar positions

**Pawn-structure fingerprint.** Compute one for every position in the bank, ideally when it's imported, and store it with the position so matching is a lookup. It is based on features, **not** exact squares:
- for each file a–h: whether White has a pawn, whether Black has a pawn
- isolated pawns (no friendly pawn on a neighbouring file), per side
- doubled pawns, per side
- passed pawns (no enemy pawn ahead on the same or a neighbouring file), per side
- pawn islands (groups of pawns on neighbouring files), count per side
- open files (no pawns of either color)

Two positions "share a fingerprint" when these features are equal. A "closest fingerprint" is the one with the most matching features. Choose any simple scoring method, but document it.

**Matching rules:**
- **Untagged positions** (openings, quiet positions):
  1. same fingerprint
  2. else the closest fingerprint (most features in common)
  3. else the same phase (opening / middlegame / endgame)
- **Themed puzzles** (Lichess puzzle themes such as fork, pin, backRankMate):
  1. same theme **and** same fingerprint
  2. else same theme, closest fingerprint
  - The theme is required. Never return a different-theme puzzle as "similar" unless no puzzle with that theme exists. In that case fall back to the untagged rules and log it.
- In every case, exclude the failed position itself, positions already in the current queue, and positions already seen in this run.
- Choose randomly among equally good matches.

Why: pawn structure decides plans, so the same structure teaches judgment. Exact square matches are too rare and are usually near-copies of the same line, which invites memorization. For tactical misses, the theme is what the player got wrong.

## Open questions (do not decide. Use the placeholder and make it configurable)

| Question | Placeholder for now |
|---|---|
| What counts as pass vs fail? (depends on the scoring thresholds, still undecided) | Pass = move is in the engine's top 3, OR loses ≤ 0.3 pawns compared with the best move. Keep it in one function / config value. |
| Cap on run length (each failure adds 3 positions) | No cap, but make a max queue size a config value (default off). |
| Order of the items added to the end of the queue | Add the 2 similar positions first, then the repeat (widens the gap before the repeat). Config flag. |
| Disguise repeats by flipping the colors (middlegame/endgame only) | Off. |
| What the 15 are sampled from (all phases? player picks a phase/opening?) | All phases, uniformly at random. |
| Challenge length | 15, as a config value. |

## Out of scope for now
- Points or rating changes from challenge mode
- Saving challenge history to player accounts (accounts aren't built yet)
