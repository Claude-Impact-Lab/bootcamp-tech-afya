"""add non doctor profile

Revision ID: 20260819_09
Revises: 20260819_08
Create Date: 2026-08-19
"""

from alembic import op
import sqlalchemy as sa

revision = "20260819_09"
down_revision = "20260819_08"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "mobile_phone" not in columns:
        op.add_column("users", sa.Column("mobile_phone", sa.String(length=11), nullable=True))


def downgrade() -> None:
    columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("users")
    }
    if "mobile_phone" in columns:
        op.drop_column("users", "mobile_phone")
