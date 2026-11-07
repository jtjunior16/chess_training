# Journal
_Newest first. Short entries as work happens: what was done, what was learned, what surprised us._

## 2026-11-06
- Scaffolded the project with project-format-toolkit v1.2.0 (app, Postgres, PR template C).
- Captured the initial game concept in README: top-3 engine moves, the "only good move" checkbox, and scoring non-top-3 moves that don't make the eval meaningfully worse.
- Alembic's patched `migrations/env.py` had a comment over ruff's 100-char limit; wrapped it.
- Docker Desktop was installed but not running, so `docker compose up` failed; the user is restarting the machine before the Postgres step.
- The guard hook blocks any shell command that mentions `.env`, including `git check-ignore`.
