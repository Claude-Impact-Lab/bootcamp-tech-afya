from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr, StringConstraints, TypeAdapter, ValidationError, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Novo usuário do projeto")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# strip_whitespace tira os espacos das pontas antes de medir o tamanho:
# assim "   " nao passa como nome valido.
Nome = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=80)]
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


@app.get("/health")
def health() -> dict[str, str]:
    """Endpoint JSON: e daqui que o HTML busca a mensagem."""
    return {"status": "ok", "message": "Hello World"}


@app.get("/users")
def list_users(nome: str | None = None, db: Session = Depends(get_db)) -> list[dict]:
    """Lista os usuarios. Com ?nome=, devolve so quem tem esse texto no nome."""
    statement = select(User).order_by(User.id)
    if nome is not None:
        statement = statement.where(User.nome.ilike(f"%{nome}%"))
    return [user.to_dict() for user in db.scalars(statement)]


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


@app.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)) -> dict:
    """Busca um usuario pelo id. Devolve 404 se ele nao existir."""
    user = db.get(User, user_id)
    if user:
        return user.to_dict()

    raise HTTPException(status_code=404, detail=f"Usuário {user_id} não encontrado")


@app.get("/")
def index(request: Request):
    """A tela. Por enquanto so mostra o Hello World."""
    return templates.TemplateResponse(request=request, name="index.html")
