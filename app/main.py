from pathlib import Path

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal, engine
from app.models import Base, Usuario

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="User Manager")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

Base.metadata.create_all(bind=engine)


class UsuarioCreate(BaseModel):
    nome: str
    email: EmailStr


class UsuarioOut(BaseModel):
    id: int
    nome: str
    email: EmailStr

    class Config:
        orm_mode = True


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health")
def health() -> dict[str, str]:
    """Endpoint JSON: e daqui que o HTML busca a mensagem."""
    return {"status": "ok", "message": "Hello World"}


@app.get("/users", response_model=list[UsuarioOut])
def listar_usuarios(db: Session = Depends(get_db)) -> list[Usuario]:
    """Devolve todos os usuarios cadastrados."""
    return db.query(Usuario).all()


@app.post("/users", status_code=201, response_model=UsuarioOut)
def criar_usuario(usuario: UsuarioCreate, db: Session = Depends(get_db)) -> Usuario:
    """Cria um novo usuario e o adiciona no fim da lista."""
    if db.query(Usuario).filter(Usuario.email == usuario.email).first():
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    novo_usuario = Usuario(nome=usuario.nome, email=usuario.email)
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)
    return novo_usuario


@app.get("/")
def index(request: Request):
    """A tela. Por enquanto so mostra o Hello World."""
    return templates.TemplateResponse(request=request, name="index.html")
