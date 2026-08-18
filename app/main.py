"""
Aplicação FastAPI mínima com duas rotas:
- GET /health: retorna JSON com status da aplicação
- GET /: retorna página HTML que fetcha a mensagem da API
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
