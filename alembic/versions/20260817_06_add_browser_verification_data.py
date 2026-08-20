"""add browser verification data

Revision ID: 20260817_06
Revises: 20260817_05
Create Date: 2026-08-17
"""

from alembic import op
import sqlalchemy as sa

revision = "20260817_06"
down_revision = "20260817_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("doctors")}
    additions = (
        sa.Column("crm_registration_date", sa.Date(), nullable=True),
        sa.Column("crm_first_registration_uf", sa.String(length=100), nullable=True),
        sa.Column("graduation_institution", sa.String(length=255), nullable=True),
        sa.Column("graduation_year", sa.String(length=20), nullable=True),
        sa.Column("verification_method", sa.String(length=32), nullable=True),
        sa.Column("verification_last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_last_error", sa.Text(), nullable=True),
    )
    for column in additions:
        if column.name not in existing:
            op.add_column("doctors", column)
    with op.batch_alter_table("doctors") as batch_op:
        batch_op.alter_column("cfm_registration_status", existing_type=sa.String(length=1), type_=sa.String(length=100))
        batch_op.alter_column("cfm_registration_type", existing_type=sa.String(length=1), type_=sa.String(length=100))


def downgrade() -> None:
    existing = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("doctors")}
    with op.batch_alter_table("doctors") as batch_op:
        batch_op.alter_column("cfm_registration_status", existing_type=sa.String(length=100), type_=sa.String(length=1))
        batch_op.alter_column("cfm_registration_type", existing_type=sa.String(length=100), type_=sa.String(length=1))
        for name in (
            "verification_last_error", "verification_last_attempt_at", "verification_method",
            "graduation_year", "graduation_institution", "crm_first_registration_uf",
            "crm_registration_date",
        ):
            if name in existing:
                batch_op.drop_column(name)
