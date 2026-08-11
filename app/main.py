from pathlib import Path

from fastapi import FastAPI, Request, status
from pydantic import BaseModel, Field
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="User Manager")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Ainda nao temos banco (isso e a missao 03), entao os usuarios moram aqui na
# memoria. Some quando o servidor reinicia -- e tudo bem por enquanto.
# "status" separa quem ja esta ativo de quem so fez o pre-cadastro.
USERS = [
    {"id": 1, "name": "Ana lucia", "status": "ativo"},
    {"id": 2, "name": "Bruna silva", "status": "pre_cadastro"},
    {"id": 3, "name": "Lucas Araujo", "status": "ativo"},
    {"id": 4, "name": "ronaldo silva", "status": "pre_cadastro"},
]


class UserCreate(BaseModel):
    """Dados que a API aceita para criar um usuário."""

    name: str = Field(min_length=3, max_length=100, examples=["Maria Souza"])


@app.get("/health")
def health() -> dict[str, str]:
    """Endpoint JSON: e daqui que o HTML busca a mensagem."""
    return {"status": "ok", "message": "Hello World"}


@app.get("/users")
def list_users() -> list[dict]:
    """Lista os usuarios. Sem nenhum cadastrado, devolve [] com status 200:
    a colecao existe, so esta vazia -- isso nao e um 404."""
    return USERS


@app.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate) -> dict:
    """Cria um usuário em pré-cadastro.

    O id e o status são definidos pela API; o cliente fornece apenas o nome.
    """
    next_id = max((registered_user["id"] for registered_user in USERS), default=0) + 1
    new_user = {"id": next_id, "name": user.name, "status": "pre_cadastro"}
    USERS.append(new_user)
    return new_user


@app.get("/")
def index(request: Request):
    """A tela. Por enquanto so mostra o Hello World."""
    return templates.TemplateResponse(request=request, name="index.html")
