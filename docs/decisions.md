# Decisions
_Newest first. One entry per decision: what was asked, what we chose, why. Never edit old entries. Add a new one that supersedes them._

## 2026-11-11: Move acceptance build details
Asked: Details the move acceptance spec leaves open while building §2, §4, §6 and §7.
Chose (Claude, flagged to the user in the PR):
- **Ranking:** forced mates first (sooner first), then centipawns, then being mated (later first). Ties are broken by UCI, so the order is stable. Win % is used only for the G and L tests.
- **The verdict's rank** ("7th of 12") counts among all legal moves. Its win-% loss is measured from the best move, from ≈100 when that move mates.
- **A rare edge case:** when every move gets mated, the moves are compared by win % (all ≈0), so all are acceptable, as §7 says.
- **The tuning report adds:**
  - the blunder_line split (scoring spec §6 asked for it);
  - G × L grids for all positions and for openings only.
- **Config:** `scoring.blunder_line: 15` is added now (a placeholder) for the report.
- **Not built yet:** the §8 display, which comes with pipeline step 6.
Why: A deterministic order keeps verdicts stable between runs. The opening grid is there because puzzles are about 99% only-move positions whatever G and L are, so an overall grid hides what G and L do.

## 2026-11-11: Move acceptance is ready to build with its placeholders
Asked: Move acceptance still had G, L and the caching question open. Should building wait for them?
Chose (user, in the design chat; spec Last revised 2026-11-11T13:46-08:00): No. The spec is **ready**. Build with G = 5 and L = 6 as placeholders, and tune them in a later design chat using the §6 tuning report once the full analysis has run. Caching the acceptable-set size is a performance detail: measure it once built and report back.
Why: G and L can only be tuned with real acceptable-set sizes, which need the tuning report, which needs move acceptance built. Waiting would block everything.

## 2026-11-11: Scoring is accuracy %, not points (new scoring spec from the design chat)
Asked: How the player's progress is measured. This was the old P3 question: points for acceptable moves and for moves outside the set, scoring the "only good move" claim, and an overall points system.
Chose (user, in the design chat; specs/scoring_spec.md, Last revised 2026-11-11T13:46-08:00, status **ready**):
- **§1 Measure:** accuracy %, which is acceptable moves ÷ moves played. There are no points, no running score and no streaks, and a rating is set aside.
- **§2 Two figures:** all-time, and recent = the last 50 attempts in each group (`scoring.recent_window`). Groups with fewer than 10 attempts show "not enough data yet" (`scoring.min_attempts`).
- **§3 Breakdowns:** by phase, opening family (the primary name before the colon), side, difficulty (acceptable-set size) and puzzle theme (motif tags only). There is no source breakdown.
- **§4 The "only good move" claim** is about the position, and is measured on its own:
  - claim accuracy = correct claims ÷ claims;
  - spotting rate = correct claims ÷ only-move positions seen.
- **§5 Which attempts count:** every attempt in both modes, except a challenge-mode repeat. Repeats are still stored and marked.
- **§6 Misses:** a non-acceptable move is a **close miss** if it is at most `blunder_line` win-% points below the best move, and a **blunder** otherwise. Figures are shown as acceptable / close miss / blunder shares.
- **§7 What each attempt records:**
  - the position, the move, the time and the mode;
  - whether it was a challenge repeat, the side, and the claim;
  - the result with its win-% loss.
- **Ready now:** build with the placeholders. `blunder_line` (15) and the difficulty buckets are settled later, with G and L.
Why: See the spec's "Why" lines. Accuracy shows understanding directly, and the breakdowns find weak areas, which is the project's goal. Two claim figures catch both claiming too often and claiming too rarely. Challenge repeats test memory, not understanding. The close miss / blunder split tells "nearly right" apart from "missed the tactic".
Note: the 13:27 draft of this spec reached main inside PR #20 by accident. An intermediate 13:29 copy was reviewed but overwritten before it was committed. PR #21 imports 13:46.

## 2026-11-11: From the design chat: forced mates, challenge pass rule, what the player sees
Asked: Three open questions in move_acceptance_spec: how to treat mates, whether challenge mode's pass rule becomes "in the acceptable set", and whether to show the whole acceptable set or the top 3. The design chat answered them, and the updated specs (Last revised 2026-11-11T13:20-08:00, newer than the repo copies) replaced the repo copies.
Chose (user, in the design chat):
- **Forced mates (move acceptance §7):** if the best move forces mate, the acceptable set is exactly the moves that also force mate, at any length. A non-mating move is never acceptable then, and G and L don't apply.
- **Challenge mode pass/fail (challenge mode §3):** a move passes if it is in the acceptable set, using the same function as normal mode's verdict.
- **Display (move acceptance §8):**
  - arrows for at most 3 acceptable moves;
  - an always-shown verdict on the player's move;
  - a count line;
  - a "show all" toggle;
  - in only-move positions, the 2nd-best move with a red or grey arrow and what it loses.
