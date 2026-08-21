# Missão 03 — Persistir no PostgreSQL 🎯

## ✅ Status: Completo

Todos os testes passando! A aplicação agora persiste dados em um banco PostgreSQL real.

---

## 📚 Explicação Detalhada do que foi Feito

### 🎯 Objetivo
Transformar a lista de usuários em memória (que desaparecia ao reiniciar) em um banco de dados PostgreSQL que **persiste para sempre**.

### 📋 Mudanças Realizadas

## 1️⃣ **Arquivo: `docker-compose.yml` (NOVO)**

```yaml
version: '3.8'
services:
  postgres:
    image: postgres:17-alpine
    ...
```

**O que faz:**
- Define como subir um container PostgreSQL
- Expõe a porta 5432 (padrão do Postgres)
- Armazena dados em um volume (`postgres_data`)
- Quando você rodar `docker compose up -d`, isso sobe o banco

**Por que é importante:**
- Você e seus colegas têm o MESMO banco, sem instalar nada diferente
- Docker garante que funciona igual no Windows, Mac, Linux

---

## 2️⃣ **Arquivo: `.env` e `.env.example` (NOVO)**

`.env` (não vai para Git):
```env
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=usermanager
DATABASE_URL=postgresql://user:password@localhost:5432/usermanager
```

`.env.example` (vai para Git como referência):
- Mesmo conteúdo do `.env`, mas com valores de exemplo
- Quando um colega clonar o repo, copia `.env.example` → `.env` e insere suas credenciais

**Por que é importante:**
- Nunca coloca senha em código commitado
- Implementa o **Fator 12**: Configuração no Ambiente

---

## 3️⃣ **Arquivo: `app/database.py` (NOVO)**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

DATABASE_URL = os.getenv("DATABASE_URL", "...")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**O que faz:**
- Conecta ao PostgreSQL usando a URL de conexão do `.env`
- `get_db()` é uma "dependência" do FastAPI (veremos abaixo)
- Para testes, usa SQLite em memória (ver conftest.py)

**Por que é importante:**
- Centraliza toda a configuração do banco
- Garante que cada requisição HTTP tem sua própria sessão do banco

---

## 4️⃣ **Arquivo: `app/models.py` (NOVO)**

```python
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
```

**O que faz:**
- Define a tabela `users` no banco de dados
- `Column(Integer, primary_key=True)` = ID auto-incrementado
- `unique=True` = não pode ter dois emails iguais
- `index=True` = acelera buscas por email

**Por que é importante:**
- SQLAlchemy transforma essa classe em uma tabela real
- Você escreve em Python, não em SQL puro (mais seguro)

---

## 5️⃣ **Arquivo: `pyproject.toml` (ATUALIZADO)**

Adicionadas dependências:
```toml
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "jinja2>=3.1",
    "sqlalchemy>=2.0",           # ← ORM para banco de dados
    "psycopg2-binary>=2.9",       # ← Driver PostgreSQL
    "alembic>=1.12",              # ← Migrations (próxima missão)
    "python-dotenv>=1.0",         # ← Lê variáveis do .env
]
```

**Por que cada uma:**
- `sqlalchemy`: Converte Python em SQL
- `psycopg2-binary`: Permite conectar ao PostgreSQL
- `alembic`: Versiona mudanças na estrutura do banco
- `python-dotenv`: Lê o arquivo `.env`

---

## 6️⃣ **Arquivo: `app/main.py` (ATUALIZADO)**

### Antes (Missão 02):
```python
# Armazenamento em memória - sumia ao reiniciar!
USUARIOS = [
    {"id": 1, "nome": "Ademilson Alves", "email": "ademilson@example.com"},
    ...
]

@app.get("/users")
def listar_usuarios() -> list[User]:
    return USUARIOS  # Diretamente da lista
```

