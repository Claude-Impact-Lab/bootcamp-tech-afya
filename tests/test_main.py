import pytest
from fastapi.testclient import TestClient

from app.cfm_client import CFMDoctor, CFMDoctorInactive, CFMDoctorNotFound, CFMUnavailable, CFMValidationTimeout


def dados_usuario(nome: str = "Joao Silva", email: str = "joao@example.com") -> dict:
    return {"nome": nome, "email": email, "senha": "senha-segura"}


def login_admin(client: TestClient) -> None:
    resposta = client.post("/admin/login", json={"usuario": "Ademilson", "senha": "12345678"})
    assert resposta.status_code == 204


def criar_usuario(client: TestClient, **kwargs) -> dict:
    dados = dados_usuario(**kwargs)
    resposta = client.post("/users", json=dados)
    assert resposta.status_code == 201
    return resposta.json()


def test_health_retorna_ok(client: TestClient):
    assert client.get("/health").json() == {"status": "ok", "message": "Hello World"}


def test_index_e_login_admin_retornam_200(client: TestClient):
    assert client.get("/").status_code == 200
    assert client.get("/admin/login").status_code == 200
    assert client.get("/admin", follow_redirects=False).status_code == 303


def test_cadastro_exige_senha_com_oito_caracteres(client: TestClient):
    sem_senha = client.post("/users", json={"nome": "Ana", "email": "ana@example.com"})
    curta = client.post("/users", json={"nome": "Ana", "email": "ana@example.com", "senha": "123"})
    assert sem_senha.status_code == 422
    assert curta.status_code == 422


def test_criar_usuario_nao_retorna_senha_nem_hash(client: TestClient):
    usuario = criar_usuario(client)
    assert usuario["nome"] == "Joao Silva"
    assert usuario["email"] == "joao@example.com"
    assert usuario["id"] > 0
    assert "senha" not in usuario
    assert "password_hash" not in usuario


def test_cadastro_usuario_e_medico_salva_os_dois_apos_validacao_cfm(client: TestClient):
    resposta = client.post(
        "/users",
        json={
            "nome": "Dra Ana",
            "email": "ana.medica@example.com",
            "senha": "senha-segura",
            "doctor": {"crm": "1234567", "uf": "SP"},
        },
    )

    assert resposta.status_code == 201
    assert resposta.json()["doctor"]["crm"] == "1234567"
    assert resposta.json()["doctor"]["cfm_validated_at"] is not None


def test_listagem_e_edicao_exigem_admin(client: TestClient):
    usuario = criar_usuario(client)
    assert client.get("/users").status_code == 401
    assert client.get(f"/users/{usuario['id']}").status_code == 401
    assert client.put(f"/users/{usuario['id']}", json={"nome": "Novo", "email": "novo@example.com"}).status_code == 401
    assert client.delete(f"/users/{usuario['id']}").status_code == 401


def test_login_admin_invalido_e_valido(client: TestClient):
    assert client.post("/admin/login", json={"usuario": "Ademilson", "senha": "errada"}).status_code == 401
    login_admin(client)
    assert client.get("/users").status_code == 200
    assert client.get("/admin").status_code == 200


def test_login_admin_nao_diferencia_maiusculas_no_usuario(client: TestClient):
    resposta = client.post("/admin/login", json={"usuario": "aDeMiLsOn", "senha": "12345678"})
    assert resposta.status_code == 204


def test_email_de_cadastro_nao_diferencia_maiusculas(client: TestClient):
    criar_usuario(client, nome="Ana", email="ANA@EXAMPLE.COM")
    resposta = client.post("/users", json=dados_usuario("Outra Ana", "ana@example.com"))
    assert resposta.status_code == 409


def test_admin_lista_e_edita_usuario_sem_expor_hash(client: TestClient):
    usuario = criar_usuario(client, nome="Ana", email="ana@example.com")
    login_admin(client)
    listagem = client.get("/users")
    assert listagem.status_code == 200
    assert listagem.json()[0]["email"] == "ana@example.com"
    assert "password_hash" not in listagem.json()[0]

    resposta = client.put(f"/users/{usuario['id']}", json={"nome": "Ana Paula", "email": "ana.paula@example.com", "senha": "nova-senha-segura"})
    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Ana Paula"
    assert client.get(f"/users/{usuario['id']}").json()["email"] == "ana.paula@example.com"


