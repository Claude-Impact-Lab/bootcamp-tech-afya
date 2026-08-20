"""add CFM verification data

Revision ID: 20260814_03
Revises: 20260814_02
Create Date: 2026-08-14
"""

from alembic import op
import sqlalchemy as sa

revision = "20260814_03"
down_revision = "20260814_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "doctors",
        sa.Column("crm_verified", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "doctors",
        sa.Column("verification_status", sa.String(length=32), server_default="not_verified", nullable=False),
    )
    op.add_column("doctors", sa.Column("cfm_crm_display", sa.String(length=30), nullable=True))
    op.add_column("doctors", sa.Column("cfm_official_name", sa.String(length=80), nullable=True))
    op.add_column("doctors", sa.Column("cfm_registration_status", sa.String(length=1), nullable=True))
    op.add_column("doctors", sa.Column("cfm_registration_type", sa.String(length=1), nullable=True))
    op.add_column("doctors", sa.Column("cfm_validated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("doctors", sa.Column("cfm_source_updated_at", sa.Date(), nullable=True))

    op.create_table(
        "doctor_specialties",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("doctor_id", sa.Integer(), nullable=False),
        sa.Column("official_name", sa.String(length=255), nullable=False),
        sa.Column("rqe", sa.String(length=30), nullable=True),
        sa.Column("official_description", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_doctor_specialties_doctor_id"),
        "doctor_specialties",
        ["doctor_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_doctor_specialties_doctor_id"), table_name="doctor_specialties")
    op.drop_table("doctor_specialties")
    op.drop_column("doctors", "cfm_source_updated_at")
    op.drop_column("doctors", "cfm_validated_at")
    op.drop_column("doctors", "cfm_registration_type")
    op.drop_column("doctors", "cfm_registration_status")
    op.drop_column("doctors", "cfm_official_name")
    op.drop_column("doctors", "cfm_crm_display")
    op.drop_column("doctors", "verification_status")
    op.drop_column("doctors", "crm_verified")
