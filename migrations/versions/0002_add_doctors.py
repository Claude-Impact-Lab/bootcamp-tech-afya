"""Add doctors table for mission 05.

Revision ID: 0002_add_doctors
Revises: 0001_create_users
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_add_doctors"
down_revision = "0001_create_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "doctors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("crm", sa.String(length=32), nullable=False),
        sa.Column("uf", sa.String(length=2), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_doctors_id", "doctors", ["id"])
    op.create_index("ix_doctors_user_id", "doctors", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_doctors_user_id", table_name="doctors")
    op.drop_index("ix_doctors_id", table_name="doctors")
    op.drop_table("doctors")
