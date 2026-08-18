"""
Modelos SQLAlchemy que representam as tabelas do banco de dados.

Cada classe aqui herda de Base e é automaticamente mapeada para uma tabela.
SQLAlchemy cuida de converter operações Python em SQL.
"""

from sqlalchemy import Column, Integer, String
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

    def __repr__(self) -> str:
        """Representação em string do objeto User (para debug)."""
        return f"User(id={self.id}, name={self.name}, email={self.email})"
