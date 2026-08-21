import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.database import Base, get_db
from app.main import app
from app.models import Doctor, User


test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    bind=test_engine, autoflush=False, expire_on_commit=False
)


def override_get_db():
    with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def banco_limpo():
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    main.EMAIL_OUTBOX.clear()
    yield
    Base.metadata.drop_all(test_engine)


def usuario_no_banco() -> User:
    with TestingSessionLocal() as session:
        return session.scalar(select(User).order_by(User.id))


def test_health_retorna_ok():
    resposta = client.get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok", "message": "Hello World"}


def test_users_retorna_a_lista_em_json():
    resposta = client.get("/users")

    assert resposta.status_code == 200

    usuarios = resposta.json()
    assert isinstance(usuarios, list)
    assert all("id" in usuario and "name" in usuario for usuario in usuarios)


def test_admin_visualiza_pre_cadastros():
    client.post("/users", json={"first_name": "Nery"})
    admin_client = TestClient(app)
    login = admin_client.post(
        "/admin/login", json={"username": "afya", "password": "programação"}
    )

    resposta = admin_client.get("/users")

    assert login.status_code == 200
    assert any(usuario["status"] == "pre_cadastro" for usuario in resposta.json())


def test_login_admin_rejeita_senha_incorreta():
    resposta = client.post(
        "/admin/login", json={"username": "afya", "password": "incorreta"}
    )

    assert resposta.status_code == 401


def test_logout_remove_acesso_de_administrador():
    admin_client = TestClient(app)
    admin_client.post(
        "/admin/login", json={"username": "afya", "password": "programação"}
    )

    admin_client.post("/admin/logout")
    resposta = admin_client.get("/admin/session")

    assert resposta.json() == {"is_admin": False}


def test_todo_usuario_tem_um_status_conhecido():
    """A tela filtra por status, entao nenhum usuario pode vir sem ele."""
    usuarios = client.get("/users").json()

    assert all(
        usuario["status"] in {"ativo", "pre_cadastro", "aguardando_confirmacao_email"}
        for usuario in usuarios
    )
    assert all("confirmation_token" not in usuario for usuario in usuarios)


def test_users_sem_cadastro_devolve_lista_vazia():
    """Sem usuarios a resposta continua sendo sucesso, e nao um 404."""
    resposta = client.get("/users")

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_cria_usuario_com_nome_valido():
    resposta = client.post(
        "/users",
        json={
            "first_name": "Maria",
            "last_name": "Souza",
            "age": 28,
            "email": "maria.souza@exemplo.com",
            "password": "senha-segura",
            "password_confirmation": "senha-segura",
        },
    )

    assert resposta.status_code == 201
    assert resposta.json() == {
        "id": 1,
        "name": "Maria Souza",
        "age": 28,
        "email": "maria.souza@exemplo.com",
        "email_confirmed": False,
        "status": "aguardando_confirmacao_email",
    }
    usuario_salvo = usuario_no_banco()
    assert usuario_salvo.name == "Maria Souza"
    assert usuario_salvo.confirmation_token is not None
    assert "confirmation_token" not in resposta.json()
    assert usuario_salvo.password_hash is not None
    assert usuario_salvo.password_hash != "senha-segura"
    assert "password_hash" not in resposta.json()
    assert main.EMAIL_OUTBOX[0]["from"] == "resposta.noreply.2025@gmail.com"
    assert main.EMAIL_OUTBOX[0]["to"] == "maria.souza@exemplo.com"


def test_dados_incompletos_criam_pre_cadastro():
    resposta = client.post("/users", json={"first_name": "Nery"})

    assert resposta.status_code == 201
    assert resposta.json()["status"] == "pre_cadastro"
    assert main.EMAIL_OUTBOX == []


