import os
import re
from datetime import UTC, datetime
from hmac import compare_digest
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import (
    BaseModel,
    EmailStr,
    StringConstraints,
    TypeAdapter,
    ValidationError,
    field_validator,
    model_validator,
)
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from starlette.middleware.sessions import SessionMiddleware

from app.database import get_db
from app.dependencies import get_notification_publisher
from app.models import Doctor, User
from app.security import hash_password, verify_password
from app.services.notifications import NotificationPublisher

BASE_DIR = Path(__file__).resolve().parent

ACCOUNT_DOCTOR = "doctor"
ACCOUNT_NON_DOCTOR = "non_doctor"
STATUS_PENDING = "pending_verification"
STATUS_APPROVED_INCOMPLETE = "approved_incomplete"
STATUS_ACTIVE = "active"
STATUS_REJECTED = "rejected"


def required_setting(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} não foi definida no arquivo .env")
    return value


app = FastAPI(title="Gestão de acessos profissionais")
app.add_middleware(
    SessionMiddleware,
    secret_key=required_setting("SESSION_SECRET"),
    same_site="lax",
    https_only=os.getenv("SESSION_HTTPS_ONLY", "false").lower() == "true",
)
templates = Jinja2Templates(directory=BASE_DIR / "templates")

Nome = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=80)]
CRM = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
UF = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=2, to_upper=True)]
Motivo = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]
email_validator = TypeAdapter(EmailStr)
UFS_BRASILEIRAS = frozenset(
    {
        "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
        "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
        "SP", "SE", "TO",
    }
)


class UserIn(BaseModel):
    nome: Nome
    email: str

    @field_validator("email", mode="before")
    @classmethod
    def validar_email(cls, value: str) -> str:
        if value is None or not isinstance(value, str):
            raise ValueError("EMAIL NÃO É VÁLIDO")
        value = value.strip()
        try:
            email_validator.validate_python(value)
        except ValidationError as exc:
            raise ValueError("EMAIL NÃO É VÁLIDO") from exc
        return value.lower()


class DoctorIn(BaseModel):
    crm: CRM
    uf: UF

    @field_validator("crm")
    @classmethod
    def validar_crm(cls, value: str) -> str:
        if re.fullmatch(r"\d+(?:-\d+)?", value) is None:
            raise ValueError("CRM deve conter apenas números, com hífen opcional")
        return value

    @field_validator("uf")
    @classmethod
    def validar_uf(cls, value: str) -> str:
        if value not in UFS_BRASILEIRAS:
            raise ValueError("UF deve ser uma sigla de estado brasileiro válida")
        return value


class PasswordRegistration(BaseModel):
    user: UserIn
    senha: str
    confirmacao_senha: str

    @model_validator(mode="after")
    def senhas_devem_coincidir(self):
        if not 8 <= len(self.senha) <= 128 or not 8 <= len(self.confirmacao_senha) <= 128:
            raise ValueError("A senha deve ter entre 8 e 128 caracteres")
        if self.senha != self.confirmacao_senha:
            raise ValueError("As senhas não coincidem")
        return self


class DoctorRegistrationIn(PasswordRegistration):
    doctor: DoctorIn


class NonDoctorRegistrationIn(PasswordRegistration):
    pass


class DoctorRegistrationUpdateIn(BaseModel):
    user: UserIn
    doctor: DoctorIn


class AccountLogin(BaseModel):
    email: str
    senha: str

    @field_validator("email", mode="before")
    @classmethod
    def normalizar_email(cls, value: str) -> str:
        return value.strip().lower() if isinstance(value, str) else ""


class AdminLogin(BaseModel):
    nome: str
    senha: str


class RejectionIn(BaseModel):
    motivo: Motivo


class ProfileCompletionIn(BaseModel):
    confirmar: Literal[True]


def require_admin(request: Request) -> str:
    admin_name = required_setting("ADMIN_NAME")
    if request.session.get("admin") != admin_name:
        raise HTTPException(status_code=401, detail="Acesso de administrador necessário")
    return admin_name


def get_authenticated_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = request.session.get("user_id")
    user = db.get(User, user_id) if isinstance(user_id, int) else None
    if user is None or not user.password_hash:
        request.session.pop("user_id", None)
        raise HTTPException(status_code=401, detail="Faça login para continuar")
    return user


