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

def test_users_retorna_lista_de_usuarios():
    resposta = client.get("/users")

    assert resposta.status_code == 200

    usuarios = resposta.json()
    assert isinstance(usuarios, list)

    for usuario in usuarios:
        assert "id" in usuario
        assert "nome" in usuario
        assert "email" in usuario
