# 📊 Status Atual do Projeto — Agosto 2026

```
╔════════════════════════════════════════════════════════════════╗
║                   ✅ PROJETO ATUALIZADO                       ║
╚════════════════════════════════════════════════════════════════╝
```

---

## ✅ Missões Completas (01-04)

| # | Missão | Endpoints | Testes | Status |
|---|--------|-----------|--------|--------|
| 01 | GET /users | 1 rota | 1 ✓ | ✅ |
| 02 | POST /users | 1 rota | 3 ✓ | ✅ |
| 03 | Banco de dados | - | 4 ✓ | ✅ |
| 04 | PUT/DELETE | 2 rotas | 4 ✓ | ✅ |

**Total:** 12 testes passando | 6 rotas HTTP | Database integrado

---

## 📁 O que foi atualizado hoje

### 1. README.md
- ✅ Adicionada tabela de status das missões
- ✅ Atualizado número de testes (2 → 12)
- ✅ Documentação com links para arquivos educacionais
- ✅ Links para Swagger UI e ReDoc

### 2. MISSAO_05_ROTEIRO.md (NOVO)
- ✅ Guia completo para implementar relacionamentos
- ✅ Modelos SQLAlchemy com ForeignKey
- ✅ Schemas Pydantic para Doctor
- ✅ 7 novas rotas CRUD para doctors
- ✅ Exemplos de testes
- ✅ Desafios adicionais (bônus)

### 3. GitHub
- ✅ Commit com atualizações
- ✅ Push para branch `missao-01`

---

## 📚 Documentação Disponível

```
Guias de Aprendizado:
├─ AULA_MISSOES_01_02.md    (conceitos HTTP, JSON, validação)
├─ AULA_MISSOES_03_04.md    (banco de dados, CRUD, testes)
├─ MISSAO_05_ROTEIRO.md     (relacionamentos, Foreign Key)
└─ RESUMO_FINAL.md          (arquitetura geral)

Referências:
├─ API_REFERENCIA.md         (todos endpoints com exemplos)
├─ PROGRESSO.md              (roadmap das missões)
└─ README.md                 (como rodar e começar)
```

---

## 🎯 Próximo Passo: Missão 05

### Relacionamentos (User ↔ Doctor)

**O que você vai implementar:**

```python
# Novo modelo Doctor
class Doctor(Base):
    id: int (PK)
    user_id: int (FK → users.id)
    crm: str (Conselho Regional de Medicina)
    especialidade: str (ex: Cardiologia)
    created_at: datetime
```

**Novas rotas:**
- POST /doctors → Criar médico
- GET /doctors → Listar médicos
- GET /doctors/{id} → Ver médico
- PUT /doctors/{id} → Editar médico
- DELETE /doctors/{id} → Remover médico

**Novos testes:**
- ✓ Criar doctor para user existente
- ✓ Erro 404 para user inexistente
- ✓ Listar doctors
- ✓ Editar e deletar

**Resultado esperado:**
- ~18 testes passando (12 anteriores + 6 novos)
- Banco com 2 tabelas (users + doctors)
- Relacionamento 1:N funcional

---

## 🚀 Como Começar a Missão 05

### 1. Consultar o roteiro
Abra o arquivo `MISSAO_05_ROTEIRO.md` para ver o passo a passo completo.

### 2. Estrutura de trabalho
```bash
# Você está na branch missao-01
git status

# Será algo como:
# On branch missao-01
# nothing to commit, working tree clean
```

### 3. Criar uma nova branch para Missão 05
```bash
git checkout -b missao-05-relacionamentos
```

### 4. Implementar os passos do roteiro
1. Atualizar `app/models.py`
2. Adicionar rotas em `app/main.py`
3. Escrever testes em `tests/test_main.py`
4. Rodar `uv run pytest` para validar

### 5. Publicar seu trabalho
```bash
git add -A
git commit -m "feat: implementar modelo Doctor e CRUD completo"
git push -u origin missao-05-relacionamentos
```

---

## 📈 Roadmap Completo

```
Concluído:
✅ Missão 01 — GET /users
✅ Missão 02 — POST /users com validação
✅ Missão 03 — Banco de dados SQLAlchemy
✅ Missão 04 — PUT e DELETE (CRUD completo)

Em andamento:
⏳ Missão 05 — Relacionamentos User ↔ Doctor

Próximas:
⏳ Missão 06 — Autenticação JWT
⏳ Missão 07 — Agendamentos (Appointments)
⏳ Missão 08 — Filtros e paginação

Futuro:
💭 Missão 09+ — Integração com API do CFM
```

---

## 💻 Comandos Úteis

### Testar
```bash
uv run pytest -q        # Rápido
uv run pytest -v        # Detalhado
uv run pytest --cov     # Com cobertura
```

### Rodar servidor
```bash
uv run uvicorn app.main:app --reload
```

### Ver histórico do Git
```bash
git log --oneline
git status
git diff
```

### Desfazer mudanças (se errar)
```bash
git restore arquivo.py              # Desfaz mudanças em um arquivo
git reset HEAD~ --soft              # Desfaz último commit (mantém mudanças)
git stash                           # Guarda mudanças temporariamente
```

---

## 🏆 Próxima Meta

```
┌─────────────────────────────────────────────────────┐
│         🎯 Completar Missão 05 com sucesso         │
│                                                     │
│  • Modelo Doctor criado                            │
│  • 7 rotas CRUD implementadas                      │
│  • 18+ testes passando                             │
│  • Relacionamento User ↔ Doctor funcionando        │
│  • Push para GitHub com PR aberto                  │
└─────────────────────────────────────────────────────┘
```

---

## 📞 Se Travar

1. **"AttributeError: User has no attribute doctor"**
   → Você atualizou models.py? Rode `uv run pytest` para validar
   
2. **"Foreign key constraint failed"**
   → Você está criando doctor para user_id que não existe
   
3. **Muitos testes falhando**
   → Rode `uv run pytest -v` para ver qual falhou e por quê
   
4. **Servidor não sobe**
   → Erro na importação? Veja o erro no terminal
   → Tente `python -m py_compile app/models.py` para validar syntax

5. **Git diz "working directory not clean"**
   → Você tem mudanças não commitadas
   → `git status` mostra quais são
   → `git add .` e depois `git commit -m "..."`

---

## ✨ Dicas Finais

- 📖 Leia o roteiro inteiro antes de começar
- 🧪 Escreva os testes JUNTO com o código (não depois)
- 💾 Commit frequente (depois de cada rota)
- 🔄 Teste no Swagger UI enquanto desenvolve
- 💬 Se travar, veja o erro no terminal (é sempre descritivo)
- 🎯 Uma rota por vez: implementa → testa → commita → próxima

---

**Status:** Projeto preparado e pronto para Missão 05 ✅  
**Última atualização:** 14 de agosto de 2026  
**Branch ativa:** `missao-01` (histórico completo das missões)

