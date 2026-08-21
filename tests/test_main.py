import pytest
from fastapi.testclient import TestClient

from app.cfm_client import CFMDoctor, CFMDoctorInactive, CFMDoctorNotFound, CFMUnavailable, CFMValidationTimeout
from app.main import CFM_RETRY_COUNT


def dados_usuario(nome: str = "Joao Silva", email: str = "joao@example.com") -> dict:
    return {"nome": nome, "email": email, "senha": "senha-segura"}


def login_admin(client: TestClient) -> None:
    resposta = client.post("/admin/login", json={"usuario": "Ademilson", "senha": "12345678"})
    assert resposta.status_code == 204


def login_usuario(client: TestClient, email: str = "joao@example.com", senha: str = "senha-segura") -> None:
    resposta = client.post("/login", json={"email": email, "senha": senha})
    assert resposta.status_code == 204


def criar_usuario(client: TestClient, **kwargs) -> dict:
    dados = dados_usuario(**kwargs)
    resposta = client.post("/users", json=dados)
    assert resposta.status_code == 201
    return resposta.json()


def test_health_retorna_ok(client: TestClient):
    assert client.get("/health").json() == {"status": "ok", "message": "Hello World"}


def test_index_e_login_admin_retornam_200(client: TestClient):
    index = client.get("/")
    assert index.status_code == 200
    assert "/static/hero-medica-institucional.png" in index.text
    assert client.get("/static/hero-medica-institucional.png").status_code == 200
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
    assert resposta.json()["doctor"]["cfm_validation_status"] == "VALIDATED"


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


def test_cfm_nao_encontrado_bloqueia_e_indisponibilidade_deixa_pendente(client: TestClient, definir_cliente_cfm):
    usuario_ausente = criar_usuario(client, nome="Ausente", email="ausente@example.com")

    class ClienteNaoEncontrado:
        def find_doctor(self, crm: str, uf: str):
            raise CFMDoctorNotFound()

    definir_cliente_cfm(ClienteNaoEncontrado())
    nao_encontrado = client.post(f"/users/{usuario_ausente['id']}/doctor", json={"crm": "12345", "uf": "SP"})

    class ClienteIndisponivel:
        calls = 0

        def find_doctor(self, crm: str, uf: str):
            self.calls += 1
            raise CFMUnavailable()

    usuario_indisponivel = criar_usuario(client, nome="Indisponivel", email="indisponivel@example.com")
    definir_cliente_cfm(ClienteIndisponivel())
    indisponivel = client.post(f"/users/{usuario_indisponivel['id']}/doctor", json={"crm": "12345", "uf": "SP"})

    assert nao_encontrado.status_code == 422
    assert nao_encontrado.json()["detail"]["code"] == "CRM_NOT_FOUND"
    assert indisponivel.status_code == 202
    assert indisponivel.json()["cfm_validation_status"] == "VALIDATION_PENDING"
    assert indisponivel.json()["cfm_validation_reason"] == "CFM_UNAVAILABLE"
    assert indisponivel.json()["cfm_validated_at"] is None


