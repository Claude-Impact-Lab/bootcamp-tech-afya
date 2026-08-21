import base64
import binascii
import hashlib
import hmac
import os
import re
import secrets
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import func, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from app.database import get_db, engine
from app.cfm_client import (
    CFMClient,
    CFMConfigurationError,
    CFMDoctor,
    CFMDoctorInactive,
    CFMDoctorNotFound,
    CFMInvalidInput,
    CFMUnavailable,
    CFMValidationTimeout,
)
from app.models import Base, Doctor as DoctorModel, User as UserModel

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "Ademilson")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "12345678")
SESSION_SECRET = os.getenv("SESSION_SECRET") or secrets.token_urlsafe(32)
UFS_VALIDAS = frozenset(
    {
        "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
        "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
        "RS", "RO", "RR", "SC", "SP", "SE", "TO",
    }
)

app = FastAPI(title="User Manager")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, same_site="lax", https_only=os.getenv("SESSION_HTTPS_ONLY", "false").lower() == "true")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def hash_password(password: str) -> str:
    """Gera um hash PBKDF2 com salt; a senha nunca e armazenada em texto puro."""
    salt = secrets.token_bytes(16)
    iterations = 210_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return "pbkdf2_sha256${}${}${}".format(iterations, base64.b64encode(salt).decode(), base64.b64encode(digest).decode())


def verify_password(password: str, stored_hash: str | None) -> bool:
    """Compara uma senha com o hash PBKDF2 salvo, sem expor o valor original."""
    if not stored_hash:
        return False
    try:
        algorithm, iterations_text, salt_text, digest_text = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_text)
        if not 100_000 <= iterations <= 1_000_000:
            return False
        salt = base64.b64decode(salt_text, validate=True)
        expected_digest = base64.b64decode(digest_text, validate=True)
        received_digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    except (ValueError, TypeError, binascii.Error):
        return False
    return hmac.compare_digest(received_digest, expected_digest)


