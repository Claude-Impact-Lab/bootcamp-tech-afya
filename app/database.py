import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/usermanager",
)


class Base(DeclarativeBase):
    """Classe-base compartilhada por todas as tabelas da aplicação."""


engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    """Entrega uma sessão por requisição e garante seu fechamento."""
    with SessionLocal() as session:
        yield session
