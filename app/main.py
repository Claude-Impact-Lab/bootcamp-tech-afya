from pathlib import Path

from fastapi import FastAPI, Request, Depends
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db, engine
from app.models import User as UserModel, Base

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="User Manager")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.on_event("startup")
def startup():
    """Criar as tabelas no banco de dados (se não existirem)."""
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"⚠️  Aviso: Não foi possível criar tabelas no banco: {e}")
        print("   Tudo continua funcionando com SQLite local!")


class UserCreate(BaseModel):
    """Modelo de dados que o cliente envia para cadastrar um usuario."""
    nome: str
    email: str


class User(UserCreate):
    """Modelo de dados retornado pela API quando um usuario e criado."""
    id: int

    model_config = ConfigDict(from_attributes=True)


@app.get("/")
def index(request: Request):
    """Renderiza a página HTML."""
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/health")
def health() -> dict[str, str]:
    """Endpoint JSON: e daqui que o HTML busca a mensagem."""
    return {"status": "ok", "message": "Hello World"}


@app.get("/users")
def listar_usuarios(db: Session = Depends(get_db)) -> list[User]:
    """Lista os usuarios cadastrados no banco de dados."""
    usuarios = db.query(UserModel).all()
    return usuarios


@app.post("/users", response_model=User, status_code=201)
def criar_usuario(dados: UserCreate, db: Session = Depends(get_db)) -> User:
    """Cria um novo usuario no banco de dados."""
    usuario = UserModel(nome=dados.nome, email=dados.email)
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario
    return usuario


@app.get("/")
def index(request: Request):
    """A tela. Busca os usuarios na API e mostra o formulario."""
    return templates.TemplateResponse(request=request, name="index.html")
