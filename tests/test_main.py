from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import BASE_DIR, app

client = TestClient(app)

INDEX_HTML = Path(BASE_DIR / "templates" / "index.html").read_text(encoding="utf-8")


@pytest.fixture
def base_isolada(monkeypatch):
    """Da a cada teste a sua propria lista vazia.

    Sem isto um teste que cadastra alguem mudaria o USERS do modulo e quebraria
    os testes seguintes, dependendo da ordem em que rodassem.
    """
    users = []
    monkeypatch.setattr("app.main.USERS", users)
    return users


def test_health_retorna_ok():
    resposta = client.get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok", "message": "Hello World"}


def test_index_renderiza_a_tela():
    resposta = client.get("/")

    assert resposta.status_code == 200
    assert "Bem vindo" in resposta.text or "Novo usuário do projeto" in resposta.text


def test_list_users_retorna_a_lista(monkeypatch):
    users = [
        {"id": 1, "nome": "Ana Souza", "email": "ana@exemplo.com"},
        {"id": 2, "nome": "Bruno Lima", "email": "bruno@exemplo.com"},
    ]
    monkeypatch.setattr("app.main.USERS", users)

    resposta = client.get("/users")

    assert resposta.status_code == 200
    assert len(resposta.json()) == 2
    assert resposta.json()[0]["nome"] == "Ana Souza"


def test_list_users_filtra_por_nome(monkeypatch):
    users = [
        {"id": 1, "nome": "Ana Souza", "email": "ana@exemplo.com"},
        {"id": 2, "nome": "Bruno Lima", "email": "bruno@exemplo.com"},
    ]
    monkeypatch.setattr("app.main.USERS", users)

    resposta = client.get("/users", params={"nome": "Ana"})

    assert resposta.status_code == 200
    assert len(resposta.json()) == 1
    assert resposta.json()[0]["nome"] == "Ana Souza"


def test_list_users_filtra_ignorando_maiusculas_e_parte_do_nome(monkeypatch):
    users = [
        {"id": 1, "nome": "Ana Souza", "email": "ana@exemplo.com"},
        {"id": 2, "nome": "Bruno Lima", "email": "bruno@exemplo.com"},
    ]
    monkeypatch.setattr("app.main.USERS", users)

    resposta = client.get("/users", params={"nome": "souza"})

    assert resposta.status_code == 200
    assert len(resposta.json()) == 1


def test_list_users_sem_resultado_retorna_lista_vazia_com_200(monkeypatch):
    """Busca que nao acha nada nao e erro: e uma lista vazia."""
    monkeypatch.setattr("app.main.USERS", [])

    resposta = client.get("/users", params={"nome": "Ninguem"})

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_get_user_retorna_o_usuario_pedido(monkeypatch):
    users = [
        {"id": 1, "nome": "Ana Souza", "email": "ana@exemplo.com"},
        {"id": 2, "nome": "Bruno Lima", "email": "bruno@exemplo.com"},
    ]
    monkeypatch.setattr("app.main.USERS", users)

    resposta = client.get("/users/2")

    assert resposta.status_code == 200
    assert resposta.json() == {
        "id": 2,
        "nome": "Bruno Lima",
        "email": "bruno@exemplo.com",
    }


def test_get_user_inexistente_retorna_404(monkeypatch):
    monkeypatch.setattr("app.main.USERS", [])

    resposta = client.get("/users/999")

    assert resposta.status_code == 404
    assert resposta.json()["detail"] == "Usuário 999 não encontrado"


def test_get_user_com_id_nao_numerico_retorna_422():
    """O FastAPI recusa o id invalido antes da funcao rodar, por causa do `user_id: int`."""
    resposta = client.get("/users/abc")

    assert resposta.status_code == 422


def test_list_users_sem_ninguem_cadastrado_retorna_200_e_lista_vazia(monkeypatch):
    """Base vazia nao e erro: a rota responde 200 com []."""
    monkeypatch.setattr("app.main.USERS", [])

    resposta = client.get("/users")

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_list_users_responde_json():
    resposta = client.get("/users")

    assert resposta.headers["content-type"].startswith("application/json")


