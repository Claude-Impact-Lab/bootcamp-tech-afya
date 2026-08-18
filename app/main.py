from pathlib import Path

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr
import hashlib
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import Response
from fastapi import Query

from app.config import settings
from app.db import SessionLocal, engine
from app.models import Base, Usuario

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="User Manager")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

Base.metadata.create_all(bind=engine)

# adiciona coluna senha caso ainda não exista (migration simples)
with engine.begin() as conn:
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS senha VARCHAR;"))
    # adiciona colunas crm e uf se não existirem
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS crm VARCHAR;"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS uf VARCHAR;"))

# Compatibilidade com testes da missão: lista em memória
USUARIOS: list[dict] = []


class UsuarioCreate(BaseModel):
    nome: str
    email: EmailStr
    senha: str | None = None
    uf: str | None = None
    crm: str | None = None


class UsuarioOut(BaseModel):
    id: int
    nome: str
    email: EmailStr
    senha: str | None = None
    uf: str | None = None
    crm: str | None = None

    class Config:
        orm_mode = True


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Lista de UFs válidas (fonte: Brasil)
UF_LIST = [
    'AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG',
    'PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO'
]

# e-mail do admin (constante em lowercase)
ADMIN_EMAIL = "andre.seabra@teste.com"


def normalize_crm(crm: str | None) -> str | None:
    if crm is None:
        return None
    # remove tudo que não é dígito
    only = ''.join(ch for ch in crm if ch.isdigit())
    # remove zeros à esquerda
    normalized = only.lstrip('0')
    if normalized == '':
        # se tudo era zero, mantemos '0'
        normalized = '0'
    # limita a 10 dígitos
    return normalized[:10]


def validate_uf(uf: str | None) -> str | None:
    if uf is None or uf == '':
        return None
    uf_up = uf.strip().upper()
    if uf_up not in UF_LIST:
        raise HTTPException(status_code=400, detail=f"UF inválida: {uf}")
    return uf_up


def normalize_email(email: str | None) -> str | None:
    if email is None:
        return None
    return email.strip().lower()


def normalize_name(nome: str | None) -> str | None:
    """Normaliza o nome para comparações: remove espaços nas extremidades e baixa para lowercase.
    Note que espaços internos são preservados (ex.: 'André Seabra' -> 'andré seabra').
    """
    if nome is None:
        return None
    return nome.strip().lower()


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

    # modo app real: somente admin pode listar via DB (ignora maiúsculas/minúsculas)
    if normalize_email(admin_email) != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Acesso negado")
    return db.query(Usuario).all()


@app.get("/users/search", response_model=UsuarioOut)
def buscar_usuario_por_email(email: EmailStr = Query(...), db: Session = Depends(get_db)) -> Usuario | None:
    """Procura um usuário por e-mail — usado pelo frontend para checar existência sem ser admin."""
    # se estamos no modo de testes com lista em memória, procurar nela
    if USUARIOS:
        ne = normalize_email(email)
        usuario = next((u for u in USUARIOS if normalize_email(u.get('email')) == ne), None)
        if not usuario:
            raise HTTPException(status_code=404, detail="Usuario não encontrado")
        return usuario

    usuario = db.query(Usuario).filter(func.lower(func.trim(Usuario.email)) == normalize_email(email)).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario não encontrado")
    return usuario


@app.put("/users/{user_id}", response_model=UsuarioOut)
def atualizar_usuario(user_id: int, usuario: UsuarioCreate, admin_email: EmailStr = Query(...), db: Session = Depends(get_db)) -> Usuario:
    """Atualiza um usuário — somente admin (André) via `admin_email` query param."""
    if normalize_email(admin_email) != ADMIN_EMAIL:
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
        existente = next((u for u in USUARIOS if normalize_email(u.get('email')) == normalize_email(usuario.email) and u['id'] != user_id), None)
        if existente:
            raise HTTPException(status_code=400, detail="Email já cadastrado por outro usuário")
        alvo['nome'] = usuario.nome
        alvo['email'] = usuario.email
        # normalize crm/uf if provided
        if hasattr(usuario, 'crm') and usuario.crm is not None:
            alvo['crm'] = normalize_crm(usuario.crm)
        if hasattr(usuario, 'uf') and usuario.uf is not None:
            alvo['uf'] = validate_uf(usuario.uf)
        if usuario.senha:
            alvo['senha'] = _hash(usuario.senha)
        return alvo

    alvo = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not alvo:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")

    # evita duplicar email em outro registro
    existente = db.query(Usuario).filter(func.lower(func.trim(Usuario.email)) == normalize_email(usuario.email), Usuario.id != user_id).first()
    if existente:
        raise HTTPException(status_code=400, detail="Email já cadastrado por outro usuário")

    alvo.nome = usuario.nome
    alvo.email = usuario.email
    # normalize and validate crm/uf for DB
    if hasattr(usuario, 'crm') and usuario.crm is not None:
        alvo.crm = normalize_crm(usuario.crm)
    if hasattr(usuario, 'uf') and usuario.uf is not None:
        alvo.uf = validate_uf(usuario.uf)
    if usuario.senha:
        alvo.senha = _hash(usuario.senha)
    db.add(alvo)
    db.commit()
    db.refresh(alvo)
    return alvo


