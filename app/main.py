import os
from hmac import compare_digest
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr, StringConstraints, TypeAdapter, ValidationError, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from starlette.middleware.sessions import SessionMiddleware

from app.database import get_db
from app.models import Doctor, User

BASE_DIR = Path(__file__).resolve().parent


def required_setting(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} não foi definida no arquivo .env")
    return value


app = FastAPI(title="Novo usuário do projeto")
app.add_middleware(
    SessionMiddleware,
    secret_key=required_setting("SESSION_SECRET"),
    same_site="lax",
)
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# strip_whitespace tira os espacos das pontas antes de medir o tamanho:
# assim "   " nao passa como nome valido.
Nome = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=80)]
CRM = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
UF = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=2, to_upper=True)]
email_validator = TypeAdapter(EmailStr)


class UserIn(BaseModel):
    """O que o cliente envia no POST. Sem `id`: quem decide o id e o servidor."""

    nome: Nome
    email: str

    @field_validator("email", mode="before")
    @classmethod
    def validar_email(cls, value: str) -> str:
        if value is None or not isinstance(value, str):
            raise ValueError("EMAIL NÃO É VÁLIDO")

        valor = value.strip()
        try:
            email_validator.validate_python(valor)
        except ValidationError as exc:
            raise ValueError("EMAIL NÃO É VÁLIDO") from exc
        return valor.lower()


class DoctorIn(BaseModel):
    """Dados profissionais do perfil médico; as regras de negócio entram na missão 06."""

    crm: CRM
    uf: UF


class DoctorRegistrationIn(BaseModel):
    """Cadastro conjunto que evidencia a relação entre usuário e médico."""

    user: UserIn
    doctor: DoctorIn


class AdminLogin(BaseModel):
    nome: str
    senha: str


def require_admin(request: Request) -> None:
    """Impede que visitantes consultem ou alterem os cadastros."""
    admin_name = required_setting("ADMIN_NAME")
    if request.session.get("admin") != admin_name:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Acesso de administrador necessário")


def user_with_doctor_dict(user: User) -> dict:
    return {
        **user.to_dict(),
        "doctor": user.doctor.to_dict() if user.doctor else None,
    }


def ensure_doctor_is_available(
    novo: DoctorIn,
    db: Session,
    ignore_doctor_id: int | None = None,
) -> None:
    doctor = db.scalar(select(Doctor).where(Doctor.crm == novo.crm, Doctor.uf == novo.uf))
    if doctor and doctor.id != ignore_doctor_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"O CRM {novo.crm}/{novo.uf} já está cadastrado",
        )


@app.get("/health")
def health() -> dict[str, str]:
    """Endpoint JSON: e daqui que o HTML busca a mensagem."""
    return {"status": "ok", "message": "Hello World"}


@app.get("/users")
def list_users(
    nome: str | None = None,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> list[dict]:
    """Lista cadastros somente para o administrador."""
    statement = select(User).options(selectinload(User.doctor)).order_by(User.id)
    if nome is not None:
        statement = statement.where(User.nome.ilike(f"%{nome}%"))
    return [user_with_doctor_dict(user) for user in db.scalars(statement)]


@app.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(novo: UserIn, db: Session = Depends(get_db)) -> dict:
    """Cadastra um usuario. Devolve 201 com o usuario criado, ja com o id."""
    email = novo.email.lower()

    user = User(nome=novo.nome, email=email)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"O e-mail {email} já está cadastrado",
        )

    db.refresh(user)
    return user.to_dict()


@app.post("/registrations", status_code=status.HTTP_201_CREATED)
def create_doctor_registration(novo: DoctorRegistrationIn, db: Session = Depends(get_db)) -> dict:
    """Cria usuário e perfil médico juntos, na mesma transação."""
    if db.scalar(select(User).where(User.email == novo.user.email)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"O e-mail {novo.user.email} já está cadastrado",
        )
    ensure_doctor_is_available(novo.doctor, db)

    user = User(
        nome=novo.user.nome,
        email=novo.user.email,
        doctor=Doctor(crm=novo.doctor.crm, uf=novo.doctor.uf),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Não foi possível concluir: e-mail ou CRM já cadastrado",
        )

    db.refresh(user)
    return user_with_doctor_dict(user)


