"""Store when a doctor was validated by the CFM.

Revision ID: 0004_add_cfm_validated_at
Revises: 0003_add_user_password_hash
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_add_cfm_validated_at"
down_revision = "0003_add_user_password_hash"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("doctors", sa.Column("cfm_validated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("doctors", "cfm_validated_at")
