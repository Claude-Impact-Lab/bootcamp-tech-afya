"""
Testes para a aplicação FastAPI com persistência em banco de dados.

O conftest.py automaticamente configura um banco SQLite em memória,
então esses testes rodam rápido e isolados.
"""

from fastapi.testclient import TestClient

from app.cfm.dependency import get_cfm_client
from app.cfm.fake_client import FakeCFMClient
from app.main import app
from app.models import Doctor, User

# Client para fazer requisições nos testes
client = TestClient(app)


def ficha_valida(**sobrescritas):
    """Payload válido para PUT /users/{id}/doctor (Etapa 2)."""
    payload = {
        "data_nascimento": "01/01/1990",
        "cpf": "123.456.789-00",
        "telefone": "(11) 91234-5678",
        "crm": "123456",
        "uf": "sp",
        "especialidade": "Cardiologia",
        "especialidade_outra": None,
        "instituicao_formacao": "USP",
        "ano_formacao": "2015",
        "cep": "01310-000",
        "logradouro": "Av. Paulista",
        "numero": "1000",
        "complemento": None,
        "bairro": "Bela Vista",
        "cidade": "São Paulo",
        "estado": "SP",
        "foto": None,
        "bio": None,
        "idiomas": ["Português", "Inglês"],
    }
    payload.update(sobrescritas)
    return payload


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


def test_index_nao_contem_campos_de_ficha_medica():
    """A Etapa 1 não deve exibir CRM/UF nem a Ficha do Médico."""
    resposta = client.get("/")

    assert 'id="crm"' not in resposta.text
    assert 'id="uf"' not in resposta.text
    assert "FICHA DO MÉDICO" not in resposta.text.upper()


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
    """Cria um usuário sem perfil médico (Etapa 1, checkbox desmarcado)."""
    resposta = client.post(
        "/users",
        json={"name": "Usuário Comum", "email": "comum@example.com"},
    )

    assert resposta.status_code == 201
    assert resposta.json()["is_doctor"] is False
    assert resposta.json()["doctor"] is None


def test_post_users_marca_is_doctor_sem_exigir_ficha_ainda():
    """Etapa 1: marcar 'é médico' cria o usuário sem exigir a ficha completa."""
    resposta = client.post(
        "/users",
        json={"name": "Dra. Ana", "email": "ana.medica@example.com", "is_doctor": True},
    )

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["is_doctor"] is True
    assert corpo["has_doctor_profile"] is False
    assert corpo["doctor"] is None


def test_delete_users_medico_sem_ficha_exclui_normalmente():
    """Médico sem ficha ainda (Doctor não criado) é excluído normalmente."""
    criado = client.post(
        "/users",
        json={"name": "Dra. Carla", "email": "carla.medica@example.com", "is_doctor": True},
    ).json()

    resposta = client.delete(f"/users/{criado['id']}")

    assert resposta.status_code == 200
    assert client.get(f"/users/{criado['id']}").status_code == 404


def test_delete_users_medico_com_ficha_exclui_usuario_e_ficha(db_session):
    """Excluir um médico com ficha cadastrada remove usuário e ficha, sem deixar órfã."""
    criado = client.post(
        "/users",
        json={"name": "Dr. Diego", "email": "diego.medico@example.com", "is_doctor": True},
    ).json()
    client.put(f"/users/{criado['id']}/doctor", json=ficha_valida())

    resposta = client.delete(f"/users/{criado['id']}")

    assert resposta.status_code == 200
    assert client.get(f"/users/{criado['id']}").status_code == 404
    assert db_session.query(Doctor).filter(Doctor.user_id == criado["id"]).first() is None


# --- Fluxo de duas etapas: Etapa 2 (Ficha do Médico) ---


def test_medico_page_retorna_200_para_qualquer_id():
    """A página /medico/{id} sempre carrega; ela mesma trata erros via fetch no cliente."""
    resposta = client.get("/medico/999999")

    assert resposta.status_code == 200
    assert "FICHA DO MÉDICO" in resposta.text.upper()


