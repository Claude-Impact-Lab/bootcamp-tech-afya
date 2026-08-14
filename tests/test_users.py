from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_user_valido():
    payload = {"name": "Alice Test", "email": "alice@example.com"}

    resposta = client.post("/users", json=payload)

    assert resposta.status_code == 201
    data = resposta.json()
    assert data["name"] == payload["name"]
    assert data["email"] == payload["email"]
    assert "id" in data

    # usuário deve aparecer na listagem
    lista = client.get("/users")
    assert lista.status_code == 200
    assert any(u["email"] == payload["email"] for u in lista.json())


def test_create_user_email_invalido_retorna_422():
    payload = {"name": "Bob", "email": "not-an-email"}

    resposta = client.post("/users", json=payload)

    assert resposta.status_code == 422
    body = resposta.json()
    # pydantic coloca os erros em 'detail' com informação de campo
    assert "detail" in body
    assert any("email" in str(item.get("loc", [])) for item in body["detail"]) 
