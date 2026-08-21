"""Add user profile, address and doctor workplace fields.

Revision ID: 0005_add_user_profiles
Revises: 0004_add_cfm_validated_at
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_add_user_profiles"
down_revision = "0004_add_cfm_validated_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("telefone", sa.String(length=20), nullable=True))
    op.add_column("users", sa.Column("documento", sa.String(length=32), nullable=True))
    op.add_column("users", sa.Column("data_nascimento", sa.Date(), nullable=True))
    op.add_column("users", sa.Column("escolaridade", sa.String(length=120), nullable=True))
    op.add_column("users", sa.Column("cep", sa.String(length=9), nullable=True))
    op.add_column("users", sa.Column("logradouro", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("numero", sa.String(length=30), nullable=True))
    op.add_column("users", sa.Column("complemento", sa.String(length=120), nullable=True))
    op.add_column("users", sa.Column("bairro", sa.String(length=120), nullable=True))
    op.add_column("users", sa.Column("cidade", sa.String(length=120), nullable=True))
    op.add_column("users", sa.Column("endereco_uf", sa.String(length=2), nullable=True))
    op.create_index("ix_users_documento", "users", ["documento"], unique=True)

    op.add_column("doctors", sa.Column("hospital", sa.String(length=255), nullable=True))
    op.add_column("doctors", sa.Column("especialidade_atuacao", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("doctors", "especialidade_atuacao")
    op.drop_column("doctors", "hospital")

    op.drop_index("ix_users_documento", table_name="users")
    op.drop_column("users", "endereco_uf")
    op.drop_column("users", "cidade")
    op.drop_column("users", "bairro")
    op.drop_column("users", "complemento")
    op.drop_column("users", "numero")
    op.drop_column("users", "logradouro")
    op.drop_column("users", "cep")
    op.drop_column("users", "escolaridade")
    op.drop_column("users", "data_nascimento")
    op.drop_column("users", "documento")
    op.drop_column("users", "telefone")
