from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="User Manager")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

USUARIOS = [
    {"id": 1, "nome": "André Seabra"},
    {"id": 2, "nome": "Ademilson Mamilo"},
    {"id": 3, "nome": "Sant'anna Thanos"},
]


@app.get("/health")
def health() -> dict[str, str]:
    """Endpoint JSON: e daqui que o HTML busca a mensagem."""
    return {"status": "ok", "message": "Hello World"}

@app.get("/users")
def listar_usuarios() -> list[dict[str, int | str]]:
    """Devolve todos os usuarios cadastrados."""
    return USUARIOS


@app.get("/")
def index(request: Request):
    """A tela. Por enquanto so mostra o Hello World."""
    return templates.TemplateResponse(request=request, name="index.html")