Why: See the "Why" lines in both specs. In short: a slower mate still wins by force, one rule everywhere keeps the verdict and pass/fail consistent, and the old top 3 disagreed with the acceptable set.

## 2026-11-11: Batch analysis details
Asked: Spec §6 leaves some details open: what "well above L" means for the deep-pass margin check, how to keep results reproducible across parallel workers, which "first 100 positions" to time, and how many workers to use.
Chose (proposed in the build plan, approved by the user):
- The check is deep_margin ≥ 2 × L, and it fails at startup otherwise. G and L are now in `config.yaml` (`move_acceptance`), marked as placeholders from the draft move acceptance spec.
- Every position starts a new UCI game, so the hash is cleared, and each engine uses 1 thread. A position's scores therefore don't depend on which worker ran it or what it ran before.
- Positions are processed in a fixed shuffled order (md5 of `fen_key`). The first 100 then mix openings and puzzles and all three phases, and the full run resumes in the same order.
- 10 worker processes on this 12-core machine.
- The quick pass is one MultiPV search over all legal moves, and the deep pass is one MultiPV search restricted to the candidate moves. A move that MultiPV misses gets scored on its own.
- The win-% curve lives in `chess_training/winpct.py` for move acceptance to reuse.
Why: 2 × L leaves a clear safety band between "might be acceptable" and "skipped by the deep pass". Clearing the hash per position is what makes the 1-thread rule actually reproducible. A shuffled order makes the timing sample representative. Both passes as single searches avoid running one search per move.

## 2026-11-11: Endgame rule: a side without a queen may have 3 pieces
Asked: The puzzle importer's phase check found Lichess calling 1,000 of the 5,000 sampled puzzles endgames where we said middlegame. 900 of them had 3 pieces against 3 or 2. The options were to raise the limit to 3, to allow 3 only without queens, or to keep 2. A follow-up asked whether "without queens" applies per side or to the whole board.
Chose (user): 3 pieces without queens, **per side**. A side passes the endgame test with at most 2 pieces, at most 8 points, or no queen and at most 3 pieces, and both sides must pass. So Q+R v R+B+N is an endgame, and Q+R+B v Q+R+N is not. The limit is `phase.endgame_max_pieces_per_side_without_queen: 3`. A new `chess_training/relabel_phases.py` recomputes every label after a rule change. It treats a position as "from a named line" if it has any `source = 'opening'` row, the same as the importers, and takes the move number from `positions.fen` (the FEN as first seen). To undo the rule, set the no-queen limit to 2 and relabel: with 2 it adds nothing to the 2-piece test. This supersedes the 2-piece-only rule from 2026-11-09 for queenless sides.
Why: Positions like R+B+N v R+B+N play like endgames, but with queens on, 3 pieces still feel like a middlegame. That's why 3 was rejected outright on 2026-11-09. Result: 298 positions were relabelled middlegame → endgame, and the disagreement with Lichess fell to 702, almost all with queens on.

## 2026-11-11: The 11 unplaced Lichess tags are not themes
Asked: Should any of advancedPawn, attackingF2F7, castling, enPassant, exposedKing, kingsideAttack, queensideAttack, promotion, underPromotion, collinearMove, defensiveMove count as motif themes? Earlier today this was a placeholder.
Chose (user): None of them. They stay in their own `puzzles.themes.unplaced` list in `config.yaml`, which the code treats as not themes. The earlier entry's placeholder is now decided.
Why: Keeping the theme set to clear tactical motifs and mate patterns means challenge mode won't call puzzles "similar" for broad features like a kingside attack or a castling move.

