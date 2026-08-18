"""
Testes para a aplicação FastAPI.

Usa TestClient do FastAPI para fazer requisições HTTP sem precisar
iniciar um servidor real.
"""

from fastapi.testclient import TestClient

from app.main import app

# Client para fazer requisições nos testes
client = TestClient(app)


def test_health_retorna_status_ok():
    """
    Testa a rota GET /health.
    
    Verifica que:
    - Retorna status HTTP 200 (sucesso)
    - Retorna JSON com status "ok" e message "Hello World"
    """
    resposta = client.get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok", "message": "Hello World"}


def test_index_renderiza_html():
    """
    Testa a rota GET /.
    
    Verifica que:
    - Retorna status HTTP 200 (sucesso)
    - Retorna HTML que contém "User Manager" no título
    """
    resposta = client.get("/")

    assert resposta.status_code == 200
    assert "User Manager" in resposta.text
