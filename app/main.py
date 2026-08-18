from pathlib import Path
from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.schemas import UserCreate, DoctorCreate

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

@app.post("/users/{user_id}/doctors", status_code=status.HTTP_201_CREATED)
def criar_doctor(user_id: int, payload: DoctorCreate, db: Session = Depends(get_db)):
    """Cria um registro de médico vinculado a um usuário existente."""
    usuario = db.query(models.User).filter(models.User.id == user_id).first()

    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")

    doctor_existente = db.query(models.Doctor).filter(models.Doctor.user_id == user_id).first()

    if doctor_existente is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Usuário já possui um médico associado")

    # NOVO: checagem de CRM duplicado
    crm_existente = db.query(models.Doctor).filter(models.Doctor.crm == payload.crm).first()

    if crm_existente is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="CRM já cadastrado")

    novo_doctor = models.Doctor(crm=payload.crm, uf=payload.uf, user_id=user_id)
    db.add(novo_doctor)
    db.commit()
    db.refresh(novo_doctor)

    return novo_doctor

@app.put("/users/{user_id}")
def atualizar_usuario(user_id: int, payload: UserCreate, db: Session = Depends(get_db)):
    """Substitui os dados de um usuário existente pelo id."""
    usuario = db.query(models.User).filter(models.User.id == user_id).first()
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")

    usuario.nome = payload.nome
    usuario.email = payload.email
    db.commit()
    db.refresh(usuario)
    return usuario

@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_usuario(user_id: int, db: Session = Depends(get_db)):
    """Remove um usuário pelo id. Retorna 404 se o usuário não existir."""
    usuario = db.query(models.User).filter(models.User.id == user_id).first()

    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")

    db.delete(usuario)
    db.commit()
    return None