def require_active_doctor(user: User = Depends(get_authenticated_user)) -> User:
    if user.account_type != ACCOUNT_DOCTOR:
        raise HTTPException(status_code=403, detail="Área exclusiva para médicos")
    if user.registration_status != STATUS_ACTIVE:
        raise HTTPException(status_code=403, detail="Seu cadastro ainda não permite este acesso")
    return user


def require_active_non_doctor(user: User = Depends(get_authenticated_user)) -> User:
    if user.account_type != ACCOUNT_NON_DOCTOR:
        raise HTTPException(status_code=403, detail="Área exclusiva para usuários não médicos")
    if user.registration_status != STATUS_ACTIVE:
        raise HTTPException(status_code=403, detail="Seu cadastro ainda não permite este acesso")
    return user


def user_with_doctor_dict(user: User) -> dict:
    return {**user.to_dict(), "doctor": user.doctor.to_dict() if user.doctor else None}


def basic_user_dict(user: User) -> dict:
    return {"id": user.id, "nome": user.nome, "email": user.email}


def ensure_doctor_is_available(novo: DoctorIn, db: Session, ignore_doctor_id: int | None = None) -> None:
    doctor = db.scalar(select(Doctor).where(Doctor.crm == novo.crm, Doctor.uf == novo.uf))
    if doctor and doctor.id != ignore_doctor_id:
        raise HTTPException(status_code=409, detail=f"O CRM {novo.crm}/{novo.uf} já está cadastrado")


def commit_registration(db: Session, user: User, conflict_message: str) -> dict:
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=conflict_message)
    db.refresh(user)
    return user_with_doctor_dict(user)


def destination_for(user: User) -> str:
    if user.registration_status in {STATUS_PENDING, STATUS_REJECTED}:
        return "/account/status"
    if user.registration_status == STATUS_APPROVED_INCOMPLETE:
        return "/doctor/complete-profile"
    if user.registration_status == STATUS_ACTIVE and user.account_type == ACCOUNT_DOCTOR:
        return "/doctor/dashboard"
    if user.registration_status == STATUS_ACTIVE and user.account_type == ACCOUNT_NON_DOCTOR:
        return "/non-medical/dashboard"
    return "/account/status"


def authenticate_account(
    credentials: AccountLogin, expected_type: str, request: Request, db: Session
) -> dict[str, str]:
    user = db.scalar(select(User).where(User.email == credentials.email))
    valid = user is not None and verify_password(credentials.senha, user.password_hash)
    if not valid or user.account_type != expected_type:
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos")
    request.session.clear()
    request.session["user_id"] = user.id
    return {"message": "Login realizado", "redirect_url": destination_for(user)}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "message": "Hello World"}


@app.post("/registrations", status_code=201)
def create_doctor_registration(novo: DoctorRegistrationIn, db: Session = Depends(get_db)) -> dict:
    """Pré-cadastro médico sem consulta automática ao CFM."""
    if db.scalar(select(User).where(User.email == novo.user.email)):
        raise HTTPException(status_code=409, detail=f"O e-mail {novo.user.email} já está cadastrado")
    ensure_doctor_is_available(novo.doctor, db)
    user = User(
        nome=novo.user.nome,
        email=novo.user.email,
        password_hash=hash_password(novo.senha),
        account_type=ACCOUNT_DOCTOR,
        registration_status=STATUS_PENDING,
        doctor=Doctor(crm=novo.doctor.crm, uf=novo.doctor.uf, verification_status="pending_manual"),
    )
    return commit_registration(db, user, "Não foi possível concluir: e-mail ou CRM já cadastrado")


@app.post("/non-medical/registrations", status_code=201)
def create_non_doctor_registration(novo: NonDoctorRegistrationIn, db: Session = Depends(get_db)) -> dict:
    if db.scalar(select(User).where(User.email == novo.user.email)):
        raise HTTPException(status_code=409, detail=f"O e-mail {novo.user.email} já está cadastrado")
    user = User(
        nome=novo.user.nome,
        email=novo.user.email,
        password_hash=hash_password(novo.senha),
        account_type=ACCOUNT_NON_DOCTOR,
        registration_status=STATUS_PENDING,
    )
    return commit_registration(db, user, "Não foi possível concluir: e-mail já cadastrado")


