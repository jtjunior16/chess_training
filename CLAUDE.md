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
- **Spec revision timestamps.** Every spec has a `**Last revised:** YYYY-MM-DDTHH:MM±HH:MM` line right under its title, above the status line. It uses ISO 8601 local time with the UTC offset, e.g. `2026-11-09T09:22-08:00`.
  - **When you edit a spec** (any change, including the status line), set `Last revised` to the current time (`date +%Y-%m-%dT%H:%M%:z`) in the same commit. Use the same value in that spec's new row in `specs/spec_log.md`.
  - **When the user hands you a spec with the same file name as one in `specs/`:** compare the two `Last revised` values as moments in time, taking the offsets into account, never as plain text.
    - Incoming is **newer:** it replaces the repo copy. Keep its timestamp; don't overwrite it with the import time. Log the update in the spec log.
    - Incoming is **older**, or **the same with different content:** don't overwrite. Show the user what differs and ask which to keep, or whether to merge them. (For example, the repo copy may be newer only because a status line was changed here.)
    - Incoming has **no timestamp**, or one in the wrong format: treat it as unknown. Ask, and don't assume either copy is newer.
    - **Identical content:** nothing to do.
  - A spec without a `Last revised` line is a gap: add one and flag it to the user.

<!-- Add project rules and overrides below. Record the reason for each one in docs/decisions.md. -->
