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


def test_admin_pode_aprovar_usuario_pendente():
    USUARIOS.append({
        "id": 5,
        "nome": "Médico Pendente",
        "email": "pendente@example.com",
        "crm": "123",
        "uf": "SP",
        "cfm_status": "VALIDATION_PENDING",
    })

    resposta = client.patch(
        "/users/5/cfm-status?admin_email=andre.seabra@teste.com",
        json={"action": "approve"},
    )

    assert resposta.status_code == 200
    assert resposta.json()["cfm_status"] == "VALIDATED"
    assert resposta.json()["cfm_validated_at"] is not None


def test_medico_pendente_continua_pendente_ao_tentar_novamente():
    USUARIOS.append({
        "id": 5,
        "nome": "Médico Pendente",
        "email": "pendente@example.com",
        "crm": "123",
        "uf": "SP",
        "cfm_status": "VALIDATION_PENDING",
    })

    resposta = client.post(
        "/users",
        json={"nome": "Médico Pendente", "email": "pendente@example.com", "crm": "123", "uf": "SP", "is_doctor": True},
    )

    assert resposta.status_code == 200
    assert resposta.json()["cfm_status"] == "VALIDATION_PENDING"
