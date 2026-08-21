from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///usermanager.db")

# Detectar se está usando SQLite ou PostgreSQL
IS_SQLITE = DATABASE_URL.startswith("sqlite")
IS_TESTING = os.getenv("TESTING", "false").lower() == "true"

if IS_SQLITE:
    # SQLite - Funciona sem Docker!
    # Dados armazenados em arquivo local
    if IS_TESTING:
        # Testes: usar SQLite em memória
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        # Desenvolvimento: arquivo SQLite local
        engine = create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
else:
    # PostgreSQL - Requer Docker ou servidor PostgreSQL local
    engine = create_engine(DATABASE_URL, echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """Dependência que fornece uma sessão do banco para cada requisição."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
