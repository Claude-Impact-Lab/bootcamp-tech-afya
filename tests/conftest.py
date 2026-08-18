"""
Configuração global dos testes com pytest.

Este arquivo é automaticamente descoberto pelo pytest e fornece
fixtures e configurações para todos os testes.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Criar banco de dados em memória para testes ANTES de importar a app
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)

# Importar DEPOIS de criar o engine de teste
from app.database import Base
from app.models import User
import app.main

# Sobrescrever o SessionLocal na app para usar o de teste
app.main.SessionLocal = TestingSessionLocal

# Criar as tabelas no banco de teste
Base.metadata.create_all(bind=test_engine)


def setup_test_users():
    """Cria usuários de teste no banco de dados."""
    db = TestingSessionLocal()
    try:
        # Limpar usuários anteriores
        db.query(User).delete()
        db.commit()
        
        test_users = [
            User(id=1, name="João Silva", email="joao.silva@example.com"),
            User(id=2, name="Maria Santos", email="maria.santos@example.com"),
            User(id=3, name="Pedro Oliveira", email="pedro.oliveira@example.com"),
        ]
        for user in test_users:
            db.add(user)
        db.commit()
    finally:
        db.close()


# Fixture do pytest que injeta em cada teste
@pytest.fixture(autouse=True)
def setup():
    """Setup e teardown para cada teste."""
    # Antes do teste: popular dados
    setup_test_users()
    
    # Executar o teste
    yield
    
    # Depois do teste: limpar dados
    db = TestingSessionLocal()
    try:
        db.query(User).delete()
        db.commit()
    finally:
        db.close()


# Fixture para passar a SessionLocal nos testes se necessário
@pytest.fixture
def db_session():
    """Fornece uma sessão de banco de dados para testes."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
