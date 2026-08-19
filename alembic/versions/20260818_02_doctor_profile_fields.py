"""Add is_doctor to users and the full doctor profile fields.

Revision ID: 20260818_02
Revises: 20260818_01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260818_02"
down_revision: Union[str, Sequence[str], None] = "20260818_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_doctor",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column("doctors", sa.Column("data_nascimento", sa.String(length=10), nullable=True))
    op.add_column("doctors", sa.Column("cpf", sa.String(length=14), nullable=True))
    op.add_column("doctors", sa.Column("telefone", sa.String(length=20), nullable=True))
    op.add_column("doctors", sa.Column("especialidade", sa.String(length=80), nullable=True))
    op.add_column("doctors", sa.Column("especialidade_outra", sa.String(length=120), nullable=True))
    op.add_column("doctors", sa.Column("instituicao_formacao", sa.String(length=160), nullable=True))
    op.add_column("doctors", sa.Column("ano_formacao", sa.String(length=4), nullable=True))
    op.add_column("doctors", sa.Column("cep", sa.String(length=9), nullable=True))
    op.add_column("doctors", sa.Column("logradouro", sa.String(length=160), nullable=True))
    op.add_column("doctors", sa.Column("numero", sa.String(length=20), nullable=True))
    op.add_column("doctors", sa.Column("complemento", sa.String(length=120), nullable=True))
    op.add_column("doctors", sa.Column("bairro", sa.String(length=80), nullable=True))
    op.add_column("doctors", sa.Column("cidade", sa.String(length=80), nullable=True))
    op.add_column("doctors", sa.Column("estado", sa.String(length=80), nullable=True))
    op.add_column("doctors", sa.Column("foto", sa.String(), nullable=True))
    op.add_column("doctors", sa.Column("bio", sa.String(length=600), nullable=True))
    op.add_column("doctors", sa.Column("idiomas", sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column("doctors", "idiomas")
    op.drop_column("doctors", "bio")
    op.drop_column("doctors", "foto")
    op.drop_column("doctors", "estado")
    op.drop_column("doctors", "cidade")
    op.drop_column("doctors", "bairro")
    op.drop_column("doctors", "complemento")
    op.drop_column("doctors", "numero")
    op.drop_column("doctors", "logradouro")
    op.drop_column("doctors", "cep")
    op.drop_column("doctors", "ano_formacao")
    op.drop_column("doctors", "instituicao_formacao")
    op.drop_column("doctors", "especialidade_outra")
    op.drop_column("doctors", "especialidade")
    op.drop_column("doctors", "telefone")
    op.drop_column("doctors", "cpf")
    op.drop_column("doctors", "data_nascimento")
    op.drop_column("users", "is_doctor")
