"""make doctor crm and uf unique

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

from alembic import op


revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_doctors_crm_uf", "doctors", ["crm", "uf"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_doctors_crm_uf", "doctors", type_="unique")
