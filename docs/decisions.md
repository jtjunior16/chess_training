# Decisions
_Newest first. One entry per decision: what was asked, what we chose, why. Never edit old entries. Add a new one that supersedes them._

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
