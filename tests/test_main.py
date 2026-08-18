from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.dependencies import get_doctor_verification_service
from app.main import BASE_DIR, app
from app.models import Base, User
from app.services.cfm import CFMDoctor, CFMSpecialty, CFMUnavailableError
from app.services.doctor_verification import DoctorIrregular, DoctorNameMismatch, DoctorNotFound

client = TestClient(app)
INDEX_HTML = Path(BASE_DIR / "templates" / "index.html").read_text(encoding="utf-8")


class SuccessfulDoctorVerifier:
    """Substitui o CFM nos testes de rota sem fazer chamadas externas."""

    def verify(self, name, crm, uf):
        return CFMDoctor(
            crm_display=crm,
            uf=uf,
            official_name=name,
            registration_status="A",
            registration_type="P",
            source_updated_at=date(2026, 8, 14),
            specialties=(
                CFMSpecialty(
                    name="CARDIOLOGIA",
                    rqe="1111",
                    official_description="CARDIOLOGIA - RQE Nº: 1111",
                ),
            ),
            photo_url="https://portal.cfm.org.br/foto-oficial.png",
        )


class FailingDoctorVerifier:
    def __init__(self, error):
        self.error = error

    def verify(self, name, crm, uf):
        raise self.error


@pytest.fixture
def db_isolado(tmp_path):
    """Cada teste ganha banco temporário e sessão administrativa isolada."""
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_doctor_verification_service] = SuccessfulDoctorVerifier
    client.cookies.clear()
    login = client.post("/admin/login", json={"nome": "santanna", "senha": "12345"})
    assert login.status_code == 200
    yield session_local
    client.cookies.clear()
    app.dependency_overrides.clear()
    engine.dispose()


def adicionar_usuarios(session_local, usuarios):
    db = session_local()
    try:
        db.add_all([User(**usuario) for usuario in usuarios])
        db.commit()
    finally:
        db.close()


def test_health_retorna_ok():
    resposta = client.get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok", "message": "Aplicação funcionando"}


def test_index_renderiza_a_tela():
    resposta = client.get("/")

    assert resposta.status_code == 200
    assert "Portal de acessos" in resposta.text


def test_list_users_retorna_a_lista(db_isolado):
    adicionar_usuarios(db_isolado, [
        {"nome": "Ana Souza", "email": "ana@exemplo.com"},
        {"nome": "Bruno Lima", "email": "bruno@exemplo.com"},
    ])

    resposta = client.get("/users")

    assert resposta.status_code == 200
    assert len(resposta.json()) == 2
    assert resposta.json()[0]["nome"] == "Ana Souza"


def test_list_users_filtra_por_nome(db_isolado):
    adicionar_usuarios(db_isolado, [
        {"nome": "Ana Souza", "email": "ana@exemplo.com"},
        {"nome": "Bruno Lima", "email": "bruno@exemplo.com"},
    ])

    resposta = client.get("/users", params={"nome": "Ana"})

    assert resposta.status_code == 200
    assert len(resposta.json()) == 1
    assert resposta.json()[0]["nome"] == "Ana Souza"


def test_list_users_filtra_ignorando_maiusculas_e_parte_do_nome(db_isolado):
    adicionar_usuarios(db_isolado, [
        {"nome": "Ana Souza", "email": "ana@exemplo.com"},
        {"nome": "Bruno Lima", "email": "bruno@exemplo.com"},
    ])

    resposta = client.get("/users", params={"nome": "souza"})

    assert resposta.status_code == 200
    assert len(resposta.json()) == 1


def test_list_users_sem_resultado_retorna_lista_vazia_com_200(db_isolado):
    resposta = client.get("/users", params={"nome": "Ninguem"})

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_get_user_retorna_o_usuario_pedido(db_isolado):
    adicionar_usuarios(db_isolado, [
        {"nome": "Ana Souza", "email": "ana@exemplo.com"},
        {"nome": "Bruno Lima", "email": "bruno@exemplo.com"},
    ])

    resposta = client.get("/users/2")

    assert resposta.status_code == 200
    assert resposta.json() == {"id": 2, "nome": "Bruno Lima", "email": "bruno@exemplo.com"}


