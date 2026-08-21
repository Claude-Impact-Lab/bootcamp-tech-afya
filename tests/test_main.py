from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.cfm_client import CfmDoctorDetails
from app.main import CFM_REVALIDATION_EVENTS, CFM_REVALIDATION_LOCK, USUARIOS, app

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


def test_admin_pode_revalidar_automaticamente_usuario_pendente(monkeypatch):
    USUARIOS.append({
        "id": 5,
        "nome": "Médico Pendente",
        "email": "pendente@example.com",
        "crm": "123",
        "uf": "SP",
        "cfm_status": "VALIDATION_PENDING",
    })
    validado_em = datetime.now(timezone.utc)
    monkeypatch.setattr(
        "app.main.validar_medico_no_cfm",
        lambda crm, uf, cancelled=None: (
            "VALIDATED",
            validado_em,
            CfmDoctorDetails(situacao="Ativo", ano_formatura="2002"),
        ),
    )

    resposta = client.post(
        "/users/5/cfm-revalidate?admin_email=andre.seabra@teste.com",
    )

    assert resposta.status_code == 200
    assert resposta.json()["cfm_status"] == "VALIDATED"
    assert resposta.json()["cfm_validated_at"] is not None
    assert resposta.json()["cfm_situacao"] == "Ativo"
    assert resposta.json()["cfm_ano_formatura"] == "2002"


def test_revalidacao_sem_confirmacao_mantem_usuario_pendente(monkeypatch):
    USUARIOS.append({
        "id": 5,
        "nome": "Médico Pendente",
        "email": "pendente@example.com",
        "crm": "123",
        "uf": "SP",
        "cfm_status": "VALIDATION_PENDING",
    })
    monkeypatch.setattr(
        "app.main.validar_medico_no_cfm",
        lambda crm, uf, cancelled=None: ("VALIDATION_PENDING", None, None),
    )

    resposta = client.post(
        "/users/5/cfm-revalidate?admin_email=andre.seabra@teste.com",
    )

    assert resposta.status_code == 200
    assert resposta.json()["cfm_status"] == "VALIDATION_PENDING"


def test_admin_pode_interromper_revalidacao_ativa():
    from threading import Event

    event = Event()
    with CFM_REVALIDATION_LOCK:
        CFM_REVALIDATION_EVENTS["validacao-teste"] = event
    try:
        resposta = client.post(
            "/cfm/revalidation/validacao-teste/cancel?admin_email=andre.seabra@teste.com",
        )

        assert resposta.status_code == 200
        assert resposta.json() == {"cancelled": True}
        assert event.is_set()
    finally:
        with CFM_REVALIDATION_LOCK:
            CFM_REVALIDATION_EVENTS.pop("validacao-teste", None)


def test_admin_pode_editar_detalhes_cfm_de_medico_pendente():
    USUARIOS.append({
        "id": 5,
        "nome": "Médico Pendente",
        "email": "pendente@example.com",
        "crm": "123",
        "uf": "SP",
        "cfm_status": "VALIDATION_PENDING",
    })

    resposta = client.patch(
        "/users/5/cfm-details?admin_email=andre.seabra@teste.com",
        json={
            "cfm_data_inscricao": "01/02/2003",
            "cfm_situacao": "Ativo",
            "cfm_especialidades_areas": "Cardiologia",
        },
    )

    assert resposta.status_code == 200
    assert resposta.json()["cfm_data_inscricao"] == "01/02/2003"
    assert resposta.json()["cfm_situacao"] == "Ativo"
    assert resposta.json()["cfm_especialidades_areas"] == "Cardiologia"


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


def test_mesmo_crm_e_mesmos_dados_retorna_login_sem_duplicar():
    USUARIOS.append({
        "id": 5,
        "nome": "Médico Existente",
        "email": "medico@example.com",
        "crm": "123",
        "uf": "SP",
        "cfm_status": "VALIDATED",
    })

    resposta = client.post(
        "/users",
        json={"nome": "Médico Existente", "email": "medico@example.com", "crm": "123", "uf": "SP", "is_doctor": True},
    )

    assert resposta.status_code == 200
    assert len([item for item in USUARIOS if item.get("crm") == "123"]) == 1


@pytest.mark.parametrize("campo, valor", [
    ("nome", "Outro Médico"),
    ("email", "outro@example.com"),
])
def test_mesmo_crm_e_uf_com_dados_diferentes_e_invalido(campo, valor):
    USUARIOS.append({
        "id": 5,
        "nome": "Médico Existente",
        "email": "medico@example.com",
        "crm": "123",
        "uf": "SP",
        "cfm_status": "VALIDATED",
    })
    payload = {
        "nome": "Médico Existente",
        "email": "medico@example.com",
        "crm": "123",
        "uf": "SP",
        "is_doctor": True,
    }
    payload[campo] = valor

    resposta = client.post("/users", json=payload)

    assert resposta.status_code == 409
    assert resposta.json()["detail"] == "Dados inválidos. Confira e tente novamente"
    assert len([item for item in USUARIOS if item.get("crm") == "123"]) == 1


def test_mesmo_numero_de_crm_em_ufs_diferentes_e_permitido():
    USUARIOS.append({
        "id": 5,
        "nome": "Médico de São Paulo",
        "email": "sp@example.com",
        "crm": "123",
        "uf": "SP",
        "cfm_status": "VALIDATED",
    })

    resposta = client.post(
        "/users",
        json={"nome": "Médica do Rio", "email": "rj@example.com", "crm": "123", "uf": "RJ", "is_doctor": True},
    )

    assert resposta.status_code == 201
    registros = [item for item in USUARIOS if item.get("crm") == "123"]
    assert len(registros) == 2
    assert {item["uf"] for item in registros} == {"SP", "RJ"}