def test_confirmacao_de_email_ativa_usuario():
    client.post(
        "/users",
        json={
            "first_name": "Maria",
            "last_name": "Souza",
            "age": 28,
            "email": "maria.souza@exemplo.com",
            "password": "senha-segura",
            "password_confirmation": "senha-segura",
        },
    )
    token = usuario_no_banco().confirmation_token

    resposta = client.get(f"/users/confirm?token={token}")

    assert resposta.status_code == 200
    assert resposta.json()["user"]["status"] == "ativo"
    assert resposta.json()["user"]["email_confirmed"] is True


def test_nao_cria_usuario_com_sobrenome_curto():
    resposta = client.post(
        "/users",
        json={
            "first_name": "Maria",
            "last_name": "S",
            "age": 28,
            "email": "maria.souza@exemplo.com",
        },
    )

    assert resposta.status_code == 422


def test_sem_dados_cria_pre_cadastro():
    resposta = client.post("/users", json={})

    assert resposta.status_code == 201
    assert resposta.json()["status"] == "pre_cadastro"


def test_nao_cria_usuario_com_email_invalido():
    resposta = client.post(
        "/users",
        json={
            "first_name": "Maria",
            "last_name": "Souza",
            "age": 28,
            "email": "email-invalido",
        },
    )

    assert resposta.status_code == 422


def test_nao_cria_cadastro_com_senhas_diferentes():
    resposta = client.post(
        "/users",
        json={"password": "senha-segura", "password_confirmation": "outra-senha"},
    )

    assert resposta.status_code == 422


def test_usuario_confirmado_consegue_entrar():
    client.post(
        "/users",
        json={
            "first_name": "Maria",
            "last_name": "Souza",
            "age": 28,
            "email": "maria.souza@exemplo.com",
            "password": "senha-segura",
            "password_confirmation": "senha-segura",
        },
    )
    token = usuario_no_banco().confirmation_token
    client.get(f"/users/confirm?token={token}")

    resposta = client.post(
        "/users/login",
        json={"email": "maria.souza@exemplo.com", "password": "senha-segura"},
    )

    assert resposta.status_code == 200
    assert resposta.json()["user"]["name"] == "Maria Souza"


def test_nao_permite_email_duplicado():
    dados = {
        "first_name": "Maria",
        "last_name": "Souza",
        "age": 28,
        "email": "maria.souza@exemplo.com",
        "password": "senha-segura",
        "password_confirmation": "senha-segura",
    }
    primeira = client.post("/users", json=dados)
    segunda = client.post("/users", json=dados)

    assert primeira.status_code == 201
    assert segunda.status_code == 409
    assert segunda.json()["detail"] == "Este e-mail ja esta cadastrado."


def test_index_renderiza_a_tela():
    resposta = client.get("/")

    assert resposta.status_code == 200
    assert "User Manager" in resposta.text
    assert "Equipe Afya em desenvolvimento" in resposta.text
    assert "Usuario" in resposta.text
    assert "Administrador" in resposta.text
    assert "Realizar cadastro" in resposta.text
    assert resposta.text.count('autocomplete="new-password"') == 2
    assert resposta.text.count('autocomplete="off"') >= 6
    assert 'id="senha-cadastro"' in resposta.text
    assert 'id="confirmar-senha"' in resposta.text


def test_pagina_de_congratulations_exibe_nome_e_logo():
    resposta = client.get("/congratulations?name=Maria%20Souza")

    assert resposta.status_code == 200
    assert "Parabens, Maria Souza!" in resposta.text
    assert "/static/afya-logo.svg" in resposta.text


def test_put_atualiza_usuario_e_pode_ser_repetido():
    criado = client.post("/users", json={"first_name": "Nery"}).json()
    dados = {"name": "Nery Silva", "age": 35, "email": "nery@exemplo.com"}

    primeira = client.put(f"/users/{criado['id']}", json=dados)
    segunda = client.put(f"/users/{criado['id']}", json=dados)

    assert primeira.status_code == 200
    assert segunda.status_code == 200
    assert primeira.json() == segunda.json()
    assert segunda.json()["name"] == "Nery Silva"


def test_put_de_usuario_inexistente_retorna_404():
    resposta = client.put(
        "/users/999", json={"name": "Pessoa Teste", "age": None, "email": None}
    )

    assert resposta.status_code == 404


