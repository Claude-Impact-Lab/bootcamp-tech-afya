from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

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
    doctor: Mapped["Doctor | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )


class Doctor(Base):
    """Dados profissionais ligados a exatamente um usuario."""

    __tablename__ = "doctors"
    __table_args__ = (UniqueConstraint("crm", "uf", name="uq_doctors_crm_uf"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    crm: Mapped[str] = mapped_column(String(20), nullable=False)
    uf: Mapped[str] = mapped_column(String(2), nullable=False)
    specialty: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cfm_validation_status: Mapped[str] = mapped_column(
        String(30), default="VALIDATION_PENDING", nullable=False
    )
    cfm_validated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cfm_name: Mapped[str | None] = mapped_column(String(70), nullable=True)
    cfm_registration_status: Mapped[str | None] = mapped_column(String(1), nullable=True)
    cfm_registration_type: Mapped[str | None] = mapped_column(String(1), nullable=True)
    user: Mapped[User] = relationship(back_populates="doctor")