@pytest.mark.parametrize(
    ("cliente", "status_esperado", "codigo"),
    [
        (CFMDoctorNotFound(), 422, "CRM_NOT_FOUND"),
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


def test_cfm_reexecuta_ate_obter_validacao_com_sucesso(client: TestClient, definir_cliente_cfm):
    class ClienteOscilando:
        def __init__(self):
            self.calls = 0

        def find_doctor(self, crm: str, uf: str):
            self.calls += 1
            if self.calls <= CFM_RETRY_COUNT:
                raise CFMUnavailable()
            return CFMDoctor(
                nome="Medico Recuperado",
                crm=crm,
                uf=uf,
                situacao="Regular",
                tipo_inscricao="Principal",
                especialidades=(),
            )

    cliente = ClienteOscilando()
    definir_cliente_cfm(cliente)
    resposta = client.post(
        "/users",
        json={
            "nome": "Dra Retry",
            "email": "retry@example.com",
            "senha": "senha-segura",
            "doctor": {"crm": "12345", "uf": "SP"},
        },
    )

    assert resposta.status_code == 201
    assert cliente.calls == CFM_RETRY_COUNT + 1
    assert resposta.json()["doctor"]["cfm_validation_status"] == "VALIDATED"


def test_timeout_salva_pendente_e_medico_pode_tentar_novamente(client: TestClient, definir_cliente_cfm):
    class ClienteComTimeout:
        def __init__(self):
            self.calls = 0

        def find_doctor(self, crm: str, uf: str):
            self.calls += 1
            raise CFMValidationTimeout()

    cliente_timeout = ClienteComTimeout()
    definir_cliente_cfm(cliente_timeout)
    cadastro = client.post(
        "/users",
        json={
            "nome": "Dra Pendente",
            "email": "pendente@example.com",
            "senha": "senha-segura",
            "doctor": {"crm": "12345", "uf": "SP"},
        },
    )
    assert cadastro.status_code == 202
    assert cliente_timeout.calls == CFM_RETRY_COUNT + 1
    assert cadastro.json()["doctor"]["cfm_validation_reason"] == "VALIDATION_TIMEOUT"

    class ClienteDisponivel:
        def find_doctor(self, crm: str, uf: str):
            return CFMDoctor(
                nome="Medico Pendente",
                crm=crm,
                uf=uf,
                situacao="Regular",
                tipo_inscricao="Principal",
                especialidades=(),
            )

    definir_cliente_cfm(ClienteDisponivel())
    login_usuario(client, email="pendente@example.com")
    revalidacao = client.post("/me/doctor/revalidate")

    assert revalidacao.status_code == 200
    assert revalidacao.json()["cfm_validation_status"] == "VALIDATED"
    assert revalidacao.json()["cfm_validation_reason"] is None


def test_endpoint_de_validacao_retorna_pendente_apos_timeout(client: TestClient, definir_cliente_cfm):
    class ClienteComTimeout:
        def __init__(self):
            self.calls = 0

        def find_doctor(self, crm: str, uf: str):
            self.calls += 1
            raise CFMValidationTimeout()

    cliente = ClienteComTimeout()
    definir_cliente_cfm(cliente)
    resposta = client.post("/cfm/validate", json={"crm": "12345", "uf": "SP"})

    assert resposta.status_code == 200
    assert resposta.json()["valid"] is False
    assert resposta.json()["reason"] == "VALIDATION_TIMEOUT"
    assert cliente.calls == CFM_RETRY_COUNT + 1


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


def test_paginas_de_login_e_conta_exigem_sessao(client: TestClient):
    assert client.get("/login").status_code == 200
    assert client.get("/conta", follow_redirects=False).status_code == 303
    assert client.get("/me").status_code == 401


def test_usuario_faz_login_com_email_sem_diferenciar_maiusculas(client: TestClient):
    criar_usuario(client)

    assert client.post("/login", json={"email": "JOAO@EXAMPLE.COM", "senha": "errada"}).status_code == 401
    login_usuario(client, email="JOAO@EXAMPLE.COM")

    assert client.get("/conta").status_code == 200
    assert client.get("/me").json()["email"] == "joao@example.com"


def test_usuario_edita_apenas_o_proprio_perfil_completo(client: TestClient):
    primeiro = criar_usuario(client, nome="Primeiro", email="primeiro@example.com")
    criar_usuario(client, nome="Segundo", email="segundo@example.com")
    login_usuario(client, email=primeiro["email"])

    resposta = client.put(
        "/me",
        json={
            "nome": "Primeiro Atualizado",
            "email": "PRIMEIRO.NOVO@EXAMPLE.COM",
            "telefone": "(11) 99999-9999",
            "documento": "123.456.789-00",
            "data_nascimento": "1990-05-10",
            "escolaridade": "Superior completo",
            "cep": "01310100",
            "logradouro": "Avenida Paulista",
            "numero": "1000",
            "complemento": "Sala 1",
            "bairro": "Bela Vista",
            "cidade": "Sao Paulo",
            "endereco_uf": "sp",
        },
    )

    assert resposta.status_code == 200
    perfil = resposta.json()
    assert perfil["id"] == primeiro["id"]
    assert perfil["email"] == "primeiro.novo@example.com"
    assert perfil["cep"] == "01310-100"
    assert perfil["endereco_uf"] == "SP"
    assert perfil["documento"] == "123.456.789-00"

    login_admin(client)
    usuarios = client.get("/users").json()
    assert len(usuarios) == 2
    assert "documento" not in usuarios[0]


def test_medico_completa_dados_profissionais_sem_alterar_crm(client: TestClient):
    resposta_cadastro = client.post(
        "/users",
        json={
            "nome": "Dra Ana",
            "email": "dra.ana@example.com",
            "senha": "senha-segura",
            "doctor": {"crm": "12345", "uf": "SP"},
        },
    )
    assert resposta_cadastro.status_code == 201
    login_usuario(client, email="dra.ana@example.com")

    resposta = client.put(
        "/me",
        json={
            "nome": "Dra Ana",
            "email": "dra.ana@example.com",
            "doctor": {
                "hospital": "Hospital Central",
                "especialidade_atuacao": "Cardiologia",
            },
        },
    )

    assert resposta.status_code == 200
    assert resposta.json()["doctor"]["crm"] == "12345"
    assert resposta.json()["doctor"]["uf"] == "SP"
    assert resposta.json()["doctor"]["hospital"] == "Hospital Central"
    assert resposta.json()["doctor"]["especialidade_atuacao"] == "Cardiologia"


def test_usuario_comum_nao_pode_gravar_campos_de_medico(client: TestClient):
    criar_usuario(client)
    login_usuario(client)

    resposta = client.put(
        "/me",
        json={
            "nome": "Joao Silva",
            "email": "joao@example.com",
            "doctor": {"hospital": "Hospital Central"},
        },
    )

    assert resposta.status_code == 422
    assert "exclusivos" in resposta.text


def test_documento_nao_pode_ser_usado_por_duas_contas(client: TestClient):
    criar_usuario(client, nome="Ana", email="ana@example.com")
    criar_usuario(client, nome="Bia", email="bia@example.com")

    login_usuario(client, email="ana@example.com")
    primeiro = client.put(
        "/me",
        json={"nome": "Ana", "email": "ana@example.com", "documento": "RG-123456"},
    )
    assert primeiro.status_code == 200
    assert client.post("/logout").status_code == 204

    login_usuario(client, email="bia@example.com")
    duplicado = client.put(
        "/me",
        json={"nome": "Bia", "email": "bia@example.com", "documento": "rg-123456"},
    )
    assert duplicado.status_code == 409


def test_usuario_troca_senha_informando_a_atual(client: TestClient):
    criar_usuario(client)
    login_usuario(client)

    incorreta = client.put(
        "/me/password",
        json={"senha_atual": "senha-incorreta", "nova_senha": "nova-senha-segura"},
    )
    assert incorreta.status_code == 401

    correta = client.put(
        "/me/password",
        json={"senha_atual": "senha-segura", "nova_senha": "nova-senha-segura"},
    )
    assert correta.status_code == 204
    assert client.post("/logout").status_code == 204
    assert client.post("/login", json={"email": "joao@example.com", "senha": "senha-segura"}).status_code == 401
    login_usuario(client, senha="nova-senha-segura")


def test_logout_de_usuario_encerra_sessao(client: TestClient):
    criar_usuario(client)
    login_usuario(client)

    assert client.post("/logout").status_code == 204
    assert client.get("/me").status_code == 401
