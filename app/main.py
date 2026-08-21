from pathlib import Path
from datetime import datetime, timezone
import subprocess
import sys
from threading import Event, Lock
from collections.abc import Callable

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr
import hashlib
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import Response
from fastapi import Query

from app.config import settings
from app.db import SessionLocal, engine
from app.models import Base, Usuario
from app.cfm_client import CFM_SEARCH_URL, CfmClient, CfmDoctorDetails, CfmLookupStatus, crm_for_cfm

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
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS cfm_status VARCHAR;"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS cfm_validated_at TIMESTAMP WITH TIME ZONE;"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS cfm_data_inscricao VARCHAR;"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS cfm_primeira_inscricao_uf VARCHAR;"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS cfm_tipo_inscricao VARCHAR;"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS cfm_situacao VARCHAR;"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS cfm_inscricoes_outros_estados VARCHAR;"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS cfm_especialidades_areas VARCHAR;"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS cfm_endereco VARCHAR;"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS cfm_telefone VARCHAR;"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS cfm_instituicao_graduacao VARCHAR;"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS cfm_ano_formatura VARCHAR;"))
    conn.execute(text("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_email_key;"))
    conn.execute(text("DROP INDEX IF EXISTS uq_users_crm;"))
    conn.execute(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_users_crm_uf "
        "ON users (crm, uf) WHERE crm IS NOT NULL AND uf IS NOT NULL;"
    ))

# Compatibilidade com testes da missão: lista em memória
USUARIOS: list[dict] = []
CFM_REVALIDATION_EVENTS: dict[str, Event] = {}
CFM_REVALIDATION_LOCK = Lock()


def register_cfm_revalidation(validation_id: str | None) -> Event:
    event = Event()
    if validation_id:
        with CFM_REVALIDATION_LOCK:
            CFM_REVALIDATION_EVENTS[validation_id] = event
    return event


def unregister_cfm_revalidation(validation_id: str | None, event: Event) -> None:
    if not validation_id:
        return
    with CFM_REVALIDATION_LOCK:
        if CFM_REVALIDATION_EVENTS.get(validation_id) is event:
            CFM_REVALIDATION_EVENTS.pop(validation_id, None)


class UsuarioCreate(BaseModel):
    nome: str
    email: EmailStr
    senha: str | None = None
    uf: str | None = None
    crm: str | None = None
    is_doctor: bool = False


class UsuarioOut(BaseModel):
    id: int
    nome: str
    email: EmailStr
    senha: str | None = None
    uf: str | None = None
    crm: str | None = None
    cfm_status: str | None = None
    cfm_validated_at: datetime | None = None
    cfm_data_inscricao: str | None = None
    cfm_primeira_inscricao_uf: str | None = None
    cfm_tipo_inscricao: str | None = None
    cfm_situacao: str | None = None
    cfm_inscricoes_outros_estados: str | None = None
    cfm_especialidades_areas: str | None = None
    cfm_endereco: str | None = None
    cfm_telefone: str | None = None
    cfm_instituicao_graduacao: str | None = None
    cfm_ano_formatura: str | None = None

    class Config:
        orm_mode = True


class CfmDecision(BaseModel):
    action: str


class CfmDetailsUpdate(BaseModel):
    cfm_data_inscricao: str | None = None
    cfm_primeira_inscricao_uf: str | None = None
    cfm_tipo_inscricao: str | None = None
    cfm_situacao: str | None = None
    cfm_inscricoes_outros_estados: str | None = None
    cfm_especialidades_areas: str | None = None
    cfm_endereco: str | None = None
    cfm_telefone: str | None = None
    cfm_instituicao_graduacao: str | None = None
    cfm_ano_formatura: str | None = None


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
INVALID_DOCTOR_DATA = "Dados inválidos. Confira e tente novamente"
CFM_DETAIL_FIELD_MAP = {
    "data_inscricao": "cfm_data_inscricao",
    "primeira_inscricao_uf": "cfm_primeira_inscricao_uf",
    "inscricao": "cfm_tipo_inscricao",
    "situacao": "cfm_situacao",
    "inscricoes_outros_estados": "cfm_inscricoes_outros_estados",
    "especialidades_areas": "cfm_especialidades_areas",
    "endereco": "cfm_endereco",
    "telefone": "cfm_telefone",
    "instituicao_graduacao": "cfm_instituicao_graduacao",
    "ano_formatura": "cfm_ano_formatura",
}


def apply_cfm_details(target, details: CfmDoctorDetails | None) -> None:
    if details is None:
        return
    for detail_field, model_field in CFM_DETAIL_FIELD_MAP.items():
        value = getattr(details, detail_field)
        if isinstance(target, dict):
            target[model_field] = value
        else:
            setattr(target, model_field, value)


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


