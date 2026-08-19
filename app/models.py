"""
Modelos SQLAlchemy que representam as tabelas do banco de dados.

Cada classe aqui herda de Base e é automaticamente mapeada para uma tabela.
SQLAlchemy cuida de converter operações Python em SQL.
"""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    """
    Modelo que representa um usuário no banco de dados.
    
    Mapeia para a tabela 'users' no PostgreSQL com colunas:
    - id: Identificador único (chave primária)
    - name: Nome do usuário
    - email: Email do usuário
    
    Exemplo de uso:
        user = User(id=1, name="João Silva", email="joao@example.com")
        db.add(user)
        db.commit()
    """

    __tablename__ = "users"

    # Coluna: id
    # Integer = tipo numérico
    # primary_key=True = identificador único, auto-incremento
    id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
        doc="Identificador único do usuário",
    )

    # Coluna: name
    # String = texto (até 255 caracteres por padrão)
    # nullable=False = obrigatório
    name = Column(
        String,
        nullable=False,
        doc="Nome completo do usuário",
    )

    # Coluna: email
    # String = texto
    # nullable=False = obrigatório
    # unique=True = sem duplicatas
    email = Column(
        String,
        nullable=False,
        unique=True,
        index=True,
        doc="Email único do usuário",
    )

    # Marcado na Etapa 1; a ficha (Doctor) só é criada na Etapa 2.
    is_doctor = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        doc="Indica se o usuário se cadastrou como médico",
    )

    doctor = relationship(
        "Doctor",
        back_populates="user",
        uselist=False,
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        """Representação em string do objeto User (para debug)."""
        return f"User(id={self.id}, name={self.name}, email={self.email})"


class Doctor(Base):
    """Ficha médica (Etapa 2) vinculada exclusivamente a um usuário."""

    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
        index=True,
    )
    crm = Column(String(20), nullable=False)
    uf = Column(String(2), nullable=False)
    cfm_validated_at = Column(DateTime(timezone=True), nullable=True)

    # Dados pessoais
    data_nascimento = Column(String(10), nullable=True)
    cpf = Column(String(14), nullable=True)
    telefone = Column(String(20), nullable=True)

    # Dados profissionais
    especialidade = Column(String(80), nullable=True)
    especialidade_outra = Column(String(120), nullable=True)
    instituicao_formacao = Column(String(160), nullable=True)
    ano_formacao = Column(String(4), nullable=True)

    # Endereço
    cep = Column(String(9), nullable=True)
    logradouro = Column(String(160), nullable=True)
    numero = Column(String(20), nullable=True)
    complemento = Column(String(120), nullable=True)
    bairro = Column(String(80), nullable=True)
    cidade = Column(String(80), nullable=True)
    estado = Column(String(80), nullable=True)

    # Informações adicionais
    foto = Column(String, nullable=True)
    bio = Column(String(600), nullable=True)
    idiomas = Column(String(200), nullable=True)

    user = relationship("User", back_populates="doctor")
