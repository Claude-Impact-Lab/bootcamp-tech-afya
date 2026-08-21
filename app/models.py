from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    # Nullable para permitir que cadastros antigos sejam atualizados pelo admin.
    password_hash = Column(String(512), nullable=True)
    telefone = Column(String(20), nullable=True)
    documento = Column(String(32), nullable=True, unique=True, index=True)
    data_nascimento = Column(Date, nullable=True)
    escolaridade = Column(String(120), nullable=True)
    cep = Column(String(9), nullable=True)
    logradouro = Column(String(255), nullable=True)
    numero = Column(String(30), nullable=True)
    complemento = Column(String(120), nullable=True)
    bairro = Column(String(120), nullable=True)
    cidade = Column(String(120), nullable=True)
    endereco_uf = Column(String(2), nullable=True)
    doctor = relationship("Doctor", back_populates="user", uselist=False, cascade="all, delete-orphan")


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    crm = Column(String(32), nullable=False)
    uf = Column(String(2), nullable=False)
    cfm_validated_at = Column(DateTime(timezone=True), nullable=True)
    cfm_validation_status = Column(String(32), nullable=False, default="VALIDATION_PENDING")
    cfm_validation_reason = Column(String(64), nullable=True)
    hospital = Column(String(255), nullable=True)
    especialidade_atuacao = Column(String(255), nullable=True)
    user = relationship("User", back_populates="doctor")
