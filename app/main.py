from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="User Manager")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Enquanto nao existe banco (missao 03), os usuarios moram aqui.
USUARIOS = [
    {"id": 1, "nome": "Ademilson Alves", "email": "ademilson@example.com"},
    {"id": 2, "nome": "Maria Silva", "email": "maria@example.com"},
    {"id": 3, "nome": "Joao Souza", "email": "joao@example.com"},
]


@app.get("/health")
def health() -> dict[str, str]:
    """Endpoint JSON: e daqui que o HTML busca a mensagem."""
    return {"status": "ok", "message": "Hello World"}


@app.get("/users")
def listar_usuarios() -> list[dict]:
    """Lista os usuarios cadastrados.

    Sem nenhum usuario, devolve 200 com lista vazia: quem consome nao
    precisa tratar "vazio" como erro.
    """
    return USUARIOS


@app.get("/")
def index(request: Request):
    """A tela. Busca os usuarios na API e monta a lista."""
    return templates.TemplateResponse(request=request, name="index.html")
