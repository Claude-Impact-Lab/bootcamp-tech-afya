from fastapi.testclient import TestClient


def test_health_retorna_ok(client: TestClient):
    resposta = client.get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok", "message": "Hello World"}


def test_index_retorna_200(client: TestClient):
    """Página index retorna status 200."""
    resposta = client.get("/")

    assert resposta.status_code == 200


def test_listar_usuarios_vazio_retorna_lista_vazia(client: TestClient):
    """Quando nenhum usuário foi criado, a lista deve estar vazia."""
    resposta = client.get("/users")

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_criar_usuario_retorna_dados_com_id(client: TestClient):
    """Criar um usuário retorna os dados incluindo o ID gerado pelo banco."""
    dados = {"nome": "Joao Silva", "email": "joao@example.com"}
    resposta = client.post("/users", json=dados)

    assert resposta.status_code == 201
    usuario = resposta.json()
    assert usuario["nome"] == "Joao Silva"
    assert usuario["email"] == "joao@example.com"
    assert "id" in usuario
    assert usuario["id"] > 0


def test_listar_usuarios_apos_criar(client: TestClient):
    """Listar usuários deve retornar os criados anteriormente."""
    # Criar dois usuários
    client.post("/users", json={"nome": "Alice", "email": "alice@example.com"})
    client.post("/users", json={"nome": "Bob", "email": "bob@example.com"})

    # Listar
    resposta = client.get("/users")

    assert resposta.status_code == 200
    usuarios = resposta.json()
    assert len(usuarios) == 2
    assert usuarios[0]["nome"] == "Alice"
    assert usuarios[1]["nome"] == "Bob"


def test_cada_usuario_tem_id_e_nome_e_email(client: TestClient):
    """Verificar que cada usuário tem os campos obrigatórios."""
    client.post("/users", json={"nome": "Carlos", "email": "carlos@example.com"})
    resposta = client.get("/users")

    usuarios = resposta.json()
    assert len(usuarios) > 0
    for usuario in usuarios:
        assert "id" in usuario
        assert "nome" in usuario
        assert "email" in usuario
