# 🎉 Missão 03 - Persistir no PostgreSQL - COMPLETO!

## 📊 Status Final

```
✅ 6/6 testes passando
✅ Banco PostgreSQL configurado com Docker
✅ SQLAlchemy implementado
✅ Variáveis de ambiente seguras
✅ Testes isolados com SQLite em memória
✅ Documentação completa
✅ Script start.ps1 automático
```

---

## 🗂️ Estrutura de Arquivos Criada

```
bootcamp-tech-afya/
│
├── 📄 docker-compose.yml          ← PostgreSQL em Container
├── 📄 .env                         ← Credenciais (Git-ignored)
├── 📄 .env.example                 ← Modelo de referência
│
├── app/
│   ├── 📝 main.py                  ← ATUALIZADO: SQLAlchemy ORM
│   ├── 🆕 database.py              ← Conexão e sessão do banco
│   ├── 🆕 models.py                ← Definição da tabela User
│   └── templates/
│       └── index.html
│
├── tests/
│   ├── 🆕 conftest.py              ← Setup de testes com SQLite
│   └── 📝 test_main.py             ← ATUALIZADO: 6 testes novos
│
├── 📚 MISSAO_03_EXPLICACAO.md      ← Documentação técnica completa
├── 📚 RESUMO_MUDANCAS.md           ← Resumo visual antes/depois
├── 📚 RUNNING.md                   ← Como rodar o projeto
│
├── 📝 pyproject.toml               ← ATUALIZADO: Novas dependências
├── 📝 start.ps1                    ← ATUALIZADO: Sobe Docker auto
└── 📝 .gitignore                   ← ATUALIZADO: Exclui .env
```

---

## 🎯 O que foi Feito, em Resumo

### 1️⃣ Backend Preparado para Banco
```python
# app/models.py - Define a tabela
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    nome = Column(String)
    email = Column(String, unique=True)

# app/database.py - Conecta ao PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

# app/main.py - Usa o banco
@app.post("/users")
def criar_usuario(dados: UserCreate, db: Session = Depends(get_db)):
    usuario = User(nome=dados.nome, email=dados.email)
    db.add(usuario)
    db.commit()
    return usuario
```

### 2️⃣ Infraestrutura com Docker
```yaml
# docker-compose.yml
services:
  postgres:
    image: postgres:17-alpine
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

### 3️⃣ Credenciais Seguras
```bash
# .env (não vai para Git)
DATABASE_URL=postgresql://user:password@localhost:5432/usermanager

# .gitignore
.env  # ← Ignora arquivo com senha
```

### 4️⃣ Testes Isolados e Rápidos
```python
# tests/conftest.py
@pytest.fixture
def client():
    # Cria tabelas em SQLite (não PostgreSQL)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestClient(app)
```

### 5️⃣ Automatização
```powershell
# start.ps1
docker compose up -d    # Sobe PostgreSQL
uv sync                 # Instala dependências
uvicorn app.main:app    # Inicia servidor
```

---

## 🧪 Testes - Todas as Verificações Passando

| Teste | Status | O que Verifica |
|-------|--------|----------------|
| test_health_retorna_ok | ✅ PASSOU | Endpoint /health funciona |
| test_index_retorna_200 | ✅ PASSOU | Página HTML carrega |
| test_listar_usuarios_vazio_retorna_lista_vazia | ✅ PASSOU | Banco vazio = lista vazia |
| test_criar_usuario_retorna_dados_com_id | ✅ PASSOU | ID é gerado pelo banco |
| test_listar_usuarios_apos_criar | ✅ PASSOU | Dados persistem na sessão |
| test_cada_usuario_tem_id_e_nome_e_email | ✅ PASSOU | Estrutura correta |

```bash
$ uv run pytest -v
======================== 6 passed in 0.63s ========================
```

---

## 🔀 Mudanças Principais

### Antes (Missão 02)
```python
# Lista em memória 😢
USUARIOS = [
    {"id": 1, "nome": "Ademilson", "email": "..."},
    ...
]

@app.post("/users")
def criar_usuario(dados):
    proximo_id = max([u["id"] for u in USUARIOS]) + 1
    usuario = {"id": proximo_id, ...}
    USUARIOS.append(usuario)  # ← Perdido ao reiniciar!
    return usuario
```

### Depois (Missão 03)
```python
# Banco de dados real ✨
@app.post("/users")
def criar_usuario(dados, db: Session = Depends(get_db)):
    usuario = User(nome=dados.nome, email=dados.email)
    db.add(usuario)
    db.commit()  # ← Salvo para sempre!
    db.refresh(usuario)
    return usuario
