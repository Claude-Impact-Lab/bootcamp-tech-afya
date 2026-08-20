from datetime import date
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.dependencies import get_doctor_verification_service, get_notification_publisher
from app.main import app
from app.models import Base
from app.services.cfm import CFMDoctor, CFMSpecialty


class JourneyDoctorVerifier:
    def _doctor(self, name: str, crm: str, uf: str) -> CFMDoctor:
        return CFMDoctor(
            crm_display=crm,
            uf=uf,
            official_name=name,
            registration_status="Regular",
            registration_type="Principal",
            source_updated_at=date(2026, 8, 19),
            specialties=(
                CFMSpecialty("CLÍNICA MÉDICA", "4321", "CLÍNICA MÉDICA - RQE Nº: 4321"),
            ),
            photo_url="https://portal.cfm.org.br/foto-jornada.png",
        )

    def verify(self, name, crm, uf):
        return self._doctor(name, crm, uf)

    def lookup_for_manual_review(self, crm, uf):
        return self._doctor("Médica da Jornada", crm, uf)


class RecordingNotifications:
    def __init__(self):
        self.status_changes = []
        self.password_resets = []

    def account_status_changed(self, user_id, email, new_status):
        self.status_changes.append((user_id, email, new_status))

    def password_reset_requested(self, email, reset_url):
        self.password_resets.append((email, reset_url))


@pytest.fixture
def journey(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'journeys.db'}")
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    notifications = RecordingNotifications()

    def override_get_db():
        with session_local() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_doctor_verification_service] = JourneyDoctorVerifier
    app.dependency_overrides[get_notification_publisher] = lambda: notifications
    with TestClient(app) as client:
        yield client, notifications
    app.dependency_overrides.clear()
    engine.dispose()


def doctor_payload():
    return {
        "user": {"nome": "Médica da Jornada", "email": "medica.jornada@exemplo.com"},
        "doctor": {"crm": "987654", "uf": "SP"},
        "senha": "senha-inicial",
        "confirmacao_senha": "senha-inicial",
    }


def non_doctor_payload(
    email="usuario.jornada@exemplo.com",
    name="Usuário da Jornada",
    cpf="222.222.222-22",
):
    return {
        "user": {"nome": name, "email": email},
        "cpf": cpf,
        "senha": "senha-inicial",
        "confirmacao_senha": "senha-inicial",
    }


def admin_login(client):
    response = client.post("/admin/login", json={"nome": "santanna", "senha": "12345"})
    assert response.status_code == 200


def test_jornada_medica_do_cadastro_ao_perfil_ativo(journey):
    client, _ = journey

    registration = client.post("/registrations", json=doctor_payload())
    status = client.get("/account/me")
    completion_page = client.get("/doctor/complete-profile")
    completion = client.put(
        "/doctor/profile",
        json={
            "email": "medica.jornada@exemplo.com",
            "cpf": "529.982.247-25",
            "marital_status": "solteiro",
            "mobile_phone": "(11) 99999-8888",
            "action": "complete",
        },
    )
    dashboard = client.get("/doctor/dashboard")

    assert registration.status_code == 202
    assert registration.json()["registration_status"] == "crm_verification_pending"
    assert status.json()["registration_status"] == "approved_incomplete"
    assert status.json()["redirect_url"] == "/doctor/complete-profile"
    assert "Médica da Jornada" in completion_page.text
    assert "CLÍNICA MÉDICA" in completion_page.text
    assert completion.json()["registration_status"] == "active"
    assert dashboard.status_code == 200
    assert "Seu cadastro profissional" in dashboard.text


def test_jornada_sem_crm_rejeicao_reenvio_aprovacao_e_edicao(journey):
    client, notifications = journey

    registration = client.post("/non-medical/registrations", json=non_doctor_payload())
    pending_page = client.get("/account/status")
    admin_login(client)
    rejection = client.post(
        f"/admin/registrations/{registration.json()['id']}/reject",
        json={"motivo": "Complete seus dados de contato."},
    )
    client.post("/admin/logout")
    client.post(
        "/non-medical/login",
        json={"email": "usuario.jornada@exemplo.com", "senha": "senha-inicial"},
    )
    resubmission = client.put(
        "/non-medical/profile",
        json={
            "nome": "Usuário Atualizado",
            "email": "usuario.jornada@exemplo.com",
            "cpf": "333.333.333-33",
            "mobile_phone": "(21) 98888-7777",
            "action": "resubmit",
        },
    )
    admin_login(client)
    approval = client.post(f"/admin/registrations/{registration.json()['id']}/approve")
    client.post("/admin/logout")
    login = client.post(
        "/non-medical/login",
        json={"email": "usuario.jornada@exemplo.com", "senha": "senha-inicial"},
    )
    dashboard = client.get("/non-medical/dashboard")

    assert registration.status_code == 201
    assert "aguardam a decisão do administrador" in pending_page.text
    assert "nova consulta ao CFM" not in pending_page.text
    assert rejection.json()["registration_status"] == "rejected"
    assert resubmission.json()["registration_status"] == "pending_admin_approval"
    assert resubmission.json()["cpf"] == "33333333333"
    assert resubmission.json()["mobile_phone"] == "21988887777"
    assert approval.json()["registration_status"] == "active"
    assert login.json()["redirect_url"] == "/non-medical/dashboard"
    assert "Informações de contato" in dashboard.text
    assert notifications.status_changes[-1][2] == "active"


def test_jornada_administrativa_busca_paginacao_e_recuperacao_de_senha(journey):
    client, notifications = journey
    admin_login(client)
    for number in range(22):
        client.post(
            "/non-medical/registrations",
            json=non_doctor_payload(
                email=f"usuario{number:02d}@exemplo.com",
                name=f"Usuário {number:02d}",
                cpf=f"{number:011d}",
            ),
        )

    first_page = client.get("/admin/registrations", params={"page": 1, "page_size": 10})
    third_page = client.get("/admin/registrations", params={"page": 3, "page_size": 10})
    search = client.get("/admin/registrations", params={"q": "usuario17@"})

    client.post("/admin/logout")
    reset_request = client.post(
        "/account/password-reset/request",
        json={"email": "usuario17@exemplo.com"},
    )
    token = parse_qs(urlparse(reset_request.json()["reset_url"]).query)["token"][0]
    reset = client.post(
        "/account/password-reset/confirm",
        json={"token": token, "senha": "senha-atualizada", "confirmacao_senha": "senha-atualizada"},
    )
    login = client.post(
        "/non-medical/login",
        json={"email": "usuario17@exemplo.com", "senha": "senha-atualizada"},
    )

    assert first_page.json()["total"] == 22
    assert len(first_page.json()["items"]) == 10
    assert first_page.json()["pages"] == 3
    assert len(third_page.json()["items"]) == 2
    assert search.json()["total"] == 1
    assert search.json()["items"][0]["nome"] == "Usuário 17"
    assert notifications.password_resets[0][0] == "usuario17@exemplo.com"
    assert reset.json()["redirect_url"] == "/non-medical/login"
    assert login.status_code == 200
