"""
Testes para a aplicação FastAPI com persistência em banco de dados.

O conftest.py automaticamente configura um banco SQLite em memória,
então esses testes rodam rápido e isolados.
"""

from fastapi.testclient import TestClient

from app.main import app
from app.models import Doctor, User

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
    - Retorna HTML com a marca Afya Medicine
    - Não exibe os textos antigos da interface
    """
    resposta = client.get("/")

    assert resposta.status_code == 200
    assert "Afya Medicine" in resposta.text
    assert "User Manager" not in resposta.text
    assert "Hello World" not in resposta.text


def test_get_users_retorna_lista():
    """
    Testa a rota GET /users.
    
    Verifica que:
    - Retorna status HTTP 200 (sucesso)
    - Retorna um JSON que é uma lista
    """
    resposta = client.get("/users")

    assert resposta.status_code == 200
    usuarios = resposta.json()
    assert isinstance(usuarios, list)


def test_get_users_estrutura_valida():
    """
    Testa a estrutura dos dados retornados por GET /users.
    
    Verifica que:
    - A lista tem pelo menos um usuário
    - Cada usuário tem os campos necessários: id, name, email
    - Os campos têm os tipos de dados corretos
    """
    resposta = client.get("/users")
    usuarios = resposta.json()

    # Verificar que a lista não está vazia
    assert len(usuarios) > 0

    # Verificar a estrutura do primeiro usuário
    primeiro_usuario = usuarios[0]
    assert "id" in primeiro_usuario
    assert "name" in primeiro_usuario
    assert "email" in primeiro_usuario

    # Verificar os tipos de dados
    assert isinstance(primeiro_usuario["id"], int)
    assert isinstance(primeiro_usuario["name"], str)
    assert isinstance(primeiro_usuario["email"], str)


def test_get_users_contém_dados_esperados():
    """
    Testa se os usuários retornados têm os dados esperados.
    
    Verifica que:
    - Existem pelo menos 3 usuários (João, Maria, Pedro)
    - João Silva está na lista
    """
    resposta = client.get("/users")
    usuarios = resposta.json()

    # Verificar quantidade de usuários
    assert len(usuarios) >= 3

    # Verificar que João Silva está na lista
    nomes = [usuario["name"] for usuario in usuarios]
    assert "João Silva" in nomes


def test_usuarios_persistem_no_banco(db_session):
    """
    Testa se os usuários estão sendo persistidos no banco de dados.
    
    Verifica que:
    - Ao consultar o banco diretamente, encontramos os mesmos usuários
    - O banco de dados está sendo usado corretamente
    """
    from app.models import User
    
    resposta = client.get("/users")
    usuarios_da_api = resposta.json()

    # Consultar o banco diretamente
    usuarios_do_banco = db_session.query(User).all()
    
    assert len(usuarios_do_banco) == len(usuarios_da_api)
    assert usuarios_do_banco[0].name == usuarios_da_api[0]["name"]


def test_put_users_atualiza_usuario(db_session):
    """Atualiza nome e email de um usuário persistido."""
    resposta = client.put(
        "/users/1",
        json={"name": "João Atualizado", "email": "joao.novo@example.com"},
    )

    assert resposta.status_code == 200
    assert resposta.json()["name"] == "João Atualizado"
    assert resposta.json()["email"] == "joao.novo@example.com"

    usuario = db_session.query(User).filter(User.id == 1).first()
    assert usuario.name == "João Atualizado"
    assert usuario.email == "joao.novo@example.com"


def test_put_users_retorna_404_para_usuario_inexistente():
    """Retorna 404 quando o usuário informado não existe."""
    resposta = client.put(
        "/users/999",
        json={"name": "Usuário", "email": "usuario@example.com"},
    )

    assert resposta.status_code == 404


def test_put_users_retorna_400_para_email_duplicado():
    """Retorna 400 quando o novo email já pertence a outro usuário."""
    resposta = client.put(
        "/users/1",
        json={"name": "João Atualizado", "email": "maria.santos@example.com"},
    )

    assert resposta.status_code == 400


def test_delete_users_exclui_usuario(db_session):
    """Exclui um usuário persistido e confirma que ele não pode mais ser consultado."""
    resposta = client.delete("/users/1")

    assert resposta.status_code == 200
    assert db_session.query(User).filter(User.id == 1).first() is None


def test_delete_users_retorna_404_para_usuario_inexistente():
    """Retorna 404 quando tenta excluir um usuário inexistente."""
    resposta = client.delete("/users/999")

    assert resposta.status_code == 404


def test_post_users_cria_usuario_comum():
    """Cria um usuário sem perfil médico."""
    resposta = client.post(
        "/users",
        json={"name": "Usuário Comum", "email": "comum@example.com"},
    )

    assert resposta.status_code == 201
    assert resposta.json()["is_doctor"] is False
    assert resposta.json()["doctor"] is None


def test_post_users_cria_usuario_medico():
    """Cria um usuário com perfil médico e seus dados."""
    resposta = client.post(
        "/users",
        json={
            "name": "Dra. Ana",
            "email": "ana.medica@example.com",
            "is_doctor": True,
            "crm": "123456",
            "uf": "sp",
        },
    )

    assert resposta.status_code == 201
    assert resposta.json()["is_doctor"] is True
    assert resposta.json()["doctor"] == {"crm": "123456", "uf": "SP"}


def test_get_user_informa_se_e_medico():
    """Consulta individualmente os dados médicos do usuário."""
    criado = client.post(
        "/users",
        json={
            "name": "Dr. Bruno",
            "email": "bruno.medico@example.com",
            "is_doctor": True,
            "crm": "654321",
            "uf": "RJ",
        },
    ).json()

    resposta = client.get(f"/users/{criado['id']}")

    assert resposta.status_code == 200
    assert resposta.json()["doctor"] == {"crm": "654321", "uf": "RJ"}


def test_delete_users_medico_retorna_409_e_preserva_usuario():
    """Impede a exclusão de usuário que possui perfil médico."""
    criado = client.post(
        "/users",
        json={
            "name": "Dra. Carla",
            "email": "carla.medica@example.com",
            "is_doctor": True,
            "crm": "789012",
            "uf": "MG",
        },
    ).json()

    resposta = client.delete(f"/users/{criado['id']}")

    assert resposta.status_code == 409
    assert client.get(f"/users/{criado['id']}").status_code == 200


# --- Missão 06: validação local de CRM e UF ---


def test_post_users_medico_com_uf_invalida_retorna_422():
    """UF que não existe no Brasil deve ser rejeitada com 422."""
    resposta = client.post(
        "/users",
        json={
            "name": "Dra. Fake",
            "email": "fake.uf@example.com",
            "is_doctor": True,
            "crm": "123456",
            "uf": "ZZ",
        },
    )

    assert resposta.status_code == 422
    detalhe = resposta.json()["detail"]
    assert any(erro["loc"][-1] == "uf" for erro in detalhe)


def test_post_users_medico_com_crm_com_letras_retorna_422():
    """CRM com letras não é um formato válido."""
    resposta = client.post(
        "/users",
        json={
            "name": "Dr. Letras",
            "email": "crm.letras@example.com",
            "is_doctor": True,
            "crm": "ABC123",
            "uf": "SP",
        },
    )

    assert resposta.status_code == 422
    detalhe = resposta.json()["detail"]
    assert any(erro["loc"][-1] == "crm" for erro in detalhe)


def test_post_users_medico_com_crm_curto_demais_retorna_422():
    """CRM com menos de 4 dígitos é rejeitado."""
    resposta = client.post(
        "/users",
        json={
            "name": "Dr. Curto",
            "email": "crm.curto@example.com",
            "is_doctor": True,
            "crm": "12",
            "uf": "SP",
        },
    )

    assert resposta.status_code == 422
    detalhe = resposta.json()["detail"]
    assert any(erro["loc"][-1] == "crm" for erro in detalhe)


def test_post_users_medico_com_crm_e_uf_validos_cria_usuario():
    """CRM e UF válidos permitem o cadastro do médico."""
    resposta = client.post(
        "/users",
        json={
            "name": "Dra. Válida",
            "email": "valida@example.com",
            "is_doctor": True,
            "crm": "111222",
            "uf": "pr",
        },
    )

    assert resposta.status_code == 201
    assert resposta.json()["doctor"] == {"crm": "111222", "uf": "PR"}


def test_post_users_medico_normaliza_espacos_do_crm():
    """Espaços nas bordas do CRM são removidos, sem alterar os dígitos."""
    resposta = client.post(
        "/users",
        json={
            "name": "Dr. Espaço",
            "email": "espaco@example.com",
            "is_doctor": True,
            "crm": "  555666  ",
            "uf": "SP",
        },
    )

    assert resposta.status_code == 201
    assert resposta.json()["doctor"]["crm"] == "555666"


def test_put_doctor_atualiza_crm_e_uf_com_dados_validos():
    """Edita CRM/UF de um médico já cadastrado com dados válidos."""
    criado = client.post(
        "/users",
        json={
            "name": "Dr. Editável",
            "email": "editavel@example.com",
            "is_doctor": True,
            "crm": "222333",
            "uf": "SP",
        },
    ).json()

    resposta = client.put(
        f"/users/{criado['id']}/doctor",
        json={"crm": "444555", "uf": "rj"},
    )

    assert resposta.status_code == 200
    assert resposta.json()["doctor"] == {"crm": "444555", "uf": "RJ"}


def test_put_doctor_com_uf_invalida_retorna_422_e_preserva_dados(db_session):
    """Não é possível alterar um médico válido para uma UF inexistente."""
    criado = client.post(
        "/users",
        json={
            "name": "Dr. Protegido",
            "email": "protegido@example.com",
            "is_doctor": True,
            "crm": "333444",
            "uf": "SP",
        },
    ).json()

    resposta = client.put(
        f"/users/{criado['id']}/doctor",
        json={"crm": "333444", "uf": "XX"},
    )

    assert resposta.status_code == 422
    doctor = db_session.query(Doctor).filter(Doctor.user_id == criado["id"]).first()
    assert doctor.uf == "SP"


def test_put_doctor_com_crm_invalido_retorna_422_e_preserva_dados(db_session):
    """Não é possível alterar um médico válido para um CRM com letras."""
    criado = client.post(
        "/users",
        json={
            "name": "Dr. Blindado",
            "email": "blindado@example.com",
            "is_doctor": True,
            "crm": "666777",
            "uf": "MG",
        },
    ).json()

    resposta = client.put(
        f"/users/{criado['id']}/doctor",
        json={"crm": "abc", "uf": "MG"},
    )

    assert resposta.status_code == 422
    doctor = db_session.query(Doctor).filter(Doctor.user_id == criado["id"]).first()
    assert doctor.crm == "666777"


def test_put_doctor_retorna_422_para_usuario_sem_perfil_medico():
    """Não é possível atualizar CRM/UF de um usuário que não é médico."""
    resposta = client.put(
        "/users/1/doctor",
        json={"crm": "123456", "uf": "SP"},
    )

    assert resposta.status_code == 422


def test_post_users_medico_sem_crm_e_uf_retorna_422():
    """CRM e UF são obrigatórios quando is_doctor é verdadeiro."""
    resposta = client.post(
        "/users",
        json={"name": "Dra. Incompleta", "email": "incompleta@example.com", "is_doctor": True},
    )

    assert resposta.status_code == 422


def test_post_users_comum_com_crm_retorna_422():
    """Usuário comum não pode informar CRM/UF."""
    resposta = client.post(
        "/users",
        json={
            "name": "Usuário Confuso",
            "email": "confuso@example.com",
            "is_doctor": False,
            "crm": "123456",
            "uf": "SP",
        },
    )

    assert resposta.status_code == 422


def test_post_users_comum_continua_funcionando_apos_validacao_de_medico():
    """Cadastro de usuário comum não é afetado pela regra de CRM/UF."""
    resposta = client.post(
        "/users",
        json={"name": "Usuário Normal", "email": "normal@example.com"},
    )

    assert resposta.status_code == 201
    assert resposta.json()["is_doctor"] is False
    assert resposta.json()["doctor"] is None


