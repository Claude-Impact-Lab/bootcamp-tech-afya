"""Modelos SQLAlchemy que descrevem as tabelas da aplicação."""

from __future__ import annotations

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Classe-base usada pelo Alembic para descobrir as tabelas."""


class User(Base):
    """Usuário persistido na tabela ``users``."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(80), nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    doctor: Mapped[Doctor | None] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )

    def to_dict(self) -> dict[str, int | str]:
        return {"id": self.id, "nome": self.nome, "email": self.email}


class Doctor(Base):
    """Perfil médico associado a exatamente um usuário."""

    __tablename__ = "doctors"
    __table_args__ = (UniqueConstraint("crm", "uf", name="uq_doctors_crm_uf"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    crm: Mapped[str] = mapped_column(String(20), nullable=False)
    uf: Mapped[str] = mapped_column(String(2), nullable=False)
    user: Mapped[User] = relationship(back_populates="doctor")

    def to_dict(self) -> dict[str, int | str]:
        return {"id": self.id, "user_id": self.user_id, "crm": self.crm, "uf": self.uf}
