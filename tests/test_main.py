"""
Testes para a aplicação FastAPI com persistência em banco de dados.

O conftest.py automaticamente configura um banco SQLite em memória,
então esses testes rodam rápido e isolados.
"""

from fastapi.testclient import TestClient

from app.main import app

# Client para fazer requisições nos testes
client = TestClient(app)


def test_health_retorna_status_ok():
    """
    Testa a rota GET /health.
    
    Verifica que:
    - Retorna status HTTP 200 (sucesso)
    - Retorna JSON com status "ok" e message "Hello World"
    """
    resposta = client.get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok", "message": "Hello World"}


def test_index_renderiza_html():
    """
    Testa a rota GET /.
    
    Verifica que:
    - Retorna status HTTP 200 (sucesso)
    - Retorna HTML que contém "User Manager" no título
    """
    resposta = client.get("/")

    assert resposta.status_code == 200
    assert "User Manager" in resposta.text


def test_get_users_retorna_lista():
    """
    Testa a rota GET /users.
    
    Verifica que:
    - Retorna status HTTP 200 (sucesso)
    - Retorna um JSON que é uma lista
    """
    resposta = client.get("/users")

    assert resposta.status_code == 200
    usuarios = resposta.json()
    assert isinstance(usuarios, list)


def test_get_users_estrutura_valida():
    """
    Testa a estrutura dos dados retornados por GET /users.
    
    Verifica que:
    - A lista tem pelo menos um usuário
    - Cada usuário tem os campos necessários: id, name, email
    - Os campos têm os tipos de dados corretos
    """
    resposta = client.get("/users")
    usuarios = resposta.json()

    # Verificar que a lista não está vazia
    assert len(usuarios) > 0

    # Verificar a estrutura do primeiro usuário
    primeiro_usuario = usuarios[0]
    assert "id" in primeiro_usuario
    assert "name" in primeiro_usuario
    assert "email" in primeiro_usuario

    # Verificar os tipos de dados
    assert isinstance(primeiro_usuario["id"], int)
    assert isinstance(primeiro_usuario["name"], str)
    assert isinstance(primeiro_usuario["email"], str)


def test_get_users_contém_dados_esperados():
    """
    Testa se os usuários retornados têm os dados esperados.
    
    Verifica que:
    - Existem pelo menos 3 usuários (João, Maria, Pedro)
    - João Silva está na lista
    """
    resposta = client.get("/users")
    usuarios = resposta.json()

    # Verificar quantidade de usuários
    assert len(usuarios) >= 3

    # Verificar que João Silva está na lista
    nomes = [usuario["name"] for usuario in usuarios]
    assert "João Silva" in nomes


def test_usuarios_persistem_no_banco(db_session):
    """
    Testa se os usuários estão sendo persistidos no banco de dados.
    
    Verifica que:
    - Ao consultar o banco diretamente, encontramos os mesmos usuários
    - O banco de dados está sendo usado corretamente
    """
    from app.models import User
    
    resposta = client.get("/users")
    usuarios_da_api = resposta.json()

    # Consultar o banco diretamente
    usuarios_do_banco = db_session.query(User).all()
    
    assert len(usuarios_do_banco) == len(usuarios_da_api)
    assert usuarios_do_banco[0].name == usuarios_da_api[0]["name"]