def canonical_doctor_crm(crm: str | None, uf: str | None) -> str | None:
    """Normaliza o CRM armazenado; no RJ, remove o prefixo visual fixo 52."""
    normalized = normalize_crm(crm)
    if normalized is None or uf is None:
        return normalized
    return crm_for_cfm(normalized, uf)


def doctor_data_matches(existing, usuario: UsuarioCreate, crm: str, uf: str) -> bool:
    """Confere os quatro dados que identificam um login médico existente."""
    get_value = existing.get if isinstance(existing, dict) else lambda key: getattr(existing, key, None)
    existing_uf = validate_uf(get_value("uf"))
    return all((
        normalize_name(get_value("nome")) == normalize_name(usuario.nome),
        normalize_email(get_value("email")) == normalize_email(usuario.email),
        existing_uf == uf,
        canonical_doctor_crm(get_value("crm"), existing_uf) == crm,
    ))


def validar_medico_no_cfm(
    crm: str | None,
    uf: str | None,
    cancelled: Callable[[], bool] | None = None,
) -> tuple[str | None, datetime | None, CfmDoctorDetails | None]:
    """Converte o contrato do client nos dados persistidos pelo domínio."""
    if not crm or not uf:
        return None, None, None

    resultado = CfmClient(cancelled=cancelled).find_doctor(crm, uf)
    if resultado.status is CfmLookupStatus.NOT_FOUND:
        return CfmLookupStatus.UNAVAILABLE.value, None, None
    if resultado.status is CfmLookupStatus.FOUND:
        return resultado.status.value, datetime.now(timezone.utc), resultado.details
    return resultado.status.value, None, None


@app.get("/cfm/manual-search", response_class=HTMLResponse)
def abrir_consulta_manual_cfm(crm: str = Query(...), uf: str = Query(...)) -> str:
    """Abre o formulário do CFM preenchido; CAPTCHA e envio ficam com a pessoa."""
    uf_validada = validate_uf(uf)
    crm_normalizado = crm_for_cfm(normalize_crm(crm) or "", uf_validada or "")
    subprocess.Popen(
        [sys.executable, "-m", "app.cfm_browser", uf_validada or "", crm_normalizado],
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )
    return """<!doctype html><html lang=\"pt-BR\"><body>
      <p>O formulário do CFM foi aberto com UF e CRM preenchidos. Confira os dados, resolva o CAPTCHA se necessário e clique em ENVIAR.</p>
    </body></html>"""


@app.patch("/users/{user_id}/cfm-status", response_model=UsuarioOut)
def decidir_validacao_cfm(
    user_id: int,
    decisao: CfmDecision,
    admin_email: EmailStr = Query(...),
    db: Session = Depends(get_db),
) -> Usuario:
    """Permite ao Admin aprovar ou recusar um médico pendente."""
    if normalize_email(admin_email) != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Acesso negado")
    if decisao.action not in {"approve", "reject"}:
        raise HTTPException(status_code=400, detail="Ação inválida")

    if USUARIOS:
        usuario = next((item for item in USUARIOS if item["id"] == user_id), None)
        if not usuario:
            raise HTTPException(status_code=404, detail="Usuario não encontrado")
        if usuario.get("cfm_status") != CfmLookupStatus.UNAVAILABLE.value:
            raise HTTPException(status_code=409, detail="Usuário não está pendente")
        usuario["cfm_status"] = "VALIDATED" if decisao.action == "approve" else "REJECTED"
        usuario["cfm_validated_at"] = datetime.now(timezone.utc) if decisao.action == "approve" else None
        return usuario

    usuario = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario não encontrado")
    if usuario.cfm_status != CfmLookupStatus.UNAVAILABLE.value:
        raise HTTPException(status_code=409, detail="Usuário não está pendente")
    if decisao.action == "approve":
        usuario_comum = db.query(Usuario).filter(
            func.lower(func.trim(Usuario.email)) == normalize_email(usuario.email),
            Usuario.id != usuario.id,
            Usuario.crm.is_(None),
        ).first()
        if usuario_comum:
            db.delete(usuario_comum)
    usuario.cfm_status = "VALIDATED" if decisao.action == "approve" else "REJECTED"
    usuario.cfm_validated_at = datetime.now(timezone.utc) if decisao.action == "approve" else None
    db.commit()
    db.refresh(usuario)
    return usuario


