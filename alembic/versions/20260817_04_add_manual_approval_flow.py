"""add manual approval and account authentication flow

Revision ID: 20260817_04
Revises: 20260814_03
Create Date: 2026-08-17
"""

from alembic import op
import sqlalchemy as sa

revision = "20260817_04"
down_revision = "20260814_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("account_type", sa.String(length=20), nullable=True))
    op.add_column("users", sa.Column("registration_status", sa.String(length=32), nullable=True))
    op.add_column(
        "users",
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.add_column("users", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("approved_by_admin", sa.String(length=80), nullable=True))
    op.add_column("users", sa.Column("verification_method", sa.String(length=32), nullable=True))
    op.add_column("users", sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("rejection_reason", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("profile_completed_at", sa.DateTime(timezone=True), nullable=True))

    # Cadastros anteriores continuam acessíveis no painel administrativo sem perder dados.
    op.execute(
        """
        UPDATE users
        SET account_type = CASE
                WHEN EXISTS (SELECT 1 FROM doctors WHERE doctors.user_id = users.id)
                    THEN 'doctor'
                ELSE 'non_doctor'
            END,
            registration_status = 'active'
        """
    )
    # O modo batch também atende PostgreSQL e permite recriar a tabela no SQLite,
    # que não suporta ALTER COLUMN diretamente.
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "account_type",
            existing_type=sa.String(length=20),
            nullable=False,
            server_default="non_doctor",
        )
        batch_op.alter_column(
            "registration_status",
            existing_type=sa.String(length=32),
            nullable=False,
            server_default="active",
        )


def downgrade() -> None:
    op.drop_column("users", "profile_completed_at")
    op.drop_column("users", "rejection_reason")
    op.drop_column("users", "rejected_at")
    op.drop_column("users", "verification_method")
    op.drop_column("users", "approved_by_admin")
    op.drop_column("users", "approved_at")
    op.drop_column("users", "created_at")
    op.drop_column("users", "registration_status")
    op.drop_column("users", "account_type")
    op.drop_column("users", "password_hash")
