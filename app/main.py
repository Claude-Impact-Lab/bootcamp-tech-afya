from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="User Manager")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


# Enquanto nao existe banco, os usuarios moram aqui: uma lista em memoria.
# Ela volta ao estado original toda vez que o servidor reinicia.
USERS = [
    {"id": 1, "name": "Ada Lovelace"},
    {"id": 2, "name": "Alan Turing"},
]


class UserCreate(BaseModel):
    name: str = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("name must not be empty")
        return normalized


@app.get("/health")
def health() -> dict[str, str]:
    """Endpoint JSON: e daqui que o HTML busca a mensagem."""
    return {"status": "ok", "message": "Hello World"}


@app.get("/users")
def list_users() -> list[dict]:
    """Lista os usuarios. Sem nenhum, devolve [] com status 200 — nao 404."""
    return USERS


@app.post("/users", status_code=201)
def create_user(user: UserCreate) -> dict[str, str | int]:
    """Cria um usuario com nome valido e proximo id disponivel."""
    next_id = max((u["id"] for u in USERS), default=0) + 1
    new_user = {"id": next_id, "name": user.name}
    USERS.append(new_user)
    return new_user


@app.get("/")
def index(request: Request):
    """A tela. Por enquanto so mostra o Hello World."""
    return templates.TemplateResponse(request=request, name="index.html")
