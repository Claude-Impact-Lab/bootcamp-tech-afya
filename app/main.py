from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="User Manager")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

#Base de dados de mentira: uma lista na memória.
#Quando o servidor reinicia , volta pro estado original - e isso é esperado.

usuarios = [
    {"id": 1, "nome": "Yuri Mestre", "email": "yuri@example.com"},
    {"id": 2, "nome": "Torres Diamante", "email": "torres@macbook.com"},
    {"id": 3, "nome": "Daniel Mestre", "email": "daniel@example.com"}
]

@app.get("/health")
def health() -> dict[str, str]:
    """Endpoint JSON: e daqui que o HTML busca a mensagem."""
    return {"status": "ok", "message": "Hello World"}

@app.get("/users")
def listar_usuarios() -> list[dict]:
    """Endpoint JSON: lista todos os usuários.

    Lista vazia nao e erro: devolve 200 com [] e quem chama decide o que mostrar.
    """
    return usuarios


@app.get("/")
def index(request: Request):
    """A tela. Os nomes nao vem daqui - o HTML busca em /users."""
    return templates.TemplateResponse(request=request, name="index.html")
