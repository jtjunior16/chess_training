# Feature spec: Position pipeline (bank, phase labels, importers, batch analysis)

**Last revised:** 2026-11-11T12:03-08:00

**Status: in progress** (steps 1–5 built: the position bank tables and the phase labeller on 2026-11-09; the opening and puzzle importers and batch analysis on 2026-11-11. The full analysis run and step 6 are still to go)

> For Claude Code. Implement what's under **Decided**. Do **not** pick answers for anything under **Open questions**: use the stated placeholder, make it easy to change, and flag it. Record each decision in the project's decision log (Question → Choice → Why).

## Summary
Fill a Postgres **position bank** with training positions: named-opening positions and a sample of Lichess puzzles. Give each one a phase label, then have Stockfish score **every legal move** in every position. The game and the [move acceptance](move_acceptance_spec.md) rule read from these stored scores, so no engine runs while the player plays.

## Decided

### 1. Build order (one PR per step)
| Step | PR | Notes |
|---|---|---|
| 1 | `data:` position bank tables (Alembic migration) | Everything else writes into these tables. |
| 2 | `feat:` phase labeller | Small, self-contained function. The importers use it, so it comes first. |
| 3 | `feat:` opening importer | Small source (about 3,500 lines), so it's the first end-to-end test. |
| 4 | `feat:` puzzle importer | A filtered, stratified sample of 5,000 (see §5). |
| 5 | `feat:` batch engine analysis | Scores every legal move and stores raw scores. |
| 6 | `feat:` the game reads from the bank | Replaces the hardcoded `chess_training/positions.py`. |

Move acceptance (its own spec) comes after step 5.

### 2. Tables
**`positions`**: one row per **unique** position (decided 2026-11-09).
- `id`
- `fen`: the FEN as first seen
- `fen_key`: the FEN without the move counters. **Unique.** Only keep an en passant square when an en passant capture is actually legal, so identical positions get identical keys.
- `side_to_move`
- `phase`: opening / middlegame / endgame
- `opening_name`: the **primary** opening name (see §4), or empty
- `opening_names`: a list of **all** matching opening names (see §4)
- `pawn_fingerprint` (nullable; filled later, see §7)
- `pawn_fingerprint_version` (nullable; filled together with the fingerprint)
- `created_at`

