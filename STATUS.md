# Status
_Last saved: 2026-11-06 17:22 · Overwritten by /project-format-toolkit:save-state at the end of each session._

## Where things stand
- Scaffolded with project-format-toolkit v1.2.0: app, Postgres (Docker + Alembic), PR template C, deploy none, Issues off.
- `.venv` created; dependencies installed and locked in `uv.lock`; ruff passes.
- Alembic initialised in `migrations/` (reads `DATABASE_URL`); no migrations written yet.
- `.env` filled in by the user. Postgres not started yet: the Docker engine wasn't running, so the user is restarting the machine.
- One local commit on `main` (the scaffold). No GitHub remote yet, nothing pushed.

## Unfinished work
- Project-starter setup is paused at step 4 ("Turn on the gates"), after `.env`.

## Next steps
1. Make sure Docker Desktop is running (`docker info` succeeds), then `docker compose up -d`, wait for `docker compose ps` to show healthy, and run `uv run --env-file .env alembic upgrade head`.
2. Ask the user public or private, then `gh repo create chess_training --<public|private> --source=. --remote=origin`, `git push -u origin main`, `gh run watch --exit-status`.
3. Install the git hooks: `uv run pre-commit install --hook-type pre-commit --hook-type commit-msg`.
4. Apply the squash-only repo settings and main branch protection (project-starter steps 6–7).
5. Then start the first real task: the position + move + top-3-engine-moves game loop (see README "Game concept").

## Open questions
- Public or private GitHub repo? (Branch protection is free only on public repos.)
- Scoring thresholds for "made the position worse" are not decided yet.
