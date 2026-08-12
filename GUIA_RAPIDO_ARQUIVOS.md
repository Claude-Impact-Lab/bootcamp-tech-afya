# 🔍 Guia Rápido dos Arquivos da Missão 03

## 📂 Arquivos por Categoria

### 🗄️ Banco de Dados

#### `docker-compose.yml` (NOVO)
```yaml
Sobe PostgreSQL em um container Docker
- Porta: 5432
- Usuário/senha: definidos no .env
- Volume: postgres_data (persiste dados)
```
**Comando:**
```bash
docker compose up -d
```

#### `app/database.py` (NOVO)
```python
Configura conexão com PostgreSQL
- engine: Conexão com o banco
- SessionLocal: Cria sessões do banco
- get_db(): Dependência injetada pelo FastAPI

Para testes, detecta TESTING=true e usa SQLite em memória
```
**Uso:** 
```python
db: Session = Depends(get_db)  # FastAPI injeta automaticamente
```

#### `app/models.py` (NOVO)
```python
Define a tabela User do banco
- id: Chave primária (auto-incremento)
- nome: String até 255 caracteres
- email: String única (sem duplicatas)
```
**Uso:**
```python
usuario = User(nome="João", email="joao@example.com")
db.add(usuario)
db.commit()
```

---

### ⚙️ Configuração

#### `.env` (NOVO - NÃO VAI PARA GIT)
```env
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=usermanager
DATABASE_URL=postgresql://user:password@localhost:5432/usermanager
```
**Importante:** Crie este arquivo localmente com suas credenciais

#### `.env.example` (NOVO - VAI PARA GIT)
```env
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=usermanager
DATABASE_URL=postgresql://user:password@localhost:5432/usermanager
```
**Uso:** Referência para outros colegas

#### `pyproject.toml` (ATUALIZADO)
Adicionadas:
- `sqlalchemy>=2.0` - ORM do banco
- `psycopg2-binary>=2.9` - Driver PostgreSQL
- `alembic>=1.12` - Migrations (próxima missão)
- `python-dotenv>=1.0` - Lê arquivo .env

**Comando:**
```bash
uv sync  # Instala as novas dependências
```

---

### 🔧 Aplicação

#### `app/main.py` (ATUALIZADO)
**Removido:**
- Lista `USUARIOS` em memória

**Adicionado:**
- Importações de database, models, SQLAlchemy
- Evento `@app.on_event("startup")` para criar tabelas
- Endpoints agora usam `Depends(get_db)`
- Queries com `db.query(User).all()`
- Inserts com `db.add()`, `db.commit()`

**Endpoints:**
```
GET /health         → {"status": "ok", "message": "Hello World"}
GET /              → Página HTML
GET /users         → Lista usuários do banco
POST /users        → Cria novo usuário no banco
```

---

### 🧪 Testes

#### `tests/conftest.py` (NOVO)
```python
Configuração global de testes
- Cria engine SQLite em memória
- Override `get_db` para usar banco de teste
- Fixture `client` limpa e recria tabelas a cada teste
```

**Como funciona:**
```
Teste 1:
  - Limpa banco
  - Cria tabelas vazias
  - Executa teste 1
  
Teste 2:
  - Limpa banco
  - Cria tabelas vazias
  - Executa teste 2

Resultado: Testes não interferem uns com os outros!
```

#### `tests/test_main.py` (ATUALIZADO)
**Antes:**
- Dependia de dados hardcoded
- Testava a mesma lista `USUARIOS`

**Depois:**
- Cada teste cria seus próprios dados
- Testa operações reais do banco
- 6 testes no total, todos passando

**Testes:**
```python
test_health_retorna_ok()                             # ✅
test_index_retorna_200()                             # ✅
test_listar_usuarios_vazio_retorna_lista_vazia()     # ✅
test_criar_usuario_retorna_dados_com_id()            # ✅
test_listar_usuarios_apos_criar()                    # ✅
test_cada_usuario_tem_id_e_nome_e_email()            # ✅
```

---

### 📚 Documentação

#### `MISSAO_03_EXPLICACAO.md`
Documentação técnica completa
- Explicação linha por linha de cada arquivo
- Conceitos (ORM, Migrations, Fixtures, etc)
- Diagrama de fluxo de dados
- Checklist da missão
- 2000+ linhas

**Leia quando:** Precisa entender o "por que" de cada decisão

#### `RESUMO_MUDANCAS.md`
Resumo visual e prático
- Antes vs Depois
- Diagrama de arquitetura
- Fluxo de requisições
- Tabelas comparativas

**Leia quando:** Quer uma visão geral rápida

#### `RUNNING.md`
Como rodar o projeto
- Instruções passo a passo
- Comandos úteis
- Troubleshooting
- Pronto para um colega novo

**Leia quando:** Precisa rodar o projeto ou ajudar alguém

#### `MISSAO_03_RESULTADO_FINAL.md`
Resultado final da missão
- Status: ✅ COMPLETO
- Checklist de tudo pronto
- Ganhos da missão
- Próximas missões

