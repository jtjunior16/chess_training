# chess_training

A chess training game: the player finds the best move in a position and is scored against the engine's top 3 moves, with a bonus for spotting 'only move' positions.

## Setup
```bash
uv sync                                          # creates .venv and installs locked dependencies
uv run pre-commit install --hook-type pre-commit --hook-type commit-msg
uv run --no-project python scripts/sync_env.py   # creates .env from .env.example; then fill in the values
```
```bash
docker compose up -d                       # local Postgres 16
uv run --env-file .env alembic upgrade head
```

## Working with Claude Code
This repo was scaffolded with the **project-format-toolkit** plugin. Say "start session" to begin and "I have to go" to save state. Run `/project-format-toolkit:toolkit` for every command.

- Rules: `.claude/universal-rules.md` (don't edit here; overrides go in `CLAUDE.md`)
- Current status: `STATUS.md` · Decisions: `docs/decisions.md` · Journal: `docs/journal.md`

## Game concept (initial)
- The app shows the player a chess position on a board; the player makes a move.
- After the move, the app reveals the engine's top 3 moves.
- Before moving, the player can tick **"this is the only good move"** for positions where exactly one move keeps the evaluation and every other move makes it worse.
- A move outside the top 3 can still score if it doesn't make the position meaningfully worse. "Worse" is relative: +1.0 → +0.8 is a small loss, while +1.0 → +0.2 or −1.0 is a real one. Exact thresholds are still to be decided.
- More features will follow.
