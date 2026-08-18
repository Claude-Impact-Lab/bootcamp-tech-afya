"""
Configuração da conexão com o banco de dados PostgreSQL.

Este módulo define:
- ENGINE: A conexão com o banco de dados
- SessionLocal: Factory para criar sessões (transações)
- Base: Classe base para todos os modelos SQLAlchemy

Para testes, o conftest.py sobrescreve SessionLocal com SQLite em memória.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# URL de conexão com PostgreSQL (pode ser sobrescrita via variável de ambiente)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/usermanager",
)

# Criar engine (conexão com o banco de dados)
# echo=True mostra as queries SQL no console (útil para debug)
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Mude para True para ver as queries SQL
)

# SessionLocal é uma factory que cria novas sessões (transações) com o banco
# Cada requisição HTTP usará: session = SessionLocal()
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Base é a classe mãe para todos os modelos SQLAlchemy
# Todos os modelos devem herdar de Base:
# class User(Base):
#     ...
Base = declarative_base()