@app.post("/doctor/login")
def doctor_login(credentials: AccountLogin, request: Request, db: Session = Depends(get_db)) -> dict:
    return authenticate_account(credentials, ACCOUNT_DOCTOR, request, db)


@app.post("/non-medical/login")
def non_doctor_login(credentials: AccountLogin, request: Request, db: Session = Depends(get_db)) -> dict:
    return authenticate_account(credentials, ACCOUNT_NON_DOCTOR, request, db)


@app.post("/account/logout", status_code=204)
def account_logout(request: Request) -> Response:
    request.session.clear()
    return Response(status_code=204)


@app.get("/account/me")
def account_me(user: User = Depends(get_authenticated_user)) -> dict:
    return user_with_doctor_dict(user)


@app.get("/doctor/profile")
def doctor_profile(user: User = Depends(require_active_doctor)) -> dict:
    return user_with_doctor_dict(user)


@app.get("/non-medical/profile")
def non_doctor_profile(user: User = Depends(require_active_non_doctor)) -> dict:
    return basic_user_dict(user)


@app.post("/doctor/complete-profile")
def complete_doctor_profile(
    data: ProfileCompletionIn,
    user: User = Depends(get_authenticated_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    if user.account_type != ACCOUNT_DOCTOR or user.registration_status != STATUS_APPROVED_INCOMPLETE:
        raise HTTPException(status_code=403, detail="Esta etapa não está disponível para seu cadastro")
    user.registration_status = STATUS_ACTIVE
    user.profile_completed_at = datetime.now(UTC)
    db.commit()
    return {"message": "Cadastro concluído", "redirect_url": "/doctor/dashboard"}


@app.get("/admin/registrations")
def admin_registrations(
    registration_status: str | None = None,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
) -> list[dict]:
    statement = (
        select(User)
        .options(selectinload(User.doctor).selectinload(Doctor.specialties))
        .order_by(User.created_at, User.id)
    )
    if registration_status:
        statement = statement.where(User.registration_status == registration_status)
    return [user_with_doctor_dict(user) for user in db.scalars(statement)]


@app.get("/admin/registrations/summary")
def admin_registration_summary(
    db: Session = Depends(get_db), _: str = Depends(require_admin)
) -> dict[str, int]:
    count = db.scalar(select(func.count()).select_from(User).where(User.registration_status == STATUS_PENDING))
    return {"pending_count": count or 0}


@app.get("/admin/registrations/{user_id}")
def admin_registration_detail(
    user_id: int, db: Session = Depends(get_db), _: str = Depends(require_admin)
) -> dict:
    user = db.scalar(
        select(User)
        .options(selectinload(User.doctor).selectinload(Doctor.specialties))
        .where(User.id == user_id)
    )
    if not user:
        raise HTTPException(status_code=404, detail=f"Usuário {user_id} não encontrado")
    return user_with_doctor_dict(user)


@app.post("/admin/registrations/{user_id}/approve")
def approve_registration(
    user_id: int,
    db: Session = Depends(get_db),
    admin_name: str = Depends(require_admin),
    notifications: NotificationPublisher = Depends(get_notification_publisher),
) -> dict:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"Usuário {user_id} não encontrado")
    if user.registration_status != STATUS_PENDING:
        raise HTTPException(status_code=409, detail="Somente cadastros pendentes podem ser aprovados")
    now = datetime.now(UTC)
    user.registration_status = STATUS_APPROVED_INCOMPLETE if user.account_type == ACCOUNT_DOCTOR else STATUS_ACTIVE
    user.approved_at = now
    user.approved_by_admin = admin_name
    user.reviewed_by_admin = admin_name
    user.verification_method = "manual"
    user.rejected_at = None
    user.rejection_reason = None
    if user.doctor:
        user.doctor.crm_verified = True
        user.doctor.verification_status = "manually_verified"
    db.commit()
    db.refresh(user)
    notifications.account_status_changed(user.id, user.email, user.registration_status)
    return user_with_doctor_dict(user)


@app.post("/admin/registrations/{user_id}/reject")
def reject_registration(
    user_id: int,
    data: RejectionIn,
    db: Session = Depends(get_db),
    admin_name: str = Depends(require_admin),
    notifications: NotificationPublisher = Depends(get_notification_publisher),
) -> dict:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"Usuário {user_id} não encontrado")
    if user.registration_status != STATUS_PENDING:
        raise HTTPException(status_code=409, detail="Somente cadastros pendentes podem ser rejeitados")
    user.registration_status = STATUS_REJECTED
    user.rejected_at = datetime.now(UTC)
    user.rejection_reason = data.motivo
    user.approved_at = None
    user.reviewed_by_admin = admin_name
    user.verification_method = "manual"
    if user.doctor:
        user.doctor.crm_verified = False
        user.doctor.verification_status = "rejected"
    db.commit()
    db.refresh(user)
    notifications.account_status_changed(user.id, user.email, user.registration_status)
    return user_with_doctor_dict(user)


