"""Attempts table: one row per move the player makes (specs/scoring_spec.md §7).

Table definitions in chess_training/db.py must match.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "attempts",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("position_id", sa.BigInteger(), nullable=False),
        sa.Column("uci", sa.Text(), nullable=False),
        sa.Column("san", sa.Text(), nullable=False),
        sa.Column(
            "played_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("mode", sa.Text(), nullable=False),
        sa.Column(
            "challenge_repeat", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("side", sa.Text(), nullable=False),
        sa.Column("claimed_only_move", sa.Boolean(), nullable=False),
        sa.Column("result", sa.Text(), nullable=False),
        sa.Column("win_loss", sa.Float(), nullable=False),
        sa.Column("engine_version", sa.Text(), nullable=False),
        sa.CheckConstraint("mode IN ('normal', 'challenge')", name="ck_attempts_mode"),
        sa.CheckConstraint(
            "result IN ('acceptable', 'close miss', 'blunder')", name="ck_attempts_result"
        ),
        sa.CheckConstraint("side IN ('w', 'b')", name="ck_attempts_side"),
        sa.CheckConstraint("win_loss >= 0", name="ck_attempts_win_loss_not_negative"),
        sa.CheckConstraint(
            "mode = 'challenge' OR NOT challenge_repeat",
            name="ck_attempts_repeat_only_in_challenge",
        ),
        sa.ForeignKeyConstraint(
            ["position_id"],
            ["positions.id"],
            name="fk_attempts_position_id_positions",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_attempts"),
    )
    op.create_index("ix_attempts_position_id", "attempts", ["position_id"], unique=False)
    op.create_index("ix_attempts_played_at", "attempts", ["played_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_attempts_played_at", table_name="attempts")
    op.drop_index("ix_attempts_position_id", table_name="attempts")
    op.drop_table("attempts")
