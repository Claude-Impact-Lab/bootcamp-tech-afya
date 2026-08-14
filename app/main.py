from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import engine, get_db
from app.models import Base, User, UserCreate, UserResponse

BASE_DIR = Path(__file__).resolve().parent

# Criar tabelas ao importar (apenas para produção com SQLite)
# Nos testes, as tabelas são criadas pelo fixture
try:
    Base.metadata.create_all(bind=engine)
except Exception:
    # Ignorar erros em testes
    pass

app = FastAPI(title="User Manager")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.get("/health")
def health() -> dict[str, str]:
    """Endpoint JSON: e daqui que o HTML busca a mensagem."""
    return {"status": "ok", "message": "Hello World"}


@app.get("/users")
def list_users(db: Annotated[Session, Depends(get_db)]) -> list[UserResponse]:
    """Lista os usuarios. Sem nenhum, devolve [] com status 200 — nao 404."""
    users = db.query(User).all()
    return [UserResponse.model_validate(user) for user in users]


@app.post("/users", status_code=201)
def create_user(
    user: UserCreate, db: Annotated[Session, Depends(get_db)]
) -> UserResponse:
    """Cria um usuario com nome valido e proximo id disponivel."""
    db_user = User(name=user.name, password=user.password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return UserResponse.model_validate(db_user)


@app.put("/users/{user_id}")
def update_user(
    user_id: int, user: UserCreate, db: Annotated[Session, Depends(get_db)]
) -> UserResponse:
    """Atualiza um usuario existente."""
    db_user = db.query(User).filter(User.id == user_id).first()
    
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario não encontrado")
    
    db_user.name = user.name
    db_user.password = user.password
    db.commit()
    db.refresh(db_user)
    
    return UserResponse.model_validate(db_user)


@app.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, db: Annotated[Session, Depends(get_db)]):
    """Deleta um usuario existente."""
    db_user = db.query(User).filter(User.id == user_id).first()
    
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario não encontrado")
    
    db.delete(db_user)
    db.commit()
    
    # Status 204 não retorna conteúdo


@app.get("/")
def index(request: Request):
    """A tela. Por enquanto so mostra o Hello World."""
    return templates.TemplateResponse(request=request, name="index.html")
