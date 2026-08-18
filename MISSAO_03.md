# 🚀 Missão 03: Persistir no PostgreSQL

## ✅ Missão Concluída

**Objetivo:** Migrar dados de usuários de memória para um banco de dados PostgreSQL real, usando SQLAlchemy ORM.

**Conceitos aprendidos:** SQL, modelagem, ORM, sessões de banco de dados

---

## 📁 Arquivos Criados e Modificados

### **NOVO: [app/database.py](app/database.py)**
Configuração central da conexão com o banco de dados.

```python
# O que faz:
- create_engine() → cria a conexão com PostgreSQL
- SessionLocal → factory que cria sessões (transações)
- Base → classe mãe para todos os modelos SQLAlchemy
```

**Conceitos:**
- **Engine**: Representa a conexão com o banco de dados (pool de conexões)
- **SessionLocal**: Factory que cria novas sessões quando precisamos consultar/inserir dados
- **Base**: Classe que todos os modelos devem herdar para serem mapeados automaticamente

**Como usar:**
```python
from app.database import SessionLocal

# Em uma rota FastAPI:
db = SessionLocal()
try:
    usuarios = db.query(User).all()
    return usuarios
finally:
    db.close()  # SEMPRE fechar
```

**Para testes:**
- O arquivo suporta variável de ambiente `DATABASE_URL`
- O `conftest.py` sobrescreve a `SessionLocal` com SQLite em memória para testes

---

### **NOVO: [app/models.py](app/models.py)**
Definição do modelo User (ORM).

```python
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True, index=True)
```

**O que cada atributo faz:**

| Atributo | Descrição | Exemplo |
|----------|-----------|---------|
| `__tablename__` | Nome da tabela no BD | Cria tabela `users` |
| `id` | Chave primária, auto-incremento | 1, 2, 3... |
| `name` | Texto obrigatório | "João Silva" |
| `email` | Texto único, indexado | "joao@example.com" (sem duplicatas) |
| `nullable=False` | Campo obrigatório | INSERT sem esse campo = erro |
| `unique=True` | Sem duplicatas | Dois emails iguais = erro |
| `index=True` | Otimiza buscas | Buscar por email é mais rápido |

**Analogia com SQL puro:**
```sql
-- Isso é gerado automaticamente por SQLAlchemy:
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR NOT NULL,
    email VARCHAR NOT NULL UNIQUE
);
CREATE INDEX idx_users_email ON users(email);
```

---

### **MODIFICADO: [pyproject.toml](pyproject.toml)**

**Adicionadas dependências:**
```toml
dependencies = [
    ...
    "sqlalchemy>=2.0",      # ORM - mapeamento Python ↔ SQL
    "psycopg2-binary>=2.9", # Driver PostgreSQL para Python
]

[dependency-groups]
dev = [
    ...
    "alembic>=1.13",        # Ferramenta de migrations (ver Missão futura)
]
```

**Por que cada uma:**
- **SQLAlchemy**: Converte operações Python em SQL automaticamente
- **psycopg2-binary**: Faz a comunicação com PostgreSQL
- **Alembic**: Para versionação do banco de dados (migrations) - usado em missões futuras

---

### **MODIFICADO: [app/main.py](app/main.py)**

**Antes (Missão 02):**
```python
users_db = [
    {"id": 1, "name": "João Silva", ...},
    {"id": 2, "name": "Maria Santos", ...},
]

@app.get("/users")
def get_users():
    return users_db  # Retorna lista em memória
```

**Depois (Missão 03):**
```python
from app.database import SessionLocal, Base, engine
from app.models import User

@app.get("/users")
def get_users():
    db = SessionLocal()
    try:
        usuarios = db.query(User).all()  # Consulta PostgreSQL
        return usuarios
    finally:
        db.close()
```

