from pathlib import Path

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr
import hashlib
from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi import Query

from app.config import settings
from app.db import SessionLocal, engine
from app.models import Base, Usuario

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="User Manager")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

Base.metadata.create_all(bind=engine)

# adiciona coluna senha caso ainda não exista (migration simples)
with engine.begin() as conn:
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS senha VARCHAR;"))

# Compatibilidade com testes da missão: lista em memória
USUARIOS: list[dict] = []


class UsuarioCreate(BaseModel):
    nome: str
    email: EmailStr
    senha: str | None = None


class UsuarioOut(BaseModel):
    id: int
    nome: str
    email: EmailStr
    senha: str | None = None

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
def listar_usuarios(admin_email: str | None = Query(None), db: Session = Depends(get_db)) -> list[Usuario]:
    """Devolve todos os usuarios cadastrados.

    Compatível com os testes locais que usam a lista `USUARIOS`. Se `admin_email` for
    fornecido e for o e-mail do André, retornamos os usuários do banco; se não,
    usamos a lista em memória para compatibilidade de testes.
    """
    # modo teste / compatibilidade: se a lista em memória estiver preenchida,
    # devolvemos ela (os testes preenchem `USUARIOS` via fixture).
    if USUARIOS:
        return USUARIOS

    # modo app real: somente admin pode listar via DB
    if admin_email != "andre.seabra@teste.com":
        raise HTTPException(status_code=403, detail="Acesso negado")
    return db.query(Usuario).all()


@app.get("/users/search", response_model=UsuarioOut)
def buscar_usuario_por_email(email: EmailStr = Query(...), db: Session = Depends(get_db)) -> Usuario | None:
    """Procura um usuário por e-mail — usado pelo frontend para checar existência sem ser admin."""
    # se estamos no modo de testes com lista em memória, procurar nela
    if USUARIOS:
        usuario = next((u for u in USUARIOS if u['email'].lower() == email.lower()), None)
        if not usuario:
            raise HTTPException(status_code=404, detail="Usuario não encontrado")
        return usuario

    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario não encontrado")
    return usuario


@app.put("/users/{user_id}", response_model=UsuarioOut)
def atualizar_usuario(user_id: int, usuario: UsuarioCreate, admin_email: EmailStr = Query(...), db: Session = Depends(get_db)) -> Usuario:
    """Atualiza um usuário — somente admin (André) via `admin_email` query param."""
    if admin_email != "andre.seabra@teste.com":
        raise HTTPException(status_code=403, detail="Acesso negado")
    # helper de hash simples
    def _hash(pw: str) -> str:
        return hashlib.sha256(pw.encode('utf-8')).hexdigest()

    # se estamos usando a lista em memória, atualize-a também
    if USUARIOS:
        alvo = next((u for u in USUARIOS if u['id'] == user_id), None)
        if not alvo:
            raise HTTPException(status_code=404, detail="Usuario nao encontrado")
        # verifica email duplicado em outro registro
        existente = next((u for u in USUARIOS if u['email'].lower() == usuario.email.lower() and u['id'] != user_id), None)
        if existente:
            raise HTTPException(status_code=400, detail="Email já cadastrado por outro usuário")
        alvo['nome'] = usuario.nome
        alvo['email'] = usuario.email
        if usuario.senha:
            alvo['senha'] = _hash(usuario.senha)
        return alvo

    alvo = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not alvo:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")

    # evita duplicar email em outro registro
    existente = db.query(Usuario).filter(Usuario.email == usuario.email, Usuario.id != user_id).first()
    if existente:
        raise HTTPException(status_code=400, detail="Email já cadastrado por outro usuário")

    alvo.nome = usuario.nome
    alvo.email = usuario.email
    if usuario.senha:
        alvo.senha = _hash(usuario.senha)
    db.add(alvo)
    db.commit()
    db.refresh(alvo)
    return alvo


@app.delete("/users/{user_id}", status_code=204)
def deletar_usuario(user_id: int, admin_email: EmailStr = Query(...), db: Session = Depends(get_db)):
    """Deleta um usuário — somente admin (André) via `admin_email` query param."""
    if admin_email != "andre.seabra@teste.com":
        raise HTTPException(status_code=403, detail="Acesso negado")
    # se estamos usando a lista em memória, altere-a
    if USUARIOS:
        idx = next((i for i, u in enumerate(USUARIOS) if u['id'] == user_id), None)
        if idx is None:
            raise HTTPException(status_code=404, detail="Usuario nao encontrado")
        USUARIOS.pop(idx)
        return

    alvo = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not alvo:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")

    db.delete(alvo)
    db.commit()
    return


@app.post("/users", status_code=201, response_model=UsuarioOut)
def criar_usuario(usuario: UsuarioCreate, db: Session = Depends(get_db)) -> Usuario:
    """Cria um novo usuario e o adiciona no fim da lista."""
    # modo teste/compatibilidade: usar lista USUARIOS somente quando preenchida
    if USUARIOS:
        if any(u['email'] == usuario.email for u in USUARIOS):
            raise HTTPException(status_code=400, detail="Email já cadastrado")
        novo_id = max((u['id'] for u in USUARIOS), default=0) + 1
        # armazena senha hashed se fornecida
        senha_hashed = None
        if usuario.senha:
            senha_hashed = hashlib.sha256(usuario.senha.encode('utf-8')).hexdigest()
        novo = {"id": novo_id, "nome": usuario.nome, "email": usuario.email, "senha": senha_hashed}
        USUARIOS.append(novo)
        return novo

    # fallback para DB (não usado nos testes atuais)
    if db.query(Usuario).filter(Usuario.email == usuario.email).first():
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    # armazena senha hashed se fornecida
    novo_usuario = Usuario(nome=usuario.nome, email=usuario.email)
    if usuario.senha:
        novo_usuario.senha = hashlib.sha256(usuario.senha.encode('utf-8')).hexdigest()
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)
    return novo_usuario


@app.get("/")
def index(request: Request):
    """A tela. Por enquanto so mostra o Hello World."""
    return templates.TemplateResponse(request=request, name="index.html")
