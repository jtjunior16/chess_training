"""Position bank tables: positions, position_sources, position_moves.

See specs/position_pipeline_spec.md §2. Table definitions in chess_training/db.py must match.

Revision ID: 0001
Revises:
Create Date: 2026-11-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "positions",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("fen", sa.Text(), nullable=False),
        sa.Column("fen_key", sa.Text(), nullable=False),
        sa.Column("side_to_move", sa.Text(), nullable=False),
        sa.Column("phase", sa.Text(), nullable=False),
        sa.Column("opening_name", sa.Text(), nullable=True),
        sa.Column(
            "opening_names",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.Column("pawn_fingerprint", postgresql.JSONB(), nullable=True),
        sa.Column("pawn_fingerprint_version", sa.SmallInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("side_to_move IN ('w', 'b')", name="ck_positions_side_to_move"),
        sa.CheckConstraint(
            "phase IN ('opening', 'middlegame', 'endgame')", name="ck_positions_phase"
        ),
        sa.CheckConstraint(
            "(pawn_fingerprint IS NULL) = (pawn_fingerprint_version IS NULL)",
            name="ck_positions_fingerprint_with_version",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_positions"),
        sa.UniqueConstraint("fen_key", name="uq_positions_fen_key"),
    )

    op.create_table(
        "position_sources",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("position_id", sa.BigInteger(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=False),
        sa.Column("fullmove_number", sa.Integer(), nullable=False),
        sa.Column("moves_to_position", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("opening_eco", sa.Text(), nullable=True),
        sa.Column("puzzle_rating", sa.Integer(), nullable=True),
        sa.Column("puzzle_themes", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("puzzle_popularity", sa.Integer(), nullable=True),
        sa.Column("puzzle_nb_plays", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("source IN ('opening', 'puzzle')", name="ck_position_sources_source"),
        sa.ForeignKeyConstraint(
            ["position_id"],
            ["positions.id"],
            name="fk_position_sources_position_id_positions",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_position_sources"),
        sa.UniqueConstraint("source", "source_ref", name="uq_position_sources_source_source_ref"),
    )
    op.create_index(
        "ix_position_sources_position_id", "position_sources", ["position_id"], unique=False
    )

    op.create_table(
        "position_moves",
        sa.Column("position_id", sa.BigInteger(), nullable=False),
        sa.Column("uci", sa.Text(), nullable=False),
        sa.Column("san", sa.Text(), nullable=False),
        sa.Column("score_cp", sa.Integer(), nullable=True),
        sa.Column("score_mate", sa.Integer(), nullable=True),
        sa.Column("depth", sa.SmallInteger(), nullable=False),
        sa.Column("engine_version", sa.Text(), nullable=False),
        sa.Column(
            "analysed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(score_cp IS NULL) <> (score_mate IS NULL)", name="ck_position_moves_one_score"
        ),
        sa.ForeignKeyConstraint(
            ["position_id"],
            ["positions.id"],
            name="fk_position_moves_position_id_positions",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("position_id", "uci", "engine_version", name="pk_position_moves"),
    )


def downgrade() -> None:
    op.drop_table("position_moves")
    op.drop_index("ix_position_sources_position_id", table_name="position_sources")
    op.drop_table("position_sources")
    op.drop_table("positions")