def ensure_legacy_schema() -> None:
    """Acrescenta colunas em bancos SQLite locais criados em versoes anteriores."""
    if not str(engine.url).startswith("sqlite"):
        return
    table_names = inspect(engine).get_table_names()
    with engine.begin() as connection:
        if "users" in table_names:
            columns = {column["name"] for column in inspect(engine).get_columns("users")}
            user_columns = {
                "password_hash": "VARCHAR(512)",
                "telefone": "VARCHAR(20)",
                "documento": "VARCHAR(32)",
                "data_nascimento": "DATE",
                "escolaridade": "VARCHAR(120)",
                "cep": "VARCHAR(9)",
                "logradouro": "VARCHAR(255)",
                "numero": "VARCHAR(30)",
                "complemento": "VARCHAR(120)",
                "bairro": "VARCHAR(120)",
                "cidade": "VARCHAR(120)",
                "endereco_uf": "VARCHAR(2)",
            }
            for column_name, column_type in user_columns.items():
                if column_name not in columns:
                    connection.execute(text(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}"))
            connection.execute(
                text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_documento ON users (documento)")
            )
        if "doctors" in table_names:
            columns = {column["name"] for column in inspect(engine).get_columns("doctors")}
            doctor_columns = {
                "cfm_validated_at": "DATETIME",
                "cfm_validation_status": "VARCHAR(32)",
                "cfm_validation_reason": "VARCHAR(64)",
                "hospital": "VARCHAR(255)",
                "especialidade_atuacao": "VARCHAR(255)",
            }
            for column_name, column_type in doctor_columns.items():
                if column_name not in columns:
                    connection.execute(text(f"ALTER TABLE doctors ADD COLUMN {column_name} {column_type}"))
            connection.execute(
                text(
                    "UPDATE doctors SET cfm_validation_status = "
                    "CASE WHEN cfm_validated_at IS NULL THEN 'VALIDATION_PENDING' ELSE 'VALIDATED' END "
                    "WHERE cfm_validation_status IS NULL"
                )
            )


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    ensure_legacy_schema()


class UserCreate(BaseModel):
    nome: str
    email: str
    senha: str

    @field_validator("nome")
    @classmethod
    def validar_nome(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("nome nao pode ser vazio")
        return valor

    @field_validator("email")
    @classmethod
    def validar_email(cls, valor: str) -> str:
        valor = valor.strip().lower()
        if "@" not in valor or valor.startswith("@") or valor.endswith("@"):
            raise ValueError("email invalido")
        return valor

    @field_validator("senha")
    @classmethod
    def validar_senha(cls, valor: str) -> str:
        if len(valor) < 8:
            raise ValueError("senha deve ter pelo menos 8 caracteres")
        if len(valor) > 128:
            raise ValueError("senha deve ter no maximo 128 caracteres")
        return valor


class UserUpdate(BaseModel):
    """Senha vazia mantem a senha que ja esta cadastrada."""
    nome: str
    email: str
    senha: str | None = None
    _validar_nome = field_validator("nome")(UserCreate.validar_nome)
    _validar_email = field_validator("email")(UserCreate.validar_email)

    @field_validator("senha")
    @classmethod
    def validar_nova_senha(cls, valor: str | None) -> str | None:
        if valor is not None and valor != "" and len(valor) < 8:
            raise ValueError("senha deve ter pelo menos 8 caracteres")
        if valor is not None and len(valor) > 128:
            raise ValueError("senha deve ter no maximo 128 caracteres")
        return valor


class DoctorCreate(BaseModel):
    crm: str
    uf: str

    @field_validator("crm")
    @classmethod
    def validar_crm(cls, valor: str) -> str:
        valor = valor.strip()
        if not re.fullmatch(r"\d{1,7}", valor):
            raise ValueError("crm deve conter de 1 a 7 digitos numericos")
        return valor

    @field_validator("uf")
    @classmethod
    def validar_uf(cls, valor: str) -> str:
        valor = valor.strip().upper()
        if valor not in UFS_VALIDAS:
            raise ValueError("uf deve ser uma sigla de estado brasileiro valida")
        return valor


class UserRegistration(UserCreate):
    """Cadastro publico que cria usuario e medico na mesma transacao."""

    doctor: DoctorCreate | None = None


class Doctor(DoctorCreate):
    id: int
    user_id: int
    cfm_validated_at: datetime | None = None
    cfm_validation_status: str = "VALIDATION_PENDING"
    cfm_validation_reason: str | None = None
    hospital: str | None = None
    especialidade_atuacao: str | None = None
    model_config = ConfigDict(from_attributes=True)


class CFMValidationResult(BaseModel):
    valid: bool
    crm: str
    uf: str
    name: str | None = None
    status: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class CFMValidationOutcome:
    doctor: CFMDoctor | None
    pending_reason: str | None
    attempts: int


class DoctorUpdate(DoctorCreate):
    """Reutiliza as mesmas regras de CRM e UF no fluxo de edicao."""


class User(BaseModel):
    """Dados seguros retornados pela API: jamais inclui hash/senha."""
    id: int
    nome: str
    email: str
    doctor: Doctor | None = None
    model_config = ConfigDict(from_attributes=True)


class AdminLogin(BaseModel):
    usuario: str
    senha: str


class UserLogin(BaseModel):
    email: str
    senha: str

    @field_validator("email")
    @classmethod
    def normalizar_email(cls, valor: str) -> str:
        return UserCreate.validar_email(valor)

    @field_validator("senha")
    @classmethod
    def validar_tamanho_senha(cls, valor: str) -> str:
        if len(valor) > 128:
            raise ValueError("senha deve ter no maximo 128 caracteres")
        return valor


class DoctorProfessionalUpdate(BaseModel):
    hospital: str | None = None
    especialidade_atuacao: str | None = None

    @field_validator("hospital", "especialidade_atuacao", mode="before")
    @classmethod
    def limpar_campos(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        valor = valor.strip()
        if not valor:
            return None
        if len(valor) > 255:
            raise ValueError("campo deve ter no maximo 255 caracteres")
        return valor


class ProfileUpdate(BaseModel):
    nome: str
    email: str
    telefone: str | None = None
    documento: str | None = None
    data_nascimento: date | None = None
    escolaridade: str | None = None
    cep: str | None = None
    logradouro: str | None = None
    numero: str | None = None
    complemento: str | None = None
    bairro: str | None = None
    cidade: str | None = None
    endereco_uf: str | None = None
    doctor: DoctorProfessionalUpdate | None = None

    @field_validator("nome")
    @classmethod
    def validar_nome(cls, valor: str) -> str:
        return UserCreate.validar_nome(valor)

    @field_validator("email")
    @classmethod
    def validar_email(cls, valor: str) -> str:
        return UserCreate.validar_email(valor)

    @field_validator(
        "telefone", "documento", "escolaridade", "cep", "logradouro",
        "numero", "complemento", "bairro", "cidade", "endereco_uf",
        mode="before",
    )
    @classmethod
    def vazio_vira_nulo(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        valor = valor.strip()
        return valor or None

    @field_validator("telefone")
    @classmethod
    def validar_telefone(cls, valor: str | None) -> str | None:
        if valor and (len(valor) > 20 or not re.fullmatch(r"[0-9+() .-]{8,20}", valor)):
            raise ValueError("telefone invalido")
        return valor

    @field_validator("documento")
    @classmethod
    def validar_documento(cls, valor: str | None) -> str | None:
        if valor and not re.fullmatch(r"[0-9A-Za-z./ -]{5,32}", valor):
            raise ValueError("documento invalido")
        return valor.upper() if valor else None

    @field_validator("cep")
    @classmethod
    def validar_cep(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        digits = re.sub(r"\D", "", valor)
        if len(digits) != 8:
            raise ValueError("cep deve conter 8 digitos")
        return f"{digits[:5]}-{digits[5:]}"

    @field_validator("endereco_uf")
    @classmethod
    def validar_endereco_uf(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        valor = valor.upper()
        if valor not in UFS_VALIDAS:
            raise ValueError("UF de endereco invalida")
        return valor

    @field_validator("data_nascimento")
    @classmethod
    def validar_data_nascimento(cls, valor: date | None) -> date | None:
        if valor and valor > date.today():
            raise ValueError("data de nascimento nao pode estar no futuro")
        return valor

    @field_validator("escolaridade", "numero", "complemento", "bairro", "cidade")
    @classmethod
    def validar_campos_medios(cls, valor: str | None) -> str | None:
        if valor and len(valor) > 120:
            raise ValueError("campo deve ter no maximo 120 caracteres")
        return valor

    @field_validator("logradouro")
    @classmethod
    def validar_logradouro(cls, valor: str | None) -> str | None:
        if valor and len(valor) > 255:
            raise ValueError("logradouro deve ter no maximo 255 caracteres")
        return valor


class UserProfile(BaseModel):
    id: int
    nome: str
    email: str
    telefone: str | None = None
    documento: str | None = None
    data_nascimento: date | None = None
    escolaridade: str | None = None
    cep: str | None = None
    logradouro: str | None = None
    numero: str | None = None
    complemento: str | None = None
    bairro: str | None = None
    cidade: str | None = None
    endereco_uf: str | None = None
    doctor: Doctor | None = None
    model_config = ConfigDict(from_attributes=True)


class PasswordChange(BaseModel):
    senha_atual: str
    nova_senha: str

    @field_validator("senha_atual", "nova_senha")
    @classmethod
    def validar_senhas(cls, valor: str, info) -> str:
        if info.field_name == "nova_senha" and len(valor) < 8:
            raise ValueError("nova senha deve ter pelo menos 8 caracteres")
        if len(valor) > 128:
            raise ValueError("senha deve ter no maximo 128 caracteres")
        return valor


def exigir_admin(request: Request) -> None:
    if not request.session.get("admin"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Acesso de administrador necessario")


def exigir_usuario(request: Request, db: Session = Depends(get_db)) -> UserModel:
    user_id = request.session.get("user_id")
    if not isinstance(user_id, int):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login de usuario necessario")
    usuario = db.get(UserModel, user_id)
    if usuario is None:
        request.session.clear()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessao de usuario invalida")
    return usuario


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return max(0, int(os.getenv(name, str(default))))
    except ValueError:
        return default


_cfm_client = CFMClient(
    timeout_seconds=_env_float("CFM_PLAYWRIGHT_TIMEOUT_SECONDS", 120),
    browser_channel=os.getenv("CFM_BROWSER_CHANNEL", "chrome"),
    browser_path=os.getenv("CFM_BROWSER_PATH"),
    cache_ttl_seconds=_env_float("CFM_CACHE_TTL_SECONDS", 3600),
    min_request_interval_seconds=_env_float("CFM_MIN_REQUEST_INTERVAL_SECONDS", 3),
)
CFM_RETRY_COUNT = _env_int("CFM_RETRY_COUNT", 2)
CFM_RETRY_DELAY_SECONDS = _env_float("CFM_RETRY_DELAY_SECONDS", 0)


def get_cfm_client() -> CFMClient:
    """Dependencia substituivel nos testes, sem chamadas reais ao CFM."""
    return _cfm_client


def validar_medico_no_cfm(cfm_client: CFMClient, dados: DoctorCreate) -> CFMValidationOutcome:
    try:
        for attempt in range(1, CFM_RETRY_COUNT + 2):
            try:
                return CFMValidationOutcome(
                    doctor=cfm_client.find_doctor(dados.crm, dados.uf),
                    pending_reason=None,
                    attempts=attempt,
                )
            except (CFMUnavailable, CFMValidationTimeout) as error:
                if attempt == CFM_RETRY_COUNT + 1:
                    reason = "VALIDATION_TIMEOUT" if isinstance(error, CFMValidationTimeout) else "CFM_UNAVAILABLE"
                    return CFMValidationOutcome(doctor=None, pending_reason=reason, attempts=attempt)
                if CFM_RETRY_DELAY_SECONDS > 0:
                    time.sleep(CFM_RETRY_DELAY_SECONDS * attempt)
    except CFMInvalidInput as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "INVALID_INPUT", "message": "CRM ou UF invalido"},
        ) from error
    except CFMDoctorNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "CRM_NOT_FOUND", "message": "CRM nao encontrado no CFM"},
        ) from error
    except CFMDoctorInactive as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "CRM_INACTIVE",
                "message": "O CRM nao esta ativo no CFM",
                "name": error.doctor.nome,
                "status": error.doctor.situacao.upper(),
            },
        ) from error
    except CFMConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "CFM_CONFIGURATION", "message": "A integracao com o CFM nao esta disponivel"},
        ) from error


