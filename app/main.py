"""
Aplicação FastAPI com persistência em PostgreSQL:
- GET /health: retorna JSON com status da aplicação
- GET /: retorna página HTML que fetcha a mensagem da API
- GET /users: retorna lista de usuários do banco de dados
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from app.database import engine, SessionLocal, Base
from app.models import User

# Configuração de diretórios
BASE_DIR = Path(__file__).resolve().parent

# Inicializar aplicação FastAPI
app = FastAPI(
    title="User Manager",
    description="Aplicação com persistência em PostgreSQL",
    version="0.1.0",
)

# Configurar templates (para renderizar HTML)
templates = Jinja2Templates(directory=BASE_DIR / "templates")


class UserUpdate(BaseModel):
    """Dados permitidos para substituir um usuário existente."""

    name: str
    email: str


# Criar tabelas no banco de dados (se não existirem)
# NOTA: No localhost, você precisa ter PostgreSQL rodando
# em testes, o conftest.py cria as tabelas no SQLite em memória
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    # Em testes ou sem PostgreSQL, a tabela pode não existir ainda
    # Mas isso é ok - os testes criam em memória
    print(f"Aviso: não foi possível criar tabelas no startup: {e}")


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
def get_users():
    """
    Retorna a lista de todos os usuários cadastrados no banco de dados.
    
    Usa SQLAlchemy para consultar a tabela 'users' no PostgreSQL.
    Cada objeto User retornado é convertido para dict (JSON) automaticamente.
    
    Returns:
        list[User]: Lista de usuários do banco de dados
        
    Nota: O FastAPI converte automaticamente objetos SQLAlchemy para JSON
    """
    # Criar uma sessão (transação) com o banco de dados
    db = SessionLocal()

    try:
        # Consultar todos os usuários da tabela
        usuarios = db.query(User).all()
        return usuarios
    finally:
        # Importante: sempre fechar a sessão para liberar recursos
        db.close()


@app.put("/users/{user_id}", tags=["Users"])
def update_user(user_id: int, user_data: UserUpdate):
    """Atualiza o nome e o email de um usuário existente."""
    db = SessionLocal()

    try:
        usuario = db.query(User).filter(User.id == user_id).first()
        if usuario is None:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")

        usuario.name = user_data.name
        usuario.email = user_data.email
        db.commit()
        db.refresh(usuario)
        return usuario
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email já está em uso")
    finally:
        db.close()


@app.delete("/users/{user_id}", tags=["Users"])
def delete_user(user_id: int):
    """Exclui um usuário existente."""
    db = SessionLocal()

    try:
        usuario = db.query(User).filter(User.id == user_id).first()
        if usuario is None:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")

        db.delete(usuario)
        db.commit()
        return {"message": "Usuário excluído com sucesso"}
    finally:
        db.close()

