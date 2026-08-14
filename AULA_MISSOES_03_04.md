# Aula: Missões 03 e 04 — Banco de Dados e CRUD Completo

## Missão 03: Persistência de Dados com SQLAlchemy

### O que é um banco de dados?

Um **banco de dados** é um arquivo ou servidor que armazena dados de forma estruturada e durável. Os dados criados na aplicação precisam ser **persistidos** — ou seja, salvos para não desaparecerem quando a aplicação reinicia.

```
Sem banco:  [ App em memória ] —— dados perdidos ao desligar
Com banco:  [ App ] ↔ [ Arquivo data.db ] —— dados salvos permanentemente
```

### SQLAlchemy: O mapa da aplicação para banco

**SQLAlchemy** é um ORM (Object-Relational Mapping) que traduz:

- **Classe Python** → **Tabela no banco**
- **Atributo da classe** → **Coluna da tabela**
- **Instância da classe** → **Linha da tabela**

```python
# Definição no Python
class User(Base):
    __tablename__ = "users"
    id: int           # Coluna: id INTEGER PRIMARY KEY
    name: str         # Coluna: name VARCHAR(255)
    password: str     # Coluna: password VARCHAR(255)

# Transforma em SQL automático:
# CREATE TABLE users (
#     id INTEGER PRIMARY KEY AUTO_INCREMENT,
#     name VARCHAR(255) NOT NULL,
#     password VARCHAR(255) NOT NULL
# );
```

### Arquitetura: Camadas da aplicação

```
┌─────────────────────────────────────┐
│   Frontend: HTML + JavaScript       │
├─────────────────────────────────────┤
│   API Layer: FastAPI (@app.post)    │
├─────────────────────────────────────┤
│   Business: Validação Pydantic      │
├─────────────────────────────────────┤
│   ORM: SQLAlchemy (User model)      │
├─────────────────────────────────────┤
│   Database Layer: SQLite (data.db)  │
└─────────────────────────────────────┘
```

### CREATE TABLE: Criação automática

Ao importar `app.models`, o SQLAlchemy cria as tabelas:

```python
# app/database.py
from app.models import Base

Base.metadata.create_all(bind=engine)  # ← Cria tabela "users"
```

### INSERT: Criar registro (POST)

```python
@app.post("/users", status_code=201)
def create_user(user: UserCreate, db: Session):
    # 1. Criar instância Python
    db_user = User(name=user.name, password=user.password)
    
    # 2. Adicionar à sessão
    db.add(db_user)
    
    # 3. Fazer commit (salvar no banco)
    db.commit()
    
    # 4. Recarregar para obter o ID gerado
    db.refresh(db_user)
    
    return UserResponse.model_validate(db_user)
```

### SELECT: Ler registros (GET)

```python
@app.get("/users")
def list_users(db: Session) -> list[UserResponse]:
    # Query retorna lista de objetos User
    users = db.query(User).all()
    
    # Converter para Pydantic (remove senha!)
    return [UserResponse.model_validate(user) for user in users]
```

**Importante:** Nunca retornar senha no JSON! Use `UserResponse` que tem apenas `id` e `name`.

---

## Missão 04: CRUD Completo (Update e Delete)

### CRUD = Create, Read, Update, Delete

| Operação | Método | Rota | Status |
|----------|--------|------|--------|
| **Create** | POST | `/users` | 201 Created |
| **Read** | GET | `/users` | 200 OK |
| **Update** | PUT | `/users/{id}` | 200 OK |
| **Delete** | DELETE | `/users/{id}` | 204 No Content |

### UPDATE: Editar registro (PUT)

```python
@app.put("/users/{user_id}")
def update_user(user_id: int, user: UserCreate, db: Session) -> UserResponse:
    # 1. Buscar o usuário no banco
    db_user = db.query(User).filter(User.id == user_id).first()
    
    # 2. Validar se existe
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario não encontrado")
    
    # 3. Atualizar atributos
    db_user.name = user.name
    db_user.password = user.password
    
    # 4. Salvar mudanças
    db.commit()
    db.refresh(db_user)
    
    return UserResponse.model_validate(db_user)
```

