from fastapi.testclient import TestClient

from app import main
from app.main import app

client = TestClient(app)


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


def test_users_sem_cadastro_devolve_lista_vazia(monkeypatch):
    """Sem usuarios a resposta continua sendo sucesso, e nao um 404."""
    monkeypatch.setattr(main, "USERS", [])

    resposta = client.get("/users")

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_cria_usuario_com_nome_valido(monkeypatch):
    monkeypatch.setattr(main, "USERS", [])
    monkeypatch.setattr(main, "EMAIL_OUTBOX", [])

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
    assert main.USERS[0]["name"] == "Maria Souza"
    assert "confirmation_token" in main.USERS[0]
    assert "confirmation_token" not in resposta.json()
    assert "password_hash" in main.USERS[0]
    assert "senha-segura" not in str(main.USERS[0])
    assert "password_hash" not in resposta.json()
    assert main.EMAIL_OUTBOX[0]["from"] == "resposta.noreply.2025@gmail.com"
    assert main.EMAIL_OUTBOX[0]["to"] == "maria.souza@exemplo.com"


def test_dados_incompletos_criam_pre_cadastro(monkeypatch):
    monkeypatch.setattr(main, "USERS", [])
    monkeypatch.setattr(main, "EMAIL_OUTBOX", [])

    resposta = client.post("/users", json={"first_name": "Nery"})

    assert resposta.status_code == 201
    assert resposta.json()["status"] == "pre_cadastro"
    assert main.EMAIL_OUTBOX == []


def test_confirmacao_de_email_ativa_usuario(monkeypatch):
    monkeypatch.setattr(main, "USERS", [])
    monkeypatch.setattr(main, "EMAIL_OUTBOX", [])
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
    token = main.USERS[0]["confirmation_token"]

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


def test_usuario_confirmado_consegue_entrar(monkeypatch):
    monkeypatch.setattr(main, "USERS", [])
    monkeypatch.setattr(main, "EMAIL_OUTBOX", [])
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
    token = main.USERS[0]["confirmation_token"]
    client.get(f"/users/confirm?token={token}")

    resposta = client.post(
        "/users/login",
        json={"email": "maria.souza@exemplo.com", "password": "senha-segura"},
    )

    assert resposta.status_code == 200
    assert resposta.json()["user"]["name"] == "Maria Souza"


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