@app.get("/users")
def list_users(
    nome: str | None = None, db: Session = Depends(get_db), _: str = Depends(require_admin)
) -> list[dict]:
    statement = select(User).options(selectinload(User.doctor).selectinload(Doctor.specialties)).order_by(User.id)
    if nome is not None:
        statement = statement.where(User.nome.ilike(f"%{nome}%"))
    return [user_with_doctor_dict(user) for user in db.scalars(statement)]


@app.post("/users", status_code=201)
def create_user(novo: UserIn, db: Session = Depends(get_db), _: str = Depends(require_admin)) -> dict:
    user = User(nome=novo.nome, email=novo.email)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"O e-mail {novo.email} já está cadastrado")
    db.refresh(user)
    return basic_user_dict(user)


@app.put("/registrations/{user_id}")
def update_doctor_registration(
    user_id: int,
    novo: DoctorRegistrationUpdateIn,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
) -> dict:
    user = db.scalar(select(User).options(selectinload(User.doctor)).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail=f"Usuário {user_id} não encontrado")
    is_legacy_without_profile = user.account_type == ACCOUNT_NON_DOCTOR and user.password_hash is None and user.doctor is None
    if user.account_type != ACCOUNT_DOCTOR and not is_legacy_without_profile:
        raise HTTPException(status_code=409, detail="Este cadastro não pertence a um médico")
    if is_legacy_without_profile:
        user.account_type = ACCOUNT_DOCTOR
    email_owner = db.scalar(select(User).where(User.email == novo.user.email, User.id != user_id))
    if email_owner:
        raise HTTPException(status_code=409, detail=f"O e-mail {novo.user.email} já está cadastrado")
    doctor_id = user.doctor.id if user.doctor else None
    ensure_doctor_is_available(novo.doctor, db, doctor_id)
    needs_new_review = bool(
        user.password_hash
        and (
            user.nome != novo.user.nome
            or user.doctor is None
            or user.doctor.crm != novo.doctor.crm
            or user.doctor.uf != novo.doctor.uf
        )
    )
    user.nome = novo.user.nome
    user.email = novo.user.email
    if user.doctor:
        user.doctor.crm = novo.doctor.crm
        user.doctor.uf = novo.doctor.uf
    else:
        user.doctor = Doctor(crm=novo.doctor.crm, uf=novo.doctor.uf)
    if needs_new_review:
        user.registration_status = STATUS_PENDING
        user.approved_at = None
        user.approved_by_admin = None
        user.reviewed_by_admin = None
        user.verification_method = None
        user.profile_completed_at = None
        user.doctor.crm_verified = False
        user.doctor.verification_status = "pending_manual"
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Não foi possível atualizar: e-mail ou CRM já cadastrado")
    db.refresh(user)
    return user_with_doctor_dict(user)


@app.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db), _: str = Depends(require_admin)) -> dict:
    user = db.get(User, user_id)
    if user:
        return basic_user_dict(user)
    raise HTTPException(status_code=404, detail=f"Usuário {user_id} não encontrado")


@app.post("/users/{user_id}/doctor", status_code=201)
def create_doctor_profile(
    user_id: int, novo: DoctorIn, db: Session = Depends(get_db), _: str = Depends(require_admin)
) -> dict:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"Usuário {user_id} não encontrado")
    if user.doctor:
        raise HTTPException(status_code=409, detail=f"Usuário {user_id} já possui perfil médico")
    ensure_doctor_is_available(novo, db)
    user.account_type = ACCOUNT_DOCTOR
    if user.password_hash:
        user.registration_status = STATUS_PENDING
    doctor = Doctor(
        user=user,
        crm=novo.crm,
        uf=novo.uf,
        verification_status="pending_manual" if user.password_hash else "not_verified",
    )
    db.add(doctor)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Não foi possível criar o perfil médico")
    db.refresh(doctor)
    return doctor.to_dict()