def aplicar_resultado_validacao(
    medico: DoctorModel,
    dados: DoctorCreate,
    outcome: CFMValidationOutcome,
) -> None:
    medico.crm = dados.crm
    medico.uf = dados.uf
    medico.cfm_validation_status = "VALIDATION_PENDING" if outcome.pending_reason else "VALIDATED"
    medico.cfm_validation_reason = outcome.pending_reason
    medico.cfm_validated_at = None if outcome.pending_reason else datetime.now(timezone.utc)


@app.get("/")
def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/login")
def user_login_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/conta", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request=request, name="user_login.html")


@app.post("/login", status_code=status.HTTP_204_NO_CONTENT)
def user_login(dados: UserLogin, request: Request, db: Session = Depends(get_db)) -> Response:
    usuario = db.query(UserModel).filter(func.lower(UserModel.email) == dados.email).first()
    if usuario is None or not verify_password(dados.senha, usuario.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email ou senha invalidos")
    request.session.clear()
    request.session["user_id"] = usuario.id
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/conta")
def user_account_page(request: Request):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request=request, name="profile.html")


@app.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def user_logout(request: Request, _: UserModel = Depends(exigir_usuario)) -> Response:
    request.session.clear()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/me", response_model=UserProfile)
def get_my_profile(usuario: UserModel = Depends(exigir_usuario)) -> UserModel:
    return usuario


