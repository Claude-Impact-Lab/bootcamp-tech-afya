"""add CFM validation fields

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "doctors",
        sa.Column(
            "cfm_validation_status",
            sa.String(length=30),
            server_default="VALIDATION_PENDING",
            nullable=False,
        ),
    )
    op.add_column("doctors", sa.Column("cfm_validated_at", sa.DateTime(timezone=True)))
    op.add_column("doctors", sa.Column("cfm_name", sa.String(length=70)))
    op.add_column("doctors", sa.Column("cfm_registration_status", sa.String(length=1)))
    op.add_column("doctors", sa.Column("cfm_registration_type", sa.String(length=1)))
    op.alter_column("doctors", "cfm_validation_status", server_default=None)


def downgrade() -> None:
    op.drop_column("doctors", "cfm_registration_type")
    op.drop_column("doctors", "cfm_registration_status")
    op.drop_column("doctors", "cfm_name")
    op.drop_column("doctors", "cfm_validated_at")
    op.drop_column("doctors", "cfm_validation_status")
