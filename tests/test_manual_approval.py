import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.main import app
from app.models import Base, User
from app.security import verify_password

client = TestClient(app)


@pytest.fixture
def db_isolado(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'manual-approval.db'}")
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client.cookies.clear()
    login = client.post("/admin/login", json={"nome": "santanna", "senha": "12345"})
    assert login.status_code == 200
    yield session_local
    client.cookies.clear()
    app.dependency_overrides.clear()
    engine.dispose()


def doctor_payload(email="medica@exemplo.com", crm="123456"):
    return {
        "user": {"nome": "Ana Médica", "email": email},
        "doctor": {"crm": crm, "uf": "SP"},
        "senha": "senha-segura",
        "confirmacao_senha": "senha-segura",
    }


def non_doctor_payload():
    return {
        "user": {"nome": "Bruno Usuário", "email": "bruno@exemplo.com"},
        "senha": "senha-segura",
        "confirmacao_senha": "senha-segura",
    }


def test_senha_e_armazenada_com_hash_e_nao_e_exposta(db_isolado):
    response = client.post("/registrations", json=doctor_payload())

    db = db_isolado()
    try:
        user = db.scalar(select(User).where(User.email == "medica@exemplo.com"))
        assert user.password_hash != "senha-segura"
        assert verify_password("senha-segura", user.password_hash)
    finally:
        db.close()
    assert "password_hash" not in response.json()
    assert "senha" not in response.json()


def test_admin_recebe_contagem_de_cadastros_pendentes(db_isolado):
    client.post("/registrations", json=doctor_payload())
    client.post("/non-medical/registrations", json=non_doctor_payload())

    summary = client.get("/admin/registrations/summary")
    pending = client.get("/admin/registrations", params={"registration_status": "pending_verification"})

    assert summary.json() == {"pending_count": 2}
    assert len(pending.json()) == 2


def test_aprovacao_medica_exige_conclusao_antes_do_painel(db_isolado):
    client.post("/registrations", json=doctor_payload())
    approval = client.post("/admin/registrations/1/approve")
    assert approval.status_code == 200
    assert approval.json()["registration_status"] == "approved_incomplete"
    assert approval.json()["verification_method"] == "manual"
    assert approval.json()["approved_by_admin"] == "santanna"
    assert approval.json()["doctor"]["verification_status"] == "manually_verified"

    client.post("/admin/logout")
    login = client.post("/doctor/login", json={"email": "medica@exemplo.com", "senha": "senha-segura"})
    blocked = client.get("/doctor/profile")
    completed = client.post("/doctor/complete-profile", json={"confirmar": True})
    allowed = client.get("/doctor/profile")

    assert login.json()["redirect_url"] == "/doctor/complete-profile"
    assert blocked.status_code == 403
    assert completed.json()["redirect_url"] == "/doctor/dashboard"
    assert allowed.status_code == 200


def test_usuario_sem_crm_e_aprovado_diretamente_como_ativo(db_isolado):
    registration = client.post("/non-medical/registrations", json=non_doctor_payload())
    approval = client.post(f"/admin/registrations/{registration.json()['id']}/approve")
    client.post("/admin/logout")
    login = client.post(
        "/non-medical/login",
        json={"email": "bruno@exemplo.com", "senha": "senha-segura"},
    )

    assert approval.json()["registration_status"] == "active"
    assert approval.json()["doctor"] is None
    assert login.json()["redirect_url"] == "/non-medical/dashboard"
    assert client.get("/non-medical/profile").status_code == 200
    assert client.get("/doctor/profile").status_code == 403


def test_rejeicao_mostra_motivo_e_bloqueia_acesso(db_isolado):
    client.post("/registrations", json=doctor_payload())
    reason = "CRM ou dados informados não correspondem aos registros consultados."
    rejection = client.post("/admin/registrations/1/reject", json={"motivo": reason})
    client.post("/admin/logout")
    login = client.post("/doctor/login", json={"email": "medica@exemplo.com", "senha": "senha-segura"})
    status_page = client.get("/account/status")

    assert rejection.json()["registration_status"] == "rejected"
    assert rejection.json()["rejection_reason"] == reason
    assert rejection.json()["reviewed_by_admin"] == "santanna"
    assert login.json()["redirect_url"] == "/account/status"
    assert reason in status_page.text
    assert client.get("/doctor/profile").status_code == 403


def test_login_especifico_nao_aceita_tipo_de_conta_diferente(db_isolado):
    client.post("/registrations", json=doctor_payload())
    client.post("/admin/logout")

    response = client.post(
        "/non-medical/login",
        json={"email": "medica@exemplo.com", "senha": "senha-segura"},
    )

    assert response.status_code == 401


def test_aprovacao_e_rejeicao_exigem_sessao_administrativa(db_isolado):
    client.post("/registrations", json=doctor_payload())
    client.post("/admin/logout")

    assert client.post("/admin/registrations/1/approve").status_code == 401
    assert client.post("/admin/registrations/1/reject", json={"motivo": "Dados divergentes"}).status_code == 401
