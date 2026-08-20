"""add doctor personal profile

Revision ID: 20260819_08
Revises: 20260817_07
Create Date: 2026-08-19
"""

from alembic import op
import sqlalchemy as sa

revision = "20260819_08"
down_revision = "20260817_07"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("doctors")}
    if "cpf" not in columns:
        op.add_column("doctors", sa.Column("cpf", sa.String(length=11), nullable=True))
    if "marital_status" not in columns:
        op.add_column(
            "doctors", sa.Column("marital_status", sa.String(length=30), nullable=True)
        )
    if "mobile_phone" not in columns:
        op.add_column(
            "doctors", sa.Column("mobile_phone", sa.String(length=11), nullable=True)
        )
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("doctors")}
    if "ix_doctors_cpf" not in indexes:
        op.create_index("ix_doctors_cpf", "doctors", ["cpf"], unique=True)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    indexes = {index["name"] for index in inspector.get_indexes("doctors")}
    if "ix_doctors_cpf" in indexes:
        op.drop_index("ix_doctors_cpf", table_name="doctors")
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("doctors")}
    if "mobile_phone" in columns:
        op.drop_column("doctors", "mobile_phone")
    if "marital_status" in columns:
        op.drop_column("doctors", "marital_status")
    if "cpf" in columns:
        op.drop_column("doctors", "cpf")