@app.put("/me", response_model=UserProfile)
def update_my_profile(
    dados: ProfileUpdate,
    usuario: UserModel = Depends(exigir_usuario),
    db: Session = Depends(get_db),
) -> UserModel:
    email_owner = (
        db.query(UserModel)
        .filter(func.lower(UserModel.email) == dados.email, UserModel.id != usuario.id)
        .first()
    )
    if email_owner is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email ja cadastrado")

    if dados.documento:
        document_owner = (
            db.query(UserModel)
            .filter(UserModel.documento == dados.documento, UserModel.id != usuario.id)
            .first()
        )
        if document_owner is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Documento ja cadastrado")

    if dados.doctor is not None and usuario.doctor is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Campos profissionais sao exclusivos para medicos",
        )

    profile_fields = (
        "nome", "email", "telefone", "documento", "data_nascimento",
        "escolaridade", "cep", "logradouro", "numero", "complemento",
        "bairro", "cidade", "endereco_uf",
    )
    for field_name in profile_fields:
        setattr(usuario, field_name, getattr(dados, field_name))

    if dados.doctor is not None:
        usuario.doctor.hospital = dados.doctor.hospital
        usuario.doctor.especialidade_atuacao = dados.doctor.especialidade_atuacao

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email ou documento ja cadastrado",
        ) from error
    db.refresh(usuario)
    return usuario