### Depois (Missão 03):
```python
from app.database import get_db, engine
from app.models import User as UserModel, Base

# Criar tabelas ao iniciar
@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

@app.get("/users")
def listar_usuarios(db: Session = Depends(get_db)) -> list[User]:
    usuarios = db.query(UserModel).all()  # Consulta o banco!
    return usuarios

@app.post("/users", response_model=User, status_code=201)
def criar_usuario(dados: UserCreate, db: Session = Depends(get_db)) -> User:
    usuario = UserModel(nome=dados.nome, email=dados.email)
    db.add(usuario)
    db.commit()      # Salva no banco
    db.refresh(usuario)  # Busca o ID gerado
    return usuario
```

**O que mudou:**
- `db: Session = Depends(get_db)` = FastAPI injeta a sessão do banco
- `db.query(UserModel).all()` = SELECT * FROM users
- `db.add()`, `db.commit()` = INSERT no banco
- A lista `USUARIOS` foi completamente removida

---

## 7️⃣ **Arquivo: `tests/conftest.py` (NOVO)**

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"  # Banco em RAM para testes
engine = create_engine(SQLALCHEMY_DATABASE_URL, ...)

def override_get_db():
    TestingSessionLocal = sessionmaker(...)
    db = TestingSessionLocal()
    yield db
    db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture
def client():
    Base.metadata.drop_all(bind=engine)   # Limpa testes anteriores
    Base.metadata.create_all(bind=engine) # Cria tabelas vazias
    return TestClient(app)
```

**O que faz:**
- Todos os testes usam um banco **SQLite em memória**, não o PostgreSQL
- Cada teste começa com um banco limpo (sem poluição de dados)
- `app.dependency_overrides` intercepta a dependência `get_db`
  - Ao invés de conectar ao PostgreSQL, conecta ao SQLite em memória

**Por que é importante:**
- Testes **não deixam lixo** no banco real
- Cada desenvolvedor pode rodar `pytest` **sem** precisar do PostgreSQL local
- Testes são **rápidos** (SQLite em memória é 1000x mais rápido)

---

## 8️⃣ **Arquivo: `tests/test_main.py` (ATUALIZADO)**

### Antes:
```python
def test_listar_usuarios_retorna_a_lista():
    resposta = client.get("/users")
    assert resposta.json() == main.USUARIOS  # Hardcoded na memória
```

### Depois:
```python
def test_listar_usuarios_vazio_retorna_lista_vazia(client: TestClient):
    """Quando nenhum usuário foi criado, a lista deve estar vazia."""
    resposta = client.get("/users")
    assert resposta.status_code == 200
    assert resposta.json() == []  # Banco vazio!

def test_criar_usuario_retorna_dados_com_id(client: TestClient):
    dados = {"nome": "Joao Silva", "email": "joao@example.com"}
    resposta = client.post("/users", json=dados)
    
    assert resposta.status_code == 201
    usuario = resposta.json()
    assert usuario["nome"] == "Joao Silva"
    assert "id" in usuario  # ID gerado pelo banco!
    assert usuario["id"] > 0
```

**O que mudou:**
- Não depende de dados hardcoded
- Cada teste cria seus próprios dados
- Verifica se o ID vem do banco (não mais gerado na mão)

---

## 9️⃣ **Arquivo: `RUNNING.md` (NOVO)**

Documentação de como rodar o projeto:
- Como subir Docker
- Como rodar testes
- Troubleshooting

---

## 🟣 **Arquivo: `start.ps1` (ATUALIZADO)**

Adicionado:
```powershell
# Verificar se Docker está rodando
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host 'Docker não foi encontrado...'
    exit 1
}

# Subir PostgreSQL se não estiver rodando
$running = docker ps --filter "name=usermanager-postgres" ...
if ($running -ne $containerName) {
    docker-compose up -d
    Start-Sleep -Seconds 5
}