@app.put("/registrations/{user_id}")
def update_doctor_registration(
    user_id: int,
    novo: DoctorRegistrationIn,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> dict:
    """Atualiza os dados do usuário e do médico na mesma transação."""
    user = db.scalar(
        select(User).options(selectinload(User.doctor)).where(User.id == user_id)
    )
    if not user:
        raise HTTPException(status_code=404, detail=f"Usuário {user_id} não encontrado")

    email_owner = db.scalar(
        select(User).where(User.email == novo.user.email, User.id != user_id)
    )
    if email_owner:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"O e-mail {novo.user.email} já está cadastrado",
        )

    doctor_id = user.doctor.id if user.doctor else None
    ensure_doctor_is_available(novo.doctor, db, ignore_doctor_id=doctor_id)
    user.nome = novo.user.nome
    user.email = novo.user.email
    if user.doctor:
        user.doctor.crm = novo.doctor.crm
        user.doctor.uf = novo.doctor.uf
    else:
        user.doctor = Doctor(crm=novo.doctor.crm, uf=novo.doctor.uf)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Não foi possível atualizar: e-mail ou CRM já cadastrado",
        )

    db.refresh(user)
    return user_with_doctor_dict(user)


@app.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db), _: None = Depends(require_admin)) -> dict:
    """Busca um usuario pelo id. Devolve 404 se ele nao existir."""
    user = db.get(User, user_id)
    if user:
        return user.to_dict()

    raise HTTPException(status_code=404, detail=f"Usuário {user_id} não encontrado")


@app.post("/users/{user_id}/doctor", status_code=status.HTTP_201_CREATED)
def create_doctor_profile(
    user_id: int,
    novo: DoctorIn,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> dict:
    """Associa um perfil médico a um usuário que ainda não possui um."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"Usuário {user_id} não encontrado")
    if user.doctor:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Usuário {user_id} já possui perfil médico",
        )
    ensure_doctor_is_available(novo, db)

    doctor = Doctor(user=user, crm=novo.crm, uf=novo.uf)
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
    user_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> dict:
    """Consulta o perfil médico relacionado ao usuário."""
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
    _: None = Depends(require_admin),
) -> dict:
    """Atualiza CRM e UF de um perfil médico existente."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"Usuário {user_id} não encontrado")
    if not user.doctor:
        raise HTTPException(status_code=404, detail=f"Usuário {user_id} não possui perfil médico")

    ensure_doctor_is_available(novos_dados, db, ignore_doctor_id=user.doctor.id)
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
    _: None = Depends(require_admin),
) -> dict:
    """Substitui nome e e-mail de um usuário existente."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"Usuário {user_id} não encontrado")

    user.nome = novos_dados.nome
    user.email = novos_dados.email
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"O e-mail {novos_dados.email} já está cadastrado",
        )

    db.refresh(user)
    return user.to_dict()


@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int, db: Session = Depends(get_db), _: None = Depends(require_admin)
) -> Response:
    """Remove um usuário. Repetir a chamada mantém o mesmo resultado (204)."""
    user = db.get(User, user_id)
    if user:
        db.delete(user)
        db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/admin/login")
def admin_login(credenciais: AdminLogin, request: Request) -> dict[str, str]:
    """Inicia a sessão do administrador para a demonstração local."""
    admin_name = required_setting("ADMIN_NAME")
    admin_password = required_setting("ADMIN_PASSWORD")
    if not (
        compare_digest(credenciais.nome, admin_name)
        and compare_digest(credenciais.senha, admin_password)
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Nome ou senha inválidos")

    request.session["admin"] = admin_name
    return {"message": "Login realizado"}


@app.post("/admin/logout")
def admin_logout(request: Request) -> Response:
    request.session.clear()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/")
def index(request: Request):
    """Tela pública: somente para envio de novos cadastros."""
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/admin")
def admin_page(request: Request):
    """Tela de login e aprovação de cadastros."""
    return templates.TemplateResponse(request=request, name="admin.html")
