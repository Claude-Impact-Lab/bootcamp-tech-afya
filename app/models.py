from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    """Representação da tabela users no PostgreSQL."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(101), nullable=False)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    email: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    email_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="pre_cadastro", nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    password_salt: Mapped[str | None] = mapped_column(String(32), nullable=True)
    confirmation_token: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
