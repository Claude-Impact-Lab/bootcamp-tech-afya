import base64
import hashlib
import hmac
import os
import re
import secrets
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
    """Acrescenta a coluna de senha em bancos SQLite criados antes desta versao."""
    if not str(engine.url).startswith("sqlite") or "users" not in inspect(engine).get_table_names():
        return
    columns = {column["name"] for column in inspect(engine).get_columns("users")}
    if "password_hash" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(512)"))


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
        if not re.fullmatch(r"\d{4,6}", valor):
            raise ValueError("crm deve conter de 4 a 6 digitos numericos")
        return valor

    @field_validator("uf")
    @classmethod
    def validar_uf(cls, valor: str) -> str:
        valor = valor.strip().upper()
        if valor not in UFS_VALIDAS:
            raise ValueError("uf deve ser uma sigla de estado brasileiro valida")
        return valor


class Doctor(DoctorCreate):
    id: int
    user_id: int
    model_config = ConfigDict(from_attributes=True)


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


@app.post("/users", response_model=User, status_code=status.HTTP_201_CREATED)
def criar_usuario(dados: UserCreate, db: Session = Depends(get_db)) -> User:
    usuario = UserModel(nome=dados.nome, email=dados.email, password_hash=hash_password(dados.senha))
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
def criar_medico(user_id: int, dados: DoctorCreate, db: Session = Depends(get_db)) -> Doctor:
    usuario = db.get(UserModel, user_id)
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado")
    if usuario.doctor is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Usuario ja e medico")
    medico = DoctorModel(user_id=user_id, crm=dados.crm, uf=dados.uf)
    db.add(medico)
    db.commit()
    db.refresh(medico)
    return medico


@app.put("/users/{user_id}/doctor", response_model=Doctor, dependencies=[Depends(exigir_admin)])
def editar_medico(user_id: int, dados: DoctorUpdate, db: Session = Depends(get_db)) -> Doctor:
    """Atualiza CRM e UF de um medico, aplicando as validacoes da Missao 06."""
    usuario = db.get(UserModel, user_id)
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado")
    if usuario.doctor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cadastro medico nao encontrado")

    usuario.doctor.crm = dados.crm
    usuario.doctor.uf = dados.uf
    db.commit()
    db.refresh(usuario.doctor)
    return usuario.doctor
