from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker, Session
import pytest

from app.main import app
from app.database import get_db
from app.models import Base

# Usar banco SQLite em memória para testes - com StaticPool para evitar problemas de thread
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Criar todas as tabelas no engine de teste
Base.metadata.create_all(bind=engine)


@pytest.fixture
def db() -> Session:
    """Fornece uma sessão de banco para cada teste com isolamento de transações."""
    # Iniciar uma transação
    connection = engine.connect()
    transaction = connection.begin()
    
    # Usar a conexão da transação para criar a sessão
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    # Fazer rollback da transação após o teste
    transaction.rollback()
    connection.close()
    session.close()


@pytest.fixture
def client(db: Session) -> TestClient:
    """Fornece um cliente de teste com banco de testes."""
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    test_client = TestClient(app)
    
    yield test_client
    
    app.dependency_overrides.clear()


def test_health_retorna_ok(client):
    resposta = client.get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok", "message": "Hello World"}


def test_index_renderiza_a_tela(client):
    resposta = client.get("/")

    assert resposta.status_code == 200
    assert "AFYA" in resposta.text


def test_a_tela_nao_traz_nenhum_nome_escrito_no_html(client):
    """Os nomes chegam pela API: o HTML servido nao pode conte-los."""
    resposta = client.get("/")

    assert "Ada Lovelace" not in resposta.text
    assert "Alan Turing" not in resposta.text


def test_lista_usuarios_retorna_json_com_id_e_nome(client):
    resposta = client.get("/users")

    assert resposta.status_code == 200
    assert resposta.headers["content-type"] == "application/json"

    usuarios = resposta.json()
    assert isinstance(usuarios, list)
    for usuario in usuarios:
        assert "id" in usuario
        assert "name" in usuario


def test_lista_vazia_continua_sendo_sucesso(client):
    """Sem usuarios a resposta e 200 com [], nunca 404: a tela nao trata isso como erro."""
    resposta = client.get("/users")

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_cria_usuario_com_nome_valido(client):
    resposta = client.post("/users", json={"name": "Grace Hopper", "password": "senha123"})

    assert resposta.status_code == 201
    data = resposta.json()
    assert data["name"] == "Grace Hopper"
    assert "id" in data


def test_nao_cria_usuario_com_nome_vazio(client):
    resposta = client.post("/users", json={"name": "", "password": "senha123"})

    assert resposta.status_code == 422


def test_nao_cria_usuario_com_senha_curta(client):
    resposta = client.post("/users", json={"name": "Maria", "password": "123"})

    assert resposta.status_code == 422


def test_atualiza_usuario_existente(client):
    # Primeiro, cria um usuário
    resposta_criacao = client.post("/users", json={"name": "Ana", "password": "senha123"})
    user_id = resposta_criacao.json()["id"]
    
    # Depois, atualiza
    resposta = client.put(
        f"/users/{user_id}",
        json={"name": "Ana Silva", "password": "nova_senha_123"}
    )
    
    assert resposta.status_code == 200
    data = resposta.json()
    assert data["name"] == "Ana Silva"
    assert data["id"] == user_id


def test_retorna_404_ao_atualizar_usuario_inexistente(client):
    resposta = client.put(
        "/users/9999",
        json={"name": "Inexistente", "password": "senha123"}
    )
    
    assert resposta.status_code == 404


def test_deleta_usuario_existente(client):
    # Primeiro, cria um usuário
    resposta_criacao = client.post("/users", json={"name": "Pedro", "password": "senha123"})
    user_id = resposta_criacao.json()["id"]
    
    # Depois, deleta
    resposta = client.delete(f"/users/{user_id}")
    
    assert resposta.status_code == 204
    
    # Verifica que foi deletado
    resposta_get = client.get("/users")
    usuarios = resposta_get.json()
    assert len(usuarios) == 0


def test_retorna_404_ao_deletar_usuario_inexistente(client):
    resposta = client.delete("/users/9999")
    
    assert resposta.status_code == 404