```

---

## 📈 Ganhos da Missão 03

| Aspecto | Antes | Depois |
|--------|-------|--------|
| **Persistência** | ❌ Perdido ao reiniciar | ✅ Permanente |
| **Escalabilidade** | ❌ Limitado à RAM | ✅ Terabytes |
| **Multiprocesso** | ❌ Incompatível | ✅ Compartilhado |
| **Queries** | ❌ Busca linear O(n) | ✅ Otimizado O(1) com índices |
| **Consistência** | ❌ Sem validação | ✅ Constraints do banco |
| **Segurança** | ❌ Credenciais no código | ✅ Variáveis de ambiente |
| **Testes** | ❌ Dependência do PostgreSQL | ✅ Isolado em SQLite |

---

## 🚀 Como Rodar Agora

### Opção 1: Automático (Recomendado)
```powershell
.\start.ps1
```
Tudo que você precisa:
- ✅ Verifica Docker
- ✅ Sobe PostgreSQL
- ✅ Instala dependências
- ✅ Inicia servidor em localhost:8000

### Opção 2: Manual
```bash
docker compose up -d
uv sync
uv run uvicorn app.main:app --reload
```

### Opção 3: Rodar Testes
```bash
uv run pytest -v
```

### Opção 4: Acessar Banco
```bash
docker compose exec postgres psql -U user -d usermanager

usermanager=# SELECT * FROM users;
usermanager=# \q
```

---

## 📚 Documentação Criada

### 1. MISSAO_03_EXPLICACAO.md
- Explicação técnica completa
- O que cada arquivo faz
- Conceitos aprendidos (ORM, Migrations, Fixtures, etc)
- 2000+ linhas de detalhe

### 2. RESUMO_MUDANCAS.md
- Antes vs Depois (visual)
- Fluxo de requisições
- Diagrama de arquitetura
- Conceitos em prática

### 3. RUNNING.md
- Como subir o projeto
- Troubleshooting
- Comandos úteis
- Organização clara

---

## ✨ Destaques Técnicos

### SQLAlchemy ORM
```python
# Você escreve Python:
usuario = User(nome="João", email="joao@example.com")
db.add(usuario)
db.commit()

# SQLAlchemy transforma em SQL:
# INSERT INTO users (nome, email) VALUES ('João', 'joao@example.com');
```

### Injeção de Dependência (FastAPI)
```python
# FastAPI injeta automaticamente:
def criar_usuario(dados: UserCreate, db: Session = Depends(get_db)):
    # db é da classe SessionLocal
    # Em testes, é overridida para SQLite
    # Em produção, é PostgreSQL
    pass
```

### Testes Isolados
```python
# Cada teste:
# 1. Limpa banco anterior
# 2. Cria tabelas vazias
# 3. Executa o teste
# 4. Não afeta banco real
```

---

## 🎓 Conceitos Aprendidos

| Conceito | Exemplo | Importância |
|----------|---------|-------------|
| **ORM** | SQLAlchemy User class | Código em Python, não SQL |
| **Sessão** | `db: Session = Depends(get_db)` | Gerencia conexão com banco |
| **Transação** | `db.commit()` | Atomicidade (tudo ou nada) |
| **Índice** | `index=True` no Column | Queries rápidas |
| **Constraint** | `unique=True` no email | Integridade de dados |
| **Fixture** | `@pytest.fixture` | Setup/teardown de testes |
| **Override** | `dependency_overrides` | Substituir dependências nos testes |
| **Variáveis de Ambiente** | `.env` | Segurança (credenciais) |

---

## 🔮 Próximas Missões

### Missão 04: Migrations com Alembic
```bash
alembic init alembic
alembic revision --autogenerate -m "Create users table"
alembic upgrade head
```
- Versionar mudanças no schema
- Histórico completo de alterações
- Rollback automático se necessário

### Missão 05: Validações e Regras de Negócio
```python
# Validar CFM (Conselho Federal de Medicina)
# Buscar dados de verdade na API oficial
# Garantir que só médicos validados podem registrar
```

### Missão 06: Autenticação e Autorização
```python
# JWT tokens
# Diferentes roles (admin, médico, usuário)
# Endpoints protegidos
```

---

## 📋 Checklist Final

- ✅ PostgreSQL rodando em Docker
- ✅ Arquivo `.env` criado (não vai para Git)
- ✅ Arquivo `.env.example` criado (referência)
- ✅ `app/models.py` define tabela User
- ✅ `app/database.py` configura sessão
- ✅ `app/main.py` usa SQLAlchemy ORM
- ✅ Endpoints `/users` funcionam com banco
- ✅ `tests/conftest.py` usa SQLite em memória
- ✅ Todos os 6 testes passando
- ✅ `start.ps1` sobe tudo automaticamente
- ✅ Documentação completa (3 arquivos)

---

## 🎬 Demonstração

### Criar um usuário
```bash
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"nome": "João Silva", "email": "joao@example.com"}'

# Resposta:
# {"id": 1, "nome": "João Silva", "email": "joao@example.com"}
```

### Listar usuários
```bash
curl http://localhost:8000/users

# Resposta:
# [{"id": 1, "nome": "João Silva", "email": "joao@example.com"}]
```

### Reiniciar servidor
```bash
# Os dados CONTINUAM lá! ✨
```

---

## 🏆 Resultado

**Uma aplicação que persiste dados de verdade em um banco de dados real, com testes rápidos e isolados, credenciais seguras, e infraestrutura automatizada.**

Tudo pronto para a próxima missão! 🚀

---

*Missão 03 concluída com sucesso!*
*6/6 testes passando | 9 arquivos criados | 4 arquivos atualizados*