@app.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_my_password(
    dados: PasswordChange,
    usuario: UserModel = Depends(exigir_usuario),
    db: Session = Depends(get_db),
) -> Response:
    if not verify_password(dados.senha_atual, usuario.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Senha atual incorreta")
    if hmac.compare_digest(dados.senha_atual, dados.nova_senha):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="A nova senha deve ser diferente")
    usuario.password_hash = hash_password(dados.nova_senha)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/me/doctor/revalidate", response_model=Doctor)
def revalidate_my_doctor(
    response: Response,
    usuario: UserModel = Depends(exigir_usuario),
    db: Session = Depends(get_db),
    cfm_client: CFMClient = Depends(get_cfm_client),
) -> Doctor:
    if usuario.doctor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cadastro medico nao encontrado")

    dados = DoctorCreate(crm=usuario.doctor.crm, uf=usuario.doctor.uf)
    outcome = validar_medico_no_cfm(cfm_client, dados)
    aplicar_resultado_validacao(usuario.doctor, dados, outcome)
    db.commit()
    db.refresh(usuario.doctor)
    if outcome.pending_reason:
        response.status_code = status.HTTP_202_ACCEPTED
    return usuario.doctor


@app.get("/admin")
def admin(request: Request):
    if not request.session.get("admin"):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request=request, name="admin.html")


@app.get("/admin/login")
def admin_login_page(request: Request):
    if request.session.get("admin"):
        return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request=request, name="admin_login.html")


@app.post("/admin/login", status_code=status.HTTP_204_NO_CONTENT)
def admin_login(dados: AdminLogin, request: Request) -> Response:
    # O nome de usuario nao diferencia maiusculas de minusculas.
    user_ok = hmac.compare_digest(dados.usuario.strip().casefold(), ADMIN_USERNAME.strip().casefold())
    password_ok = hmac.compare_digest(dados.senha, ADMIN_PASSWORD)
    if not (user_ok and password_ok):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais invalidas")
    request.session.clear()
    request.session["admin"] = True
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/admin/logout", status_code=status.HTTP_204_NO_CONTENT)
def admin_logout(request: Request, _: None = Depends(exigir_admin)) -> Response:
    request.session.clear()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "message": "Hello World"}


@app.post("/cfm/validate", response_model=CFMValidationResult)
def validar_crm_no_cfm(
    dados: DoctorCreate,
    cfm_client: CFMClient = Depends(get_cfm_client),
) -> CFMValidationResult:
    """Permite testar a validacao sem criar ou alterar um usuario."""
    try:
        outcome = validar_medico_no_cfm(cfm_client, dados)
    except HTTPException as error:
        detail = error.detail if isinstance(error.detail, dict) else {}
        reason = detail.get("code", "CFM_UNAVAILABLE")
        if reason == "CFM_CONFIGURATION":
            reason = "CFM_UNAVAILABLE"
        return CFMValidationResult(
            valid=False,
            crm=dados.crm,
            uf=dados.uf,
            name=detail.get("name"),
            status=detail.get("status"),
            reason=reason,
        )

    if outcome.pending_reason:
        return CFMValidationResult(valid=False, crm=dados.crm, uf=dados.uf, reason=outcome.pending_reason)
    return CFMValidationResult(
        valid=True,
        crm=dados.crm,
        uf=dados.uf,
        name=outcome.doctor.nome,
        status="ATIVO",
    )