@app.get("/users/{user_id}/doctor")
def get_doctor_profile(
    user_id: int, db: Session = Depends(get_db), _: str = Depends(require_admin)
) -> dict:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"Usuário {user_id} não encontrado")
    if not user.doctor:
        raise HTTPException(status_code=404, detail=f"Usuário {user_id} não possui perfil médico")
    return user.doctor.to_dict()


@app.put("/users/{user_id}/doctor")
def update_doctor_profile(
    user_id: int,
    novos_dados: DoctorIn,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
) -> dict:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"Usuário {user_id} não encontrado")
    if not user.doctor:
        raise HTTPException(status_code=404, detail=f"Usuário {user_id} não possui perfil médico")
    ensure_doctor_is_available(novos_dados, db, user.doctor.id)
    user.doctor.crm = novos_dados.crm
    user.doctor.uf = novos_dados.uf
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Não foi possível atualizar o perfil médico")
    db.refresh(user.doctor)
    return user.doctor.to_dict()


@app.put("/users/{user_id}")
def update_user(
    user_id: int,
    novos_dados: UserIn,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
) -> dict:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"Usuário {user_id} não encontrado")
    user.nome = novos_dados.nome
    user.email = novos_dados.email
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"O e-mail {novos_dados.email} já está cadastrado")
    db.refresh(user)
    return basic_user_dict(user)


@app.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: int, db: Session = Depends(get_db), _: str = Depends(require_admin)
) -> Response:
    user = db.get(User, user_id)
    if user:
        db.delete(user)
        db.commit()
    return Response(status_code=204)


@app.post("/admin/login")
def admin_login(credentials: AdminLogin, request: Request) -> dict[str, str]:
    admin_name = required_setting("ADMIN_NAME")
    admin_password = required_setting("ADMIN_PASSWORD")
    if not (
        compare_digest(credentials.nome, admin_name)
        and compare_digest(credentials.senha, admin_password)
    ):
        raise HTTPException(status_code=401, detail="Nome ou senha inválidos")
    request.session.clear()
    request.session["admin"] = admin_name
    return {"message": "Login realizado"}


@app.post("/admin/logout", status_code=204)
def admin_logout(request: Request) -> Response:
    request.session.clear()
    return Response(status_code=204)


@app.get("/")
def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/non-medical/register")
def non_medical_register_page(request: Request):
    return templates.TemplateResponse(request=request, name="non_medical_register.html")


@app.get("/doctor/login")
def doctor_login_page(request: Request):
    return templates.TemplateResponse(request=request, name="account_login.html", context={"account_type": ACCOUNT_DOCTOR})


@app.get("/non-medical/login")
def non_medical_login_page(request: Request):
    return templates.TemplateResponse(request=request, name="account_login.html", context={"account_type": ACCOUNT_NON_DOCTOR})


@app.get("/account/status")
def account_status_page(request: Request, user: User = Depends(get_authenticated_user)):
    if user.registration_status not in {STATUS_PENDING, STATUS_REJECTED}:
        return RedirectResponse(destination_for(user), status_code=303)
    return templates.TemplateResponse(request=request, name="account_status.html", context={"user": user})


@app.get("/doctor/complete-profile")
def complete_profile_page(request: Request, user: User = Depends(get_authenticated_user)):
    if user.account_type != ACCOUNT_DOCTOR or user.registration_status != STATUS_APPROVED_INCOMPLETE:
        return RedirectResponse(destination_for(user), status_code=303)
    return templates.TemplateResponse(request=request, name="complete_profile.html", context={"user": user})


@app.get("/doctor/dashboard")
def doctor_dashboard_page(request: Request, user: User = Depends(require_active_doctor)):
    return templates.TemplateResponse(request=request, name="dashboard.html", context={"user": user, "kind": ACCOUNT_DOCTOR})


@app.get("/non-medical/dashboard")
def non_medical_dashboard_page(request: Request, user: User = Depends(require_active_non_doctor)):
    return templates.TemplateResponse(request=request, name="dashboard.html", context={"user": user, "kind": ACCOUNT_NON_DOCTOR})


@app.get("/admin")
def admin_page(request: Request):
    return templates.TemplateResponse(request=request, name="admin.html")
