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


def test_users_sem_cadastro_devolve_lista_vazia(monkeypatch):
    """Sem usuarios a resposta continua sendo sucesso, e nao um 404."""
    monkeypatch.setattr(main, "USERS", [])

    resposta = client.get("/users")

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_index_renderiza_a_tela():
    resposta = client.get("/")

    assert resposta.status_code == 200
    assert "User Manager" in resposta.text
