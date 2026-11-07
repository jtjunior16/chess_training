# Journal
_Newest first. Short entries as work happens: what was done, what was learned, what surprised us._

## 2026-11-06 (game loop skeleton)
- Built the first playable version: FastAPI + python-chess + Stockfish 19, and a chessground board page. Shows a sample position, takes the player's move and the "only good move" checkbox, then shows the top 3 moves as arrows, the move's score and the pawns lost.
- Stockfish 19 ships "universal" builds per OS that pick CPU features themselves, so the download script needs no CPU detection. Our SHA-256 checksums matched GitHub's published digests.
- Depth 18 takes about a second per position on this machine. Sample check: Caro-Kann Advance top 3 within 0.16 (several fine moves); Blackburne Shilling trap Qxg2 +7.2 vs about −5 for anything else (a clear only move).
- FastAPI's TestClient warns that `httpx` is deprecated in favour of `httpx2`; harmless for now.
- Tests skip without Stockfish locally but fail in CI (CI=true), so a broken download step can't hide behind skipped tests.

## 2026-11-06 (position sources)
- Decided the position sources: generated named-opening lines (up to move 10, both sides), plus Lichess puzzles and quiet positions from real Lichess games.
- Learned: Lichess puzzles already carry phase and opening-name tags, but their opening puzzles are tactics, not theory. Most named opening lines end before move 10.
- Agreed on one phase rule for all sources (opening by move number or theory, endgame by material).

## 2026-11-06 (later)
- After a restart, Docker Desktop was running; Postgres 16 came up healthy, and Alembic connected (no migrations yet).
- Created the public repo, pushed the scaffold commit; the first CI run passed (lint, gitleaks, migrations on a fresh DB, tests).
- Turned on the gates: pre-commit + commit-msg hooks, squash-only merges with branch auto-delete, and main protection requiring the `checks` job (admins included, no force-pushes).

## 2026-11-06
- Scaffolded the project with project-format-toolkit v1.2.0 (app, Postgres, PR template C).
- Captured the initial game concept in README: top-3 engine moves, the "only good move" checkbox, and scoring non-top-3 moves that don't make the eval meaningfully worse.
- Alembic's patched `migrations/env.py` had a comment over ruff's 100-char limit; wrapped it.
- Docker Desktop was installed but not running, so `docker compose up` failed; the user is restarting the machine before the Postgres step.
- The guard hook blocks any shell command that mentions `.env`, including `git check-ignore`.
