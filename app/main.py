import hashlib
import os
import re
from datetime import UTC, datetime
from hmac import compare_digest
from pathlib import Path
from typing import Annotated, Literal

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
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
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from app.database import get_db
from app.dependencies import get_doctor_verification_service, get_notification_publisher
from app.models import Doctor, DoctorSpecialty, User
from app.security import (
    create_password_reset_token,
    hash_password,
    read_password_reset_token,
    verify_password,
)
from app.services.cfm import CFMDoctor, CFMServiceError
from app.services.crm_numbers import crm_digits
from app.services.doctor_verification import DoctorVerificationFailure, DoctorVerificationService
from app.services.notifications import NotificationPublisher

BASE_DIR = Path(__file__).resolve().parent

ACCOUNT_DOCTOR = "doctor"
ACCOUNT_NON_DOCTOR = "non_doctor"
STATUS_PENDING = "pending_verification"
STATUS_ADMIN_PENDING = "pending_admin_approval"
STATUS_CRM_PENDING = "crm_verification_pending"
STATUS_CRM_FAILED = "crm_verification_failed"
STATUS_APPROVED_INCOMPLETE = "approved_incomplete"
STATUS_ACTIVE = "active"
STATUS_REJECTED = "rejected"


def required_setting(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} não foi definida no arquivo .env")
    return value


