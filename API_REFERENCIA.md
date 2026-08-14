# 📡 Referência da API — Missões 01-04

## Base URL
```
http://127.0.0.1:8000
```

---

## 1️⃣ Health Check

### GET /health
Verifica se o servidor está ativo.

**Request:**
```bash
GET /health
```

**Response (200 OK):**
```json
{
  "status": "ok",
  "message": "Hello World"
}
```

---

## 2️⃣ Usuários - Leitura

### GET /users
Lista todos os usuários cadastrados.

**Request:**
```bash
GET /users
```

**Response (200 OK):**
```json
[
  {"id": 1, "name": "Alice Silva"},
  {"id": 2, "name": "Bob Santos"}
]
```

**Casos especiais:**
- Se não houver usuários, retorna `[]` (array vazio) com status 200

---

## 3️⃣ Usuários - Criação

### POST /users
Cria um novo usuário com validação.

**Request:**
```bash
POST /users
Content-Type: application/json

{
  "name": "Maria Santos",
  "password": "minhaSenha123"
}
```

**Response (201 Created):**
```json
{
  "id": 3,
  "name": "Maria Santos"
}
```

**Validações:**
- `name`: mínimo 1 caractere (não pode ser vazio)
- `password`: mínimo 6 caracteres

**Erros:**

| Código | Motivo |
|--------|--------|
| 422 | Validação falhou (name vazio ou password < 6 chars) |
| 400 | JSON inválido |

**Exemplo erro:**
```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "password"],
      "msg": "String should have at least 6 characters",
      "input": "123"
    }
  ]
}
```

---

## 4️⃣ Usuários - Edição

### PUT /users/{id}
Atualiza nome e/ou senha de um usuário existente.

**Request:**
```bash
PUT /users/1
Content-Type: application/json

{
  "name": "Alice Silva Atualizado",
  "password": "novaSenha456"
}
```

**Response (200 OK):**
```json
{
  "id": 1,
  "name": "Alice Silva Atualizado"
}
```

**Parâmetros:**
- `{id}`: ID do usuário (inteiro)

**Validações:**
- Mesmo de POST (name min 1 char, password min 6 chars)
- Usuário deve existir

**Erros:**

| Código | Motivo |
|--------|--------|
| 404 | Usuário não encontrado |
| 422 | Validação falhou |
| 400 | JSON inválido |

---

## 5️⃣ Usuários - Deleção

### DELETE /users/{id}
Remove um usuário do banco de dados.

**Request:**
```bash
DELETE /users/1
```

**Response (204 No Content):**
```
(sem corpo)
```

**Parâmetros:**
- `{id}`: ID do usuário (inteiro)

**Comportamento:**
- Status 204 significa sucesso sem retornar dados
- Usuário é deletado permanentemente do banco

**Erros:**

| Código | Motivo |
|--------|--------|
| 404 | Usuário não encontrado |

---

## 6️⃣ Frontend

### GET /
Retorna a página HTML do formulário de registro.

**Request:**
```bash
GET /
```

**Response (200 OK):**
```html
<!DOCTYPE html>
<html>
  <head>
    <title>AFYA - User Manager</title>
  </head>
  <body>
    <!-- Formulário com campos name e password -->
  </body>
</html>
```

---

## 📋 Fluxos de Exemplo

### Exemplo 1: Criar e depois editar um usuário

```bash
# 1. Criar usuário
POST /users
{"name": "João", "password": "senha123"}
→ 201 Created: {"id": 1, "name": "João"}

# 2. Listar para confirmar
GET /users
→ 200 OK: [{"id": 1, "name": "João"}]

# 3. Editar nome
PUT /users/1
{"name": "João Silva", "password": "senha123"}
→ 200 OK: {"id": 1, "name": "João Silva"}

# 4. Listar novamente
GET /users
→ 200 OK: [{"id": 1, "name": "João Silva"}]

# 5. Deletar
DELETE /users/1
→ 204 No Content

# 6. Listar para confirmar deleção
GET /users
→ 200 OK: []
```

### Exemplo 2: Tratamento de erros

```bash
# POST com validação falha (password muito curta)
POST /users
{"name": "Ana", "password": "123"}
→ 422 Unprocessable Entity

# PUT em usuário inexistente
PUT /users/999
{"name": "Fictício", "password": "senha123"}
→ 404 Not Found: {"detail": "Usuario não encontrado"}

# DELETE em usuário inexistente
DELETE /users/999
→ 404 Not Found: {"detail": "Usuario não encontrado"}
```

---

## 🔐 Segurança

### O que está protegido:
- ✅ **Senhas nunca retornadas** — Resposta JSON só tem `id` e `name`
- ✅ **Validação de entrada** — Pydantic valida tipo, tamanho e formato
- ✅ **SQL injection prevenido** — SQLAlchemy usa queries paramétrizadas
- ✅ **Status codes corretos** — 404 se não encontrado, 422 se inválido

### O que ainda falta (Missão 06+):
- ❌ Hash de senha (atualmente armazenada em texto plano)
- ❌ Autenticação JWT
- ❌ Rate limiting
- ❌ CORS restrito

---

## 🧪 Testando com curl

### PowerShell (Windows):
```powershell
# GET
Invoke-WebRequest -Uri "http://127.0.0.1:8000/users" -Method Get

# POST
$body = @{name="Pedro"; password="senha123"} | ConvertTo-Json
Invoke-WebRequest -Uri "http://127.0.0.1:8000/users" -Method Post `
  -Headers @{"Content-Type"="application/json"} -Body $body

# PUT
$body = @{name="Pedro Silva"; password="nova123"} | ConvertTo-Json
Invoke-WebRequest -Uri "http://127.0.0.1:8000/users/1" -Method Put `
  -Headers @{"Content-Type"="application/json"} -Body $body

# DELETE
Invoke-WebRequest -Uri "http://127.0.0.1:8000/users/1" -Method Delete
```

### Bash/Linux (curl):
```bash
# GET
curl http://127.0.0.1:8000/users

# POST
curl -X POST http://127.0.0.1:8000/users \
  -H "Content-Type: application/json" \
  -d '{"name":"Pedro","password":"senha123"}'

# PUT
curl -X PUT http://127.0.0.1:8000/users/1 \
  -H "Content-Type: application/json" \
  -d '{"name":"Pedro Silva","password":"nova123"}'

# DELETE
curl -X DELETE http://127.0.0.1:8000/users/1
```

---

## 📚 Documentação Automática

FastAPI gera documentação interativa automaticamente:

- **Swagger UI:** http://127.0.0.1:8000/docs
- **ReDoc:** http://127.0.0.1:8000/redoc

Acesse qualquer uma para testar as rotas diretamente no navegador!

---

**Versão:** 1.0 (Missões 01-04)  
**Última atualização:** 2024

