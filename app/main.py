import hashlib
import hmac
import os
from datetime import datetime, timezone
from pathlib import Path
from secrets import token_hex, token_urlsafe

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator, model_validator
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.cfm import CFMClient, CFMUnavailableError, get_cfm_client
from app.models import Doctor, User

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="User Manager")
templates = Jinja2Templates(directory=BASE_DIR / "templates")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

EMAIL_SENDER = "resposta.noreply.2025@gmail.com"
ADMIN_USERNAME = "afya"
ADMIN_PASSWORD = "programação"
ADMIN_SESSION_SECRET = os.getenv("ADMIN_SESSION_SECRET", "chave-local-para-treinamento")
# Enquanto nao ha um provedor configurado, esta caixa registra os e-mails para
# testar o fluxo sem transmitir dados reais.
EMAIL_OUTBOX: list[dict[str, str]] = []


class UserCreate(BaseModel):
    """Dados que a API aceita para criar um usuário."""

    first_name: str | None = Field(default=None, min_length=2, max_length=50, examples=["Maria"])
    last_name: str | None = Field(default=None, min_length=2, max_length=50, examples=["Souza"])
    age: int | None = Field(default=None, ge=0, le=130, examples=[28])
    email: str | None = Field(
        default=None,
        min_length=5,
        max_length=100,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        examples=["maria.souza@exemplo.com"],
    )
    password: str | None = Field(default=None, min_length=8, max_length=128)
    password_confirmation: str | None = Field(default=None, min_length=8, max_length=128)

    @model_validator(mode="after")
    def validate_password_confirmation(self):
        if (self.password is None) != (self.password_confirmation is None):
            raise ValueError("Informe a senha e a confirmacao da senha.")
        if self.password is not None and self.password != self.password_confirmation:
            raise ValueError("As senhas nao conferem.")
        return self


class AdminLogin(BaseModel):
    username: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class UserUpdate(BaseModel):
    """Representacao completa dos dados editaveis pelo PUT."""

    name: str = Field(min_length=2, max_length=101)
    age: int | None = Field(default=None, ge=0, le=130)
    email: str | None = Field(
        default=None,
        min_length=5,
        max_length=100,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        name = value.strip()
        if len(name) < 2:
            raise ValueError("O nome deve ter pelo menos 2 caracteres.")
        return name


class DoctorCreate(BaseModel):
    """Dados profissionais validados pelas regras locais da missao 06."""

    crm: str = Field(min_length=1, max_length=20)
    uf: str = Field(min_length=2, max_length=2)
    specialty: str | None = Field(default=None, min_length=2, max_length=100)

    @field_validator("crm")
    @classmethod
    def validate_crm(cls, value: str) -> str:
        crm = value.strip()
        if not crm.isdecimal():
            raise ValueError("O CRM deve conter apenas numeros.")
        return crm

    @field_validator("uf")
    @classmethod
    def validate_uf(cls, value: str) -> str:
        uf = value.strip().upper()
        valid_ufs = {
            "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO",
            "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
            "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
        }
        if uf not in valid_ufs:
            raise ValueError("Informe uma UF brasileira valida.")
        return uf


def admin_session_value() -> str:
    return hmac.new(
        ADMIN_SESSION_SECRET.encode(), b"admin", hashlib.sha256
    ).hexdigest()


def is_admin(request: Request) -> bool:
    session = request.cookies.get("admin_session", "")
    return hmac.compare_digest(session, admin_session_value())


def send_confirmation_email(recipient: str, name: str, confirmation_link: str) -> None:
    """Adaptador temporário de e-mail para desenvolvimento local."""
    EMAIL_OUTBOX.append(
        {
            "from": EMAIL_SENDER,
            "to": recipient,
            "subject": "Confirme seu cadastro",
            "body": f"Olá, {name}! Confirme seu cadastro: {confirmation_link}",
        }
    )


def hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt), 200_000
    ).hex()


def verify_password(password: str, user: User) -> bool:
    saved_hash = user.password_hash
    salt = user.password_salt
    if not saved_hash or not salt:
        return False
    return hmac.compare_digest(hash_password(password, salt), saved_hash)