@app.delete("/users/{user_id}", status_code=204)
def deletar_usuario(user_id: int, admin_email: EmailStr = Query(...), db: Session = Depends(get_db)):
    """Deleta um usuário — somente admin (André) via `admin_email` query param."""
    if normalize_email(admin_email) != ADMIN_EMAIL:
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
def criar_usuario(usuario: UsuarioCreate, db: Session = Depends(get_db), response: Response = None) -> Usuario:
    """Cria um novo usuario e o adiciona no fim da lista."""
    # modo teste/compatibilidade: usar lista USUARIOS somente quando preenchida
    if USUARIOS:
        ne = normalize_email(usuario.email)
        existente = next((u for u in USUARIOS if normalize_email(u.get('email')) == ne), None)
        if existente:
            # Só atualiza se payload contém dados de médico ou senha (completar cadastro)
            has_medico_data = (hasattr(usuario, 'crm') and usuario.crm not in (None, '')) or (hasattr(usuario, 'uf') and usuario.uf not in (None, '')) or (usuario.senha not in (None, ''))
            if has_medico_data:
                if hasattr(usuario, 'crm') and usuario.crm is not None:
                    existente['crm'] = normalize_crm(usuario.crm)
                if hasattr(usuario, 'uf') and usuario.uf is not None:
                    existente['uf'] = validate_uf(usuario.uf)
                # manter senha se fornecida
                if usuario.senha:
                    existente['senha'] = hashlib.sha256(usuario.senha.encode('utf-8')).hexdigest()
                if response is not None:
                    response.status_code = 200
                return existente
            # sem dados adicionais, considerada tentativa de login como usuário: informar duplicado
            raise HTTPException(status_code=400, detail="Email já cadastrado")
        novo_id = max((u['id'] for u in USUARIOS), default=0) + 1
        # armazena senha hashed se fornecida
        senha_hashed = None
        if usuario.senha:
            senha_hashed = hashlib.sha256(usuario.senha.encode('utf-8')).hexdigest()
        novo = {"id": novo_id, "nome": usuario.nome, "email": usuario.email, "senha": senha_hashed}
        if hasattr(usuario, 'crm') and usuario.crm is not None:
            novo['crm'] = normalize_crm(usuario.crm)
        if hasattr(usuario, 'uf') and usuario.uf is not None:
            novo['uf'] = validate_uf(usuario.uf)
        USUARIOS.append(novo)
        return novo

    # fallback para DB (não usado nos testes atuais)
    # procura por e-mail de forma normalizada
    existente_db = db.query(Usuario).filter(func.lower(func.trim(Usuario.email)) == normalize_email(usuario.email)).first()
    if existente_db:
        # Só atualiza se payload contém dados de médico ou senha (completar cadastro)
        has_medico_data = (hasattr(usuario, 'crm') and usuario.crm not in (None, '')) or (hasattr(usuario, 'uf') and usuario.uf not in (None, '')) or (usuario.senha not in (None, ''))
        if has_medico_data:
            if hasattr(usuario, 'crm') and usuario.crm is not None:
                existente_db.crm = normalize_crm(usuario.crm)
            if hasattr(usuario, 'uf') and usuario.uf is not None:
                existente_db.uf = validate_uf(usuario.uf)
            if usuario.senha:
                existente_db.senha = hashlib.sha256(usuario.senha.encode('utf-8')).hexdigest()
            db.add(existente_db)
            db.commit()
            db.refresh(existente_db)
            if response is not None:
                response.status_code = 200
            return existente_db
        # sem dados adicionais, considerada tentativa de login como usuário: informar duplicado
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    # armazena senha hashed se fornecida
    novo_usuario = Usuario(nome=usuario.nome, email=usuario.email)
    if usuario.senha:
        novo_usuario.senha = hashlib.sha256(usuario.senha.encode('utf-8')).hexdigest()
    if hasattr(usuario, 'crm') and usuario.crm is not None:
        novo_usuario.crm = normalize_crm(usuario.crm)
    if hasattr(usuario, 'uf') and usuario.uf is not None:
        novo_usuario.uf = validate_uf(usuario.uf)
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)
    return novo_usuario


@app.get("/")
def index(request: Request):
    """A tela. Por enquanto so mostra o Hello World."""
    return templates.TemplateResponse(request=request, name="index.html")
