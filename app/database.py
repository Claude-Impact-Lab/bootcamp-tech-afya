"""
Configuração da conexão com o banco de dados PostgreSQL.

Este módulo define:
- ENGINE: A conexão com o banco de dados
- SessionLocal: Factory para criar sessões (transações)
- Base: Classe base para todos os modelos SQLAlchemy

Para testes, o conftest.py sobrescreve SessionLocal com SQLite em memória.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Carrega as configurações locais do arquivo .env, quando ele existir.
load_dotenv()

# URL de conexão com PostgreSQL (definida no arquivo .env ou no ambiente)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres@localhost:5432/usermanager",
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