def test_put_doctor_cria_ficha_completa_com_dados_validos():
    """Salvar a ficha de um usuário marcado como médico cria o perfil completo."""
    criado = client.post(
        "/users",
        json={"name": "Dr. Bruno", "email": "bruno.medico@example.com", "is_doctor": True},
    ).json()

    resposta = client.put(f"/users/{criado['id']}/doctor", json=ficha_valida())

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["has_doctor_profile"] is True
    assert corpo["doctor"]["crm"] == "123456"
    assert corpo["doctor"]["uf"] == "SP"
    assert corpo["doctor"]["especialidade"] == "Cardiologia"
    assert corpo["doctor"]["idiomas"] == ["Português", "Inglês"]
    assert corpo["doctor"]["cfm_validated_at"] is not None


def test_put_doctor_nao_cria_ficha_quando_medico_nao_existe_no_cfm(db_session):
    """CRM/UF em formato válido mas ausentes no CFM não podem ser salvos."""
    criado = client.post(
        "/users",
        json={"name": "Dra. Não Encontrada", "email": "ausente.cfm@example.com", "is_doctor": True},
    ).json()
    app.dependency_overrides[get_cfm_client] = lambda: FakeCFMClient(medicos={})

    try:
        resposta = client.put(
            f"/users/{criado['id']}/doctor",
            json=ficha_valida(),
        )
    finally:
        app.dependency_overrides.pop(get_cfm_client, None)

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == "Médico não encontrado no CFM para o CRM e UF informados."
    assert db_session.query(Doctor).filter(Doctor.user_id == criado["id"]).first() is None


def test_put_doctor_com_formato_invalido_nao_consulta_cfm():
    """As validações Pydantic de CRM/UF acontecem antes da consulta externa."""
    criado = client.post(
        "/users",
        json={"name": "Dr. Formato", "email": "formato.cfm@example.com", "is_doctor": True},
    ).json()

    class ClienteQueNaoDeveSerConsultado:
        def find_doctor(self, crm: str, uf: str):
            raise AssertionError("O CFM não deve ser consultado para CRM/UF inválidos.")

    app.dependency_overrides[get_cfm_client] = ClienteQueNaoDeveSerConsultado
    try:
        resposta = client.put(
            f"/users/{criado['id']}/doctor",
            json=ficha_valida(crm="ABC123"),
        )
    finally:
        app.dependency_overrides.pop(get_cfm_client, None)

    assert resposta.status_code == 422


def test_put_doctor_nao_permite_usuario_nao_medico():
    """Usuário que não marcou 'é médico' não pode ter ficha médica salva."""
    criado = client.post(
        "/users",
        json={"name": "Usuário Comum", "email": "so.usuario@example.com"},
    ).json()

    resposta = client.put(f"/users/{criado['id']}/doctor", json=ficha_valida())

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == "Este usuário não possui um cadastro médico."


def test_put_doctor_retorna_404_para_usuario_inexistente():
    """Retorna 404 ao tentar salvar ficha de um usuário que não existe."""
    resposta = client.put("/users/999999/doctor", json=ficha_valida())

    assert resposta.status_code == 404


def test_put_doctor_com_uf_invalida_retorna_422():
    """UF que não existe no Brasil deve ser rejeitada com 422."""
    criado = client.post(
        "/users",
        json={"name": "Dra. Fake", "email": "fake.uf@example.com", "is_doctor": True},
    ).json()

    resposta = client.put(
        f"/users/{criado['id']}/doctor",
        json=ficha_valida(uf="ZZ"),
    )

    assert resposta.status_code == 422
    detalhe = resposta.json()["detail"]
    assert any(erro["loc"][-1] == "uf" for erro in detalhe)


