from pathlib import Path

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.templating import Jinja2Templates
from app.schemas import UserCreate

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="User Manager")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Base de dados de mentira: uma lista na memória.
# Quando o servidor reinicia, volta pro estado original - e isso é esperado.

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


@app.post("/users", status_code=status.HTTP_201_CREATED)
def criar_usuario(payload: UserCreate):
    """Cria um novo usuário validado por Pydantic.

    Valida o payload, previne emails duplicados e anexa o novo usuário
    na lista em memória retornando o recurso criado com `id`.
    """
    if any(u["email"] == payload.email for u in usuarios):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="E-mail já cadastrado")
    new_id = max((u["id"] for u in usuarios), default=0) + 1
    novo = {"id": new_id, "nome": payload.nome, "email": payload.email}
    usuarios.append(novo)
    return novo