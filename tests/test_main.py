import pytest
from fastapi.testclient import TestClient

from app.main import USUARIOS, app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_usuarios():
    USUARIOS[:] = [
        {"id": 1, "nome": "André Seabra", "email": "andre.seabra@teste.com"},
        {"id": 2, "nome": "Ademilson Mamilo", "email": "ademilson.mamilo@teste.com"},
        {"id": 3, "nome": "Sant'anna Thanos", "email": "santanna.thanos@teste.com"},
        {"id": 4, "nome": "Pagliasse Trepa", "email": "pagliasse.trepa@teste.com"},
    ]


def test_health_retorna_ok():
    resposta = client.get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok", "message": "Hello World"}


def test_index_renderiza_a_tela():
    resposta = client.get("/")

    assert resposta.status_code == 200
    assert "User Manager" in resposta.text

def test_users_retorna_lista_de_usuarios():
    resposta = client.get("/users")

    assert resposta.status_code == 200

    usuarios = resposta.json()
    assert isinstance(usuarios, list)

    for usuario in usuarios:
        assert "id" in usuario
        assert "nome" in usuario
        assert "email" in usuario


def test_users_pode_criar_novo_usuario():
    resposta = client.post(
        "/users",
        json={"nome": "Novo Usuário", "email": "novo.usuario@example.com"},
    )

    assert resposta.status_code == 201

    usuario = resposta.json()
    assert usuario["nome"] == "Novo Usuário"
    assert usuario["email"] == "novo.usuario@example.com"

    usuarios = client.get("/users").json()
    assert usuarios[-1]["nome"] == "Novo Usuário"
    assert usuarios[-1]["email"] == "novo.usuario@example.com"


def test_users_recusa_email_invalido():
    resposta = client.post(
        "/users",
        json={"nome": "Novo Usuário", "email": "nao-email"},
    )

    assert resposta.status_code == 422

    detalhe = resposta.json()["detail"]
    assert isinstance(detalhe, list)
    assert detalhe[0]["loc"][-1] == "email"
    assert detalhe[0]["type"] in {"value_error.email", "value_error"}


def test_users_recusa_nome_ou_email_faltando():
    resposta = client.post(
        "/users",
        json={"email": "novo.usuario@example.com"},
    )

    assert resposta.status_code == 422

    detalhe = resposta.json()["detail"]
    assert any(item["loc"][-1] == "nome" for item in detalhe)