def test_put_rejeita_nome_formado_apenas_por_espacos():
    criado = client.post("/users", json={"first_name": "Nery"}).json()

    resposta = client.put(
        f"/users/{criado['id']}",
        json={"name": "   ", "age": None, "email": None},
    )

    assert resposta.status_code == 422


def test_delete_e_idempotente():
    criado = client.post("/users", json={"first_name": "Nery"}).json()

    primeira = client.delete(f"/users/{criado['id']}")
    segunda = client.delete(f"/users/{criado['id']}")

    assert primeira.status_code == 204
    assert segunda.status_code == 204
    assert client.get("/users").json() == []


def test_cria_medico_relacionado_ao_usuario():
    usuario = client.post("/users", json={"first_name": "Maria"}).json()

    resposta = client.post(
        f"/users/{usuario['id']}/doctor",
        json={"crm": "123456", "uf": "sp", "specialty": "Cardiologia"},
    )

    assert resposta.status_code == 201
    assert resposta.json() == {
        "id": 1,
        "user_id": usuario["id"],
        "crm": "123456",
        "uf": "SP",
        "specialty": "Cardiologia",
    }
    assert client.get("/doctors").json() == [resposta.json()]


def test_usuario_so_pode_ter_um_cadastro_de_medico():
    usuario = client.post("/users", json={"first_name": "Maria"}).json()
    dados = {"crm": "123456", "uf": "SP"}

    primeira = client.post(f"/users/{usuario['id']}/doctor", json=dados)
    segunda = client.post(f"/users/{usuario['id']}/doctor", json=dados)

    assert primeira.status_code == 201
    assert segunda.status_code == 409


def test_excluir_usuario_exclui_medico_relacionado():
    usuario = client.post("/users", json={"first_name": "Maria"}).json()
    client.post(
        f"/users/{usuario['id']}/doctor", json={"crm": "123456", "uf": "SP"}
    )

    client.delete(f"/users/{usuario['id']}")

    with TestingSessionLocal() as session:
        assert session.scalar(select(Doctor)) is None


def test_crm_deve_conter_apenas_numeros():
    usuario = client.post("/users", json={"first_name": "Maria"}).json()

    resposta = client.post(
        f"/users/{usuario['id']}/doctor", json={"crm": "12A456", "uf": "SP"}
    )

    assert resposta.status_code == 422


def test_uf_deve_ser_uma_sigla_brasileira_valida():
    usuario = client.post("/users", json={"first_name": "Maria"}).json()

    resposta = client.post(
        f"/users/{usuario['id']}/doctor", json={"crm": "123456", "uf": "XX"}
    )

    assert resposta.status_code == 422


def test_crm_pode_se_repetir_em_ufs_diferentes():
    primeiro = client.post("/users", json={"first_name": "Maria"}).json()
    segundo = client.post("/users", json={"first_name": "Joao"}).json()

    sp = client.post(
        f"/users/{primeiro['id']}/doctor", json={"crm": "123456", "uf": "sp"}
    )
    rj = client.post(
        f"/users/{segundo['id']}/doctor", json={"crm": "123456", "uf": "rj"}
    )

    assert sp.status_code == 201
    assert rj.status_code == 201
    assert sp.json()["uf"] == "SP"
    assert rj.json()["uf"] == "RJ"


def test_crm_e_uf_nao_podem_se_repetir():
    primeiro = client.post("/users", json={"first_name": "Maria"}).json()
    segundo = client.post("/users", json={"first_name": "Joao"}).json()
    dados = {"crm": "123456", "uf": "SP"}

    criado = client.post(f"/users/{primeiro['id']}/doctor", json=dados)
    duplicado = client.post(f"/users/{segundo['id']}/doctor", json=dados)

    assert criado.status_code == 201
    assert duplicado.status_code == 409
    assert duplicado.json()["detail"] == "Este CRM ja esta cadastrado nesta UF."
