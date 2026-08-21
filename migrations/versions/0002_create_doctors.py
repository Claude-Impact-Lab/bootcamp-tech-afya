"""create doctors table

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "doctors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("crm", sa.String(length=20), nullable=False),
        sa.Column("uf", sa.String(length=2), nullable=False),
        sa.Column("specialty", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("doctors")
