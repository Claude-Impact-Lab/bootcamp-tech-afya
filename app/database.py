"""Conexão com o banco configurada por variável de ambiente."""

import os
from collections.abc import Generator
from functools import lru_cache

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()


@lru_cache
def get_engine():
    """Cria uma única engine para a URL definida no ambiente."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL não foi definida. Copie .env.example para .env.")

    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args)


def get_db() -> Generator[Session, None, None]:
    """Entrega uma sessão por requisição e a fecha ao final."""
    session_local = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
    db = session_local()
    try:
        yield db
    finally:
        db.close()
