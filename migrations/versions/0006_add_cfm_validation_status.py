"""Track pending CFM validations after transient failures.

Revision ID: 0006_add_cfm_validation_status
Revises: 0005_add_user_profiles
"""

from alembic import op
import sqlalchemy as sa

revision = "0006_add_cfm_validation_status"
down_revision = "0005_add_user_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "doctors",
        sa.Column(
            "cfm_validation_status",
            sa.String(length=32),
            nullable=False,
            server_default="VALIDATION_PENDING",
        ),
    )
    op.add_column("doctors", sa.Column("cfm_validation_reason", sa.String(length=64), nullable=True))
    op.execute(
        "UPDATE doctors "
        "SET cfm_validation_status = CASE "
        "WHEN cfm_validated_at IS NULL THEN 'VALIDATION_PENDING' "
        "ELSE 'VALIDATED' END"
    )


def downgrade() -> None:
    op.drop_column("doctors", "cfm_validation_reason")
    op.drop_column("doctors", "cfm_validation_status")