def test_put_doctor_com_crm_com_letras_retorna_422():
    """CRM com letras não é um formato válido."""
    criado = client.post(
        "/users",
        json={"name": "Dr. Letras", "email": "crm.letras@example.com", "is_doctor": True},
    ).json()

    resposta = client.put(
        f"/users/{criado['id']}/doctor",
        json=ficha_valida(crm="ABC123"),
    )

    assert resposta.status_code == 422
    detalhe = resposta.json()["detail"]
    assert any(erro["loc"][-1] == "crm" for erro in detalhe)


def test_put_doctor_sem_campos_obrigatorios_de_endereco_retorna_422():
    """CEP/rua/número/bairro/cidade/estado são obrigatórios."""
    criado = client.post(
        "/users",
        json={"name": "Dr. Sem Endereço", "email": "sem.endereco@example.com", "is_doctor": True},
    ).json()

    resposta = client.put(
        f"/users/{criado['id']}/doctor",
        json=ficha_valida(cep="", logradouro="", numero="", bairro="", cidade="", estado=""),
    )

    assert resposta.status_code == 422
    campos_com_erro = {erro["loc"][-1] for erro in resposta.json()["detail"]}
    assert {"cep", "logradouro", "numero", "bairro", "cidade", "estado"} <= campos_com_erro


def test_put_doctor_especialidade_outra_sem_texto_retorna_422():
    """Selecionar 'Outra' exige o texto livre da especialidade."""
    criado = client.post(
        "/users",
        json={"name": "Dr. Outra", "email": "outra.especialidade@example.com", "is_doctor": True},
    ).json()

    resposta = client.put(
        f"/users/{criado['id']}/doctor",
        json=ficha_valida(especialidade="Outra", especialidade_outra=None),
    )

    assert resposta.status_code == 422


def test_put_doctor_especialidade_outra_com_texto_cria_ficha():
    """'Outra' com o texto preenchido é aceita normalmente."""
    criado = client.post(
        "/users",
        json={"name": "Dr. Outra2", "email": "outra2.especialidade@example.com", "is_doctor": True},
    ).json()

    resposta = client.put(
        f"/users/{criado['id']}/doctor",
        json=ficha_valida(especialidade="Outra", especialidade_outra="Medicina do Trabalho"),
    )

    assert resposta.status_code == 200
    assert resposta.json()["doctor"]["especialidade_outra"] == "Medicina do Trabalho"


def test_put_doctor_atualiza_ficha_existente_sem_duplicar():
    """Salvar a ficha duas vezes revalida no CFM e atualiza o mesmo registro."""
    criado = client.post(
        "/users",
        json={"name": "Dr. Duplicidade", "email": "duplicidade@example.com", "is_doctor": True},
    ).json()

    client.put(f"/users/{criado['id']}/doctor", json=ficha_valida())
    resposta = client.put(
        f"/users/{criado['id']}/doctor",
        json=ficha_valida(crm="654321", uf="RJ", cidade="Campinas"),
    )

    assert resposta.status_code == 200
    assert resposta.json()["doctor"]["cidade"] == "Campinas"
    assert resposta.json()["doctor"]["crm"] == "654321"
    assert resposta.json()["doctor"]["uf"] == "RJ"
    assert resposta.json()["doctor"]["cfm_validated_at"] is not None


def test_get_user_apos_salvar_ficha_retorna_nome_e_email_originais(db_session):
    """Nome e e-mail continuam vindo do cadastro da Etapa 1 (não são duplicados)."""
    criado = client.post(
        "/users",
        json={"name": "Dra. Persistente", "email": "persistente@example.com", "is_doctor": True},
    ).json()
    client.put(f"/users/{criado['id']}/doctor", json=ficha_valida())

    resposta = client.get(f"/users/{criado['id']}")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["name"] == "Dra. Persistente"
    assert corpo["email"] == "persistente@example.com"
    assert db_session.query(Doctor).filter(Doctor.user_id == criado["id"]).count() == 1