def test_get_user_inexistente_retorna_404(db_isolado):
    resposta = client.get("/users/999")

    assert resposta.status_code == 404
    assert resposta.json()["detail"] == "Usuário 999 não encontrado"


def test_get_user_com_id_nao_numerico_retorna_422(db_isolado):
    resposta = client.get("/users/abc")

    assert resposta.status_code == 422
    assert resposta.json()["detail"][0]["msg"] == "O valor informado possui formato inválido"


def test_list_users_sem_ninguem_cadastrado_retorna_200_e_lista_vazia(db_isolado):
    resposta = client.get("/users")

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_list_users_responde_json(db_isolado):
    resposta = client.get("/users")

    assert resposta.headers["content-type"].startswith("application/json")


def test_create_user_retorna_201_com_o_usuario_criado(db_isolado):
    resposta = client.post("/users", json={"nome": "Carla Dias", "email": "carla@exemplo.com"})

    assert resposta.status_code == 201
    assert resposta.json() == {"id": 1, "nome": "Carla Dias", "email": "carla@exemplo.com"}


def test_create_user_faz_o_usuario_aparecer_na_listagem(db_isolado):
    client.post("/users", json={"nome": "Carla Dias", "email": "carla@exemplo.com"})

    resposta = client.get("/users")

    assert len(resposta.json()) == 1
    assert resposta.json()[-1]["nome"] == "Carla Dias"


def test_create_user_ignora_id_enviado_pelo_cliente(db_isolado):
    resposta = client.post(
        "/users", json={"id": 99, "nome": "Carla Dias", "email": "carla@exemplo.com"}
    )

    assert resposta.status_code == 201
    assert resposta.json()["id"] == 1


def test_create_user_continua_do_maior_id_e_nao_do_tamanho(db_isolado):
    adicionar_usuarios(db_isolado, [{"id": 10, "nome": "Dora Reis", "email": "dora@exemplo.com"}])

    resposta = client.post("/users", json={"nome": "Carla Dias", "email": "carla@exemplo.com"})

    assert resposta.json()["id"] == 11


def test_create_user_guarda_o_email_em_minusculas(db_isolado):
    resposta = client.post("/users", json={"nome": "Carla Dias", "email": "CARLA@Exemplo.COM"})

    assert resposta.json()["email"] == "carla@exemplo.com"


def test_create_user_tira_espacos_das_pontas_do_nome(db_isolado):
    resposta = client.post("/users", json={"nome": "  Carla Dias  ", "email": "carla@exemplo.com"})

    assert resposta.json()["nome"] == "Carla Dias"


def test_create_user_com_email_repetido_retorna_409(db_isolado):
    adicionar_usuarios(db_isolado, [{"nome": "Ana Souza", "email": "ana@exemplo.com"}])

    resposta = client.post("/users", json={"nome": "Outra Ana", "email": "ana@exemplo.com"})

    assert resposta.status_code == 409
    assert "já está cadastrado" in resposta.json()["detail"]


def test_create_user_nao_diferencia_maiusculas_no_email_repetido(db_isolado):
    adicionar_usuarios(db_isolado, [{"nome": "Ana Souza", "email": "ana@exemplo.com"}])

    resposta = client.post("/users", json={"nome": "Outra Ana", "email": "ANA@exemplo.com"})

    assert resposta.status_code == 409


@pytest.mark.parametrize(
    ("corpo", "motivo"),
    [
        ({"email": "sem@nome.com"}, "falta o nome"),
        ({"nome": "Carla Dias"}, "falta o email"),
        ({"nome": "C", "email": "carla@exemplo.com"}, "nome curto demais"),
        ({"nome": "   ", "email": "carla@exemplo.com"}, "nome so com espacos"),
        ({"nome": "Carla Dias", "email": "nao-e-email"}, "email invalido"),
        ({"nome": "Carla Dias", "email": ""}, "email vazio"),
    ],
)
def test_create_user_com_dados_invalidos_retorna_422(db_isolado, corpo, motivo):
    resposta = client.post("/users", json=corpo)

    assert resposta.status_code == 422, motivo
    assert client.get("/users").json() == []


