from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="User Manager")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Enquanto nao existe banco (missao 03), os usuarios moram aqui.
# Este dicionario e apenas um armazenamento em memoria.
USUARIOS = [
    {"id": 1, "nome": "Ademilson Alves", "email": "ademilson@example.com"},
    {"id": 2, "nome": "Seabra", "email": "seabra@example.com"},
    {"id": 3, "nome": "Pagliasse", "email": "pagliasse@example.com"},
    {"id": 4, "nome": "Santana", "email": "Santana@example.com"},
]


class UserCreate(BaseModel):
    """Modelo de dados que o cliente envia para cadastrar um usuario."""
    nome: str
    email: str


class User(UserCreate):
    """Modelo de dados retornado pela API quando um usuario e criado."""
    id: int


@app.get("/health")
def health() -> dict[str, str]:
    """Endpoint JSON: e daqui que o HTML busca a mensagem."""
    return {"status": "ok", "message": "Hello World"}


@app.get("/users")
def listar_usuarios() -> list[User]:
    """Lista os usuarios cadastrados."""
    return USUARIOS


@app.post("/users", response_model=User, status_code=201)
def criar_usuario(dados: UserCreate) -> User:
    """Cria um novo usuario na lista em memoria."""
    proximo_id = max((usuario["id"] for usuario in USUARIOS), default=0) + 1
    usuario = {"id": proximo_id, "nome": dados.nome, "email": dados.email}
    USUARIOS.append(usuario)
    return usuario


@app.get("/")
def index(request: Request):
    """A tela. Busca os usuarios na API e mostra o formulario."""
    return templates.TemplateResponse(request=request, name="index.html")
