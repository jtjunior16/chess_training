"""Drop attempts.claimed_only_move: the "only good move" claim was removed (scoring_spec §4,
decided 2026-11-16).

Downgrade re-adds the column as NOT NULL with default false, so rows recorded after the
upgrade get false (no claim), which is what the game has recorded since the claim was removed.

Table definitions in chess_training/db.py must match.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("attempts", "claimed_only_move")


def downgrade() -> None:
    op.add_column(
        "attempts",
        sa.Column(
            "claimed_only_move", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
    )
