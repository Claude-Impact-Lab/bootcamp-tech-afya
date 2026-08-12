from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="User Manager")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

USUARIOS = [
    {"id": 1, "nome": "André Seabra", "email": "andre.seabra@teste.com"},
    {"id": 2, "nome": "Ademilson Mamilo", "email": "ademilson.mamilo@teste.com"},
    {"id": 3, "nome": "Sant'anna Thanos", "email": "santanna.thanos@teste.com"},
    {"id": 4, "nome": "Pagliasse Trepa", "email": "pagliasse.trepa@teste.com"},
]


class UsuarioCreate(BaseModel):
    nome: str
    email: EmailStr


@app.get("/health")
def health() -> dict[str, str]:
    """Endpoint JSON: e daqui que o HTML busca a mensagem."""
    return {"status": "ok", "message": "Hello World"}


@app.get("/users")
def listar_usuarios() -> list[dict[str, int | str]]:
    """Devolve todos os usuarios cadastrados."""
    return USUARIOS


@app.post("/users", status_code=201)
def criar_usuario(usuario: UsuarioCreate) -> dict[str, int | str]:
    """Cria um novo usuario e o adiciona no fim da lista."""
    novo_usuario = {
        "id": max((u["id"] for u in USUARIOS), default=0) + 1,
        "nome": usuario.nome,
        "email": usuario.email,
    }
    USUARIOS.append(novo_usuario)
    return novo_usuario


@app.get("/")
def index(request: Request):
    """A tela. Por enquanto so mostra o Hello World."""
    return templates.TemplateResponse(request=request, name="index.html")