def test_create_user_email_invalido_retorna_mensagem_em_portugues(db_isolado):
    resposta = client.post("/users", json={"nome": "Carla Dias", "email": "nao-e-email"})

    assert resposta.status_code == 422
    assert "EMAIL NÃO É VÁLIDO" in resposta.json()["detail"][0]["msg"]


def test_registration_cria_usuario_e_perfil_medico_juntos(db_isolado):
    resposta = client.post(
        "/registrations",
        json={
            "user": {"nome": "Carla Dias", "email": "carla@exemplo.com"},
            "doctor": {"crm": "123456", "uf": "sp"},
            "senha": "senha-segura",
            "confirmacao_senha": "senha-segura",
        },
    )

    assert resposta.status_code == 201
    assert resposta.json()["nome"] == "Carla Dias"
    assert resposta.json()["doctor"]["crm"] == "123456"
    assert resposta.json()["doctor"]["uf"] == "SP"
    assert resposta.json()["doctor"]["crm_verified"] is True
    assert resposta.json()["doctor"]["verification_status"] == "verified"
    assert resposta.json()["doctor"]["cfm_photo_url"] == "https://portal.cfm.org.br/foto-oficial.png"
    assert resposta.json()["registration_status"] == "approved_incomplete"

    usuarios = client.get("/users").json()
    assert usuarios[0]["doctor"]["user_id"] == usuarios[0]["id"]


def test_registration_com_crm_e_uf_repetidos_retorna_409(db_isolado):
    client.post(
        "/registrations",
        json={
            "user": {"nome": "Carla Dias", "email": "carla@exemplo.com"},
            "doctor": {"crm": "123456", "uf": "SP"},
            "senha": "senha-segura",
            "confirmacao_senha": "senha-segura",
        },
    )

    resposta = client.post(
        "/registrations",
        json={
            "user": {"nome": "Dora Reis", "email": "dora@exemplo.com"},
            "doctor": {"crm": "123456", "uf": "SP"},
            "senha": "senha-segura",
            "confirmacao_senha": "senha-segura",
        },
    )

    assert resposta.status_code == 409
    assert len(client.get("/users").json()) == 1


def test_registration_com_uf_mal_formatada_retorna_422(db_isolado):
    resposta = client.post(
        "/registrations",
        json={
            "user": {"nome": "Carla Dias", "email": "carla@exemplo.com"},
            "doctor": {"crm": "123456", "uf": "S"},
            "senha": "senha-segura",
            "confirmacao_senha": "senha-segura",
        },
    )

    assert resposta.status_code == 422
    assert client.get("/users").json() == []


def test_registration_aceita_crm_longo_com_hifen(db_isolado):
    resposta = client.post(
        "/registrations",
        json={
            "user": {"nome": "Raphael Costa", "email": "raphael@exemplo.com"},
            "doctor": {"crm": "42106072-4", "uf": "RJ"},
            "senha": "senha-segura",
            "confirmacao_senha": "senha-segura",
        },
    )

    assert resposta.status_code == 201
    assert resposta.json()["doctor"]["crm"] == "42106072-4"


@pytest.mark.parametrize(
    ("crm", "uf", "mensagem"),
    [
        ("12A456", "SP", "CRM deve conter apenas números"),
        ("123456", "XX", "UF deve ser uma sigla de estado brasileiro válida"),
    ],
)
def test_registration_rejeita_crm_ou_uf_invalidos_na_regra_de_negocio(db_isolado, crm, uf, mensagem):
    resposta = client.post(
        "/registrations",
        json={
            "user": {"nome": "Carla Dias", "email": "carla@exemplo.com"},
            "doctor": {"crm": crm, "uf": uf},
            "senha": "senha-segura",
            "confirmacao_senha": "senha-segura",
        },
    )

    assert resposta.status_code == 422
    assert mensagem in resposta.json()["detail"][0]["msg"]
    assert client.get("/users").json() == []