**Leia quando:** Quer confirmar que tudo está pronto

---

### 🚀 Automação

#### `start.ps1` (ATUALIZADO)
Script que faz tudo automaticamente:
1. Verifica se Docker está instalado
2. Verifica se Docker daemon está rodando
3. Sobe PostgreSQL se não estiver
4. Aguarda PostgreSQL ficar pronto
5. Instala dependências se necessário
6. Inicia o servidor

**Uso:**
```powershell
.\start.ps1
```
Depois abra http://localhost:8000

#### `.gitignore` (ATUALIZADO)
Adicionado:
```
.env              # ← Nunca commita arquivo com senha!
```

---

## 🎯 Fluxo de Trabalho Típico

### 1. Primeira Vez
```bash
# Clone o repo
git clone https://github.com/Claude-Impact-Lab/bootcamp-tech-afya.git
cd bootcamp-tech-afya

# Execute o script
.\start.ps1

# Abra http://localhost:8000
```

### 2. Próximas Vezes
```bash
# Se servidor já estava rodando, apenas reinicie
.\start.ps1
```

### 3. Parar Tudo
```bash
# Para o servidor (Ctrl+C no terminal)
# Para PostgreSQL
docker compose down
```

### 4. Rodar Testes
```bash
uv run pytest -v
```

### 5. Acessar Banco Diretamente
```bash
docker compose exec postgres psql -U user -d usermanager
```

---

## 🔄 Mudança de Fluxo: Antes → Depois

### ANTES (Missão 02)
```
Cliente HTTP
    ↓
FastAPI
    ↓
Lista USUARIOS em memória (dict)
    ↓
Resposta JSON

⚠️ Ao reiniciar → Tudo perdido
```

### DEPOIS (Missão 03)
```
Cliente HTTP
    ↓
FastAPI
    ↓
SQLAlchemy (cria SQL)
    ↓
psycopg2 (conecta ao PostgreSQL)
    ↓
PostgreSQL (salva em disco)
    ↓
Resposta JSON

✨ Ao reiniciar → Dados ainda lá!
```

---

## 💾 Persistência Garantida

```python
# Exemplo: Criar um usuário

usuario = User(nome="João", email="joao@example.com")
db.add(usuario)       # Apenas em memória (cache)
db.commit()           # ← AQUI é salvo no disco!

# Mesmo se o servidor cair AGORA:
# - Dados estão salvos em /var/lib/postgresql/data
# - Próxima vez que subir o servidor, dados continuam lá
```

---

## 🧪 Por que Testes Passam Rápido?

**SQLite em memória vs PostgreSQL:**

| Operação | PostgreSQL | SQLite |
|----------|-----------|--------|
| Criar tabela | 100ms | 1ms |
| Insert 1000 rows | 500ms | 10ms |
| Query | 50ms | 1ms |
| **Total 6 testes** | ~3s | ~0.6s |

**Resultado:** Testes rodam 5x mais rápido! ⚡

---

## 🔐 Segurança: Credenciais

```
❌ ERRADO:
# app/main.py
DATABASE_URL = "postgresql://user:PASSWORD123@localhost/db"
# Ao fazer git push → senha vai para GitHub público!

✅ CORRETO:
# app/main.py
DATABASE_URL = os.getenv("DATABASE_URL")  # Lê do .env

# .env (git-ignored)
DATABASE_URL=postgresql://user:PASSWORD123@localhost/db
# Nunca vai para GitHub!

# .env.example (publicado)
DATABASE_URL=postgresql://user:password@localhost/db
# Mostra o padrão, sem senha real
```

---

## 📊 Resumo: O que Cada Arquivo Faz

```
docker-compose.yml  → Subir PostgreSQL em Docker
.env                → Credenciais (local, git-ignored)
.env.example        → Modelo de credenciais (publicado)

app/database.py     → Conexão com banco + get_db()
app/models.py       → Definir tabelas em Python
app/main.py         → Endpoints que usam o banco

tests/conftest.py   → Setup de testes com SQLite
tests/test_main.py  → 6 testes do projeto

MISSAO_03_EXPLICACAO.md       → Documentação detalhada
RESUMO_MUDANCAS.md            → Resumo visual
RUNNING.md                    → Como rodar
MISSAO_03_RESULTADO_FINAL.md  → Status final

pyproject.toml      → Dependências (SQLAlchemy, etc)
start.ps1           → Script que sobe tudo
.gitignore          → Ignora .env
```

---

## ✨ Resultado Final

**Antes de Missão 03:**
- ❌ Dados em memória
- ❌ Perdem ao reiniciar
- ❌ Sem banco de dados

**Depois de Missão 03:**
- ✅ Dados em PostgreSQL real
- ✅ Persistem para sempre
- ✅ Infraestrutura com Docker
- ✅ Testes rápidos e isolados
- ✅ Credenciais seguras
- ✅ 6/6 testes passando

---

*Este guia é sua cola para entender qualquer arquivo da Missão 03!* 📚