def public_user(user: User) -> dict:
    """Converte o modelo do banco sem expor campos secretos."""
    return {
        "id": user.id,
        "name": user.name,
        "age": user.age,
        "email": user.email,
        "email_confirmed": user.email_confirmed,
        "status": user.status,
    }


def public_doctor(doctor: Doctor) -> dict:
    return {
        "id": doctor.id,
        "user_id": doctor.user_id,
        "crm": doctor.crm,
        "uf": doctor.uf,
        "specialty": doctor.specialty,
        "cfm_validation_status": doctor.cfm_validation_status,
        "cfm_validated_at": doctor.cfm_validated_at,
        "cfm_name": doctor.cfm_name,
        "cfm_registration_status": doctor.cfm_registration_status,
        "cfm_registration_type": doctor.cfm_registration_type,
    }


def validate_doctor_with_cfm(doctor: Doctor, cfm: CFMClient) -> None:
    """Atualiza o medico sem impedir o cadastro quando o CFM estiver fora."""
    try:
        result = cfm.find_doctor(doctor.crm, doctor.uf)
    except CFMUnavailableError:
        doctor.cfm_validation_status = "VALIDATION_PENDING"
        return

    doctor.cfm_validated_at = datetime.now(timezone.utc)
    if not result.found:
        doctor.cfm_validation_status = "NOT_FOUND"
        return
    doctor.cfm_validation_status = "VALIDATED"
    doctor.cfm_name = result.name
    doctor.cfm_registration_status = result.registration_status
    doctor.cfm_registration_type = result.registration_type


@app.get("/health")
def health() -> dict[str, str]:
    """Endpoint JSON: e daqui que o HTML busca a mensagem."""
    return {"status": "ok", "message": "Hello World"}


@app.get("/users")
def list_users(request: Request, db: Session = Depends(get_db)) -> list[dict]:
    """Lista os usuarios. Sem nenhum cadastrado, devolve [] com status 200:
    a colecao existe, so esta vazia -- isso nao e um 404."""
    query = select(User).order_by(User.id)
    if not is_admin(request):
        query = query.where(User.status == "ativo")
    users = db.scalars(query).all()
    return [public_user(user) for user in users]


@app.put("/users/{user_id}")
def update_user(user_id: int, data: UserUpdate, db: Session = Depends(get_db)) -> dict:
    """Substitui os dados editaveis; repetir o mesmo PUT mantem o mesmo estado."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado.")

    user.name = data.name
    user.age = data.age
    user.email = data.email.casefold() if data.email else None
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este e-mail ja esta cadastrado.",
        )
    db.refresh(user)
    return public_user(user)


@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db)) -> Response:
    """Remove o usuario; repetir a exclusao continua produzindo ausencia."""
    user = db.get(User, user_id)
    if user is not None:
        db.delete(user)
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/doctors")
def list_doctors(db: Session = Depends(get_db)) -> list[dict]:
    doctors = db.scalars(select(Doctor).order_by(Doctor.id)).all()
    return [public_doctor(doctor) for doctor in doctors]


@app.post("/users/{user_id}/doctor", status_code=status.HTTP_201_CREATED)
def create_doctor(
    user_id: int,
    data: DoctorCreate,
    db: Session = Depends(get_db),
    cfm: CFMClient = Depends(get_cfm_client),
) -> dict:
    """Transforma o usuario em medico por uma relacao um-para-um."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado.")
    if user.doctor is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este usuario ja possui cadastro de medico.",
        )

    doctor = Doctor(
        user_id=user_id,
        crm=data.crm,
        uf=data.uf,
        specialty=data.specialty.strip() if data.specialty else None,
    )
    db.add(doctor)
    validate_doctor_with_cfm(doctor, cfm)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este CRM ja esta cadastrado nesta UF.",
        )
    db.refresh(doctor)
    return public_doctor(doctor)


