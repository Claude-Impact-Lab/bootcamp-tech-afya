from pathlib import Path

from fastapi.testclient import TestClient

from app.main import BASE_DIR, app

client = TestClient(app)

INDEX_HTML = Path(BASE_DIR / "templates" / "index.html").read_text(encoding="utf-8")


def test_health_retorna_ok():
    resposta = client.get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok", "message": "Hello World"}


def test_index_renderiza_a_tela():
    resposta = client.get("/")

    assert resposta.status_code == 200
    assert "User Manager" in resposta.text


def test_list_users_retorna_a_lista():
    resposta = client.get("/users")

    assert resposta.status_code == 200
    assert len(resposta.json()) == 2
    assert resposta.json()[0]["nome"] == "Ana Souza"


def test_list_users_filtra_por_nome():
    resposta = client.get("/users", params={"nome": "Ana"})

    assert resposta.status_code == 200
    assert len(resposta.json()) == 1
    assert resposta.json()[0]["nome"] == "Ana Souza"


def test_list_users_filtra_ignorando_maiusculas_e_parte_do_nome():
    resposta = client.get("/users", params={"nome": "souza"})

    assert resposta.status_code == 200
    assert len(resposta.json()) == 1


def test_list_users_sem_resultado_retorna_lista_vazia_com_200():
    """Busca que nao acha nada nao e erro: e uma lista vazia."""
    resposta = client.get("/users", params={"nome": "Ninguem"})

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_get_user_retorna_o_usuario_pedido():
    resposta = client.get("/users/2")

    assert resposta.status_code == 200
    assert resposta.json() == {
        "id": 2,
        "nome": "Bruno Lima",
        "email": "bruno@exemplo.com",
    }


def test_get_user_inexistente_retorna_404():
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


def test_index_nao_tem_nomes_fixos_no_html():
    """Os nomes vem da API. Se aparecerem no HTML, a tela parou de ser dinamica."""
    for nome in ("Ana Souza", "Bruno Lima"):
        assert nome not in INDEX_HTML


def test_index_busca_os_usuarios_na_api():
    assert 'fetch("/users")' in INDEX_HTML
