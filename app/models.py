from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    # Nullable para permitir que cadastros antigos sejam atualizados pelo admin.
    password_hash = Column(String(512), nullable=True)
    doctor = relationship("Doctor", back_populates="user", uselist=False, cascade="all, delete-orphan")


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    crm = Column(String(32), nullable=False)
    uf = Column(String(2), nullable=False)
    user = relationship("User", back_populates="doctor")