@app.post("/doctors/{doctor_id}/validate-cfm")
def retry_cfm_validation(
    doctor_id: int,
    db: Session = Depends(get_db),
    cfm: CFMClient = Depends(get_cfm_client),
) -> dict:
    """Permite tentar novamente um cadastro que ficou pendente."""
    doctor = db.get(Doctor, doctor_id)
    if doctor is None:
        raise HTTPException(status_code=404, detail="Medico nao encontrado.")
    validate_doctor_with_cfm(doctor, cfm)
    db.commit()
    db.refresh(doctor)
    return public_doctor(doctor)


@app.get("/admin/session")
def admin_session(request: Request) -> dict[str, bool]:
    return {"is_admin": is_admin(request)}


@app.post("/admin/login")
def admin_login(credentials: AdminLogin, response: Response) -> dict[str, bool]:
    valid_credentials = secrets_compare(credentials.username, ADMIN_USERNAME) and secrets_compare(
        credentials.password, ADMIN_PASSWORD
    )
    if not valid_credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas.")

    response.set_cookie(
        key="admin_session",
        value=admin_session_value(),
        httponly=True,
        samesite="lax",
    )
    return {"is_admin": True}


@app.post("/admin/logout")
def admin_logout(response: Response) -> dict[str, bool]:
    response.delete_cookie("admin_session")
    return {"is_admin": False}


@app.post("/users/login")
def user_login(
    credentials: UserLogin,
    response: Response,
    db: Session = Depends(get_db),
) -> dict:
    user = db.scalar(
        select(User).where(func.lower(User.email) == credentials.email.casefold())
    )
    if user is None or not verify_password(credentials.password, user):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha invalidos.")
    if user.status != "ativo":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Confirme seu e-mail antes de entrar.")

    response.set_cookie(
        key="user_session",
        value=str(user.id),
        httponly=True,
        samesite="lax",
    )
    return {"message": f"Bem-vindo, {user.name}!", "user": public_user(user)}


def secrets_compare(value: str, expected: str) -> bool:
    return hmac.compare_digest(value.encode(), expected.encode())


@app.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(
    request: Request,
    user: UserCreate,
    db: Session = Depends(get_db),
) -> dict:
    """Cria um usuário em pré-cadastro.

    Dados incompletos ficam em pré-cadastro. Com todos os dados preenchidos,
    enviamos uma confirmação de e-mail antes de ativar o usuário.
    """
    complete_registration = all(
        value is not None
        for value in (user.first_name, user.last_name, user.age, user.email, user.password)
    )
    name = " ".join(part for part in (user.first_name, user.last_name) if part) or "Nome não informado"
    new_user = User(
        name=name,
        age=user.age,
        email=user.email.casefold() if user.email else None,
        email_confirmed=False,
        status="pre_cadastro",
    )
    if complete_registration:
        password_salt = token_hex(16)
        new_user.password_salt = password_salt
        new_user.password_hash = hash_password(user.password, password_salt)
        confirmation_token = token_urlsafe(32)
        new_user.confirmation_token = confirmation_token
        new_user.status = "aguardando_confirmacao_email"
        confirmation_link = f"{str(request.base_url).rstrip('/')}/users/confirm?token={confirmation_token}"
        send_confirmation_email(user.email, name, confirmation_link)

    db.add(new_user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este e-mail ja esta cadastrado.",
        )
    db.refresh(new_user)
    return public_user(new_user)


@app.get("/users/confirm")
def confirm_email(token: str, db: Session = Depends(get_db)) -> dict:
    """Confirma o e-mail e conclui o cadastro do usuário."""
    user = db.scalar(select(User).where(User.confirmation_token == token))
    if user is not None:
        user.email_confirmed = True
        user.status = "ativo"
        user.confirmation_token = None
        db.commit()
        db.refresh(user)
        return {"message": "E-mail confirmado. Cadastro concluído!", "user": public_user(user)}

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link de confirmação inválido ou expirado.")


@app.get("/")
def index(request: Request):
    """A tela. Por enquanto so mostra o Hello World."""
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/congratulations")
def congratulations(request: Request, name: str = ""):
    """Tela exibida depois que todas as etapas do cadastro forem preenchidas."""
    return templates.TemplateResponse(
        request=request,
        name="congratulations.html",
        context={"user_name": name.strip()},
    )
