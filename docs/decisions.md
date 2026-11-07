# Decisions
_Newest first. One entry per decision: what was asked, what we chose, why. Never edit old entries. Add a new one that supersedes them._

## 2026-11-06: Project setup choices
Asked: How should this project be set up? (/project-format-toolkit:project-starter interview)
Chose:
- Type: app
- Data storage: PostgreSQL 16 via Docker Compose + Alembic migrations (default)
- PR template: C Data
- Deploy: none
- GitHub Issues: off (default)
Why: It's an interactive game backed by a growing bank of positions, engine evals and player scores, so it's an app on Postgres; run locally until it's worth hosting.
