# Feature spec: Challenge mode

**Last revised:** 2026-11-11T13:20-08:00

**Status: ready** (designed; needs the position bank from [position_pipeline_spec.md](position_pipeline_spec.md) before it can be built)

> For Claude Code. This spec comes from the design chat. Implement what's under **Decided**. Do **not** pick answers for anything under **Open questions**: use the stated placeholder, make it easy to change, and flag it. Record each decision below in the project's decision log (Question → Choice → Why).

## Summary
A "Challenge mode" button starts a run of 15 randomly sampled positions. Each move is a pass or a fail. Failing a position sends it back to the end of the queue along with 2 *similar* positions, so the player practises their weak spots before the run ends. The challenge is complete when the queue is empty, meaning every position in it, including the added ones, has been passed.

## Decided

### 1. Flow
1. The player clicks **Challenge mode**.
2. The app samples **15 positions** at random from the position bank and puts them in a queue.
3. The app shows the next position from the front of the queue. The player moves (the "only good move" claim works as in normal mode).
4. The move is judged **pass** or **fail** (see section 3).
5. **Pass:** the position is done. Go to the next one.
6. **Fail:** append to the **end** of the queue:
   - the same position again (the *repeat*), and
   - **2 similar positions** (see section 2).
7. Repeats and similar positions follow the same rules. Failing any of them appends its own repeat + 2 similar positions.
8. A repeat only has to be passed **once** to count as done.
9. When the queue is empty, the challenge is passed. Show a summary (positions seen, first-try passes, failures).

Why: placing repeats at the end puts other positions in between, which clears short-term memory. The player has to re-solve the position with chess thinking instead of remembering the answer.

### 2. Similar positions

**Pawn-structure fingerprint.** Store one for every position in the bank so matching is a lookup. **When (decided 2026-11-09):** the `pawn_fingerprint` and `pawn_fingerprint_version` columns already exist, empty (see [position_pipeline_spec.md](position_pipeline_spec.md) §7). As part of building challenge mode, run a one-time backfill over every existing position and update the importers to compute it at import from then on. Bump the version if the feature list changes, so old rows can be recomputed. It is based on features, **not** exact squares:
- for each file a–h: whether White has a pawn, whether Black has a pawn
- isolated pawns (no friendly pawn on a neighbouring file), per side
- doubled pawns, per side
- passed pawns (no enemy pawn ahead on the same or a neighbouring file), per side
- pawn islands (groups of pawns on neighbouring files), count per side
- open files (no pawns of either color)

Two positions "share a fingerprint" when these features are equal. A "closest fingerprint" is the one with the most matching features. Choose any simple scoring method, but document it.

**What counts as a theme (decided 2026-11-09):** only Lichess **tactical motif** and **mate pattern** tags (e.g. fork, pin, skewer, intermezzo, backRankMate, mateIn2). Phase, length, goal and origin tags (middlegame, short, crushing, master and so on) are ignored. The include/exclude list is defined in [position_pipeline_spec.md](position_pipeline_spec.md) §5 and lives in `config.yaml`.

**"Same theme" with several tags (decided 2026-11-09):** a puzzle can have several motif tags. A candidate has the "same theme" if it shares **at least one** motif tag with the failed puzzle. Candidates sharing **more** motif tags rank higher (tie-breaker).

**Matching rules:**
- **Untagged positions** (openings, quiet positions, or puzzles with no motif tags):
  1. same fingerprint
  2. else the closest fingerprint (most features in common)
  3. else the same phase (opening / middlegame / endgame)
- **Themed puzzles** (at least one motif tag, such as fork, pin, backRankMate):
  1. shares ≥1 motif tag **and** same fingerprint
  2. else shares ≥1 motif tag, closest fingerprint
  - Within each step, rank by number of shared motif tags, then by fingerprint closeness.
  - Sharing a motif tag is required. Never return a puzzle with no shared motif tag as "similar" unless none exists. In that case fall back to the untagged rules and log it.
- In every case, exclude the failed position itself, positions already in the current queue, and positions already seen in this run. Compare by `positions` row (one row per unique position), not by source.
- Choose randomly among equally good matches.

Why: pawn structure decides plans, so the same structure teaches judgment. Exact square matches are too rare and are usually near-copies of the same line, which invites memorization. For tactical misses, the theme is what the player got wrong. Requiring every motif tag to match would often find nothing.

### 3. Pass or fail (decided 2026-11-11)
A move **passes** if it is in the position's **acceptable set**, and **fails** otherwise. The acceptable set is defined in [move_acceptance_spec.md](move_acceptance_spec.md) (§2, the G/L rule, and §7, forced mates). Use the same function as normal mode's "Acceptable / Not acceptable" verdict; challenge mode has no rule of its own. The "only good move" claim doesn't affect pass or fail for now (that belongs to the scoring spec).

Why: the user's decision. Challenge mode tests understanding, not a harder standard: the player must choose a move within G and L, the same thing normal mode calls acceptable. One rule everywhere means the verdict the player sees is the pass/fail, and tuning G and L changes both modes together. Replaces the placeholder "top 3 or loses ≤ 0.3 pawns", which passed bad moves in only-move positions and measured in pawns rather than win %.

## Open questions (do not decide. Use the placeholder and make it configurable)

| Question | Placeholder for now |
|---|---|
| Cap on run length (each failure adds 3 positions) | No cap, but make a max queue size a config value (default off). |
| Order of the items added to the end of the queue | Add the 2 similar positions first, then the repeat (widens the gap before the repeat). Config flag. |
| Disguise repeats by flipping the colors (middlegame/endgame only) | Off. |
| What the 15 are sampled from (all phases? player picks a phase/opening?) | All phases, uniformly at random. |
| Challenge length | 15, as a config value. |

## Out of scope for now
- Points or rating changes from challenge mode
- Saving challenge history to player accounts (accounts aren't built yet)
