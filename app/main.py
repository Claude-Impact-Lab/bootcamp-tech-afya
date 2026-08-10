from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="User Manager")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


# Enquanto nao existe banco, os usuarios moram aqui: uma lista em memoria.
# Ela volta ao estado original toda vez que o servidor reinicia.
USERS = [
    {"id": 1, "name": "Ada Lovelace"},
    {"id": 2, "name": "Alan Turing"},
]


@app.get("/health")
def health() -> dict[str, str]:
    """Endpoint JSON: e daqui que o HTML busca a mensagem."""
    return {"status": "ok", "message": "Hello World"}


@app.get("/users")
def list_users() -> list[dict]:
    """Lista os usuarios. Sem nenhum, devolve [] com status 200 — nao 404."""
    return USERS


@app.get("/")
def index(request: Request):
    """A tela. Por enquanto so mostra o Hello World."""
    return templates.TemplateResponse(request=request, name="index.html")