app = FastAPI(title="Gestão de acessos profissionais")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.add_middleware(
    SessionMiddleware,
    secret_key=required_setting("SESSION_SECRET"),
    same_site="lax",
    https_only=os.getenv("SESSION_HTTPS_ONLY", "false").lower() == "true",
)
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def validation_message_in_portuguese(error: dict) -> str:
    """Traduz mensagens estruturais do Pydantic sem devolver dados sensíveis."""

    error_type = str(error.get("type", ""))
    context = error.get("ctx") or {}
    message = str(error.get("msg", "Dados inválidos")).removeprefix("Value error, ")
    if error_type == "missing":
        return "Campo obrigatório"
    if error_type == "string_type":
        return "O campo deve ser um texto"
    if error_type == "string_too_short":
        return f"O campo deve ter pelo menos {context.get('min_length')} caracteres"
    if error_type == "string_too_long":
        return f"O campo deve ter no máximo {context.get('max_length')} caracteres"
    if error_type in {"json_invalid", "json_type"}:
        return "O conteúdo enviado não é um JSON válido"
    if error_type == "literal_error":
        return "O valor informado não é permitido"
    if error_type == "extra_forbidden":
        return "Este campo não é permitido"
    if error_type == "enum":
        return "O valor informado não é uma opção válida"
    if error_type.endswith("_parsing"):
        return "O valor informado possui formato inválido"
    if error_type.endswith("_type"):
        return "O tipo do campo é inválido"
    if error_type == "value_error":
        return message
    return "O valor informado é inválido"


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(
    _: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = [
        {
            "loc": list(error.get("loc", ())),
            "msg": validation_message_in_portuguese(error),
            "type": error.get("type", "value_error"),
        }
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": errors})


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Mantém em português também os erros padrão do framework."""

    standard_messages = {
        400: "Solicitação inválida",
        401: "Autenticação necessária",
        403: "Acesso não permitido",
        404: "Página ou recurso não encontrado",
        405: "Método não permitido",
        500: "Erro interno da aplicação",
    }
    english_defaults = {
        "Bad Request",
        "Unauthorized",
        "Forbidden",
        "Not Found",
        "Method Not Allowed",
        "Internal Server Error",
    }
    detail = exc.detail
    if not isinstance(detail, str) or detail in english_defaults:
        detail = standard_messages.get(
            exc.status_code, "Não foi possível concluir a solicitação"
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": detail},
        headers=exc.headers,
    )


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
ESTADOS_CIVIS = frozenset(
    {"solteiro", "casado", "separado", "divorciado", "viuvo", "uniao_estavel", "prefiro_nao_informar"}
)


def cpf_is_valid(value: str) -> bool:
    """Validação simplificada para o exercício: exige somente onze dígitos."""

    return len(value) == 11 and value.isdigit()


def normalize_cpf(value: str | None) -> str | None:
    digits = re.sub(r"\D", "", value) if isinstance(value, str) else ""
    if not digits:
        return None
    if not cpf_is_valid(digits):
        raise ValueError("CPF deve conter 11 dígitos")
    return digits


def normalize_mobile_phone(value: str | None) -> str | None:
    digits = re.sub(r"\D", "", value) if isinstance(value, str) else ""
    if digits.startswith("55") and len(digits) in {12, 13}:
        digits = digits[2:]
    if not digits:
        return None
    if len(digits) not in {10, 11}:
        raise ValueError("Celular deve conter DDD e número")
    return digits


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
    cpf: str

    @field_validator("cpf", mode="before")
    @classmethod
    def validar_cpf(cls, value: str | None) -> str:
        normalized = normalize_cpf(value)
        if normalized is None:
            raise ValueError("CPF deve conter 11 dígitos")
        return normalized


class DoctorRegistrationUpdateIn(BaseModel):
    user: UserIn
    doctor: DoctorIn


class DoctorRetryIn(BaseModel):
    nome: Nome
    doctor: DoctorIn


class DoctorProfileUpdateIn(BaseModel):
    model_config = {"extra": "forbid"}

    email: str
    cpf: str | None = None
    marital_status: str | None = None
    mobile_phone: str | None = None
    action: Literal["draft", "complete"]

    @field_validator("email", mode="before")
    @classmethod
    def validar_email(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("EMAIL NÃO É VÁLIDO")
        value = value.strip()
        try:
            email_validator.validate_python(value)
        except ValidationError as exc:
            raise ValueError("EMAIL NÃO É VÁLIDO") from exc
        return value.lower()

    @field_validator("cpf", mode="before")
    @classmethod
    def validar_cpf(cls, value: str | None) -> str | None:
        return normalize_cpf(value)

    @field_validator("marital_status", mode="before")
    @classmethod
    def validar_estado_civil(cls, value: str | None) -> str | None:
        normalized = value.strip().lower() if isinstance(value, str) else ""
        if not normalized:
            return None
        if normalized not in ESTADOS_CIVIS:
            raise ValueError("Estado civil inválido")
        return normalized

    @field_validator("mobile_phone", mode="before")
    @classmethod
    def validar_celular(cls, value: str | None) -> str | None:
        return normalize_mobile_phone(value)

    @model_validator(mode="after")
    def validar_conclusao(self):
        if self.action == "complete" and not all(
            (self.cpf, self.marital_status, self.mobile_phone)
        ):
            raise ValueError("Preencha CPF, estado civil e celular para concluir o perfil")
        return self


class AccountLogin(BaseModel):
    email: str
    senha: str

    @field_validator("email", mode="before")
    @classmethod
    def normalizar_email(cls, value: str) -> str:
        return value.strip().lower() if isinstance(value, str) else ""


class NonDoctorProfileUpdateIn(UserIn):
    cpf: str
    mobile_phone: str | None = None
    action: Literal["save", "resubmit"] = "save"

    @field_validator("cpf", mode="before")
    @classmethod
    def validar_cpf(cls, value: str | None) -> str:
        normalized = normalize_cpf(value)
        if normalized is None:
            raise ValueError("CPF deve conter 11 dígitos")
        return normalized

    @field_validator("mobile_phone", mode="before")
    @classmethod
    def validar_celular(cls, value: str | None) -> str | None:
        return normalize_mobile_phone(value)


class PasswordResetRequestIn(BaseModel):
    email: str

    @field_validator("email", mode="before")
    @classmethod
    def normalizar_email(cls, value: str) -> str:
        return value.strip().lower() if isinstance(value, str) else ""


class PasswordResetConfirmIn(BaseModel):
    token: str
    senha: str
    confirmacao_senha: str

    @model_validator(mode="after")
    def validar_senhas(self):
        if not 8 <= len(self.senha) <= 128:
            raise ValueError("A senha deve ter entre 8 e 128 caracteres")
        if self.senha != self.confirmacao_senha:
            raise ValueError("As senhas não coincidem")
        return self


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
    doctors = db.scalars(select(Doctor).where(Doctor.uf == novo.uf)).all()
    for doctor in doctors:
        if crm_digits(doctor.crm) == crm_digits(novo.crm) and doctor.id != ignore_doctor_id:
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
    if user.registration_status in {
        STATUS_PENDING, STATUS_ADMIN_PENDING, STATUS_CRM_PENDING, STATUS_CRM_FAILED, STATUS_REJECTED
    }:
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
    return {"status": "ok", "message": "Aplicação funcionando"}


def apply_cfm_professional_data(doctor: Doctor, result: CFMDoctor) -> None:
    """Persiste a ficha pública devolvida pelo CFM sem decidir o acesso."""

    doctor.cfm_crm_display = result.crm_display
    doctor.cfm_official_name = result.official_name
    doctor.cfm_registration_status = result.registration_status
    doctor.cfm_registration_type = result.registration_type
    doctor.cfm_photo_url = result.photo_url
    doctor.cfm_validated_at = datetime.now(UTC)
    doctor.cfm_source_updated_at = result.source_updated_at
    doctor.crm_registration_date = result.registration_date
    doctor.crm_first_registration_uf = result.first_registration_uf
    doctor.graduation_institution = result.graduation_institution
    doctor.graduation_year = result.graduation_year
    doctor.specialties.clear()
    doctor.specialties.extend(
        DoctorSpecialty(
            official_name=specialty.name,
            rqe=specialty.rqe,
            official_description=specialty.official_description,
        )
        for specialty in result.specialties
    )


def clear_cfm_professional_data(doctor: Doctor) -> None:
    """Remove dados oficiais antigos quando CRM ou UF são corrigidos."""

    doctor.crm_verified = False
    doctor.cfm_crm_display = None
    doctor.cfm_official_name = None
    doctor.cfm_registration_status = None
    doctor.cfm_registration_type = None
    doctor.cfm_photo_url = None
    doctor.cfm_validated_at = None
    doctor.cfm_source_updated_at = None
    doctor.crm_registration_date = None
    doctor.crm_first_registration_uf = None
    doctor.graduation_institution = None
    doctor.graduation_year = None
    doctor.specialties.clear()


def apply_cfm_result(user: User, result: CFMDoctor) -> None:
    doctor = user.doctor
    if doctor is None:
        raise RuntimeError("Cadastro médico sem perfil profissional")
    now = datetime.now(UTC)
    apply_cfm_professional_data(doctor, result)
    user.registration_status = STATUS_APPROVED_INCOMPLETE
    user.approved_at = now
    user.approved_by_admin = None
    user.reviewed_by_admin = None
    user.verification_method = "cfm_browser"
    user.rejection_reason = None
    user.rejected_at = None
    doctor.crm_verified = True
    doctor.verification_status = "verified"
    doctor.verification_method = "cfm_browser"
    doctor.verification_last_error = None


def attempt_automatic_verification(
    user: User,
    verifier: DoctorVerificationService,
    db: Session,
    *,
    discard_on_professional_failure: bool = False,
) -> dict:
    doctor = user.doctor
    if doctor is None:
        raise RuntimeError("Cadastro médico sem perfil profissional")
    doctor.verification_last_attempt_at = datetime.now(UTC)
    doctor.verification_method = "cfm_browser"
    try:
        result = verifier.verify(user.nome, doctor.crm, doctor.uf)
        apply_cfm_result(user, result)
    except DoctorVerificationFailure as exc:
        if discard_on_professional_failure:
            db.rollback()
            raise HTTPException(status_code=422, detail=exc.public_message) from exc
        user.registration_status = STATUS_CRM_FAILED
        user.verification_method = "cfm_browser"
        doctor.crm_verified = False
        doctor.verification_status = exc.__class__.__name__.lower()
        doctor.verification_last_error = exc.public_message
    except CFMServiceError as exc:
        user.registration_status = STATUS_CRM_PENDING
        user.verification_method = "cfm_browser"
        doctor.crm_verified = False
        doctor.verification_status = "pending_retry"
        doctor.verification_last_error = str(exc)
    db.commit()
    db.refresh(user)
    return user_with_doctor_dict(user)


def process_cfm_verification_in_background(
    user_id: int,
    expected_name: str,
    expected_crm: str,
    expected_uf: str,
    verifier: DoctorVerificationService,
    notifications: NotificationPublisher,
    bind,
) -> None:
    """Executa a consulta fora da resposta HTTP usando uma nova sessão do banco."""

    with Session(bind=bind) as db:
        user = db.scalar(
            select(User).options(selectinload(User.doctor)).where(User.id == user_id)
        )
        if user is None or user.doctor is None:
            return
        if (
            user.nome != expected_name
            or user.doctor.crm != expected_crm
            or user.doctor.uf != expected_uf
            or user.registration_status != STATUS_CRM_PENDING
        ):
            return
        result = attempt_automatic_verification(user, verifier, db)
        notifications.account_status_changed(user.id, user.email, result["registration_status"])


def schedule_cfm_verification(
    background_tasks: BackgroundTasks,
    user: User,
    verifier: DoctorVerificationService,
    notifications: NotificationPublisher,
    db: Session,
) -> None:
    if user.doctor is None:
        raise RuntimeError("Cadastro médico sem perfil profissional")
    background_tasks.add_task(
        process_cfm_verification_in_background,
        user.id,
        user.nome,
        user.doctor.crm,
        user.doctor.uf,
        verifier,
        notifications,
        db.get_bind(),
    )


@app.post("/registrations", status_code=202)
def create_doctor_registration(
    novo: DoctorRegistrationIn,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    verifier: DoctorVerificationService = Depends(get_doctor_verification_service),
    notifications: NotificationPublisher = Depends(get_notification_publisher),
) -> dict:
    """Salva o cadastro e agenda a validação profissional sem bloquear a resposta."""
    if db.scalar(select(User).where(User.email == novo.user.email)):
        raise HTTPException(status_code=409, detail=f"O e-mail {novo.user.email} já está cadastrado")
    ensure_doctor_is_available(novo.doctor, db)
    user = User(
        nome=novo.user.nome,
        email=novo.user.email,
        password_hash=hash_password(novo.senha),
        account_type=ACCOUNT_DOCTOR,
        registration_status=STATUS_CRM_PENDING,
        doctor=Doctor(crm=novo.doctor.crm, uf=novo.doctor.uf, verification_status="pending_browser"),
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Não foi possível concluir: e-mail ou CRM já cadastrado",
        )
    db.commit()
    db.refresh(user)
    request.session["user_id"] = user.id
    schedule_cfm_verification(background_tasks, user, verifier, notifications, db)
    return {
        **user_with_doctor_dict(user),
        "message": "Cadastro salvo. A validação do CFM foi iniciada em segundo plano.",
        "redirect_url": "/account/status",
    }


@app.post("/non-medical/registrations", status_code=201)
def create_non_doctor_registration(
    novo: NonDoctorRegistrationIn,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    if db.scalar(select(User).where(User.email == novo.user.email)):
        raise HTTPException(status_code=409, detail=f"O e-mail {novo.user.email} já está cadastrado")
    if db.scalar(select(User).where(User.cpf == novo.cpf)):
        raise HTTPException(status_code=409, detail="Este CPF já está cadastrado")
    user = User(
        nome=novo.user.nome,
        email=novo.user.email,
        cpf=novo.cpf,
        password_hash=hash_password(novo.senha),
        account_type=ACCOUNT_NON_DOCTOR,
        registration_status=STATUS_ADMIN_PENDING,
    )
    result = commit_registration(db, user, "Não foi possível concluir: e-mail ou CPF já cadastrado")
    request.session["user_id"] = user.id
    return {
        **result,
        "message": "Cadastro realizado. Acompanhe a análise da sua solicitação.",
        "redirect_url": "/account/status",
    }


@app.post("/doctor/login")
def doctor_login(credentials: AccountLogin, request: Request, db: Session = Depends(get_db)) -> dict:
    return authenticate_account(credentials, ACCOUNT_DOCTOR, request, db)


@app.post("/non-medical/login")
def non_doctor_login(credentials: AccountLogin, request: Request, db: Session = Depends(get_db)) -> dict:
    return authenticate_account(credentials, ACCOUNT_NON_DOCTOR, request, db)


@app.post("/account/password-reset/request")
def request_password_reset(
    data: PasswordResetRequestIn,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    notifications: NotificationPublisher = Depends(get_notification_publisher),
) -> dict:
    """Gera um link temporário sem revelar se o e-mail existe."""

    user = db.scalar(select(User).where(User.email == data.email))
    reset_url = None
    if user is not None and user.password_hash:
        token = create_password_reset_token(
            user.id,
            user.email,
            user.password_hash,
            required_setting("SESSION_SECRET"),
        )
        reset_url = str(request.url_for("password_reset_page").include_query_params(token=token))
        background_tasks.add_task(notifications.password_reset_requested, user.email, reset_url)
    result = {
        "message": "Se o e-mail estiver cadastrado, as instruções para criar uma nova senha serão enviadas.",
    }
    if reset_url and os.getenv("PASSWORD_RESET_SHOW_LINK", "true").lower() == "true":
        result["reset_url"] = reset_url
    return result


@app.post("/account/password-reset/confirm")
def confirm_password_reset(
    data: PasswordResetConfirmIn,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    payload = read_password_reset_token(
        data.token,
        required_setting("SESSION_SECRET"),
        max_age=int(os.getenv("PASSWORD_RESET_MAX_AGE_SECONDS", "3600")),
    )
    if payload is None:
        raise HTTPException(status_code=400, detail="O link de recuperação é inválido ou expirou")
    user = db.get(User, payload["user_id"])
    current_version = (
        hashlib.sha256(user.password_hash.encode()).hexdigest()[:16]
        if user is not None and user.password_hash
        else None
    )
    if (
        user is None
        or user.email != payload["email"]
        or current_version != payload.get("password_version")
    ):
        raise HTTPException(status_code=400, detail="O link de recuperação é inválido ou já foi utilizado")
    user.password_hash = hash_password(data.senha)
    db.commit()
    request.session.clear()
    login_url = "/doctor/login" if user.account_type == ACCOUNT_DOCTOR else "/non-medical/login"
    return {"message": "Senha atualizada com sucesso", "redirect_url": login_url}


@app.post("/account/logout", status_code=204)
def account_logout(request: Request) -> Response:
    request.session.clear()
    return Response(status_code=204)


@app.get("/account/me")
def account_me(user: User = Depends(get_authenticated_user)) -> dict:
    return {**user_with_doctor_dict(user), "redirect_url": destination_for(user)}


@app.get("/doctor/profile")
def doctor_profile(user: User = Depends(require_active_doctor)) -> dict:
    return user_with_doctor_dict(user)


@app.get("/non-medical/profile")
def non_doctor_profile(user: User = Depends(require_active_non_doctor)) -> dict:
    return user.to_dict()


@app.put("/non-medical/profile")
def update_own_non_doctor_profile(
    data: NonDoctorProfileUpdateIn,
    user: User = Depends(get_authenticated_user),
    db: Session = Depends(get_db),
) -> dict:
    """Permite salvar o perfil e reenviar um cadastro rejeitado para análise."""

    if user.account_type != ACCOUNT_NON_DOCTOR:
        raise HTTPException(status_code=403, detail="Esta ação está disponível apenas para usuários sem CRM")
    email_owner = db.scalar(select(User).where(User.email == data.email, User.id != user.id))
    if email_owner:
        raise HTTPException(status_code=409, detail=f"O e-mail {data.email} já está cadastrado")
    cpf_owner = db.scalar(select(User).where(User.cpf == data.cpf, User.id != user.id))
    if cpf_owner:
        raise HTTPException(status_code=409, detail="Este CPF já está cadastrado")
    if data.action == "resubmit" and user.registration_status != STATUS_REJECTED:
        raise HTTPException(status_code=409, detail="Somente cadastros rejeitados precisam ser reenviados")
    user.nome = data.nome
    user.email = data.email
    user.cpf = data.cpf
    user.mobile_phone = data.mobile_phone
    if data.action == "resubmit":
        user.registration_status = STATUS_ADMIN_PENDING
        user.rejection_reason = None
        user.rejected_at = None
        user.reviewed_by_admin = None
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="O e-mail ou CPF informado já está cadastrado")
    db.refresh(user)
    return {
        **user.to_dict(),
        "message": "Cadastro reenviado para análise" if data.action == "resubmit" else "Perfil atualizado",
        "redirect_url": destination_for(user),
    }


@app.post("/doctor/complete-profile")
def complete_doctor_profile(
    data: ProfileCompletionIn,
    user: User = Depends(get_authenticated_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    if user.account_type != ACCOUNT_DOCTOR or user.registration_status != STATUS_APPROVED_INCOMPLETE:
        raise HTTPException(status_code=403, detail="Esta etapa não está disponível para seu cadastro")
    if user.doctor is None or not all(
        (user.doctor.cpf, user.doctor.marital_status, user.doctor.mobile_phone)
    ):
        raise HTTPException(
            status_code=409,
            detail="Preencha CPF, estado civil e celular antes de concluir o perfil",
        )
    user.registration_status = STATUS_ACTIVE
    user.profile_completed_at = datetime.now(UTC)
    db.commit()
    return {"message": "Cadastro concluído", "redirect_url": "/doctor/dashboard"}


@app.put("/doctor/profile")
def update_own_doctor_profile(
    data: DoctorProfileUpdateIn,
    user: User = Depends(get_authenticated_user),
    db: Session = Depends(get_db),
) -> dict:
    """Salva dados pessoais do médico como rascunho ou conclui o perfil."""

    if user.account_type != ACCOUNT_DOCTOR or user.doctor is None:
        raise HTTPException(status_code=403, detail="Esta ação está disponível apenas para médicos")
    if user.registration_status not in {STATUS_APPROVED_INCOMPLETE, STATUS_ACTIVE}:
        raise HTTPException(status_code=403, detail="Seu CRM precisa estar aprovado antes desta etapa")
    email_owner = db.scalar(select(User).where(User.email == data.email, User.id != user.id))
    if email_owner:
        raise HTTPException(status_code=409, detail=f"O e-mail {data.email} já está cadastrado")
    if data.cpf:
        cpf_owner = db.scalar(
            select(Doctor).where(Doctor.cpf == data.cpf, Doctor.id != user.doctor.id)
        )
        if cpf_owner:
            raise HTTPException(status_code=409, detail="Este CPF já está cadastrado")
    user.email = data.email
    user.doctor.cpf = data.cpf
    user.doctor.marital_status = data.marital_status
    user.doctor.mobile_phone = data.mobile_phone
    if data.action == "complete":
        user.registration_status = STATUS_ACTIVE
        user.profile_completed_at = datetime.now(UTC)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="E-mail ou CPF já cadastrado")
    db.refresh(user)
    return {
        **user_with_doctor_dict(user),
        "message": "Perfil concluído" if data.action == "complete" else "Rascunho salvo",
        "redirect_url": "/doctor/dashboard" if data.action == "complete" else destination_for(user),
    }


@app.post("/doctor/retry-cfm")
def retry_own_cfm_verification(
    data: DoctorRetryIn,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_authenticated_user),
    db: Session = Depends(get_db),
    verifier: DoctorVerificationService = Depends(get_doctor_verification_service),
    notifications: NotificationPublisher = Depends(get_notification_publisher),
) -> dict:
    """Permite ao médico corrigir o próprio cadastro pendente e tentar novamente."""

    allowed_statuses = {
        STATUS_PENDING,
        STATUS_ADMIN_PENDING,
        STATUS_CRM_PENDING,
        STATUS_CRM_FAILED,
    }
    if user.account_type != ACCOUNT_DOCTOR or user.doctor is None:
        raise HTTPException(status_code=403, detail="Esta ação está disponível apenas para médicos")
    if user.registration_status not in allowed_statuses:
        raise HTTPException(status_code=409, detail="Este cadastro não está aguardando validação do CRM")
    ensure_doctor_is_available(data.doctor, db, user.doctor.id)
    professional_changed = user.doctor.crm != data.doctor.crm or user.doctor.uf != data.doctor.uf
    user.nome = data.nome
    if professional_changed:
        clear_cfm_professional_data(user.doctor)
    user.doctor.crm = data.doctor.crm
    user.doctor.uf = data.doctor.uf
    user.registration_status = STATUS_CRM_PENDING
    user.rejection_reason = None
    user.rejected_at = None
    user.doctor.verification_status = "pending_browser"
    user.doctor.verification_last_error = None
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="O CRM informado já está cadastrado")
    db.commit()
    db.refresh(user)
    schedule_cfm_verification(background_tasks, user, verifier, notifications, db)
    return {
        **user_with_doctor_dict(user),
        "message": "Nova consulta iniciada em segundo plano.",
        "redirect_url": "/account/status",
    }


@app.get("/admin/registrations")
def admin_registrations(
    registration_status: str | None = None,
    pending_only: bool = False,
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
) -> dict:
    filters = []
    if registration_status:
        filters.append(User.registration_status == registration_status)
    if pending_only:
        filters.append(
            User.registration_status.in_(
                {STATUS_PENDING, STATUS_ADMIN_PENDING, STATUS_CRM_PENDING, STATUS_CRM_FAILED}
            )
        )
    term = (q or "").strip()
    if term:
        pattern = f"%{term}%"
        filters.append(
            or_(User.nome.ilike(pattern), User.email.ilike(pattern), Doctor.crm.ilike(pattern))
        )

    statement = (
        select(User)
        .outerjoin(Doctor)
        .options(selectinload(User.doctor).selectinload(Doctor.specialties))
        .order_by(User.created_at, User.id)
    )
    count_statement = select(func.count(User.id)).select_from(User).outerjoin(Doctor)
    if filters:
        statement = statement.where(*filters)
        count_statement = count_statement.where(*filters)
    total = db.scalar(count_statement) or 0
    pages = max(1, (total + page_size - 1) // page_size)
    current_page = min(page, pages)
    items = db.scalars(
        statement.offset((current_page - 1) * page_size).limit(page_size)
    ).all()
    return {
        "items": [user_with_doctor_dict(user) for user in items],
        "total": total,
        "page": current_page,
        "page_size": page_size,
        "pages": pages,
    }


@app.get("/admin/registrations/summary")
def admin_registration_summary(
    db: Session = Depends(get_db), _: str = Depends(require_admin)
) -> dict[str, int]:
    count = db.scalar(
        select(func.count()).select_from(User).where(
            User.registration_status.in_(
                {STATUS_PENDING, STATUS_ADMIN_PENDING, STATUS_CRM_PENDING, STATUS_CRM_FAILED}
            )
        )
    )
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
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin_name: str = Depends(require_admin),
    verifier: DoctorVerificationService = Depends(get_doctor_verification_service),
    notifications: NotificationPublisher = Depends(get_notification_publisher),
) -> dict:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"Usuário {user_id} não encontrado")
    if user.registration_status not in {
        STATUS_PENDING, STATUS_ADMIN_PENDING, STATUS_CRM_PENDING, STATUS_CRM_FAILED
    }:
        raise HTTPException(status_code=409, detail="Somente cadastros pendentes podem ser aprovados")
    now = datetime.now(UTC)
    if user.doctor:
        user.doctor.verification_last_attempt_at = now
        try:
            result = verifier.lookup_for_manual_review(user.doctor.crm, user.doctor.uf)
        except DoctorVerificationFailure as exc:
            raise HTTPException(status_code=422, detail=exc.public_message) from exc
        except CFMServiceError as exc:
            raise HTTPException(
                status_code=503,
                detail="O CFM está indisponível. A aprovação não foi concluída para evitar uma ficha sem dados oficiais.",
            ) from exc
        apply_cfm_professional_data(user.doctor, result)
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
        user.doctor.verification_method = "manual_with_cfm_sync"
        user.doctor.verification_last_error = None
    db.commit()
    db.refresh(user)
    background_tasks.add_task(
        notifications.account_status_changed, user.id, user.email, user.registration_status
    )
    return user_with_doctor_dict(user)


@app.post("/admin/registrations/{user_id}/reject")
def reject_registration(
    user_id: int,
    data: RejectionIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin_name: str = Depends(require_admin),
    notifications: NotificationPublisher = Depends(get_notification_publisher),
) -> dict:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"Usuário {user_id} não encontrado")
    if user.registration_status not in {
        STATUS_PENDING, STATUS_ADMIN_PENDING, STATUS_CRM_PENDING, STATUS_CRM_FAILED
    }:
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
    background_tasks.add_task(
        notifications.account_status_changed, user.id, user.email, user.registration_status
    )
    return user_with_doctor_dict(user)


@app.post("/admin/registrations/{user_id}/retry-cfm")
def retry_cfm_verification(
    user_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
    verifier: DoctorVerificationService = Depends(get_doctor_verification_service),
    notifications: NotificationPublisher = Depends(get_notification_publisher),
) -> dict:
    user = db.scalar(
        select(User).options(selectinload(User.doctor)).where(User.id == user_id)
    )
    if not user:
        raise HTTPException(status_code=404, detail=f"Usuário {user_id} não encontrado")
    if user.account_type != ACCOUNT_DOCTOR or user.doctor is None:
        raise HTTPException(status_code=409, detail="Este cadastro não pertence a um médico")
    if user.registration_status not in {STATUS_CRM_PENDING, STATUS_CRM_FAILED, STATUS_PENDING}:
        raise HTTPException(status_code=409, detail="Este cadastro não está aguardando validação do CRM")
    user.registration_status = STATUS_CRM_PENDING
    user.doctor.verification_status = "pending_browser"
    db.commit()
    db.refresh(user)
    schedule_cfm_verification(background_tasks, user, verifier, notifications, db)
    return {
        **user_with_doctor_dict(user),
        "message": "Nova consulta ao CFM iniciada em segundo plano.",
    }


@app.post("/admin/registrations/{user_id}/sync-cfm")
def sync_cfm_professional_data(
    user_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
    verifier: DoctorVerificationService = Depends(get_doctor_verification_service),
) -> dict:
    """Atualiza a ficha CFM sem alterar aprovação, perfil ou permissões."""

    user = db.scalar(
        select(User)
        .options(selectinload(User.doctor).selectinload(Doctor.specialties))
        .where(User.id == user_id)
    )
    if not user:
        raise HTTPException(status_code=404, detail=f"Usuário {user_id} não encontrado")
    if user.account_type != ACCOUNT_DOCTOR or user.doctor is None:
        raise HTTPException(status_code=409, detail="Este cadastro não pertence a um médico")
    user.doctor.verification_last_attempt_at = datetime.now(UTC)
    try:
        result = verifier.lookup_for_manual_review(user.doctor.crm, user.doctor.uf)
    except DoctorVerificationFailure as exc:
        raise HTTPException(status_code=422, detail=exc.public_message) from exc
    except CFMServiceError as exc:
        raise HTTPException(status_code=503, detail="Não foi possível sincronizar os dados com o CFM") from exc
    apply_cfm_professional_data(user.doctor, result)
    user.doctor.verification_method = "cfm_browser"
    user.doctor.verification_last_error = None
    db.commit()
    db.refresh(user)
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
        user.registration_status = STATUS_CRM_PENDING
        user.approved_at = None
        user.approved_by_admin = None
        user.reviewed_by_admin = None
        user.verification_method = None
        user.profile_completed_at = None
        user.doctor.crm_verified = False
        user.doctor.verification_status = "pending_browser"
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
        user.registration_status = STATUS_CRM_PENDING
    doctor = Doctor(
        user=user,
        crm=novo.crm,
        uf=novo.uf,
        verification_status="pending_browser" if user.password_hash else "not_verified",
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


@app.get("/account/forgot-password")
def forgot_password_page(request: Request):
    return templates.TemplateResponse(request=request, name="forgot_password.html")


@app.get("/account/reset-password", name="password_reset_page")
def password_reset_page(request: Request, token: str = ""):
    return templates.TemplateResponse(
        request=request,
        name="reset_password.html",
        context={"token": token},
    )


@app.get("/account/status")
def account_status_page(request: Request, user: User = Depends(get_authenticated_user)):
    if user.registration_status not in {
        STATUS_PENDING, STATUS_ADMIN_PENDING, STATUS_CRM_PENDING, STATUS_CRM_FAILED, STATUS_REJECTED
    }:
        return RedirectResponse(destination_for(user), status_code=303)
    return templates.TemplateResponse(request=request, name="account_status.html", context={"user": user})


@app.get("/doctor/complete-profile")
def complete_profile_page(request: Request, user: User = Depends(get_authenticated_user)):
    if user.account_type != ACCOUNT_DOCTOR or user.registration_status != STATUS_APPROVED_INCOMPLETE:
        return RedirectResponse(destination_for(user), status_code=303)
    return templates.TemplateResponse(request=request, name="doctor_profile.html", context={"user": user})


@app.get("/doctor/dashboard")
def doctor_dashboard_page(request: Request, user: User = Depends(require_active_doctor)):
    return templates.TemplateResponse(request=request, name="doctor_profile.html", context={"user": user})


@app.get("/non-medical/dashboard")
def non_medical_dashboard_page(request: Request, user: User = Depends(require_active_non_doctor)):
    return templates.TemplateResponse(request=request, name="dashboard.html", context={"user": user, "kind": ACCOUNT_NON_DOCTOR})


@app.get("/admin")
def admin_page(request: Request):
    return templates.TemplateResponse(request=request, name="admin.html")
