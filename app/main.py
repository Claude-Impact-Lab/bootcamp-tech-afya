from pathlib import Path

from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.schemas import UserCreate
from app.database import get_db
from app import models

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="User Manager")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.get("/health")
def health() -> dict[str, str]:
    """Endpoint JSON: e daqui que o HTML busca a mensagem."""
    return {"status": "ok", "message": "Hello World"}


@app.get("/users")
def listar_usuarios(db: Session = Depends(get_db)):
    return db.query(models.User).all()


@app.get("/")
def index(request: Request):
    """A tela. Os nomes nao vem daqui - o HTML busca em /users."""
    return templates.TemplateResponse(request=request, name="index.html")


@app.post("/users", status_code=status.HTTP_201_CREATED)
def criar_usuario(payload: UserCreate, db: Session = Depends(get_db)):
    """Cria um novo usuário validado por Pydantic.

    Valida o payload, previne emails duplicados e persiste
    o novo usuário no banco, retornando o recurso criado com `id`.
    """
    email_existente = db.query(models.User).filter(models.User.email == payload.email).first()
    if email_existente:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="E-mail já cadastrado")

    novo_usuario = models.User(nome=payload.nome, email=payload.email)
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)
    return novo_usuario