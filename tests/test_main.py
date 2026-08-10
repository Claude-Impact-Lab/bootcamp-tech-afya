from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_retorna_ok():
    resposta = client.get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok", "message": "Hello World"}


def test_index_renderiza_a_tela():
    resposta = client.get("/")

    assert resposta.status_code == 200
    assert "User Manager" in resposta.text


def test_a_tela_nao_traz_nenhum_nome_escrito_no_html():
    """Os nomes chegam pela API: o HTML servido nao pode conte-los."""
    resposta = client.get("/")

    assert "Ada Lovelace" not in resposta.text


def test_lista_usuarios_retorna_json_com_id_e_nome():
    resposta = client.get("/users")

    assert resposta.status_code == 200
    assert resposta.headers["content-type"] == "application/json"

    usuarios = resposta.json()
    assert isinstance(usuarios, list)
    for usuario in usuarios:
        assert "id" in usuario
        assert "name" in usuario


def test_lista_vazia_continua_sendo_sucesso(monkeypatch):
    """Sem usuarios a resposta e 200 com [], nunca 404: a tela nao trata isso como erro."""
    monkeypatch.setattr("app.main.USERS", [])

    resposta = client.get("/users")

    assert resposta.status_code == 200
    assert resposta.json() == []
