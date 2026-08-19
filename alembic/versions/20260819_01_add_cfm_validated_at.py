"""Add CFM validation timestamp to doctors.

Revision ID: 20260819_01
Revises: 20260818_03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260819_01"
down_revision: Union[str, Sequence[str], None] = "20260818_03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "doctors",
        sa.Column("cfm_validated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("doctors", "cfm_validated_at")