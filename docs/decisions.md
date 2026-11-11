# Decisions
_Newest first. One entry per decision: what was asked, what we chose, why. Never edit old entries. Add a new one that supersedes them._

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
