# 🎯 Bootcamp Tech AFYA — Status das Missões

## ✅ Concluídas

### Missão 01: GET /users
- Rota retorna JSON array de usuários
- Status: 200 OK
- Resposta sem senha (privacidade)

### Missão 02: POST /users
- Rota aceita name e password
- Validação Pydantic: name mín 1 char, password mín 6 chars
- Status: 201 Created
- Testes para validação e erros

### Missão 03: Banco de Dados
- SQLAlchemy ORM integrado
- SQLite persistência em `data.db`
- Modelos e schemas definidos
- Tests com banco em memória (isolado)

### Missão 04: CRUD Completo
- ✅ PUT /users/{id} — Editar usuário (200 OK, 404 Not Found)
- ✅ DELETE /users/{id} — Deletar usuário (204 No Content, 404 Not Found)
- ✅ 4 testes adicionados (total 12 passando)
- ✅ Validação e tratamento de erros

---

## 📊 Testes: 12 Passando ✓

```
Missão 01-02: 8 testes
├─ test_health_retorna_ok
├─ test_index_renderiza_a_tela
├─ test_lista_usuarios_retorna_json_com_id_e_nome
├─ test_lista_vazia_continua_sendo_sucesso
├─ test_cria_usuario_com_nome_valido
├─ test_nao_cria_usuario_com_nome_vazio
├─ test_nao_cria_usuario_com_senha_curta
└─ test_html_valido

Missão 04: 4 testes
├─ test_atualiza_usuario_existente
├─ test_retorna_404_ao_atualizar_usuario_inexistente
├─ test_deleta_usuario_existente
└─ test_retorna_404_ao_deletar_usuario_inexistente
```

---

## 📁 Estrutura de Arquivos

```
bootcamp-tech-afya/
├── app/
│   ├── main.py              # Rotas FastAPI (GET, POST, PUT, DELETE)
│   ├── models.py            # Modelos SQLAlchemy e schemas Pydantic
│   ├── database.py          # Configuração de banco de dados
│   └── templates/
│       └── index.html       # Interface com formulário
├── tests/
│   └── test_main.py         # Suite de testes (12 testes)
├── data.db                  # Banco SQLite (gerado automaticamente)
├── pyproject.toml           # Dependências (FastAPI, SQLAlchemy, pytest)
├── AULA_MISSOES_01_02.md    # Guia educacional Missões 01-02
├── AULA_MISSOES_03_04.md    # Guia educacional Missões 03-04
└── README.md                # Este arquivo
```

---

## 🚀 Próximas Missões

### Missão 05: Relacionamentos (User ↔ Doctor)
- Criar modelo Doctor
- Adicionar foreign key em Doctor.user_id
- Rota GET /doctors retorna lista com usuário

### Missão 06: Autenticação
- Implementar JWT token
- Rota POST /login retorna token
- Proteger rotas com @app.get(dependencies=[Depends(verify_token)])

### Missão 07: Agendamentos
- Criar modelo Appointment
- Relacionar User ↔ Appointment ↔ Doctor
- Rotas CRUD para agendamentos

---

## 💻 Rodando Localmente

### Instalar dependências
```bash
uv sync
```

### Rodar servidor
```bash
uv run uvicorn app.main:app --reload --port 8000
```

Acesse em: http://127.0.0.1:8000

### Rodar testes
```bash
uv run pytest -q  # Modo silencioso
uv run pytest -v  # Modo verbose
uv run pytest --cov  # Com cobertura
```

---

## 📚 Recursos Educacionais

- [AULA_MISSOES_01_02.md](./AULA_MISSOES_01_02.md) — HTTP, JSON, Validação
- [AULA_MISSOES_03_04.md](./AULA_MISSOES_03_04.md) — Banco de dados, CRUD, Testes

---

## 🔒 Segurança (Checklist)

- ✅ Senha NUNCA retornada no JSON (apenas id e name)
- ❌ TODO: Hash de senha (usar bcrypt)
- ❌ TODO: JWT para autenticação
- ✅ Validação com Pydantic
- ✅ SQL injection prevenido (SQLAlchemy paramétrico)

---

## 📈 Progresso

| Semana | Missões | Status |
|--------|---------|--------|
| 1 | 01-02 | ✅ Concluído |
| 2 | 03-04 | ✅ Concluído |
| 3 | 05-06 | ⏳ Próxima |
| 4 | 07-08 | ⏳ Próxima |

---

**Última atualização:** $(date)  
**Branch ativa:** `missao-01` (pronto para merge)