def test_create_user_retorna_201_com_o_usuario_criado(base_isolada):
    resposta = client.post(
        "/users", json={"nome": "Carla Dias", "email": "carla@exemplo.com"}
    )

    assert resposta.status_code == 201
    assert resposta.json() == {
        "id": 1,
        "nome": "Carla Dias",
        "email": "carla@exemplo.com",
    }


def test_create_user_faz_o_usuario_aparecer_na_listagem(base_isolada):
    client.post("/users", json={"nome": "Carla Dias", "email": "carla@exemplo.com"})

    resposta = client.get("/users")

    assert len(resposta.json()) == 1
    assert resposta.json()[-1]["nome"] == "Carla Dias"


def test_create_user_ignora_id_enviado_pelo_cliente(base_isolada):
    """Quem decide o id e o servidor: o campo extra e descartado."""
    resposta = client.post(
        "/users", json={"id": 99, "nome": "Carla Dias", "email": "carla@exemplo.com"}
    )

    assert resposta.status_code == 201
    assert resposta.json()["id"] == 1


def test_create_user_continua_do_maior_id_e_nao_do_tamanho(base_isolada):
    """Com um id 10 na base, o proximo e 11 - nao 3."""
    base_isolada.append({"id": 10, "nome": "Dora Reis", "email": "dora@exemplo.com"})

    resposta = client.post(
        "/users", json={"nome": "Carla Dias", "email": "carla@exemplo.com"}
    )

    assert resposta.json()["id"] == 11


def test_create_user_guarda_o_email_em_minusculas(base_isolada):
    resposta = client.post(
        "/users", json={"nome": "Carla Dias", "email": "CARLA@Exemplo.COM"}
    )

    assert resposta.json()["email"] == "carla@exemplo.com"


def test_create_user_tira_espacos_das_pontas_do_nome(base_isolada):
    resposta = client.post(
        "/users", json={"nome": "  Carla Dias  ", "email": "carla@exemplo.com"}
    )

    assert resposta.json()["nome"] == "Carla Dias"


def test_create_user_com_email_repetido_retorna_409(base_isolada):
    base_isolada.append({"id": 1, "nome": "Ana Souza", "email": "ana@exemplo.com"})

    resposta = client.post("/users", json={"nome": "Outra Ana", "email": "ana@exemplo.com"})

    assert resposta.status_code == 409
    assert "já está cadastrado" in resposta.json()["detail"]
    assert len(base_isolada) == 1


def test_create_user_nao_diferencia_maiusculas_no_email_repetido(base_isolada):
    base_isolada.append({"id": 1, "nome": "Ana Souza", "email": "ana@exemplo.com"})

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
def test_create_user_com_dados_invalidos_retorna_422(base_isolada, corpo, motivo):
    """O Pydantic recusa antes de a funcao rodar, e nada e gravado."""
    resposta = client.post("/users", json=corpo)

    assert resposta.status_code == 422, motivo
    assert len(base_isolada) == 0


def test_create_user_email_invalido_retorna_mensagem_em_portugues(base_isolada):
    resposta = client.post("/users", json={"nome": "Carla Dias", "email": "nao-e-email"})

    assert resposta.status_code == 422
    assert "EMAIL NÃO É VÁLIDO" in resposta.json()["detail"][0]["msg"]


def test_index_tem_formulario_que_envia_post(base_isolada):
    assert '<form id="form-novo"' in INDEX_HTML
    assert 'method: "POST"' in INDEX_HTML


def test_index_nao_tem_nomes_fixos_no_html():
    """Os nomes vem da API. Se aparecerem no HTML, a tela parou de ser dinamica."""
    for nome in ("Ana Souza", "Bruno Lima"):
        assert nome not in INDEX_HTML


def test_index_busca_os_usuarios_na_api():
    assert 'fetch("/users")' in INDEX_HTML
