"""add reviewer audit field

Revision ID: 20260817_05
Revises: 20260817_04
Create Date: 2026-08-17
"""

from alembic import op
import sqlalchemy as sa

revision = "20260817_05"
down_revision = "20260817_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("users")}
    if "reviewed_by_admin" not in columns:
        op.add_column("users", sa.Column("reviewed_by_admin", sa.String(length=80), nullable=True))


def downgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("users")}
    if "reviewed_by_admin" in columns:
        op.drop_column("users", "reviewed_by_admin")
