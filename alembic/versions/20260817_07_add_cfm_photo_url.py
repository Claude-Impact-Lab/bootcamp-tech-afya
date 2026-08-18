"""add CFM photo URL

Revision ID: 20260817_07
Revises: 20260817_06
Create Date: 2026-08-17
"""

from alembic import op
import sqlalchemy as sa

revision = "20260817_07"
down_revision = "20260817_06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("doctors")
    }
    if "cfm_photo_url" not in columns:
        op.add_column(
            "doctors",
            sa.Column("cfm_photo_url", sa.String(length=500), nullable=True),
        )


def downgrade() -> None:
    columns = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("doctors")
    }
    if "cfm_photo_url" in columns:
        op.drop_column("doctors", "cfm_photo_url")