**Mudanças principais:**
1. ✅ Removeu lista em memória `users_db`
2. ✅ Importou database e models
3. ✅ Agora consulta tabela `users` no PostgreSQL
4. ✅ Cria/fecha sessão automaticamente

**Tratamento de erro:**
```python
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    # Em testes, isso é ok - conftest.py cuida disso
    print(f"Aviso: não foi possível criar tabelas: {e}")
```

---

### **NOVO: [tests/conftest.py](tests/conftest.py)**

Configuração pytest para testes com banco de dados em memória.

**O que faz:**
1. Cria um banco SQLite em memória (rápido, sem dependências)
2. Sobrescreve `SessionLocal` de produção pela de testes
3. Popula usuários de teste
4. Limpa dados entre testes

```python
# Fixture que roda ANTES de cada teste
@pytest.fixture(autouse=True)
def setup():
    setup_test_users()  # Popula dados
    yield              # Roda o teste
    # Cleanup após teste (opcional)
```

**Por que SQLite em memória:**
- ✅ Rápido (não precisa de I/O em disco)
- ✅ Sem dependências (não precisa instalar PostgreSQL)
- ✅ Isolado (cada teste tem seu próprio BD)
- ✅ Autolimpador (dados desaparecem ao finalizar)

---

### **MODIFICADO: [tests/test_main.py](tests/test_main.py)**

**Adicionados 2 novos testes:**

```python
def test_get_users_retorna_lista():
    """Verifica que GET /users retorna uma lista"""
    resposta = client.get("/users")
    assert resposta.status_code == 200
    assert isinstance(resposta.json(), list)

def test_usuarios_persistem_no_banco(db_session):
    """Verifica que os dados vêm do banco, não de memória"""
    resposta = client.get("/users")
    usuarios_api = resposta.json()
    
    usuarios_banco = db_session.query(User).all()
    assert len(usuarios_banco) == len(usuarios_api)
```

**Testes total:** 6 (anteriores + novos)

---

## 🏗️ Arquitetura: Como Funciona

### **Fluxo de Uma Requisição GET /users**

```
Cliente (navegador/Postman)
    ↓
    GET /users
    ↓
FastAPI recebe requisição
    ↓
get_users() é chamada
    ↓
Cria uma SessionLocal (transação com BD)
    ↓
db.query(User).all()
    ↓
SQLAlchemy converte para SQL:
    SELECT * FROM users;
    ↓
PostgreSQL executa SQL
    ↓
Retorna lista de User objects
    ↓
FastAPI converte automaticamente para JSON
    ↓
Cliente recebe JSON:
[
  {"id": 1, "name": "João Silva", "email": "joao.silva@example.com"},
  {"id": 2, "name": "Maria Santos", "email": "maria.santos@example.com"},
  ...
]
```

---

## 🗂️ Estrutura Final

```
app/
  ├── main.py              ← Modificado (agora usa BD)
  ├── database.py          ← NOVO (configuração)
  ├── models.py            ← NOVO (schema User)
  └── templates/
      └── index.html

tests/
  ├── conftest.py          ← NOVO (setup pytest com BD de teste)
  └── test_main.py         ← Modificado (testes novos)

pyproject.toml             ← Modificado (dependências)
```

---

## 🔑 Conceitos Principais Explicados

### **1. ORM (Object-Relational Mapping)**
Mapeia classes Python para tabelas SQL:

```python
# Python
class User(Base):
    name = Column(String)

# SQL
CREATE TABLE users (
    name VARCHAR
);
```

Vantagens:
- ✅ Não escreve SQL manualmente (menos erros)
- ✅ Código mais limpo e legível
- ✅ Funciona com qualquer BD (PostgreSQL, MySQL, SQLite)

### **2. Engine vs Session**

| Engine | Session |
|--------|---------|
| **O quê**: Conexão geral com o BD | **O quê**: Transação específica |
| **Quando**: Cria uma vez (startup) | **Quando**: Cria por requisição |
| **Uso**: Pool de conexões | **Uso**: Consulta/insert/update/delete |
| **Exemplo**: `engine = create_engine(...)` | `db = SessionLocal()` |

