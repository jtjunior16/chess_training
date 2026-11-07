# Decisions
_Newest first. One entry per decision: what was asked, what we chose, why. Never edit old entries. Add a new one that supersedes them._

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
