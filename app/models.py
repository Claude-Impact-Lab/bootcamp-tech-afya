"""Modelos SQLAlchemy que descrevem as tabelas da aplicação."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text, UniqueConstraint, false, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Classe-base usada pelo Alembic para descobrir as tabelas."""


class User(Base):
    """Usuário persistido na tabela ``users``."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(80), nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    account_type: Mapped[str] = mapped_column(
        String(20), default="non_doctor", server_default="non_doctor", nullable=False
    )
    registration_status: Mapped[str] = mapped_column(
        String(32), default="active", server_default="active", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by_admin: Mapped[str | None] = mapped_column(String(80))
    reviewed_by_admin: Mapped[str | None] = mapped_column(String(80))
    verification_method: Mapped[str | None] = mapped_column(String(32))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    profile_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    doctor: Mapped[Doctor | None] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nome": self.nome,
            "email": self.email,
            "account_type": self.account_type,
            "registration_status": self.registration_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "approved_by_admin": self.approved_by_admin,
            "reviewed_by_admin": self.reviewed_by_admin,
            "verification_method": self.verification_method,
            "rejected_at": self.rejected_at.isoformat() if self.rejected_at else None,
            "rejection_reason": self.rejection_reason,
            "profile_completed_at": (
                self.profile_completed_at.isoformat() if self.profile_completed_at else None
            ),
        }


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
    crm_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=false(),
        nullable=False,
    )
    verification_status: Mapped[str] = mapped_column(
        String(32),
        default="not_verified",
        server_default="not_verified",
        nullable=False,
    )
    cfm_crm_display: Mapped[str | None] = mapped_column(String(30))
    cfm_official_name: Mapped[str | None] = mapped_column(String(80))
    cfm_registration_status: Mapped[str | None] = mapped_column(String(100))
    cfm_registration_type: Mapped[str | None] = mapped_column(String(100))
    cfm_photo_url: Mapped[str | None] = mapped_column(String(500))
    cfm_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cfm_source_updated_at: Mapped[date | None] = mapped_column(Date)
    crm_registration_date: Mapped[date | None] = mapped_column(Date)
    crm_first_registration_uf: Mapped[str | None] = mapped_column(String(100))
    graduation_institution: Mapped[str | None] = mapped_column(String(255))
    graduation_year: Mapped[str | None] = mapped_column(String(20))
    verification_method: Mapped[str | None] = mapped_column(String(32))
    verification_last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verification_last_error: Mapped[str | None] = mapped_column(Text)
    user: Mapped[User] = relationship(back_populates="doctor")
    specialties: Mapped[list[DoctorSpecialty]] = relationship(
        back_populates="doctor",
        cascade="all, delete-orphan",
        order_by="DoctorSpecialty.id",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "crm": self.crm,
            "uf": self.uf,
            "crm_verified": self.crm_verified,
            "verification_status": self.verification_status,
            "cfm_crm_display": self.cfm_crm_display,
            "cfm_official_name": self.cfm_official_name,
            "cfm_registration_status": self.cfm_registration_status,
            "cfm_registration_type": self.cfm_registration_type,
            "cfm_photo_url": self.cfm_photo_url,
            "cfm_validated_at": self.cfm_validated_at.isoformat() if self.cfm_validated_at else None,
            "cfm_source_updated_at": (
                self.cfm_source_updated_at.isoformat() if self.cfm_source_updated_at else None
            ),
            "crm_registration_date": (
                self.crm_registration_date.isoformat() if self.crm_registration_date else None
            ),
            "crm_first_registration_uf": self.crm_first_registration_uf,
            "graduation_institution": self.graduation_institution,
            "graduation_year": self.graduation_year,
            "verification_method": self.verification_method,
            "verification_last_attempt_at": (
                self.verification_last_attempt_at.isoformat()
                if self.verification_last_attempt_at else None
            ),
            "verification_last_error": self.verification_last_error,
            "specialties": [specialty.to_dict() for specialty in self.specialties],
        }


class DoctorSpecialty(Base):
    """Especialidade profissional obtida exclusivamente do retorno do CFM."""

    __tablename__ = "doctor_specialties"

    id: Mapped[int] = mapped_column(primary_key=True)
    doctor_id: Mapped[int] = mapped_column(
        ForeignKey("doctors.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    official_name: Mapped[str] = mapped_column(String(255), nullable=False)
    rqe: Mapped[str | None] = mapped_column(String(30))
    official_description: Mapped[str] = mapped_column(Text, nullable=False)
    doctor: Mapped[Doctor] = relationship(back_populates="specialties")

    def to_dict(self) -> dict[str, int | str | None]:
        return {
            "id": self.id,
            "official_name": self.official_name,
            "rqe": self.rqe,
            "official_description": self.official_description,
        }
