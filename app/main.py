from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="User Manager")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Os usuarios moram aqui por enquanto. Somem quando o servidor reinicia:
# o banco de verdade entra na missao 03.
USERS = [
    {"id": 1, "nome": "Ana Souza", "email": "ana@exemplo.com"},
    {"id": 2, "nome": "Bruno Lima", "email": "bruno@exemplo.com"},
]


@app.get("/health")
def health() -> dict[str, str]:
    """Endpoint JSON: e daqui que o HTML busca a mensagem."""
    return {"status": "ok", "message": "Hello World"}


@app.get("/users")
def list_users(nome: str | None = None) -> list[dict]:
    """Lista os usuarios. Com ?nome=, devolve so quem tem esse texto no nome."""
    if nome is None:
        return USERS

    procurado = nome.lower()
    return [user for user in USERS if procurado in user["nome"].lower()]


@app.get("/users/{user_id}")
def get_user(user_id: int) -> dict:
    """Busca um usuario pelo id. Devolve 404 se ele nao existir."""
    for user in USERS:
        if user["id"] == user_id:
            return user

    raise HTTPException(status_code=404, detail=f"Usuário {user_id} não encontrado")


@app.get("/")
def index(request: Request):
    """A tela. Por enquanto so mostra o Hello World."""
    return templates.TemplateResponse(request=request, name="index.html")