@app.post("/users/{user_id}/cfm-revalidate", response_model=UsuarioOut)
def revalidar_medico_pendente(
    user_id: int,
    admin_email: EmailStr = Query(...),
    validation_id: str | None = Query(None),
    db: Session = Depends(get_db),
) -> Usuario:
    """Repete automaticamente a consulta do CFM para um médico pendente."""
    if normalize_email(admin_email) != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Acesso negado")

    if USUARIOS:
        usuario = next((item for item in USUARIOS if item["id"] == user_id), None)
        if not usuario:
            raise HTTPException(status_code=404, detail="Usuario não encontrado")
        if usuario.get("cfm_status") != CfmLookupStatus.UNAVAILABLE.value:
            raise HTTPException(status_code=409, detail="Usuário não está pendente")
        cancel_event = register_cfm_revalidation(validation_id)
        try:
            status_cfm, validado_em, cfm_details = validar_medico_no_cfm(
                usuario.get("crm"),
                usuario.get("uf"),
                cancel_event.is_set,
            )
        finally:
            unregister_cfm_revalidation(validation_id, cancel_event)
        if status_cfm == CfmLookupStatus.FOUND.value:
            usuario["cfm_status"] = CfmLookupStatus.FOUND.value
            usuario["cfm_validated_at"] = validado_em
            apply_cfm_details(usuario, cfm_details)
        return usuario

    usuario = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario não encontrado")
    if usuario.cfm_status != CfmLookupStatus.UNAVAILABLE.value:
        raise HTTPException(status_code=409, detail="Usuário não está pendente")

    cancel_event = register_cfm_revalidation(validation_id)
    try:
        status_cfm, validado_em, cfm_details = validar_medico_no_cfm(
            usuario.crm,
            usuario.uf,
            cancel_event.is_set,
        )
    finally:
        unregister_cfm_revalidation(validation_id, cancel_event)
    if status_cfm != CfmLookupStatus.FOUND.value:
        return usuario

    usuario_comum = db.query(Usuario).filter(
        func.lower(func.trim(Usuario.email)) == normalize_email(usuario.email),
        Usuario.id != usuario.id,
        Usuario.crm.is_(None),
    ).first()
    if usuario_comum:
        db.delete(usuario_comum)
    usuario.cfm_status = CfmLookupStatus.FOUND.value
    usuario.cfm_validated_at = validado_em
    apply_cfm_details(usuario, cfm_details)
    db.commit()
    db.refresh(usuario)
    return usuario


@app.post("/cfm/revalidation/{validation_id}/cancel")
def cancelar_revalidacao_cfm(
    validation_id: str,
    admin_email: EmailStr = Query(...),
) -> dict[str, bool]:
    """Interrompe a consulta ativa e fecha o Chromium assim que possível."""
    if normalize_email(admin_email) != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Acesso negado")
    with CFM_REVALIDATION_LOCK:
        event = CFM_REVALIDATION_EVENTS.get(validation_id)
    if event:
        event.set()
    return {"cancelled": event is not None}


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


@app.patch("/users/{user_id}/cfm-details", response_model=UsuarioOut)
def atualizar_detalhes_cfm(
    user_id: int,
    details: CfmDetailsUpdate,
    admin_email: EmailStr = Query(...),
    db: Session = Depends(get_db),
) -> Usuario:
    """Permite ao Admin corrigir ou complementar os dados públicos do CFM."""
    if normalize_email(admin_email) != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Acesso negado")
    values = {
        key: (value.strip() or None) if isinstance(value, str) else value
        for key, value in details.model_dump().items()
    }

    if USUARIOS:
        usuario = next((item for item in USUARIOS if item["id"] == user_id), None)
        if not usuario:
            raise HTTPException(status_code=404, detail="Usuario não encontrado")
        if not usuario.get("crm"):
            raise HTTPException(status_code=400, detail="Cadastro não é de médico")
        usuario.update(values)
        return usuario

    usuario = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario não encontrado")
    if not usuario.crm:
        raise HTTPException(status_code=400, detail="Cadastro não é de médico")
    for field, value in values.items():
        setattr(usuario, field, value)
    db.commit()
    db.refresh(usuario)
    return usuario


