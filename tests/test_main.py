import pytest
from fastapi.testclient import TestClient

from app import models
from app.main import app
from app.database import SessionLocal

client = TestClient(app)


@pytest.fixture(autouse=True)
def limpar_usuarios():
    """Garante que cada teste comeca com a tabela users vazia,
    evitando que um teste 'contamine' o resultado do outro."""
    db = SessionLocal()
    db.query(models.User).delete()
    db.commit()
    db.close()
    yield


def test_health_retorna_ok():
    resposta = client.get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok", "message": "Hello World"}


def test_index_renderiza_a_tela():
    resposta = client.get("/")

    assert resposta.status_code == 200
    assert "Afya" in resposta.text


def test_users_devolve_a_lista_em_json():
    client.post("/users", json={"nome": "Zeca", "email": "zeca@example.com"})

    resposta = client.get("/users")

    assert resposta.status_code == 200

    usuarios = resposta.json()
    assert isinstance(usuarios, list)
    assert len(usuarios) > 0


def test_cada_usuario_tem_id_e_nome():
    client.post("/users", json={"nome": "Zeca", "email": "zeca@example.com"})

    usuarios = client.get("/users").json()

    for usuario in usuarios:
        assert "id" in usuario
        assert "nome" in usuario


def test_users_sem_usuarios_ainda_e_sucesso():
    """Lista vazia nao e erro: continua 200, so que com []."""
    resposta = client.get("/users")

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_a_tela_nao_tem_nome_escrito_no_html():
    """Os nomes tem que vir da API, nao do template."""
    client.post("/users", json={"nome": "Zeca", "email": "zeca@example.com"})

    html = client.get("/").text
    usuarios = client.get("/users").json()

    for usuario in usuarios:
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

def test_put_users_atualiza_usuario():
    criado = client.post(
        "/users", json={"nome": "Original", "email": "original@example.com"}
    ).json()

    resp = client.put(
        f"/users/{criado['id']}",
        json={"nome": "Atualizado", "email": "atualizado@example.com"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == criado["id"]
    assert data["nome"] == "Atualizado"
    assert data["email"] == "atualizado@example.com"


def test_put_users_idempotente():
    criado = client.post(
        "/users", json={"nome": "Original", "email": "original@example.com"}
    ).json()

    payload = {"nome": "Atualizado", "email": "atualizado@example.com"}

    primeira = client.put(f"/users/{criado['id']}", json=payload)
    segunda = client.put(f"/users/{criado['id']}", json=payload)

    assert primeira.status_code == 200
    assert segunda.status_code == 200
    assert primeira.json() == segunda.json()


def test_put_users_inexistente_retorna_404():
    resp = client.put(
        "/users/99999",
        json={"nome": "Fantasma", "email": "fantasma@example.com"},
    )

    assert resp.status_code == 404


def test_delete_users_remove_usuario():
    criado = client.post(
        "/users", json={"nome": "Deletar", "email": "deletar@example.com"}
    ).json()

    resp = client.delete(f"/users/{criado['id']}")

    assert resp.status_code == 204

    usuarios = client.get("/users").json()
    assert all(u["id"] != criado["id"] for u in usuarios)


def test_delete_users_duas_vezes_retorna_404_na_segunda():
    criado = client.post(
        "/users", json={"nome": "Deletar", "email": "deletar2@example.com"}
    ).json()

    primeira = client.delete(f"/users/{criado['id']}")
    segunda = client.delete(f"/users/{criado['id']}")

    assert primeira.status_code == 204
    assert segunda.status_code == 404


def test_delete_users_inexistente_retorna_404():
    resp = client.delete("/users/99999")

    assert resp.status_code == 404