@app.post("/users", response_model=User, status_code=status.HTTP_201_CREATED)
def criar_usuario(
    dados: UserRegistration,
    response: Response,
    db: Session = Depends(get_db),
    cfm_client: CFMClient = Depends(get_cfm_client),
) -> User:
    if db.query(UserModel).filter(UserModel.email == dados.email).first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email ja cadastrado")

    outcome = None
    # Erro definitivo nao deixa cadastro parcial; erro temporario fica pendente.
    if dados.doctor is not None:
        outcome = validar_medico_no_cfm(cfm_client, dados.doctor)

    usuario = UserModel(nome=dados.nome, email=dados.email, password_hash=hash_password(dados.senha))
    if dados.doctor is not None:
        usuario.doctor = DoctorModel()
        aplicar_resultado_validacao(usuario.doctor, dados.doctor, outcome)
    db.add(usuario)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email ja cadastrado")
    db.refresh(usuario)
    if outcome is not None and outcome.pending_reason:
        response.status_code = status.HTTP_202_ACCEPTED
    return usuario


@app.get("/users", response_model=list[User], dependencies=[Depends(exigir_admin)])
def listar_usuarios(db: Session = Depends(get_db)) -> list[User]:
    return db.query(UserModel).order_by(UserModel.id).all()


@app.get("/users/{user_id}", response_model=User, dependencies=[Depends(exigir_admin)])
def consultar_usuario(user_id: int, db: Session = Depends(get_db)) -> User:
    usuario = db.get(UserModel, user_id)
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado")
    return usuario


@app.put("/users/{user_id}", response_model=User, dependencies=[Depends(exigir_admin)])
def editar_usuario(user_id: int, dados: UserUpdate, db: Session = Depends(get_db)) -> User:
    usuario = db.get(UserModel, user_id)
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado")
    usuario.nome = dados.nome
    usuario.email = dados.email
    if dados.senha:
        usuario.password_hash = hash_password(dados.senha)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email ja cadastrado")
    db.refresh(usuario)
    return usuario


@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(exigir_admin)])
def excluir_usuario(user_id: int, db: Session = Depends(get_db)) -> Response:
    usuario = db.get(UserModel, user_id)
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado")
    db.delete(usuario)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/users/{user_id}/doctor", response_model=Doctor, status_code=status.HTTP_201_CREATED)
def criar_medico(
    user_id: int,
    dados: DoctorCreate,
    response: Response,
    db: Session = Depends(get_db),
    cfm_client: CFMClient = Depends(get_cfm_client),
) -> Doctor:
    usuario = db.get(UserModel, user_id)
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado")
    if usuario.doctor is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Usuario ja e medico")
    outcome = validar_medico_no_cfm(cfm_client, dados)
    medico = DoctorModel(user_id=user_id)
    aplicar_resultado_validacao(medico, dados, outcome)
    db.add(medico)
    db.commit()
    db.refresh(medico)
    if outcome.pending_reason:
        response.status_code = status.HTTP_202_ACCEPTED
    return medico


@app.put("/users/{user_id}/doctor", response_model=Doctor, dependencies=[Depends(exigir_admin)])
def editar_medico(
    user_id: int,
    dados: DoctorUpdate,
    response: Response,
    db: Session = Depends(get_db),
    cfm_client: CFMClient = Depends(get_cfm_client),
) -> Doctor:
    """Atualiza CRM e UF de um medico, aplicando as validacoes da Missao 06."""
    usuario = db.get(UserModel, user_id)
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado")
    if usuario.doctor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cadastro medico nao encontrado")

    outcome = validar_medico_no_cfm(cfm_client, dados)
    aplicar_resultado_validacao(usuario.doctor, dados, outcome)
    db.commit()
    db.refresh(usuario.doctor)
    if outcome.pending_reason:
        response.status_code = status.HTTP_202_ACCEPTED
    return usuario.doctor
