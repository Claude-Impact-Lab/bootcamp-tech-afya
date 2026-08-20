import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.cfm_client import CFMDoctor
from app.main import Base, app, get_cfm_client
from app.database import get_db

# Configurar banco de dados de teste (SQLite em memória)
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


def override_get_db():
    """Usar banco de testes em vez do banco de produção."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


class FakeCFMClient:
    """Substitui a rede nos testes da API."""

    def find_doctor(self, crm: str, uf: str) -> CFMDoctor:
        return CFMDoctor(
            nome="Medico de Teste",
            crm=crm,
            uf=uf,
            situacao="A",
            tipo_inscricao="P",
            especialidades=(),
        )


def override_get_cfm_client() -> FakeCFMClient:
    return FakeCFMClient()


app.dependency_overrides[get_cfm_client] = override_get_cfm_client


@pytest.fixture
def client():
    """Cliente de testes que usa banco isolado."""
    # Recriar as tabelas para cada teste (limpar dados anteriores)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    return TestClient(app)


@pytest.fixture
def definir_cliente_cfm():
    """Permite simular respostas do CFM sem acesso externo."""
    def definir(cliente):
        app.dependency_overrides[get_cfm_client] = lambda: cliente

    yield definir
    app.dependency_overrides[get_cfm_client] = override_get_cfm_client
