"""Add position_sources.puzzle_opening_tags (Lichess OpeningTags for puzzle sources).

See specs/position_pipeline_spec.md §2 and §5. Informational only; positions.opening_name keeps
following our own naming rule (§4). Nullable, so existing rows need no backfill.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "position_sources",
        sa.Column("puzzle_opening_tags", postgresql.ARRAY(sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("position_sources", "puzzle_opening_tags")