def test_admin_pode_manter_senha_antiga_ao_editar(client: TestClient):
    usuario = criar_usuario(client)
    login_admin(client)
    resposta = client.put(f"/users/{usuario['id']}", json={"nome": "Joao Atualizado", "email": "joao@example.com", "senha": ""})
    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Joao Atualizado"


def test_email_duplicado_retorna_409(client: TestClient):
    criar_usuario(client, nome="Fia", email="fia@example.com")
    resposta = client.post("/users", json=dados_usuario("Outra Fia", "fia@example.com"))
    assert resposta.status_code == 409


def test_admin_exclui_usuario(client: TestClient):
    usuario = criar_usuario(client)
    login_admin(client)
    assert client.delete(f"/users/{usuario['id']}").status_code == 204
    assert client.get(f"/users/{usuario['id']}").status_code == 404


def test_medico_pode_ser_cadastrado_e_admin_consulta(client: TestClient):
    usuario = criar_usuario(client, nome="Dra Bia", email="bia@example.com")
    resposta = client.post(f"/users/{usuario['id']}/doctor", json={"crm": "12345", "uf": "sp"})
    assert resposta.status_code == 201
    login_admin(client)
    assert client.get(f"/users/{usuario['id']}").json()["doctor"]["uf"] == "SP"


def test_cadastro_medico_recusa_uf_invalida(client: TestClient):
    usuario = criar_usuario(client)
    resposta = client.post(f"/users/{usuario['id']}/doctor", json={"crm": "12345", "uf": "XX"})
    assert resposta.status_code == 422
    assert "uf" in resposta.text.lower()


def test_cadastro_medico_recusa_crm_com_letras_ou_tamanho_invalido(client: TestClient):
    usuario = criar_usuario(client)
    com_letras = client.post(f"/users/{usuario['id']}/doctor", json={"crm": "12A45", "uf": "SP"})
    vazio = client.post(f"/users/{usuario['id']}/doctor", json={"crm": "", "uf": "SP"})
    longo = client.post(f"/users/{usuario['id']}/doctor", json={"crm": "12345678", "uf": "SP"})
    assert com_letras.status_code == 422
    assert vazio.status_code == 422
    assert longo.status_code == 422
    assert "crm" in com_letras.text.lower()


def test_editar_medico_requer_admin_e_aplica_as_mesmas_validacoes(client: TestClient):
    usuario = criar_usuario(client)
    client.post(f"/users/{usuario['id']}/doctor", json={"crm": "12345", "uf": "SP"})

    sem_login = client.put(f"/users/{usuario['id']}/doctor", json={"crm": "54321", "uf": "RJ"})
    assert sem_login.status_code == 401

    login_admin(client)
    invalido = client.put(f"/users/{usuario['id']}/doctor", json={"crm": "abc", "uf": "XX"})
    valido = client.put(f"/users/{usuario['id']}/doctor", json={"crm": "054321", "uf": "rj"})

    assert invalido.status_code == 422
    assert valido.status_code == 200
    assert valido.json()["crm"] == "054321"
    assert valido.json()["uf"] == "RJ"


def test_editar_medico_retorna_404_para_usuario_ou_medico_ausente(client: TestClient):
    login_admin(client)
    usuario_sem_medico = criar_usuario(client)

    inexistente = client.put("/users/999/doctor", json={"crm": "12345", "uf": "SP"})
    sem_medico = client.put(f"/users/{usuario_sem_medico['id']}/doctor", json={"crm": "12345", "uf": "SP"})

    assert inexistente.status_code == 404
    assert sem_medico.status_code == 404


def test_nao_permite_cadastrar_o_mesmo_usuario_como_medico_duas_vezes(client: TestClient):
    usuario = criar_usuario(client)
    primeiro = client.post(f"/users/{usuario['id']}/doctor", json={"crm": "12345", "uf": "SP"})
    repetido = client.post(f"/users/{usuario['id']}/doctor", json={"crm": "54321", "uf": "RJ"})

    assert primeiro.status_code == 201
    assert repetido.status_code == 409


def test_cadastro_medico_guarda_momento_da_validacao_cfm(client: TestClient):
    usuario = criar_usuario(client)
    resposta = client.post(f"/users/{usuario['id']}/doctor", json={"crm": "1234567", "uf": "SP"})

    assert resposta.status_code == 201
    assert resposta.json()["cfm_validated_at"] is not None


