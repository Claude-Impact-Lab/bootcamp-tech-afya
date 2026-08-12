"""Modelos SQLAlchemy que descrevem as tabelas da aplicação."""

from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Classe-base usada pelo Alembic para descobrir as tabelas."""


class User(Base):
    """Usuário persistido na tabela ``users``."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(80), nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)

    def to_dict(self) -> dict[str, int | str]:
        return {"id": self.id, "nome": self.nome, "email": self.email}
