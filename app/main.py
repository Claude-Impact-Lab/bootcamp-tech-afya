"""
Aplicação FastAPI com persistência em PostgreSQL:
- GET /health: retorna JSON com status da aplicação
- GET /: página de cadastro inicial (Etapa 1) + lista de usuários
- GET /medico/{id}: Ficha do Médico (Etapa 2)
- GET /users: retorna lista de usuários do banco de dados
"""

from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, field_validator, model_validator
from sqlalchemy.exc import IntegrityError

from app.database import engine, SessionLocal, Base
from app.cfm.client import CFMClient
from app.cfm.dependency import get_cfm_client
from app.models import Doctor, User
from app.validators import (
    campo_obrigatorio_pydantic,
    normalizar_idiomas_pydantic,
    validar_crm_pydantic,
    validar_especialidade_pydantic,
    validar_uf_pydantic,
)

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


class UserCreate(BaseModel):
    """Etapa 1: cadastro inicial. CRM/UF não são coletados aqui.

    Se `is_doctor` for verdadeiro, o frontend deve navegar para a Etapa 2
    (`/medico/{id}`) para preencher a Ficha do Médico completa.
    """

    name: str
    email: str
    is_doctor: bool = False


class DoctorProfileIn(BaseModel):
    """Etapa 2: Ficha do Médico completa (cria ou atualiza o perfil)."""

    data_nascimento: str
    cpf: str | None = None
    telefone: str
    crm: str
    uf: str
    especialidade: str
    especialidade_outra: str | None = None
    instituicao_formacao: str | None = None
    ano_formacao: str | None = None
    cep: str
    logradouro: str
    numero: str
    complemento: str | None = None
    bairro: str
    cidade: str
    estado: str
    foto: str | None = None
    bio: str | None = None
    idiomas: list[str] = []

    _validar_uf = field_validator("uf")(validar_uf_pydantic)
    _validar_crm = field_validator("crm")(validar_crm_pydantic)
    _validar_especialidade = field_validator("especialidade")(
        validar_especialidade_pydantic
    )
    _validar_idiomas = field_validator("idiomas")(normalizar_idiomas_pydantic)

    _validar_data_nascimento = field_validator("data_nascimento")(
        campo_obrigatorio_pydantic("Informe a data de nascimento.")
    )
    _validar_telefone = field_validator("telefone")(
        campo_obrigatorio_pydantic("Informe o telefone.")
    )
    _validar_cep = field_validator("cep")(
        campo_obrigatorio_pydantic("Informe o CEP.")
    )
    _validar_logradouro = field_validator("logradouro")(
        campo_obrigatorio_pydantic("Informe a rua/logradouro.")
    )
    _validar_numero = field_validator("numero")(
        campo_obrigatorio_pydantic("Informe o número.")
    )
    _validar_bairro = field_validator("bairro")(
        campo_obrigatorio_pydantic("Informe o bairro.")
    )
    _validar_cidade = field_validator("cidade")(
        campo_obrigatorio_pydantic("Informe a cidade.")
    )
    _validar_estado = field_validator("estado")(
        campo_obrigatorio_pydantic("Selecione o estado.")
    )

    @model_validator(mode="after")
    def validar_especialidade_outra(self) -> "DoctorProfileIn":
        """Exige o texto livre quando a especialidade selecionada for 'Outra'."""
        if self.especialidade == "Outra" and not (
            self.especialidade_outra and self.especialidade_outra.strip()
        ):
            raise ValueError(
                "Informe sua especialidade quando selecionar 'Outra'."
            )
        return self


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
    """Página inicial: cadastro (Etapa 1) + lista de usuários."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
    )


@app.get("/medico/{user_id}", tags=["Pages"])
def pagina_ficha_medica(request: Request, user_id: int):
    """Etapa 2: página da Ficha do Médico.

    O carregamento e a validação (usuário existe? é médico?) acontecem no
    cliente via fetch em `/users/{user_id}`, para exibir mensagens amigáveis
    sem duplicar essa regra aqui no servidor.
    """
    return templates.TemplateResponse(
        request=request,
        name="medico.html",
        context={"user_id": user_id},
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
        return [serialize_user(usuario) for usuario in usuarios]
    finally:
        # Importante: sempre fechar a sessão para liberar recursos
        db.close()


def serialize_user(usuario: User) -> dict:
    """Converte usuário e ficha médica para o formato público da API."""
    doctor = usuario.doctor
    doctor_dict = None
    if doctor is not None:
        doctor_dict = {
            "crm": doctor.crm,
            "uf": doctor.uf,
            "cfm_validated_at": (
                doctor.cfm_validated_at.isoformat()
                if doctor.cfm_validated_at is not None
                else None
            ),
            "data_nascimento": doctor.data_nascimento,
            "cpf": doctor.cpf,
            "telefone": doctor.telefone,
            "especialidade": doctor.especialidade,
            "especialidade_outra": doctor.especialidade_outra,
            "instituicao_formacao": doctor.instituicao_formacao,
            "ano_formacao": doctor.ano_formacao,
            "cep": doctor.cep,
            "logradouro": doctor.logradouro,
            "numero": doctor.numero,
            "complemento": doctor.complemento,
            "bairro": doctor.bairro,
            "cidade": doctor.cidade,
            "estado": doctor.estado,
            "foto": doctor.foto,
            "bio": doctor.bio,
            "idiomas": doctor.idiomas.split(",") if doctor.idiomas else [],
        }
    return {
        "id": usuario.id,
        "name": usuario.name,
        "email": usuario.email,
        "is_doctor": usuario.is_doctor,
        "has_doctor_profile": doctor is not None,
        "doctor": doctor_dict,
    }


@app.post("/users", status_code=201, tags=["Users"])
def create_user(user_data: UserCreate):
    """Cria o usuário da Etapa 1.

    Se `is_doctor` for verdadeiro, a ficha médica (Doctor) ainda não existe:
    ela só é criada quando a Etapa 2 for salva em `PUT /users/{id}/doctor`.
    """
    db = SessionLocal()
    try:
        usuario = User(
            name=user_data.name.strip(),
            email=user_data.email,
            is_doctor=user_data.is_doctor,
        )
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
        return serialize_user(usuario)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email já está em uso")
    finally:
        db.close()


@app.get("/users/{user_id}", tags=["Users"])
def get_user(user_id: int):
    """Consulta um usuário e informa se possui perfil médico."""
    db = SessionLocal()
    try:
        usuario = db.query(User).filter(User.id == user_id).first()
        if usuario is None:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        return serialize_user(usuario)
    finally:
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


@app.put("/users/{user_id}/doctor", tags=["Users"])
def salvar_ficha_medica(
    user_id: int,
    perfil: DoctorProfileIn,
    cfm_client: CFMClient = Depends(get_cfm_client),
):
    """Etapa 2: cria ou atualiza a Ficha do Médico de um usuário.

    Só é permitido para usuários que marcaram "Este usuário é médico" na
    Etapa 1. Todos os campos já chegam validados pelo schema `DoctorProfileIn`
    (ver app/validators.py), que é a fonte única dessa regra de negócio.
    """
    db = SessionLocal()
    try:
        usuario = db.query(User).filter(User.id == user_id).first()
        if usuario is None:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        if not usuario.is_doctor:
            raise HTTPException(
                status_code=422,
                detail="Este usuário não possui um cadastro médico.",
            )

        medico_cfm = cfm_client.find_doctor(perfil.crm, perfil.uf)
        if medico_cfm is None:
            raise HTTPException(
                status_code=422,
                detail="Médico não encontrado no CFM para o CRM e UF informados.",
            )

        doctor = usuario.doctor
        if doctor is None:
            doctor = Doctor(user_id=usuario.id)
            db.add(doctor)

        doctor.crm = perfil.crm
        doctor.uf = perfil.uf
        doctor.cfm_validated_at = datetime.now(timezone.utc)
        doctor.data_nascimento = perfil.data_nascimento
        doctor.cpf = perfil.cpf
        doctor.telefone = perfil.telefone
        doctor.especialidade = perfil.especialidade
        doctor.especialidade_outra = (
            perfil.especialidade_outra if perfil.especialidade == "Outra" else None
        )
        doctor.instituicao_formacao = perfil.instituicao_formacao
        doctor.ano_formacao = perfil.ano_formacao
        doctor.cep = perfil.cep
        doctor.logradouro = perfil.logradouro
        doctor.numero = perfil.numero
        doctor.complemento = perfil.complemento
        doctor.bairro = perfil.bairro
        doctor.cidade = perfil.cidade
        doctor.estado = perfil.estado
        doctor.foto = perfil.foto
        doctor.bio = perfil.bio
        doctor.idiomas = ",".join(perfil.idiomas) if perfil.idiomas else None

        db.commit()
        db.refresh(usuario)
        return serialize_user(usuario)
    finally:
        db.close()


@app.delete("/users/{user_id}", tags=["Users"])
def delete_user(user_id: int):
    """Exclui um usuário existente.

    Se o usuário possuir ficha médica (Doctor), ela é excluída primeiro,
    na mesma transação, para respeitar a FK `doctors.user_id` (ON DELETE
    RESTRICT) sem deixar dados órfãos nem exclusões parciais.
    """
    db = SessionLocal()

    try:
        usuario = db.query(User).filter(User.id == user_id).first()
        if usuario is None:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")

        if usuario.doctor is not None:
            db.delete(usuario.doctor)
        db.delete(usuario)
        db.commit()
        return {"message": "Usuário excluído com sucesso"}
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Não foi possível excluir: existem dados relacionados a este usuário.",
        )
    finally:
        db.close()

