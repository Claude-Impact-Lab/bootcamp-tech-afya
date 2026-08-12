from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr, StringConstraints, TypeAdapter, ValidationError, field_validator

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Novo usuário do projeto")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# strip_whitespace tira os espacos das pontas antes de medir o tamanho:
# assim "   " nao passa como nome valido.
Nome = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=80)]
email_validator = TypeAdapter(EmailStr)


class UserIn(BaseModel):
    """O que o cliente envia no POST. Sem `id`: quem decide o id e o servidor."""

    nome: Nome
    email: str

    @field_validator("email", mode="before")
    @classmethod
    def validar_email(cls, value: str) -> str:
        if value is None or not isinstance(value, str):
            raise ValueError("EMAIL NÃO É VÁLIDO")

        valor = value.strip()
        try:
            email_validator.validate_python(valor)
        except ValidationError as exc:
            raise ValueError("EMAIL NÃO É VÁLIDO") from exc
        return valor.lower()


# Os usuarios moram aqui por enquanto. Somem quando o servidor reinicia:
# o banco de verdade entra na missao 03.
USERS: list[dict] = []


@app.get("/health")
def health() -> dict[str, str]:
    """Endpoint JSON: e daqui que o HTML busca a mensagem."""
    return {"status": "ok", "message": "Hello World"}


@app.get("/users")
def list_users(nome: str | None = None) -> list[dict]:
    """Lista os usuarios. Com ?nome=, devolve so quem tem esse texto no nome."""
    if nome is None:
        return USERS

    procurado = nome.lower()
    return [user for user in USERS if procurado in user["nome"].lower()]


@app.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(novo: UserIn) -> dict:
    """Cadastra um usuario. Devolve 201 com o usuario criado, ja com o id."""
    email = novo.email.lower()

    for user in USERS:
        if user["email"].lower() == email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"O e-mail {email} já está cadastrado",
            )

    # max(...) + 1 em vez de len(USERS) + 1: com exclusao (missao 04) o len
    # repetiria um id ja usado.
    proximo_id = max((user["id"] for user in USERS), default=0) + 1
    user = {"id": proximo_id, "nome": novo.nome, "email": email}
    USERS.append(user)

    return user


@app.get("/users/{user_id}")
def get_user(user_id: int) -> dict:
    """Busca um usuario pelo id. Devolve 404 se ele nao existir."""
    for user in USERS:
        if user["id"] == user_id:
            return user

    raise HTTPException(status_code=404, detail=f"Usuário {user_id} não encontrado")


@app.get("/")
def index(request: Request):
    """A tela. Por enquanto so mostra o Hello World."""
    return templates.TemplateResponse(request=request, name="index.html")
