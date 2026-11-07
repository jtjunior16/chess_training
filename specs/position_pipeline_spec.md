# Feature spec: Position pipeline (bank, phase labels, importers, batch analysis)

**Status: draft** (the design chat still needs to settle the open questions)

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
| 4 | `feat:` puzzle importer | A sample, not all 5 million (see Open questions). |
| 5 | `feat:` batch engine analysis | Scores every legal move and stores raw scores. |
| 6 | `feat:` the game reads from the bank | Replaces the hardcoded `chess_training/positions.py`. |

Move acceptance (its own spec) comes after step 5.

### 2. Tables
**`positions`**: one row per training position.
- `id`
- `fen`
- `fen_key`: the FEN without the move counters, used to find duplicates
- `side_to_move`
- `fullmove_number`
- `phase`: opening / middlegame / endgame
- `source`: opening / puzzle (game is added later)
- `source_ref`: the line's PGN or the puzzle id
- `moves_to_position`: the SAN moves leading here, plus the last move played. Stored now because it's cheap, and it lets the game later show how the position arose.
- `opening_eco`, `opening_name`
- `puzzle_rating`, `puzzle_themes` (a list)
- `pawn_fingerprint` (nullable; see Open questions)
- `created_at`

**`position_moves`**: one row per legal move per position, per engine version.
- `position_id`, `uci`, `san`
- `score_cp`, `score_mate`: the raw score from the mover's point of view
- `depth`, `engine_version`, `analysed_at`
- Primary key: (`position_id`, `uci`, `engine_version`)

Why: storing raw scores for every move means the acceptance rule, scoring thresholds and "only move" definition can all be recomputed without re-running Stockfish. Keeping `engine_version` lets old and new engine scores live side by side.

### 3. Phase labeller
One rule for every source. The thresholds live in `config.yaml`.
- **Opening:** the position comes from a named opening line, or it is before move 12.
- **Endgame:** each side has at most a rook plus a bishop or knight of non-pawn material (Q=9, R=5, B/N=3, so ≤ 8 per side).
- **Middlegame:** everything else.

Lichess's own puzzle phase tags are not used as labels. A test or report compares them with ours as a sanity check.

### 4. Opening importer
- **Source:** `lichess-org/chess-openings` (CC0), TSV files with `eco`, `name`, `pgn`. Pin it to a specific commit, like Stockfish, so imports can be reproduced. Downloads go in `data/raw/`, which is gitignored.
- Replay each line and save the position after every half-move, **up to move 10**. Both White-to-move and Black-to-move positions are included, so both sides get trained.
- Skip the starting position.

### 5. Puzzle importer
- **Source:** the Lichess puzzle database (database.lichess.org, CC0, a zstd-compressed CSV). Columns: `PuzzleId, FEN, Moves, Rating, RatingDeviation, Popularity, NbPlays, Themes, GameUrl, OpeningTags`.
- **The puzzle's FEN is the position *before* the opponent's move.** The first move in `Moves` is the opponent's. The training position is the FEN **after** that first move, and that move is stored as the last move played.
- Keep the rating and themes. Store `OpeningTags` as the game's opening name; it's informational only.

### 6. Batch engine analysis
- Score **every legal move** of every position with the pinned Stockfish (depth and thread settings as in `config.yaml`).
- Run several engine processes in parallel, each with 1 thread, so results stay reproducible.
- Resumable: skip positions that already have scores for the current engine version.
- Time the first 100 positions and report the per-position cost before the full run.

## Open questions (do not decide. Use the placeholder and make it configurable)

| Question | Placeholder for now |
|---|---|
| Puzzle sample: how many, and how spread out? | 5,000, spread evenly across 200-point rating bands, with no single theme over-represented. |
| Engine depth for scoring every move (cost × 30–40 moves per position) | Depth 18, the same as the live game. Revisit after timing. |
| Opening name for a position *inside* a named line, or reached by several lines (transpositions) | One row per position (`fen_key`), named after the **longest named line** that reaches it. |
| The same position from two sources (e.g. an opening position that is also a puzzle) | One row per (`fen_key`, `source`). |
| When to compute `pawn_fingerprint` (defined in [challenge_mode_spec.md](challenge_mode_spec.md)) | The column exists from step 1, nullable. It's filled when challenge mode is built, with a backfill for existing rows. |

## Out of scope for now
- **Quiet positions from real Lichess games.** They need their own spec, because "quiet" isn't defined yet.
- Extending openings past move 10 with the Lichess opening explorer.
- Re-analysing the bank when Stockfish is upgraded. `engine_version` makes this possible later.
- Loading new monthly Lichess puzzle dumps.
