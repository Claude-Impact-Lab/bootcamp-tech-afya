"""
Aplicação FastAPI mínima com rotas:
- GET /health: retorna JSON com status da aplicação
- GET /: retorna página HTML que fetcha a mensagem da API
- GET /users: retorna lista de usuários em JSON
"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

# Configuração de diretórios
BASE_DIR = Path(__file__).resolve().parent

# Inicializar aplicação FastAPI
app = FastAPI(
    title="User Manager",
    description="Aplicação mínima para o bootcamp Afya",
    version="0.1.0",
)

# Configurar templates (para renderizar HTML)
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Base de dados de usuários (em memória - será substituído por banco de dados)
users_db = [
    {
        "id": 1,
        "name": "João Silva",
        "email": "joao.silva@example.com",
    },
    {
        "id": 2,
        "name": "Maria Santos",
        "email": "maria.santos@example.com",
    },
    {
        "id": 3,
        "name": "Pedro Oliveira",
        "email": "pedro.oliveira@example.com",
    },
]


@app.get("/health", tags=["Health"])
def health() -> dict[str, str]:
    """
    Endpoint de health check.
    
    Retorna o status da aplicação e uma mensagem que será exibida no frontend.
    Este endpoint é chamado via fetch() na página inicial.
    
    Returns:
        dict com status "ok" e message "Hello World"
    """
    return {
        "status": "ok",
        "message": "Hello World",
    }


@app.get("/", tags=["Pages"])
def index(request: Request):
    """
    Página inicial da aplicação.
    
    Renderiza o arquivo index.html que fará uma requisição ao /health
    para buscar a mensagem a ser exibida.
    
    Args:
        request: Objeto Request do FastAPI (necessário para Jinja2Templates)
    
    Returns:
        TemplateResponse com o HTML renderizado
    """
    return templates.TemplateResponse(
        request=request,
        name="index.html",
    )


@app.get("/users", tags=["Users"])
def get_users() -> list[dict]:
    """
    Retorna a lista de todos os usuários cadastrados.
    
    Esta é a primeira rota da API de usuários. Atualmente retorna
    uma lista em memória. Posteriormente será integrada a um banco de dados.
    
    Returns:
        list[dict]: Lista de dicionários com estrutura:
        {
            "id": int,
            "name": str,
            "email": str,
        }
    """
    return users_db
