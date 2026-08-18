"""Create the optional one-to-one doctor profile.

Revision ID: 20260818_01
Revises: 05a192260709
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260818_01"
down_revision: Union[str, Sequence[str], None] = "05a192260709"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "doctors",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("crm", sa.String(length=20), nullable=False),
        sa.Column("uf", sa.String(length=2), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_doctors_user_id"),
        if_not_exists=True,
    )
    op.create_index(
        "ix_doctors_id",
        "doctors",
        ["id"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "ix_doctors_user_id",
        "doctors",
        ["user_id"],
        unique=True,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_doctors_user_id", table_name="doctors")
    op.drop_index("ix_doctors_id", table_name="doctors")
    op.drop_table("doctors")