**Fluxo HTTP:**
```
Client          Server
  │               │
  ├─ PUT /users/1 ─→
  │   { "name": "Maria", "password": "senha123" }
  │               │
  │               ├─ Buscar user id=1 no banco
  │               ├─ Atualizar valores
  │               ├─ Commit
  │               │
  ←─ 200 OK ──────┤
  │   { "id": 1, "name": "Maria" }
```

### DELETE: Remover registro

```python
@app.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session):
    # 1. Buscar o usuário
    db_user = db.query(User).filter(User.id == user_id).first()
    
    # 2. Validar se existe
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario não encontrado")
    
    # 3. Remover do banco
    db.delete(db_user)
    
    # 4. Confirmar deleção
    db.commit()
    
    # Status 204 não retorna conteúdo JSON
```

**Diferença de status:**
- **200 OK** → Retorna dados no corpo
- **204 No Content** → Sem corpo (apenas confirma sucesso)

---

## Testes: Garantindo qualidade

### Test-Driven Development (TDD)

Escrever testes **antes** do código:

```python
# 1. Escrever o teste (RED)
def test_deleta_usuario_existente(client):
    # Criar usuário
    resposta = client.post("/users", json={"name": "Pedro", "password": "123456"})
    user_id = resposta.json()["id"]
    
    # Deletar
    resposta_delete = client.delete(f"/users/{user_id}")
    assert resposta_delete.status_code == 204
    
    # Verificar que foi deletado
    resposta_get = client.get("/users")
    assert len(resposta_get.json()) == 0

# 2. Implementar a rota (GREEN)
@app.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404)
    db.delete(db_user)
    db.commit()

# 3. Testes passam (REFACTOR)
```

### Isolamento de testes

Cada teste deve começar com banco **limpo**:

```python
@pytest.fixture
def db():
    # Iniciar transação
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    # Fazer rollback após teste (desfaz todas as mudanças)
    transaction.rollback()
```

**Sem isolamento:**
```
Test 1: Criar usuário A ✓
Test 2: Criar usuário B, mas vê usuário A também! ✗ (dados vazados)

Com isolamento:
Test 1: Criar usuário A ✓ → Rollback
Test 2: Criar usuário B, vê só B ✓
```

---

## Dependências de Banco

### Adicionadas ao `pyproject.toml`:

```toml
sqlalchemy = ">=2.0"          # ORM para Python
psycopg = {version = ">=3.1", extras = ["binary"]} # Driver PostgreSQL
```

### Como usar em produção

```python
# Desenvolvimento: SQLite (arquivo simples)
DATABASE_URL = "sqlite:///data.db"

# Produção: PostgreSQL (servidor profissional)
DATABASE_URL = "postgresql://user:password@localhost/mydb"
```

O código FastAPI funciona **igual em ambos** — é transparente!

---

## Checklist de Segurança

❌ **Nunca fazer:**
```python
db_user.password = request.password  # Senha em texto plano!
return db_user  # Retorna senha no JSON!
query = f"SELECT * FROM users WHERE id = {id}"  # SQL Injection!
```

✅ **Sempre fazer:**
```python
db_user.password = hash_password(request.password)  # Hash
return UserResponse.model_validate(db_user)  # Sem senha
query = db.query(User).filter(User.id == id)  # Parâmetros seguros
```

---

## Desafios para praticar

1. **Adicionar busca:** Rota `GET /users?name=Maria` que filtra por nome
2. **Adicionar paginação:** `GET /users?page=1&limit=10` para listar 10 por página
3. **Adicionar timestamp:** Coluna `created_at` que registra quando foi criado
4. **Soft delete:** Marcar como deletado sem remover do banco (segurança)
5. **Fazer hash de senha:** Usar `bcrypt` para não guardar senha em texto plano

---

## Resumo

| Conceito | O que é | Exemplo |
|----------|---------|---------|
| **ORM** | Traduz classes → tabelas | `User` → `CREATE TABLE users` |
| **Session** | Conexão com banco | `db.query(User)` |
| **Query** | Busca dados | `db.query(User).filter(User.id == 1)` |
| **Commit** | Salva mudanças | `db.commit()` |
| **Rollback** | Desfaz mudanças | `transaction.rollback()` |
| **HTTPException** | Erro da API | `raise HTTPException(status_code=404)` |