**`position_sources`**: one row per place a position came from (decided 2026-11-09).
- `id`, `position_id` (links to `positions`)
- `source`: opening / puzzle (game is added later)
- `source_ref`: for openings, the moves played to reach this position, as PGN movetext (e.g. `1. e4 c6 2. d4`); for puzzles, the puzzle id. (Decided 2026-11-09: one opening line yields a position after every half-move, so the full line's PGN would repeat and break the unique rule below. Lines that share their first moves share one source row for those positions.)
- `fullmove_number`: as reached by this source
- `moves_to_position`: the SAN moves leading here, plus the last move played. Stored now because it's cheap, and it lets the game later show how the position arose.
- `opening_eco`: for opening sources
- `puzzle_rating`, `puzzle_themes` (a list), `puzzle_popularity`, `puzzle_nb_plays`: for puzzle sources
- `puzzle_opening_tags` (a list): the Lichess `OpeningTags` of the puzzle's game, for puzzle sources. Added by migration 0002 (decided 2026-11-11 by the user). It is informational only and never feeds `opening_name`.
- `created_at`
- Unique: (`source`, `source_ref`)

A position with any puzzle source that has at least one **motif theme** (see §5) counts as a **themed puzzle** for challenge mode.

**`position_moves`**: one row per legal move per position, per engine version.
- `position_id`, `uci`, `san`
- `score_cp`, `score_mate`: the raw score from the mover's point of view
- `depth`, `engine_version`, `analysed_at`
- Primary key: (`position_id`, `uci`, `engine_version`)

Why: storing raw scores for every move means the acceptance rule, scoring thresholds and "only move" definition can all be recomputed without re-running Stockfish. Keeping `engine_version` lets old and new engine scores live side by side.

Why one row per position plus a sources table: no duplicates. Challenge mode's "already seen in this run" check has to treat the same board as one position, each position is scored only once, and a player's history later has one answer per position.

### 3. Phase labeller
One rule for every source. The thresholds live in `config.yaml`. Checked in this order:
1. **Endgame:** each side, checked separately, passes at least one of these: at most **2 pieces**; at most 8 points of them (Q=9, R=5, B/N=3, so at most a rook plus a bishop or knight); or **no queen and at most 3 pieces**. Pieces are queens, rooks, bishops and knights. Kings and pawns never count.
2. **Opening:** the position comes from a named opening line, or it is before move 12.
3. **Middlegame:** everything else.

Decided 2026-11-09 (by the user, while building step 2):
- **Endgame beats opening.** If a position meets both tests (e.g. an early puzzle after heavy trades), it's an endgame.
- **Piece count as well as points.** With points alone, queen endings (9) and double-rook endings (10) would be labelled middlegame. Few pieces left means endgame, even if their points are high. With these numbers, any side within the points limit is also within the piece limit (three pieces are at least 9 points), so in practice the piece count decides. The points test matters only if the piece limit or piece values change.

Decided 2026-11-11 (by the user, after the puzzle importer's phase check, §5):
- **No queen, up to 3 pieces.** A side without a queen counts as endgame material with up to 3 pieces (e.g. R+B+N), checked **per side**: Q+R v R+B+N is an endgame, but Q+R+B v Q+R+N is not. Why: the first puzzle run showed Lichess calling many 3-against-3 and 3-against-2 positions endgames that our 2-piece limit didn't. With queens on, 3 pieces still feels like a middlegame. `phase.endgame_max_pieces_per_side_without_queen: 3` in `config.yaml`.
- After a rule change, `python -m chess_training.relabel_phases` recomputes every label in the bank. The importers label a board only when they first add it.

Lichess's own puzzle phase tags are not used as labels. A test or report compares them with ours as a sanity check.

### 4. Opening importer
- **Source:** `lichess-org/chess-openings` (CC0), TSV files with `eco`, `name`, `pgn`. Pin it to a specific commit, like Stockfish, so imports can be reproduced. Downloads go in `data/raw/`, which is gitignored.
- Replay each line and save the position after every half-move, **up to move 10**. Both White-to-move and Black-to-move positions are included, so both sides get trained.
- Skip the starting position.
- **Naming (decided 2026-11-09): name a position by what has actually happened on the board.**
  1. **Exact match:** if the position's `fen_key` equals the end position of a named line, use that name. Matching on the position means any move order (transposition) counts.
  2. **No exact match:** use the name of the most recent named position on the path that led here.
  3. **Several matches** (transpositions, or different named ancestors): `opening_name` = the most specific one (the longest exact match); `opening_names` = all of them.
  - Never name a position after a longer line that merely passes through it. Example: the position after 1.e4 c6 is "Caro-Kann Defense", not a deep Advance Variation sub-line.
  - Why: naming by the longest line through a position labels early positions with variations the player hasn't reached. The list of all names allows filtering by opening later.
- **ECO code (decided 2026-11-11, by the user, while building step 3).** Several named lines can share one source row, because a source row is the sequence of moves played so far. That row's `opening_eco` is the ECO of the line that names that path: the line whose end position matches exactly, otherwise the nearest named ancestor on the path. Same rule as the naming, applied to one move sequence.
- **Details approved by the user (2026-11-11, proposed in the step 3 build plan):** "up to move 10" includes Black's 10th move (at most 20 half-moves; `openings.max_fullmove` in `config.yaml`). If two names are equally specific (same line length), the alphabetically first one is primary. A position keeps the FEN it was first imported with; re-running the importer refreshes its phase and names.

### 5. Puzzle importer
- **Source:** the Lichess puzzle database (database.lichess.org, CC0, a zstd-compressed CSV). Columns: `PuzzleId, FEN, Moves, Rating, RatingDeviation, Popularity, NbPlays, Themes, GameUrl, OpeningTags`.
- **The puzzle's FEN is the position *before* the opponent's move.** The first move in `Moves` is the opponent's. The training position is the FEN **after** that first move, and that move is stored as the last move played.
- Keep the rating and themes. Store `OpeningTags` as the game's opening name in `position_sources.puzzle_opening_tags`; it's informational only.
- **Sample (decided 2026-11-09).** All numbers live in `config.yaml`.
  1. **Quality filter first:** drop puzzles with `NbPlays` < **100** or `Popularity` < **80** (popularity runs −100 to 100, from player votes).
  2. **Size: 5,000.**
  3. **Theme floor:** guarantee at least **30 puzzles per motif theme**, filled first. A puzzle with several motif themes counts towards each. If a theme has fewer than 30 after filtering, take them all and log it.
  4. **Fill the rest** evenly across **200-point rating bands**, at random within each band.
  5. Use a fixed random seed and log it, so the sample can be reproduced.
- **Motif themes (decided 2026-11-09).** Only **tactical motif** and **mate pattern** tags count as themes, both for the floor above and for challenge mode's matching (e.g. fork, pin, skewer, intermezzo, quietMove, zugzwang, xRayAttack, backRankMate, anastasiaMate, mateIn1–mateIn5). These tags are **not** themes:
  - phase: opening, middlegame, endgame, and endgame types (rookEndgame, pawnEndgame, bishopEndgame, knightEndgame, queenEndgame, queenRookEndgame)
  - length: oneMove, short, long, veryLong
  - goal: advantage, crushing, equality, mate (the generic tag)
  - origin: master, masterVsMaster, superGM

  Check this list against Lichess's official theme file (linked from database.lichess.org), keep it as one include/exclude list in `config.yaml`, and flag any tag you can't place.
  - Checked 2026-11-11 against lila's `translation/source/puzzleTheme.xml`. Eleven tags couldn't be placed: advancedPawn, attackingF2F7, castling, enPassant, exposedKing, kingsideAttack, queensideAttack, promotion, underPromotion, collinearMove, defensiveMove. **Decided 2026-11-11 (user): not themes.** They're listed under `puzzles.themes.unplaced`.
- **Decided while building (2026-11-11, by the user):**
  - "Fill the rest evenly" means the **final** per-band totals are as even as possible, floor picks included. A band short of puzzles gives its share to the others.
  - The dump is pinned by its SHA-256 (the 2026-11-01 dump). Lichess serves only the latest file, so a newer dump fails the check until it is re-pinned on purpose.
- **First run (2026-11-11):** 4,482,593 puzzles passed the quality filter. Every motif theme reached the floor. Bands got 332–333 each, except 3200–3399, which has only 14 puzzles. No tag in the data was missing from the lists. Phase check, ours against Lichess's tag:
  - Of the 2,623 puzzles Lichess tags "endgame", we label 1,623 endgame and 1,000 middlegame. 900 of those 1,000 have 3 pieces on one side against 3 or 2 on the other. Lichess's endgame line sits higher than our "at most 2 pieces each side". After the no-queen rule (§3), 702 remain, almost all with queens on (e.g. Q+R+R v Q+R+R).
  - 94 Lichess "opening" puzzles are middlegame for us (move 12 or later), and 35 Lichess "middlegame" puzzles are opening for us.
- Why: scoring every legal move rules out all ~6 million puzzles. The floor keeps challenge mode's same-theme matching from running out on rare themes. The quality filter avoids spending engine time on broken puzzles. Phase, length, goal and origin tags are on almost every puzzle, so they'd make every puzzle "similar".

### 6. Batch engine analysis
- Score **every legal move** of every position with the pinned Stockfish, in **two passes** (decided 2026-11-09; all three numbers in `config.yaml`):
  1. **Quick pass:** all legal moves at **depth 10** (MultiPV = number of legal moves).
  2. **Deep pass:** re-score at **depth 18** (must equal the live-game depth) every move within **15 win-% points** of the quick pass's best move. Use the same score → win % formula as [move acceptance](move_acceptance_spec.md).
  - `position_moves.depth` records the depth each move was finally scored at (10 or 18).
  - The deep-pass margin (15) must stay well above move acceptance's **L** (currently 6). Add a config check that fails if it doesn't.
  - Why: accuracy only matters near the edge of the acceptable set. A move that loses a queen is out either way. The 15-point margin is well beyond L, so the quick pass can't wrongly drop a borderline move.
- **The live game looks up stored scores** for bank positions and doesn't run the engine. This keeps live and stored scores consistent.
- Run several engine processes in parallel, each with 1 thread, so results stay reproducible.
- Resumable: skip positions that already have scores for the current engine version.
- Time the first 100 positions and report the per-position cost before the full run. Report per position: total time, quick-pass time, deep-pass time, number of legal moves, and **number of moves sent to the deep pass**, broken down by source and phase.
- **Built 2026-11-11** (`chess_training/analysis.py`). Details settled while building (proposed in the build plan, approved by the user):
  - "Well above L" is checked as **deep_margin ≥ 2 × L**. L lives in `config.yaml` under `move_acceptance`; it is still a placeholder (6) from the draft move acceptance spec.
  - The hash is cleared before every position (a new UCI game), so a position's scores don't depend on what the worker analysed before it.
  - "The first 100" are taken in a fixed shuffled order (md5 of `fen_key`), so they mix sources and phases. The full run uses the same order.
  - 10 workers on this 12-core machine (`analysis.workers`).
- **Timing, first 150 positions (2026-11-11):** 100 positions took 98 s and 50 more took 56 s, with 10 workers. Weighted by the bank's mix (61% openings), the full bank should take **about 4–5 hours**. Mean per position:
  - Opening positions: 13.5–17.6 s, with 30–32 legal moves and 14–19 sent to the deep pass.
  - Puzzle middlegames: 3.3 s, with 34 legal moves and 1.9 sent deep.
  - Puzzle endgames: 0.9 s, with 22 legal moves and 2.6 sent deep.
  - Opening positions cost the most because many moves stay within 15 win-% of the best.
  - Two positions have no legal moves: the checkmates that end the named lines "Barnes Opening: Fool's Mate" and "Scotch Game: Sea-Cadet Mate". Analysis skips them and reports them. The game must never serve them (step 6).
  - The stored `depth` is the depth Stockfish reports reaching, which must be at least the target. A position that fails is logged and left pending, and the run carries on.

### 7. Pawn fingerprint timing (decided 2026-11-09)
`pawn_fingerprint` and `pawn_fingerprint_version` exist from step 1, nullable, and stay empty. When challenge mode is built, a one-time **backfill** fills every existing row, and the importers compute it at import from then on. The fingerprint is defined in [challenge_mode_spec.md](challenge_mode_spec.md).
Why: it avoids committing to the fingerprint design before challenge mode exists.

### Decisions settled on 2026-11-09 (replacing the earlier placeholders)
| Question | Was (placeholder) | Now (decided) |
|---|---|---|
| Puzzle sample | 5,000, even across rating bands, no theme over-represented | 5,000 after a quality filter, ≥30 per motif theme, rest even across 200-point bands (§5) |
| Engine depth | Depth 18 for every move | Two passes: depth 10 for all moves, depth 18 for moves within 15 win-% of the best (§6) |
| Opening names | Longest named line that reaches it | Named by what has happened on the board: exact match, else nearest named ancestor; primary name + list (§4) |
| Same position from two sources | One row per (`fen_key`, `source`) | One row per `fen_key` + a `position_sources` table (§2) |
| When to compute the fingerprint | Column now, filled when challenge mode is built | Unchanged: confirmed (§7) |

## Open questions
None for this spec.

## Out of scope for now
- **Quiet positions from real Lichess games.** They need their own spec, because "quiet" isn't defined yet.
- Extending openings past move 10 with the Lichess opening explorer.
- Re-analysing the bank when Stockfish is upgraded. `engine_version` makes this possible later.
- Loading new monthly Lichess puzzle dumps.