def test_registration_exige_senha_e_confirmacao_iguais(db_isolado):
    resposta = client.post(
        "/registrations",
        json={
            "user": {"nome": "Carla Dias", "email": "carla@exemplo.com"},
            "doctor": {"crm": "123456", "uf": "SP"},
            "senha": "senha-segura",
            "confirmacao_senha": "outra-senha",
        },
    )

    assert resposta.status_code == 422
    assert "não coincidem" in resposta.json()["detail"][0]["msg"]


def test_registration_informa_tamanho_da_senha_em_portugues(db_isolado):
    resposta = client.post(
        "/registrations",
        json={
            "user": {"nome": "Carla Dias", "email": "carla@exemplo.com"},
            "doctor": {"crm": "123456", "uf": "SP"},
            "senha": "12345",
            "confirmacao_senha": "12345",
        },
    )

    assert resposta.status_code == 422
    assert "A senha deve ter entre 8 e 128 caracteres" in resposta.json()["detail"][0]["msg"]


@pytest.mark.parametrize(
    ("failure", "mensagem"),
    [
        (DoctorNotFound(), "CRM e UF não encontrados no CFM"),
        (DoctorNameMismatch(), "O nome informado não corresponde ao nome registrado no CFM"),
        (DoctorIrregular(), "O CRM foi encontrado, mas não está regular no CFM"),
    ],
)
def test_falha_profissional_nao_salva_nem_reserva_email_ou_crm(
    db_isolado, failure, mensagem
):
    app.dependency_overrides[get_doctor_verification_service] = lambda: FailingDoctorVerifier(
        failure
    )
    payload = {
        "user": {"nome": "Carla Dias", "email": "carla@exemplo.com"},
        "doctor": {"crm": "123456", "uf": "SP"},
        "senha": "senha-segura",
        "confirmacao_senha": "senha-segura",
    }

    primeira_tentativa = client.post("/registrations", json=payload)

    assert primeira_tentativa.status_code == 422
    assert primeira_tentativa.json()["detail"] == mensagem
    assert client.get("/users").json() == []

    app.dependency_overrides[get_doctor_verification_service] = SuccessfulDoctorVerifier
    nova_tentativa = client.post("/registrations", json=payload)

    assert nova_tentativa.status_code == 201
    assert len(client.get("/users").json()) == 1


def test_medico_pendente_faz_login_mas_nao_acessa_painel(db_isolado):
    app.dependency_overrides[get_doctor_verification_service] = lambda: FailingDoctorVerifier(
        CFMUnavailableError("timeout")
    )
    client.post(
        "/registrations",
        json={
            "user": {"nome": "Carla Dias", "email": "carla@exemplo.com"},
            "doctor": {"crm": "123456", "uf": "SP"},
            "senha": "senha-segura",
            "confirmacao_senha": "senha-segura",
        },
    )
    client.post("/admin/logout")

    login = client.post("/doctor/login", json={"email": "carla@exemplo.com", "senha": "senha-segura"})
    painel = client.get("/doctor/profile")

    assert login.status_code == 200
    assert login.json()["redirect_url"] == "/account/status"
    assert painel.status_code == 403


def test_admin_associa_e_consulta_perfil_medico(db_isolado):
    adicionar_usuarios(db_isolado, [{"nome": "Ana Souza", "email": "ana@exemplo.com"}])

    criacao = client.post("/users/1/doctor", json={"crm": "654321", "uf": "rj"})
    consulta = client.get("/users/1/doctor")

    assert criacao.status_code == 201
    assert consulta.status_code == 200
    assert consulta.json()["id"] == 1
    assert consulta.json()["user_id"] == 1
    assert consulta.json()["crm"] == "654321"
    assert consulta.json()["uf"] == "RJ"
    assert consulta.json()["crm_verified"] is False


def test_usuario_nao_recebe_dois_perfis_medicos_pela_api(db_isolado):
    adicionar_usuarios(db_isolado, [{"nome": "Ana Souza", "email": "ana@exemplo.com"}])
    client.post("/users/1/doctor", json={"crm": "123456", "uf": "SP"})

    resposta = client.post("/users/1/doctor", json={"crm": "654321", "uf": "RJ"})

    assert resposta.status_code == 409