## 2026-11-11: Puzzle sample: unplaced theme tags, even band totals, pinning the dump
Asked: (1) Lichess's theme file has 11 tags that spec §5 places neither as motif themes nor as not-themes: advancedPawn, attackingF2F7, castling, enPassant, exposedKing, kingsideAttack, queensideAttack, promotion, underPromotion, collinearMove, defensiveMove. (2) "Fill the rest evenly across 200-point rating bands" can mean splitting the remaining slots equally, or making the final totals even. The floor picks cluster around common ratings. (3) Lichess serves only the latest puzzle dump, at a fixed URL. How do we keep imports reproducible?
Chose: (1) The user chose to treat them as not themes for now (placeholder). They are kept in `puzzles.themes.unplaced` in `config.yaml`, so moving a tag to `motif` is a one-line change. The question goes to the design chat. Clear tactical motifs (fork, pin, sacrifice, deflection, hangingPiece, and so on) and every named mate pattern plus mateIn1–5 count as themes. (2) The user chose even final totals: water-filling over bands, counting the floor picks. A band short of puzzles gives its share to the others, and a leftover slot goes to the lowest band. (3) The SHA-256 and date of the 2026-11-01 dump are pinned in `config.yaml`. A newer dump fails the check until it is re-pinned on purpose. The sampler sorts candidates by PuzzleId and uses one numpy Generator with the configured seed, and the floor is filled rarest theme first.
Also, while building (Claude's reading of spec §3 and §5, flagged to the user): (4) A board first added by the puzzle importer is labelled without the named-line test (`from_named_line=False`), because a puzzle doesn't come from a named opening line. A board that is already in the bank keeps its row, phase and names, and the puzzle only adds a source row. (5) The sample is reproducible as long as the dump, the seed and numpy's version (pinned in `uv.lock`) all stay the same. NumPy guarantees its random stream only within one version.
Why: (1) Keeping the theme set narrow until decided means challenge mode won't call puzzles "similar" for broad tags like kingsideAttack. (2) The old placeholder's aim was an even spread across ratings. Even final totals meets that whatever the floor picks did. (3) The same dump with the same seed gives the same sample. A silent monthly change would change it. (4) The opening importer runs over every named line anyway, so a board that is also on a named line through move 10 gets its opening label from there.

## 2026-11-11: Puzzle OpeningTags get their own column
Asked: Spec §5 says to store each puzzle's Lichess `OpeningTags`, but §2 has no column for them, and `positions.opening_name` is reserved for our own naming (§4). Where should they go?
Chose (user): A new nullable `text[]` column, `position_sources.puzzle_opening_tags`, added by migration 0002 in its own PR before the puzzle importer. Rejected: skipping it for now, or sending it to the design chat.
Why: The tags belong to the puzzle's source game, not to the board, so they sit with the other `puzzle_*` source fields. Keeping them out of `opening_name` means our naming rule stays the only thing that names a position.

## 2026-11-11: Opening importer: ECO per source row, the move-10 cutoff, name ties
Asked: (1) Under option A (an opening's `source_ref` is the moves played so far), several named lines can share one source row. Which ECO code goes in `opening_eco`? (2) Does "up to move 10" include Black's 10th move? (3) Which name is primary when two are equally specific?
Chose: (1) The user chose the ECO of the line whose end position matches exactly, otherwise the nearest named ancestor on the path. This is the same rule as the naming in spec §4, applied to one move sequence. (2) and (3) were proposed in the build plan and approved by the user. (2) Yes: at most 20 half-moves, set by `openings.max_fullmove: 10` in `config.yaml`. (3) The alphabetically first name. Also: the source is pinned to lichess-org/chess-openings commit 3ba6b20 with a SHA-256 for each TSV, the same way as Stockfish. The importer upserts, so re-running it changes nothing, and a position keeps the FEN it was first imported with.
Why: (1) The ECO then always agrees with the name the player sees for that move sequence. (2) Black's 10th move completes move 10, and both sides get the same depth. (3) A tie-break has to be deterministic so that imports can be reproduced. Alphabetical is the simplest.

## 2026-11-09: Phase labels: endgame beats opening, and a piece count joins the points rule
Asked: The spec's phase rule (§3) didn't say which label wins when a position meets both the opening and the endgame test. Its points-only endgame rule (at most 8 points per side) labelled queen endings (9) and double-rook endings (10) as middlegame.
Chose (user): Endgame is checked first and beats opening. A side also counts as endgame material with at most **2 pieces** (queens, rooks, bishops, knights), even if their points are higher. The limit was picked from 1, 2 or 3 per side: 1 would still leave double-rook endings as middlegame, and 3 would call positions like Q+R+B v Q+R+N endgames. All numbers are in `config.yaml`.
Why: Few pieces left is what makes an endgame, more than the points they're worth. Note: with these numbers the points test never adds a case the piece count doesn't already cover, because three pieces are at least 9 points. It's kept in case the limits change.

## 2026-11-09: Opening source_ref is the moves played so far; position bank column types
Asked: (1) The spec made (`source`, `source_ref`) unique, with an opening's `source_ref` being "the line's PGN". But one line produces a position after every half-move, so they would all share it and break the rule. (2) Which column types to use for the position bank.
Chose: (1) Option A (user's choice): an opening's `source_ref` is the moves played to reach that position, as PGN movetext. The unique rule stays as written. Rejected: B, keeping the full line's PGN and widening the rule to include `position_id` (about 1,500 source rows for 1.e4 alone); C, deferring to the design chat. (2) Fixed-value columns (`side_to_move`, `phase`, `source`) are text with CHECK constraints, not Postgres enums. Lists are `text[]`. `pawn_fingerprint` is JSONB as a placeholder until challenge mode defines it. CHECK constraints make sure exactly one of `score_cp` and `score_mate` is set, and that the fingerprint and its version are filled together. Child rows cascade on delete. Tables are defined in `chess_training/db.py` and Alembic targets them, so CI's `alembic check` catches drift.
Why: (1) Lines sharing their first moves share one source row, so there are fewer rows and no duplicates, and the rule from the spec stays. (2) CHECK constraints are easier to extend than enum types (adding `game` as a source later is a one-line change). JSONB avoids committing to a fingerprint design early.

## 2026-11-09: Specs carry a "Last revised" timestamp, and the newer copy wins
Asked: Specs should be dated so it's clear when each was last edited. If the user later hands over a spec with the same file name, how does Claude tell which copy is newer?
Chose: Every spec has `**Last revised:** YYYY-MM-DDTHH:MM±HH:MM` (ISO 8601 local time with UTC offset) under its title. Claude updates it on every spec edit, including status-line changes, and uses the same value in the spec log. For an incoming spec with the same name, Claude compares the timestamps as moments in time. If the incoming copy is newer, it replaces the repo copy and keeps its own timestamp. If it's older, the same time with different content, or has no timestamp, Claude shows what differs and asks. Rules in CLAUDE.md; the overview in specs/spec_log.md now shows the full timestamp.
Why: The design chat and this repo both edit specs, so the file name alone doesn't say which copy is newer. A date alone can't order two edits on the same day. The offset keeps the comparison correct if the timezone changes. Never overwriting an older-looking copy protects edits made here, such as status changes.

## 2026-11-09: Position pipeline open questions settled; spec log added
Asked: (1) The five P1 open questions in the position pipeline spec. (2) How to keep track of when each spec was written, updated and built.
Chose: (1) As answered in the design chat and recorded in specs/position_pipeline_spec.md §7: one row per unique position plus a `position_sources` table; opening names based on what has happened on the board (exact match, otherwise the nearest named ancestor; primary name plus a list of all names); a 5,000-puzzle sample after a quality filter, with at least 30 per motif theme and the rest spread across 200-point rating bands; two-pass scoring (depth 10 for every move, depth 18 for moves within 15 win-% of the best); the fingerprint filled by a backfill when challenge mode is built. The challenge mode spec now says only motif and mate-pattern tags count as themes, and a similar puzzle shares at least one of them. The pipeline spec is now **ready**. (2) `specs/spec_log.md`: an overview table, plus a dated history per spec (created / updated / status change / built, with the PR). CLAUDE.md tells every session to keep it up to date.
Why: (1) See the "Why" lines in each spec. (2) Git history shows file changes but not what changed in the design or when a spec was built, and the user wants that in one place.

## 2026-11-06: Pipeline build order, and score every move instead of judging by "top 3"
Asked: Build move acceptance before there are positions? What order for the position work? Is "top 3" the right rule for an OK move?
Chose: Build order: position bank tables → phase labeller → opening importer → puzzle importer → batch analysis → game reads from the bank. Batch analysis scores every legal move and stores raw scores in a `position_moves` table. The acceptable-move rule (gap-based, in win %) is computed afterwards from the stored scores. Details in specs/position_pipeline_spec.md and specs/move_acceptance_spec.md (both draft).
Why: G and L can't be tuned without real positions. A fixed top 3 is too generous when one move stands out and too strict when many moves are equal; the acceptable set should follow each position's own spread of scores. Storing raw scores makes the rule re-runnable without Stockfish. Lichess has about 5M puzzles, too many to analyse at several seconds each, so puzzles are sampled.

## 2026-11-06: When to write a spec vs just build
Asked: When does a feature get a spec file instead of going straight to a PR?
Chose: Write a spec when decisions are still open, the work spans several PRs or sessions, it changes the data structure, the design chat should weigh in, or the order of steps matters. Otherwise (fully decided, one PR, easy to undo) just build it, with the PR description and a decisions.md line as the record. Specs carry a status line (draft / ready / in progress / done), and CLAUDE.md tells every session not to settle a spec's open questions while coding.
Why: Specs hold plans that would otherwise scroll away in chat and keep open questions from being settled by accident, but they're overhead for small, fully decided changes.

## 2026-11-06: specs/ folder for design docs
Asked: Where should design docs from the separate design chat (Claude Desktop) live?
Chose: a `specs/` folder in the repo, one Markdown file per feature (first: `specs/challenge_mode_spec.md`). A spec can be committed before it is scheduled for development.
Why: Requirements sit where Claude Code can read them, versioned with the code, without starting implementation. Specs mark what is decided and what is still open, so open questions aren't settled by accident during coding.

## 2026-11-06: License GPL-3.0-or-later
Asked: Is a GPL-3.0 license OK, and does it block monetising later?
Chose: GPL-3.0-or-later for the whole project (LICENSE file, pyproject `license`).
Why: python-chess and chessground are both GPL, so the project must be GPL-compatible anyway, and the repo is already public. GPL doesn't forbid charging money. A hosted site's server code doesn't have to be shared under GPL-3.0 (it would under AGPL); browser JavaScript and any downloadable app would. Going closed-source later would mean replacing those two libraries.

## 2026-11-06: Stockfish pinned and downloaded by script, not winget
Asked: Install Stockfish with winget, or put it in the venv?
Chose: scripts/get_stockfish.py downloads the official Stockfish 19 release into the gitignored tools/stockfish/, verifying a SHA-256 checksum recorded in config.yaml. CI runs the same script. Engine settings: depth 18, 1 thread, 64 MB hash, multipv 3.
Why: Stockfish is a compiled program, so it can't live in the venv as a Python package. Different versions give different scores, and we'll compare stored evals with live ones, so the version must match on every machine and in CI. winget is Windows-only, updates silently and installs to a machine-specific path, and CI's apt package would be a different version. Fixed depth with one thread keeps results reproducible.

## 2026-11-06: App stack: FastAPI + chessground in a plain JS page
Asked: Web page or desktop window, and which libraries?
Chose: a web page served locally. FastAPI backend with python-chess (rules) and Stockfish (engine); the front end is one plain HTML/JS page using chessground 9.2.1 (Lichess's board) from the jsDelivr CDN, with no build step. Legal moves are computed on the server and sent to the board.
Why: The user is fine with JavaScript and wants a browser board. Good boards already exist for the browser (drag-and-drop, arrows for showing the top moves), while desktop options need custom drawing, and a web page can be hosted later with few changes. Skipping React and build tools keeps the front end small while the game logic lives in Python.

## 2026-11-06: Where training positions come from, and how phases are labelled
Asked: Should positions be generated, come from puzzles, or both? How do we label opening / middlegame / endgame?
Chose:
- Opening: generated from Lichess's named-openings list (lichess-org/chess-openings), up to move 10, storing the opening name. Train both sides.
- Middlegame / endgame: Lichess puzzles plus quiet positions sampled from real Lichess games, both from the start.
- Phase label: our own rule for every position. Opening = in a named line or before about move 12; endgame = each side has at most a rook plus a bishop or knight (Q=9, R=5, B/N=3); middlegame = the rest. Thresholds in config.yaml.
- Nice-to-have (not planned yet): extend opening lines with popular continuations from the Lichess opening explorer.
Why: The user's weak spot is the first moves against players who know theory, and puzzles rarely cover theory (their "opening" puzzles are tactics). Puzzles also always contain a trick, which would make the "only good move" checkbox trivially true, so quiet real-game positions are needed too. Generating from named lines gives the opening name for free. Most games leave known theory by about move 10, and most named lines are shorter than that, so the cap covers what people memorize. One shared phase rule keeps labels consistent across sources; openings are defined by move number or theory, not material, because exchange variations trade early but are still openings.

## 2026-11-06: Public GitHub repo
Asked: Should the GitHub repo be public or private?
Chose: Public (github.com/jtjunior16/chess_training).
Why: Branch protection on main is free only on public repos, and the code holds no secrets (gitleaks and a manual check passed; credentials live in the gitignored .env).

## 2026-11-06: Project setup choices
Asked: How should this project be set up? (/project-format-toolkit:project-starter interview)
Chose:
- Type: app
- Data storage: PostgreSQL 16 via Docker Compose + Alembic migrations (default)
- PR template: C Data
- Deploy: none
- GitHub Issues: off (default)
Why: It's an interactive game backed by a growing bank of positions, engine evals and player scores, so it's an app on Postgres; run locally until it's worth hosting.
