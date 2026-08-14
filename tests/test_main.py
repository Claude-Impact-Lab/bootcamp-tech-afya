from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.main import BASE_DIR, app
from app.models import Base, User

client = TestClient(app)
INDEX_HTML = Path(BASE_DIR / "templates" / "index.html").read_text(encoding="utf-8")


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
    assert resposta.json() == {"status": "ok", "message": "Hello World"}


def test_index_renderiza_a_tela():
    resposta = client.get("/")

    assert resposta.status_code == 200
    assert "Portal médico" in resposta.text


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


def test_index_nao_tem_nomes_fixos_no_html():
    for nome in ("Ana Souza", "Bruno Lima"):
        assert nome not in INDEX_HTML


def test_index_nao_exibe_a_lista_de_usuarios():
    assert 'fetch("/users")' not in INDEX_HTML
    assert "<table" not in INDEX_HTML
    assert "Aguarde a aprovação" not in INDEX_HTML


def test_admin_tem_login_e_acoes():
    admin_html = Path(BASE_DIR / "templates" / "admin.html").read_text(encoding="utf-8")

    assert 'id="form-login"' in admin_html
    assert 'criarBotao("Editar"' in admin_html
    assert 'criarBotao("Excluir"' in admin_html
    assert 'method: "PUT"' in admin_html