def test_perfil_medico_de_usuario_inexistente_retorna_404(db_isolado):
    resposta = client.post("/users/999/doctor", json={"crm": "123456", "uf": "SP"})

    assert resposta.status_code == 404


def test_admin_atualiza_usuario_e_perfil_medico_juntos(db_isolado):
    client.post(
        "/registrations",
        json={
            "user": {"nome": "Carla Dias", "email": "carla@exemplo.com"},
            "doctor": {"crm": "123456", "uf": "SP"},
            "senha": "senha-segura",
            "confirmacao_senha": "senha-segura",
        },
    )

    resposta = client.put(
        "/registrations/1",
        json={
            "user": {"nome": "Carla de Souza", "email": "carla.souza@exemplo.com"},
            "doctor": {"crm": "654321", "uf": "RJ"},
        },
    )

    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Carla de Souza"
    assert resposta.json()["doctor"]["crm"] == "654321"
    assert resposta.json()["doctor"]["uf"] == "RJ"


def test_admin_nao_atualiza_para_crm_de_outro_medico(db_isolado):
    for nome, email, crm in (
        ("Carla Dias", "carla@exemplo.com", "111111"),
        ("Dora Reis", "dora@exemplo.com", "222222"),
    ):
        client.post(
            "/registrations",
            json={
                "user": {"nome": nome, "email": email},
                "doctor": {"crm": crm, "uf": "SP"},
                "senha": "senha-segura",
                "confirmacao_senha": "senha-segura",
            },
        )

    resposta = client.put(
        "/registrations/2",
        json={
            "user": {"nome": "Dora Reis", "email": "dora@exemplo.com"},
            "doctor": {"crm": "111111", "uf": "SP"},
        },
    )

    assert resposta.status_code == 409
    assert client.get("/users/2/doctor").json()["crm"] == "222222"


def test_admin_pode_adicionar_perfil_ao_editar_usuario_antigo(db_isolado):
    adicionar_usuarios(db_isolado, [{"nome": "Ana Souza", "email": "ana@exemplo.com"}])

    resposta = client.put(
        "/registrations/1",
        json={
            "user": {"nome": "Ana Souza", "email": "ana@exemplo.com"},
            "doctor": {"crm": "333333", "uf": "MG"},
        },
    )

    assert resposta.status_code == 200
    assert resposta.json()["doctor"]["uf"] == "MG"


def test_admin_atualiza_apenas_o_perfil_medico(db_isolado):
    adicionar_usuarios(db_isolado, [{"nome": "Ana Souza", "email": "ana@exemplo.com"}])
    client.post("/users/1/doctor", json={"crm": "123456", "uf": "SP"})

    resposta = client.put("/users/1/doctor", json={"crm": "654321", "uf": "PR"})

    assert resposta.status_code == 200
    assert resposta.json()["crm"] == "654321"
    assert resposta.json()["uf"] == "PR"


def test_list_users_exige_login_de_admin(db_isolado):
    client.post("/admin/logout")

    resposta = client.get("/users")

    assert resposta.status_code == 401


def test_admin_login_rejeita_senha_incorreta(db_isolado):
    client.post("/admin/logout")

    resposta = client.post("/admin/login", json={"nome": "santanna", "senha": "errada"})

    assert resposta.status_code == 401


def test_update_user_atualiza_nome_e_email(db_isolado):
    adicionar_usuarios(db_isolado, [{"nome": "Ana Souza", "email": "ana@exemplo.com"}])

    resposta = client.put(
        "/users/1", json={"nome": "Ana Maria Souza", "email": "ana.maria@exemplo.com"}
    )

    assert resposta.status_code == 200
    assert resposta.json() == {
        "id": 1,
        "nome": "Ana Maria Souza",
        "email": "ana.maria@exemplo.com",
    }


def test_update_user_inexistente_retorna_404(db_isolado):
    resposta = client.put("/users/999", json={"nome": "Ana Souza", "email": "ana@exemplo.com"})

    assert resposta.status_code == 404


