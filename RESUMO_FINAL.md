# 🏆 Bootcamp Tech AFYA — Missões 03 & 04 Finalizadas

```
╔════════════════════════════════════════════════════════════════╗
║                    PROGRESSO DO PROJETO                       ║
╚════════════════════════════════════════════════════════════════╝

Missão 01: GET /users              ✅ Concluída
Missão 02: POST /users             ✅ Concluída  
Missão 03: Banco de Dados          ✅ Concluída
Missão 04: PUT e DELETE            ✅ Concluída
           ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
           100% das Missões 01-04 Implementadas

Testes: ✅ 12/12 Passando
Cobertura: ✅ CRUD Completo
Documentação: ✅ 3 Arquivos educacionais
GitHub: ✅ Publicado em branch missao-01
```

---

## 📊 O que foi entregue

### Código
- ✅ **app/main.py** — 6 rotas totalmente funcionais
  - GET /health (diagnóstico)
  - GET / (interface)
  - GET /users (listar)
  - POST /users (criar)
  - PUT /users/{id} (editar)
  - DELETE /users/{id} (remover)

- ✅ **app/models.py** — Modelos de dados
  - SQLAlchemy User ORM
  - Pydantic UserCreate (POST/PUT)
  - Pydantic UserResponse (GET, sem senha)

- ✅ **app/database.py** — Persistência
  - SQLite para desenvolvimento
  - PostgreSQL pronto para produção
  - SessionLocal para gerenciar conexões

- ✅ **tests/test_main.py** — Suite de testes
  - 12 testes automatizados
  - Isolamento com transações
  - Cobertura de casos de sucesso e erro

- ✅ **app/templates/index.html** — Interface
  - Formulário com validação JavaScript
  - Estilo AFYA (rosa #fdf2f8)
  - Feedback de sucesso/erro

### Documentação

| Arquivo | Conteúdo |
|---------|----------|
| AULA_MISSOES_01_02.md | HTTP, JSON, Validação Pydantic, GET vs POST |
| AULA_MISSOES_03_04.md | SQLAlchemy, Banco de dados, CRUD, Testes |
| API_REFERENCIA.md | Todos os endpoints com exemplos curl/PowerShell |
| PROGRESSO.md | Status das missões e próximos passos |

---

## 🚀 Começar Agora

### 1. Clonar o repositório
```bash
git clone https://github.com/Claude-Impact-Lab/bootcamp-tech-afya.git
cd bootcamp-tech-afya
```

### 2. Instalar dependências
```bash
uv sync
```

### 3. Rodar servidor
```bash
uv run uvicorn app.main:app --reload --port 8000
```

### 4. Acessar
- **App:** http://127.0.0.1:8000
- **Docs (Swagger):** http://127.0.0.1:8000/docs
- **ReDoc:** http://127.0.0.1:8000/redoc

### 5. Rodar testes
```bash
uv run pytest -q      # Rápido
uv run pytest -v      # Detalhado
uv run pytest --cov   # Com cobertura
```

---

## 📈 Arquitetura Implementada

```
┌──────────────────────────────────────────────────────────────┐
│                    Frontend (HTML + JS)                      │
│  Formulário com validação local + chamadas FETCH             │
└────────────────────────────┬─────────────────────────────────┘
                             │ HTTP JSON
                             ▼
┌──────────────────────────────────────────────────────────────┐
│                    FastAPI Layer                             │
│  @app.get, @app.post, @app.put, @app.delete                 │
│  Status: 200, 201, 204, 404, 422                             │
└────────────────────────────┬─────────────────────────────────┘
                             │ Dependency Injection
                             ▼
┌──────────────────────────────────────────────────────────────┐
│                    Business Logic                            │
│  Validação Pydantic (schemas) + HTTPException               │
└────────────────────────────┬─────────────────────────────────┘
                             │ Session
                             ▼
┌──────────────────────────────────────────────────────────────┐
│                    ORM SQLAlchemy                            │
│  User model + database.py (engine, SessionLocal)             │
└────────────────────────────┬─────────────────────────────────┘
                             │ SQL
                             ▼
┌──────────────────────────────────────────────────────────────┐
│                    Database                                  │
│  SQLite (data.db) em desenvolvimento                         │
│  PostgreSQL pronto para produção                             │
└──────────────────────────────────────────────────────────────┘
```

---

## 🔍 Exemplo: Fluxo Completo

```
Usuario clica no formulário
         │
         ▼
JavaScript valida (name não vazio, password >= 6)
         │
         ▼
fetch POST para /users
         │
         ▼
FastAPI recebe JSON
         │
         ▼
Pydantic valida schema UserCreate
         │
         ▼
Business logic: criar User ORM
         │
         ▼
SQLAlchemy: INSERT INTO users
         │
         ▼
SQLite persiste em data.db
         │
         ▼
Response: 201 Created com {id, name}
         │
         ▼
JavaScript mostra mensagem de sucesso
         │
         ▼
Interface atualiza lista de usuários
```

---

## 🎓 Conceitos Ensinados

### HTTP & REST
- ✅ Status codes (200, 201, 204, 404, 422)
- ✅ Métodos (GET, POST, PUT, DELETE)
- ✅ Headers e Content-Type
- ✅ Request/Response JSON

### Validação
- ✅ Pydantic schemas
- ✅ Field validators
- ✅ Type hints em Python

### Banco de Dados
- ✅ O que é persistência
- ✅ SQLAlchemy ORM
- ✅ INSERT, SELECT, UPDATE, DELETE
- ✅ Transações e rollback

### Testing
- ✅ Pytest fixtures
- ✅ Isolamento de testes (transações)
- ✅ TestClient do FastAPI
- ✅ Dependency injection nos testes

### Git & GitHub
- ✅ Branch (missao-01)
- ✅ Commit com mensagens descritivas
- ✅ Push para repositório remoto

---

## 📋 Checklist Final

- [x] Código implementado
- [x] Testes passando (12/12)
- [x] Sem warnings ou erros
- [x] Banco de dados integrado
- [x] Documentação educacional
- [x] Referência de API
- [x] Commit e push no GitHub
- [x] Pronto para próximas missões

---

## 🎯 Próximas Etapas (Missões 05+)

1. **Missão 05:** Adicionar modelo Doctor e relacionamento User ↔ Doctor
2. **Missão 06:** Implementar autenticação com JWT
3. **Missão 07:** Criar modelo Appointment e rotas CRUD
4. **Missão 08:** Adicionar filtros, paginação e search

---

## 💡 Dicas para Continuar

1. Usar Swagger UI (/docs) para explorar interativamente
2. Adicionar print() em funções para debug
3. Usar `pytest -v` para ver detalhes dos testes
4. Consultar FastAPI docs: https://fastapi.tiangolo.com
5. Consultar SQLAlchemy docs: https://docs.sqlalchemy.org

---

```
╔════════════════════════════════════════════════════════════════╗
║          Parabéns por completar as Missões 03 & 04!           ║
║                                                                ║
║  Você aprendeu:                                               ║
║  • Como estruturar um projeto FastAPI profissional            ║
║  • Como persistir dados em banco de dados                     ║
║  • Como implementar CRUD completo                             ║
║  • Como testar suas APIs                                      ║
║  • Como trabalhar com Git e GitHub                            ║
║                                                                ║
║           Bora para as Missões 05-06! 🚀                      ║
╚════════════════════════════════════════════════════════════════╝
```