# Depois, rodar uvicorn como antes
uv run uvicorn app.main:app --reload
```

**O que faz:**
- Verifica se Docker está instalado
- Sobe o container PostgreSQL automaticamente
- Aguarda o banco estar pronto
- Depois inicia o servidor

**Por que é importante:**
- Um colega roda `.\start.ps1` e tudo funciona automaticamente

---

## 🔄 Fluxo de Dados Agora

```
┌─────────────────────────────────────────────────┐
│ Cliente (navegador em http://localhost:8000)    │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │ FastAPI (main.py)     │
         │ /users → criar_usuario│
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │ SQLAlchemy (models.py)│
         │ Converte Python → SQL │
         └───────────┬───────────┘
                     │
                     ▼
         ┌──────────────────────────┐
         │ psycopg2 (driver)        │
         │ Fala com PostgreSQL      │
         └───────────┬──────────────┘
                     │
                     ▼
         ┌──────────────────────────┐
         │ PostgreSQL (em Docker)   │
         │ Tabela: users            │
         │ Dados: PERSISTEM!        │
         └──────────────────────────┘
```

---

## 🧪 Verificação: Testes Passando

```
tests/test_main.py::test_health_retorna_ok PASSED                        [ 16%]
tests/test_main.py::test_index_retorna_200 PASSED                        [ 33%]
tests/test_main.py::test_listar_usuarios_vazio_retorna_lista_vazia PASSED [ 50%]
tests/test_main.py::test_criar_usuario_retorna_dados_com_id PASSED       [ 66%]
tests/test_main.py::test_listar_usuarios_apos_criar PASSED               [ 83%]
tests/test_main.py::test_cada_usuario_tem_id_e_nome_e_email PASSED       [100%]

======================== 6 passed in 0.63s ========================
```

---

## 🚀 Como Rodar Agora

### 1. Primeira vez:
```bash
# Subir PostgreSQL
docker compose up -d

# Sincronizar dependências
uv sync

# Rodar servidor
uv run uvicorn app.main:app --reload
```

### 2. Próximas vezes:
```bash
.\start.ps1  # Tudo automático!
```

### 3. Rodar testes:
```bash
uv run pytest -v
```

---

## 📝 Conceitos Aprendidos

| Conceito | O que é | Por que importa |
|----------|--------|-----------------|
| **ORM** | Object-Relational Mapping (SQLAlchemy) | Escreve DB em Python, não SQL |
| **Migration** | Versionamento da estrutura do DB | Histórico de mudanças no schema |
| **Dependência** | `Depends(get_db)` no FastAPI | Injeta sessão do banco em cada requisição |
| **Transação** | `db.commit()` | Salva atomicamente tudo ou nada |
| **Fixture** | `@pytest.fixture` | Setup/teardown de testes |
| **Override** | `app.dependency_overrides[get_db]` | Substitui dependência nos testes |
| **Variáveis de Ambiente** | `.env` | Credenciais não ficam no código |

---

## ✨ O que Mudou Visualmente?

**Absolutamente nada!** 😄

- A tela continua igual
- Os endpoints retornam os mesmos dados
- Usuário não vê diferença

**Mas por baixo:**
- Antes: Dados em memória (Python dict)
- Depois: Dados em banco PostgreSQL real

Essa é a mágica da Engenharia de Software: trocar o motor sem que ninguém perceba!

---

## 🎯 Checklist da Missão

- ✅ Existe um PostgreSQL rodando em Docker
- ✅ Credenciais do banco em `.env` (não em código)
- ✅ Estrutura da tabela descrita em `models.py`
- ✅ Criar e listar usuários funciona
- ✅ Usuários **persistem** após reiniciar servidor
- ✅ Testes usam banco isolado (SQLite em memória)
- ✅ `pytest` passa

---

## 🔮 Próximo Passo (Missão 04)

Agora que temos o banco funcionando, vamos aprender **Migrations com Alembic**:
- Versionar mudanças na estrutura do banco
- Quando um colega faz `git pull`, as migrations rodam automaticamente
- Histórico completo de quem mudou o quê e quando

Mas isso é assunto para a próxima missão! 🚀
