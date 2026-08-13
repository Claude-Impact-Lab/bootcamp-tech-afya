"""create users table

Revision ID: 0001
Revises:
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=101), nullable=False),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("email", sa.String(length=100), nullable=True, unique=True),
        sa.Column("email_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="pre_cadastro"),
        sa.Column("password_hash", sa.String(length=64), nullable=True),
        sa.Column("password_salt", sa.String(length=32), nullable=True),
        sa.Column("confirmation_token", sa.String(length=100), nullable=True, unique=True),
    )


def downgrade() -> None:
    op.drop_table("users")
