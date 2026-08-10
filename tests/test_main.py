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


def test_listar_usuarios_retorna_a_lista():
    resposta = client.get("/users")

    assert resposta.status_code == 200
    assert resposta.json() == main.USUARIOS


def test_cada_usuario_tem_id_e_nome():
    usuarios = client.get("/users").json()

    assert usuarios, "a lista de exemplo nao deveria estar vazia"
    for usuario in usuarios:
        assert "id" in usuario
        assert "nome" in usuario


def test_sem_usuarios_responde_200_com_lista_vazia(monkeypatch):
    """Lista vazia e sucesso, nao erro: a tela nao deve tratar como falha."""
    monkeypatch.setattr(main, "USUARIOS", [])

    resposta = client.get("/users")

    assert resposta.status_code == 200
    assert resposta.json() == []
