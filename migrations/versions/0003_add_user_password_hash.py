"""Add password hash to users.

Revision ID: 0003_add_user_password_hash
Revises: 0002_add_doctors
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_add_user_password_hash"
down_revision = "0002_add_doctors"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(length=512), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "password_hash")
