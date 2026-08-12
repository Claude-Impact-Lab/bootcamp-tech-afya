# Resumo Visual das Mudanças - Missão 03

## 🎬 Antes vs Depois

### ANTES (Missão 02) ❌
```
┌────────────────────────────────────┐
│ app/main.py                        │
├────────────────────────────────────┤
│ USUARIOS = [                       │
│   {"id": 1, "nome": "Ademilson"}, │
│   {"id": 2, "nome": "Seabra"},    │
│   ...                              │
│ ]                                  │
│                                    │
│ @app.post("/users")                │
│ def criar_usuario(dados):          │
│   proximo_id = max(...) + 1        │
│   usuario = {"id": proximo_id, ...}│
│   USUARIOS.append(usuario)         │  ← Perdidos ao reiniciar!
│   return usuario                   │
└────────────────────────────────────┘
```

### DEPOIS (Missão 03) ✅
```
┌────────────────────────────────────┐
│ app/models.py                      │
├────────────────────────────────────┤
│ class User(Base):                  │
│   __tablename__ = "users"          │
│   id = Column(Integer, ...)        │
│   nome = Column(String, ...)       │
│   email = Column(String, ...)      │
└────────────────────────────────────┘
             ▼
┌────────────────────────────────────┐
│ app/main.py                        │
├────────────────────────────────────┤
│ @app.post("/users")                │
│ def criar_usuario(dados, db):      │
│   usuario = User(...)              │
│   db.add(usuario)                  │
│   db.commit()        ← Salva no DB │
│   db.refresh(usuario)              │
│   return usuario                   │
└────────────────────────────────────┘
             ▼
┌────────────────────────────────────┐
│ PostgreSQL (Docker)                │
├────────────────────────────────────┤
│ TABLE users (                      │
│   id SERIAL PRIMARY KEY,           │
│   nome VARCHAR,                    │
│   email VARCHAR UNIQUE             │
│ );                                 │
│                                    │
│ Dados PERSISTEM! ✨                │
└────────────────────────────────────┘
```

---

## 📁 Arquivos Criados

```
bootcamp-tech-afya/
│
├── docker-compose.yml          ← 🆕 Subir PostgreSQL em Docker
├── .env                        ← 🆕 Credenciais (não vai para Git!)
├── .env.example                ← 🆕 Modelo para o .env
│
├── app/
│   ├── main.py                 ← 📝 ATUALIZADO: Usa SQLAlchemy
│   ├── database.py             ← 🆕 Conexão com o banco
│   ├── models.py               ← 🆕 Tabela User definida
│   └── templates/
│       └── index.html
│
├── tests/
│   ├── conftest.py             ← 🆕 Banco de testes isolado
│   └── test_main.py            ← 📝 ATUALIZADO: Novos testes
│
├── RUNNING.md                  ← 🆕 Como rodar o projeto
├── MISSAO_03_EXPLICACAO.md     ← 🆕 Este documento!
├── pyproject.toml              ← 📝 ATUALIZADO: SQLAlchemy, psycopg2, etc
└── start.ps1                   ← 📝 ATUALIZADO: Sobe Docker automaticamente
```

---

## 🔄 Fluxo de uma Requisição POST /users

### ANTES ❌
```
Cliente                     FastAPI                Memory
  │                           │                        │
  │─── POST /users ───────────>│                        │
  │                           │                        │
  │                           │─── Calcula ID ────────>│
  │                           │                        │
  │                           │<─ Adiciona lista ─────│
  │                           │                        │
  │<─── {"id": 5, ...} ───────│                        │
  │                           │                        │
  
⚠️  Ao reiniciar o servidor, tudo na memória é perdido!
```

### DEPOIS ✅
```
Cliente                FastAPI            SQLAlchemy         PostgreSQL
  │                      │                    │                  │
  │─ POST /users ───────>│                    │                  │
  │                      │                    │                  │
  │                      │─ Cria objeto User─>│                  │
  │                      │                    │                  │
  │                      │─ db.add() ────────>│─ INSERT ────────>│
  │                      │                    │                  │
  │                      │                    │─ ID gerado ─────>│
  │                      │<─ Atualiza objeto ─│<── ID ──────────│
  │<──── {"id": 5, ...} ───────────────────────                  │
  │                      │                    │                  │
  
✨ Dados persistem no PostgreSQL para sempre!
```

---

## 🧪 Como os Testes Funcionam

