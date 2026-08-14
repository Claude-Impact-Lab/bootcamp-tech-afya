from fastapi.testclient import TestClient

from app import main
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


def test_users_devolve_a_lista_em_json():
    resposta = client.get("/users")

    assert resposta.status_code == 200

    usuarios = resposta.json()
    assert isinstance(usuarios, list)
    assert len(usuarios) > 0


def test_cada_usuario_tem_id_e_nome():
    usuarios = client.get("/users").json()

    for usuario in usuarios:
        assert "id" in usuario
        assert "nome" in usuario


def test_users_sem_usuarios_ainda_e_sucesso(monkeypatch):
    """Lista vazia nao e erro: continua 200, so que com []."""
    monkeypatch.setattr(main, "usuarios", [])

    resposta = client.get("/users")

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_a_tela_nao_tem_nome_escrito_no_html():
    """Os nomes tem que vir da API, nao do template."""
    html = client.get("/").text

    for usuario in main.usuarios:
        assert usuario["nome"] not in html


def test_post_users_cria_usuario():
    resp = client.post(
        "/users", json={"nome": "Ana", "email": "ana@example.com"})
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["nome"] == "Ana"


def test_post_users_valida_campos():
    resp = client.post("/users", json={"nome": "SóNome"})
    assert resp.status_code == 422
    resp = client.post("/users", json={"nome": "X", "email": "not-an-email"})
    assert resp.status_code == 422


def test_post_users_duplicado():
    client.post("/users", json={"nome": "B", "email": "dup@example.com"})
    resp = client.post(
        "/users", json={"nome": "C", "email": "dup@example.com"})
    assert resp.status_code == 409