@app.post("/users", status_code=201, response_model=UsuarioOut)
def criar_usuario(usuario: UsuarioCreate, db: Session = Depends(get_db), response: Response = None) -> Usuario:
    """Cria um novo usuario e o adiciona no fim da lista."""
    # modo teste/compatibilidade: usar lista USUARIOS somente quando preenchida
    if USUARIOS:
        doctor_crm = None
        doctor_uf = None
        if usuario.is_doctor:
            doctor_uf = validate_uf(usuario.uf)
            doctor_crm = canonical_doctor_crm(usuario.crm, doctor_uf)
            if not doctor_crm or not doctor_uf:
                raise HTTPException(status_code=400, detail=INVALID_DOCTOR_DATA)
            crm_owner = next(
                (
                    item for item in USUARIOS
                    if item.get("crm")
                    and canonical_doctor_crm(item.get("crm"), item.get("uf")) == doctor_crm
                    and validate_uf(item.get("uf")) == doctor_uf
                ),
                None,
            )
            if crm_owner:
                if not doctor_data_matches(crm_owner, usuario, doctor_crm, doctor_uf):
                    raise HTTPException(status_code=409, detail=INVALID_DOCTOR_DATA)
                if response is not None:
                    response.status_code = 200
                return crm_owner

        ne = normalize_email(usuario.email)
        existente = next((u for u in USUARIOS if normalize_email(u.get('email')) == ne), None)
        if existente:
            if usuario.is_doctor and existente.get("crm"):
                raise HTTPException(status_code=409, detail=INVALID_DOCTOR_DATA)
            # Só atualiza se payload contém dados de médico ou senha (completar cadastro)
            has_medico_data = (hasattr(usuario, 'crm') and usuario.crm not in (None, '')) or (hasattr(usuario, 'uf') and usuario.uf not in (None, '')) or (usuario.senha not in (None, ''))
            if has_medico_data:
                if hasattr(usuario, 'crm') and usuario.crm is not None:
                    existente['crm'] = doctor_crm if usuario.is_doctor else normalize_crm(usuario.crm)
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
            novo['crm'] = doctor_crm if usuario.is_doctor else normalize_crm(usuario.crm)
        if hasattr(usuario, 'uf') and usuario.uf is not None:
            novo['uf'] = validate_uf(usuario.uf)
        USUARIOS.append(novo)
        return novo

    usuarios_com_email = db.query(Usuario).filter(
        func.lower(func.trim(Usuario.email)) == normalize_email(usuario.email)
    ).all()

    if not usuario.is_doctor:
        if usuarios_com_email:
            raise HTTPException(status_code=400, detail="Email já cadastrado")
        novo_usuario = Usuario(nome=usuario.nome, email=usuario.email)
        db.add(novo_usuario)
        db.commit()
        db.refresh(novo_usuario)
        return novo_usuario

    uf = validate_uf(usuario.uf)
    crm = canonical_doctor_crm(usuario.crm, uf)
    if not crm or not uf:
        raise HTTPException(status_code=400, detail=INVALID_DOCTOR_DATA)

    doctors = db.query(Usuario).filter(Usuario.crm.is_not(None)).all()
    crm_owner = next(
        (
            item for item in doctors
            if canonical_doctor_crm(item.crm, item.uf) == crm
            and validate_uf(item.uf) == uf
        ),
        None,
    )
    if crm_owner:
        if not doctor_data_matches(crm_owner, usuario, crm, uf):
            raise HTTPException(status_code=409, detail=INVALID_DOCTOR_DATA)
        if response is not None:
            response.status_code = 200
        return crm_owner

    medico_com_mesmo_email = next((item for item in usuarios_com_email if item.crm), None)
    if medico_com_mesmo_email:
        raise HTTPException(status_code=409, detail=INVALID_DOCTOR_DATA)

    status_cfm, validado_em, cfm_details = validar_medico_no_cfm(crm, uf)
    if status_cfm is None:
        status_cfm = CfmLookupStatus.UNAVAILABLE.value

    # Uma confirmação automática transforma o usuário comum no médico. Sem
    # confirmação, preservamos o usuário e criamos uma solicitação paralela.
    usuario_comum = next((item for item in usuarios_com_email if not item.crm), None)
    medico = usuario_comum if status_cfm == "VALIDATED" and usuario_comum else Usuario(nome=usuario.nome, email=usuario.email)
    medico.nome = usuario.nome
    medico.crm = crm
    medico.uf = uf
    medico.cfm_status = status_cfm
    medico.cfm_validated_at = validado_em
    if status_cfm == CfmLookupStatus.FOUND.value:
        apply_cfm_details(medico, cfm_details)
    db.add(medico)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        crm_owner = db.query(Usuario).filter(Usuario.crm == crm, Usuario.uf == uf).first()
        if crm_owner and doctor_data_matches(crm_owner, usuario, crm, uf):
            if response is not None:
                response.status_code = 200
            return crm_owner
        raise HTTPException(status_code=409, detail=INVALID_DOCTOR_DATA)
    db.refresh(medico)
    return medico


@app.get("/")
def index(request: Request):
    """A tela. Por enquanto so mostra o Hello World."""
    return templates.TemplateResponse(request=request, name="index.html")
