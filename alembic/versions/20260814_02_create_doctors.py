"""create doctors table

Revision ID: 20260814_02
Revises: 20260812_01
Create Date: 2026-08-14
"""

from alembic import op
import sqlalchemy as sa

revision = "20260814_02"
down_revision = "20260812_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "doctors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("crm", sa.String(length=20), nullable=False),
        sa.Column("uf", sa.String(length=2), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("crm", "uf", name="uq_doctors_crm_uf"),
    )
    op.create_index(op.f("ix_doctors_user_id"), "doctors", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_doctors_user_id"), table_name="doctors")
    op.drop_table("doctors")
