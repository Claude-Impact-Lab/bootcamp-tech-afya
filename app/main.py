import base64
import hashlib
import hmac
import os
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import inspect, text
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
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def hash_password(password: str) -> str:
    """Gera um hash PBKDF2 com salt; a senha nunca e armazenada em texto puro."""
    salt = secrets.token_bytes(16)
    iterations = 210_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return "pbkdf2_sha256${}${}${}".format(iterations, base64.b64encode(salt).decode(), base64.b64encode(digest).decode())


def ensure_legacy_schema() -> None:
    """Acrescenta colunas em bancos SQLite locais criados em versoes anteriores."""
    if not str(engine.url).startswith("sqlite"):
        return
    table_names = inspect(engine).get_table_names()
    with engine.begin() as connection:
        if "users" in table_names:
            columns = {column["name"] for column in inspect(engine).get_columns("users")}
            if "password_hash" not in columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(512)"))
        if "doctors" in table_names:
            columns = {column["name"] for column in inspect(engine).get_columns("doctors")}
            if "cfm_validated_at" not in columns:
                connection.execute(text("ALTER TABLE doctors ADD COLUMN cfm_validated_at DATETIME"))


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
    model_config = ConfigDict(from_attributes=True)


class CFMValidationResult(BaseModel):
    valid: bool
    crm: str
    uf: str
    name: str | None = None
    status: str | None = None
    reason: str | None = None


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


def exigir_admin(request: Request) -> None:
    if not request.session.get("admin"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Acesso de administrador necessario")


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


_cfm_client = CFMClient(
    timeout_seconds=_env_float("CFM_PLAYWRIGHT_TIMEOUT_SECONDS", 120),
    browser_channel=os.getenv("CFM_BROWSER_CHANNEL", "chrome"),
    browser_path=os.getenv("CFM_BROWSER_PATH"),
    cache_ttl_seconds=_env_float("CFM_CACHE_TTL_SECONDS", 3600),
    min_request_interval_seconds=_env_float("CFM_MIN_REQUEST_INTERVAL_SECONDS", 3),
)


def get_cfm_client() -> CFMClient:
    """Dependencia substituivel nos testes, sem chamadas reais ao CFM."""
    return _cfm_client


def validar_medico_no_cfm(cfm_client: CFMClient, dados: DoctorCreate) -> CFMDoctor:
    try:
        return cfm_client.find_doctor(dados.crm, dados.uf)
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
            detail={"code": "CRM_INACTIVE", "message": "O CRM nao esta ativo no CFM"},
        ) from error
    except CFMValidationTimeout as error:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={"code": "VALIDATION_TIMEOUT", "message": "A validacao do CFM expirou"},
        ) from error
    except CFMUnavailable as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "CFM_UNAVAILABLE", "message": "Nao foi possivel checar o CFM agora"},
        ) from error
    except CFMConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "CFM_CONFIGURATION", "message": "A integracao com o CFM nao esta disponivel"},
        ) from error


@app.get("/")
def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


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
        doctor = cfm_client.find_doctor(dados.crm, dados.uf)
        return CFMValidationResult(
            valid=True,
            crm=dados.crm,
            uf=dados.uf,
            name=doctor.nome,
            status="ATIVO",
        )
    except CFMDoctorNotFound:
        return CFMValidationResult(valid=False, crm=dados.crm, uf=dados.uf, reason="CRM_NOT_FOUND")
    except CFMDoctorInactive as error:
        return CFMValidationResult(
            valid=False,
            crm=dados.crm,
            uf=dados.uf,
            name=error.doctor.nome,
            status=error.doctor.situacao.upper(),
            reason="CRM_INACTIVE",
        )
    except CFMValidationTimeout:
        return CFMValidationResult(valid=False, crm=dados.crm, uf=dados.uf, reason="VALIDATION_TIMEOUT")
    except (CFMUnavailable, CFMConfigurationError):
        return CFMValidationResult(valid=False, crm=dados.crm, uf=dados.uf, reason="CFM_UNAVAILABLE")
    except CFMInvalidInput:
        return CFMValidationResult(valid=False, crm=dados.crm, uf=dados.uf, reason="INVALID_INPUT")


@app.post("/users", response_model=User, status_code=status.HTTP_201_CREATED)
def criar_usuario(
    dados: UserRegistration,
    db: Session = Depends(get_db),
    cfm_client: CFMClient = Depends(get_cfm_client),
) -> User:
    if db.query(UserModel).filter(UserModel.email == dados.email).first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email ja cadastrado")

    # A consulta externa acontece antes de qualquer INSERT: erro nao deixa cadastro parcial.
    if dados.doctor is not None:
        validar_medico_no_cfm(cfm_client, dados.doctor)

    usuario = UserModel(nome=dados.nome, email=dados.email, password_hash=hash_password(dados.senha))
    if dados.doctor is not None:
        usuario.doctor = DoctorModel(
            crm=dados.doctor.crm,
            uf=dados.doctor.uf,
            cfm_validated_at=datetime.now(timezone.utc),
        )
    db.add(usuario)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email ja cadastrado")
    db.refresh(usuario)
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
    db: Session = Depends(get_db),
    cfm_client: CFMClient = Depends(get_cfm_client),
) -> Doctor:
    usuario = db.get(UserModel, user_id)
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado")
    if usuario.doctor is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Usuario ja e medico")
    validar_medico_no_cfm(cfm_client, dados)
    medico = DoctorModel(
        user_id=user_id,
        crm=dados.crm,
        uf=dados.uf,
        cfm_validated_at=datetime.now(timezone.utc),
    )
    db.add(medico)
    db.commit()
    db.refresh(medico)
    return medico


@app.put("/users/{user_id}/doctor", response_model=Doctor, dependencies=[Depends(exigir_admin)])
def editar_medico(
    user_id: int,
    dados: DoctorUpdate,
    db: Session = Depends(get_db),
    cfm_client: CFMClient = Depends(get_cfm_client),
) -> Doctor:
    """Atualiza CRM e UF de um medico, aplicando as validacoes da Missao 06."""
    usuario = db.get(UserModel, user_id)
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado")
    if usuario.doctor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cadastro medico nao encontrado")

    validar_medico_no_cfm(cfm_client, dados)
    usuario.doctor.crm = dados.crm
    usuario.doctor.uf = dados.uf
    usuario.doctor.cfm_validated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(usuario.doctor)
    return usuario.doctor
