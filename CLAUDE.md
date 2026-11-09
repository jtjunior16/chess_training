# chess_training
A chess training game: the player finds the best move in a position and is scored against the engine's top 3 moves, with a bonus for spotting 'only move' positions.

@.claude/universal-rules.md
@STATUS.md

## Project specifics (these override defaults in universal-rules.md)
- Type: app
- Deploy: none
- Data storage: PostgreSQL 16 via Docker Compose + Alembic migrations (default)
- PR template: C Data
- GitHub Issues: off (default)
- Feature specs live in `specs/` (one file per feature, written in the design chat). Each starts with `Status: draft | ready | in progress | done`. Build only what's under **Decided**. Never settle a spec's **Open questions** while coding: use the placeholder, make it configurable, and flag it. Update the status line as work progresses, and add a row to `specs/spec_log.md` whenever a spec is added, updated, changes status, or is built (merged).

<!-- Add project rules and overrides below. Record the reason for each one in docs/decisions.md. -->
