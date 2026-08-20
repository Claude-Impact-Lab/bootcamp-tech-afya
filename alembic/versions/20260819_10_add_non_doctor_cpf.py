"""add non doctor cpf

Revision ID: 20260819_10
Revises: 20260819_09
Create Date: 2026-08-19
"""

from alembic import op
import sqlalchemy as sa

revision = "20260819_10"
down_revision = "20260819_09"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "cpf" not in columns:
        op.add_column("users", sa.Column("cpf", sa.String(length=11), nullable=True))
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("users")}
    if "ix_users_cpf" not in indexes:
        op.create_index("ix_users_cpf", "users", ["cpf"], unique=True)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    indexes = {index["name"] for index in inspector.get_indexes("users")}
    if "ix_users_cpf" in indexes:
        op.drop_index("ix_users_cpf", table_name="users")
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("users")}
    if "cpf" in columns:
        op.drop_column("users", "cpf")