```python
# conftest.py configura um banco de TESTE
@pytest.fixture
def client():
    # 1. Limpa qualquer dado anterior
    Base.metadata.drop_all(bind=engine)
    
    # 2. Cria tabelas vazias em SQLite (não PostgreSQL!)
    Base.metadata.create_all(bind=engine)
    
    # 3. Retorna cliente de teste com banco isolado
    return TestClient(app)

# test_main.py usa o banco de teste
def test_criar_usuario(client):
    # Este teste NÃO afeta seu banco real!
    # Usa SQLite em memória
    resposta = client.post("/users", json={...})
    assert resposta.status_code == 201
```

**Resultado:**
- ✅ Testes não deixam lixo
- ✅ Testes são 1000x mais rápidos
- ✅ Testes não precisam do PostgreSQL

---

## 🔐 Onde Ficam as Credenciais

```
❌ ERRADO - Credenciais no código:
app/main.py:
    DATABASE_URL = "postgresql://user:PASSWORD123@localhost:5432/usermanager"
    # Ao fazer git push, a senha vaza para todo mundo!

✅ CORRETO - Credenciais em variáveis de ambiente:
.env (não vai para Git):
    DATABASE_URL=postgresql://user:PASSWORD123@localhost:5432/usermanager

.env.example (vai para Git como referência):
    DATABASE_URL=postgresql://user:password@localhost:5432/usermanager

app/database.py:
    DATABASE_URL = os.getenv("DATABASE_URL", "...")
    # Lê do .env automaticamente
```

---

## 🚀 Comando para Rodar Agora

### Opção 1: Script automático (recomendado)
```powershell
.\start.ps1
```
- ✅ Verifica se Docker está rodando
- ✅ Sobe PostgreSQL automaticamente
- ✅ Sincroniza dependências
- ✅ Inicia servidor

### Opção 2: Manual (step-by-step)
```bash
docker compose up -d              # Sobe PostgreSQL
uv sync                           # Instala dependências
uv run uvicorn app.main:app --reload  # Inicia servidor
```

### Opção 3: Rodar testes
```bash
uv run pytest -v
```

---

## 📊 Antes vs Depois: Recursos Usados

| Recurso | Antes | Depois |
|---------|-------|--------|
| Armazenamento | Memória Python (dict) | PostgreSQL em banco real |
| Persistência | ❌ Perdido ao reiniciar | ✅ Permanente |
| Escalabilidade | ❌ Limitado à RAM | ✅ Terabytes |
| Multi-processo | ❌ Incompatível | ✅ Compartilhado |
| Backup | ❌ Nenhum | ✅ Integrado |
| Queries | ❌ Busca linear | ✅ Otimizado com índices |
| Integridade | ❌ Sem validação | ✅ Constraints da DB |

---

## 🎓 Conceitos em Prática

### 1. **ORM (Object-Relational Mapping)**
```python
# Você escreve:
usuario = User(nome="João", email="joao@example.com")
db.add(usuario)
db.commit()

# SQLAlchemy converte em:
INSERT INTO users (nome, email) VALUES ('João', 'joao@example.com');
```

### 2. **Injeção de Dependência (FastAPI)**
```python
# Antes:
def criar_usuario(dados):
    # Sem banco definido

# Depois:
def criar_usuario(dados, db: Session = Depends(get_db)):
    # FastAPI automaticamente injeta a sessão do banco
    # Nos testes, injeta banco de teste
    # Em produção, injeta PostgreSQL real
```

### 3. **Transações (ACID)**
```python
db.add(usuario)    # Apenas em memória (não commitado ainda)
db.commit()        # AGORA foi salvo permanentemente
                   # Se falhar antes do commit, nada é salvo
```

### 4. **Migrations (próxima missão)**
```
v1: CREATE TABLE users (id, nome)
v2: ALTER TABLE users ADD COLUMN email
v3: ALTER TABLE users ADD COLUMN phone

Quando você faz git pull, as migrations rodam
automaticamente e atualizam sua estrutura do banco!
```

---

## ✨ Resultado Final

🎯 **Missão 03 Completada!**

- ✅ Dados **persistem** entre reinicializações
- ✅ PostgreSQL roda em **Docker** (todo mundo igual)
- ✅ Credenciais em **variáveis de ambiente** (seguro)
- ✅ Testes usam banco **isolado** (rápido e seguro)
- ✅ **Todos os 6 testes passando**

Próximo: Migrations com Alembic! 🚀