def test_update_user_com_email_de_outro_usuario_retorna_409(db_isolado):
    adicionar_usuarios(db_isolado, [
        {"nome": "Ana Souza", "email": "ana@exemplo.com"},
        {"nome": "Bruno Lima", "email": "bruno@exemplo.com"},
    ])

    resposta = client.put("/users/2", json={"nome": "Bruno Lima", "email": "ana@exemplo.com"})

    assert resposta.status_code == 409


def test_update_user_com_dados_invalidos_retorna_422(db_isolado):
    adicionar_usuarios(db_isolado, [{"nome": "Ana Souza", "email": "ana@exemplo.com"}])

    resposta = client.put("/users/1", json={"nome": "A", "email": "email-invalido"})

    assert resposta.status_code == 422


def test_delete_user_remove_o_usuario_da_listagem(db_isolado):
    adicionar_usuarios(db_isolado, [{"nome": "Ana Souza", "email": "ana@exemplo.com"}])

    resposta = client.delete("/users/1")

    assert resposta.status_code == 204
    assert resposta.content == b""
    assert client.get("/users").json() == []


def test_delete_user_e_idempotente(db_isolado):
    adicionar_usuarios(db_isolado, [{"nome": "Ana Souza", "email": "ana@exemplo.com"}])

    primeira_resposta = client.delete("/users/1")
    segunda_resposta = client.delete("/users/1")

    assert primeira_resposta.status_code == 204
    assert segunda_resposta.status_code == 204
    assert client.get("/users").json() == []


def test_index_tem_formulario_que_envia_post():
    assert '<form id="form-novo"' in INDEX_HTML
    assert 'method: "POST"' in INDEX_HTML
    assert 'id="campo-crm"' in INDEX_HTML
    assert '<select id="campo-uf"' in INDEX_HTML
    assert '<option value="SP">São Paulo (SP)</option>' in INDEX_HTML
    assert 'fetch("/registrations",' in INDEX_HTML
    assert 'maxlength="20"' in INDEX_HTML
    assert "CRM validado no CFM" in INDEX_HTML
    assert 'id="campo-senha"' in INDEX_HTML


def test_index_nao_tem_nomes_fixos_no_html():
    for nome in ("Ana Souza", "Bruno Lima"):
        assert nome not in INDEX_HTML


def test_index_nao_exibe_a_lista_de_usuarios():
    assert 'fetch("/users")' not in INDEX_HTML
    assert "<table" not in INDEX_HTML
    assert 'fetch("/users")' not in INDEX_HTML


def test_admin_tem_login_e_acoes():
    admin_html = Path(BASE_DIR / "templates" / "admin.html").read_text(encoding="utf-8")

    assert 'id="login-form"' in admin_html
    assert "Cadastros pendentes" in admin_html
    assert "Aprovar manualmente" in admin_html
    assert "Rejeitar cadastro" in admin_html
    assert "/admin/registrations/${selected.id}/approve" in admin_html
    assert "/admin/registrations/${selected.id}/reject" in admin_html
    assert "cfm_photo_url" in admin_html
    assert "doctor-photo" in admin_html
    assert 'id="review-profile"' in admin_html
    assert "review-photo" in admin_html
    assert "renderReviewProfile(user)" in admin_html


@pytest.mark.parametrize(
    "template_name",
    [
        "account_login.html",
        "account_status.html",
        "admin.html",
        "complete_profile.html",
        "dashboard.html",
        "non_medical_register.html",
    ],
)
def test_paginas_secundarias_tem_volta_para_o_inicio(template_name):
    html = Path(BASE_DIR / "templates" / template_name).read_text(encoding="utf-8")

    assert 'href="/"' in html
    assert "Voltar para o início" in html


def test_erros_padrao_do_framework_sao_exibidos_em_portugues(db_isolado):
    nao_encontrado = client.get("/pagina-que-nao-existe")
    metodo_incorreto = client.patch("/health")

    assert nao_encontrado.status_code == 404
    assert nao_encontrado.json()["detail"] == "Página ou recurso não encontrado"
    assert metodo_incorreto.status_code == 405
    assert metodo_incorreto.json()["detail"] == "Método não permitido"