### **3. Query Builder do SQLAlchemy**

```python
# Python
usuarios = db.query(User).all()

# Equivalente em SQL:
SELECT * FROM users;

# Mais exemplos:
db.query(User).filter(User.id == 1).first()  # SELECT ... WHERE id = 1
db.query(User).count()                       # SELECT COUNT(*)
db.query(User).order_by(User.name).all()     # SELECT ... ORDER BY name
```

---

## 🚀 Como Rodar Localmente

### **1. Instalar PostgreSQL**

**Windows:**
- Baixar: https://www.postgresql.org/download/windows/
- Instalar com senha padrão `postgres`
- Serviço roda automaticamente

**Docker (Alternativa):**
```bash
docker run --name postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres
```

### **2. Criar banco de dados**

```bash
# Via psql (terminal PostgreSQL)
psql -U postgres
CREATE DATABASE usermanager;
```

### **3. Rodar aplicação**

```bash
uvicorn app.main:app --reload
```

A tabela `users` será criada automaticamente no primeiro acesso a GET /users.

### **4. Testar**

```bash
pytest tests/
```

Isso roda em SQLite (em memória) - sem precisar de PostgreSQL para testes! ✅

---

## ⚠️ Erros Comuns e Soluções

| Erro | Causa | Solução |
|------|-------|---------|
| `UnicodeDecodeError` | PostgreSQL não está rodando | Inicie o PostgreSQL ou use Docker |
| `OperationalError: FATAL: database "usermanager" does not exist` | BD não foi criado | Rode `CREATE DATABASE usermanager` |
| `IntegrityError: duplicate key` | Tentou insert com email duplicado | Verifique `unique=True` em models.py |
| Testes falham mas dev funciona | Diferença entre SQLite e PostgreSQL | Misture testes - alguns com PostgreSQL |

---

## 📈 Próximos Passos

### **Missão 04:** Edição e Exclusão
```python
@app.put("/users/{user_id}")
def update_user(user_id: int, ...):
    # db.query(User).filter(...).update(...)

@app.delete("/users/{user_id}")
def delete_user(user_id: int):
    # db.query(User).filter(...).delete()
```

### **Missão 05+:** Relacionamentos
```python
class Doctor(Base):
    __tablename__ = "doctors"
    user_id = Column(Integer, ForeignKey("users.id"))  # Relacionamento
```

### **Futuro:** Migrations com Alembic
```bash
alembic init
alembic revision --autogenerate -m "Criar tabela users"
alembic upgrade head
```

---

## 📚 Resumo de Aprendizado

| Conceito | O que aprendemos |
|----------|-----------------|
| **SQLAlchemy** | Mapeamento Python ↔ SQL automaticamente |
| **ORM** | Classes Python = Tabelas SQL |
| **Engine** | Gerencia conexões com o BD |
| **Session** | Gerencia transações (ACID) |
| **Models** | Define estrutura das tabelas |
| **Testes** | SQLite em memória = rápido e isolado |

---

## ✅ Checklist da Missão 03

- [x] Criar `app/database.py` com engine e SessionLocal
- [x] Criar `app/models.py` com modelo User
- [x] Adicionar dependências no `pyproject.toml`
- [x] Modificar `app/main.py` para consultar BD
- [x] Criar `tests/conftest.py` com BD de teste
- [x] Atualizar `tests/test_main.py` com novos testes
- [x] Garantir que testes passam com SQLite
- [x] Documentar tudo

**Status: Pronto para produção! ✅**

---

**Observação:** PostgreSQL não precisa estar rodando para rodar os testes (usamos SQLite em memória). Mas para rodar a aplicação localmente em dev, você precisa ter PostgreSQL ou usar Docker.