def test_endpoint_cfm_validate_retorna_contrato_da_validacao(client: TestClient):
    resposta = client.post("/cfm/validate", json={"crm": "197", "uf": "ro"})

    assert resposta.status_code == 200
    assert resposta.json() == {
        "valid": True,
        "crm": "197",
        "uf": "RO",
        "name": "Medico de Teste",
        "status": "ATIVO",
        "reason": None,
    }


def test_endpoint_cfm_validate_informa_crm_inativo(client: TestClient, definir_cliente_cfm):
    medico = CFMDoctor(
        nome="Medico Inativo",
        crm="12345",
        uf="SP",
        situacao="Cancelado",
        tipo_inscricao="Principal",
        especialidades=(),
    )

    class ClienteInativo:
        def find_doctor(self, crm: str, uf: str):
            raise CFMDoctorInactive(medico)

    definir_cliente_cfm(ClienteInativo())
    resposta = client.post("/cfm/validate", json={"crm": "12345", "uf": "SP"})

    assert resposta.status_code == 200
    assert resposta.json()["valid"] is False
    assert resposta.json()["reason"] == "CRM_INACTIVE"
    assert resposta.json()["status"] == "CANCELADO"


def test_cfm_nao_encontrado_e_indisponivel_sao_diferenciados(client: TestClient, definir_cliente_cfm):
    usuario_ausente = criar_usuario(client, nome="Ausente", email="ausente@example.com")

    class ClienteNaoEncontrado:
        def find_doctor(self, crm: str, uf: str):
            raise CFMDoctorNotFound()

    definir_cliente_cfm(ClienteNaoEncontrado())
    nao_encontrado = client.post(f"/users/{usuario_ausente['id']}/doctor", json={"crm": "12345", "uf": "SP"})

    class ClienteIndisponivel:
        def find_doctor(self, crm: str, uf: str):
            raise CFMUnavailable()

    usuario_indisponivel = criar_usuario(client, nome="Indisponivel", email="indisponivel@example.com")
    definir_cliente_cfm(ClienteIndisponivel())
    indisponivel = client.post(f"/users/{usuario_indisponivel['id']}/doctor", json={"crm": "12345", "uf": "SP"})

    assert nao_encontrado.status_code == 422
    assert nao_encontrado.json()["detail"]["code"] == "CRM_NOT_FOUND"
    assert indisponivel.status_code == 503
    assert indisponivel.json()["detail"]["code"] == "CFM_UNAVAILABLE"


@pytest.mark.parametrize(
    ("cliente", "status_esperado", "codigo"),
    [
        (CFMDoctorNotFound(), 422, "CRM_NOT_FOUND"),
        (CFMUnavailable(), 503, "CFM_UNAVAILABLE"),
        (CFMValidationTimeout(), 504, "VALIDATION_TIMEOUT"),
    ],
)
def test_falha_cfm_no_cadastro_nao_salva_usuario(client: TestClient, definir_cliente_cfm, cliente, status_esperado, codigo):
    class ClienteComFalha:
        def find_doctor(self, crm: str, uf: str):
            raise cliente

    definir_cliente_cfm(ClienteComFalha())
    resposta = client.post(
        "/users",
        json={
            "nome": "Cadastro Sem Sucesso",
            "email": "sem.sucesso@example.com",
            "senha": "senha-segura",
            "doctor": {"crm": "12345", "uf": "SP"},
        },
    )

    assert resposta.status_code == status_esperado
    assert resposta.json()["detail"]["code"] == codigo
    login_admin(client)
    assert client.get("/users").json() == []


def test_crm_invalido_no_cadastro_tambem_nao_salva_usuario(client: TestClient):
    resposta = client.post(
        "/users",
        json={
            "nome": "CRM Invalido",
            "email": "crm.invalido@example.com",
            "senha": "senha-segura",
            "doctor": {"crm": "abc", "uf": "SP"},
        },
    )

    assert resposta.status_code == 422
    login_admin(client)
    assert client.get("/users").json() == []


def test_logout_remove_acesso_administrativo(client: TestClient):
    login_admin(client)
    assert client.post("/admin/logout").status_code == 204
    assert client.get("/users").status_code == 401
