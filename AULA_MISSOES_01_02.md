# Aula: Missões 01 e 02 - Rotas e Validação com FastAPI

## 📚 Objetivo

Entender como criar rotas HTTP e validar dados em uma API REST usando FastAPI e Pydantic.

---

## Missão 01: GET /users — Rotas, JSON e Status Codes

### O que é uma Rota?

Uma rota é um caminho na URL que conecta a uma função da sua aplicação. É como um "endereço" que o navegador ou cliente acessa.

```
http://127.0.0.1:8000/users
                       ↑
                    Rota (path)
```

### O que é JSON?

JSON (JavaScript Object Notation) é um formato texto para trocar dados. É fácil de ler e entender:

```json
{
  "id": 1,
  "name": "Ada Lovelace"
}
```

### Status Codes HTTP

Quando um servidor responde, ele sempre devolve um **status code** de 3 dígitos:

| Código | Significado | Exemplo |
|--------|-------------|---------|
| 200 | OK — funcionou | Uma lista de usuários |
| 201 | Created — foi criado | Um novo usuário foi salvo |
| 400 | Bad Request — erro no cliente | Você mandou dados ruins |
| 404 | Not Found — não existe | A rota não existe |
| 422 | Unprocessable Entity — dados inválidos | Faltou um campo obrigatório |
| 500 | Internal Server Error — erro do servidor | Um erro inesperado aconteceu |

### Implementação: GET /users

```python
@app.get("/users")
def list_users() -> list[dict]:
    """Lista todos os usuários."""
    return USERS
```

**O que acontece:**
1. Quando alguém acessa `http://127.0.0.1:8000/users`, FastAPI chama `list_users()`
2. A função retorna `USERS` (uma lista em Python)
3. FastAPI converte automaticamente para JSON
4. Retorna status code **200** por padrão

### Testando GET /users

**No navegador:**
```
http://127.0.0.1:8000/users
```

**No terminal (curl):**
```bash
curl http://127.0.0.1:8000/users
```

**No Swagger (documentação automática):**
```
http://127.0.0.1:8000/docs
```

**No código (pytest):**
```python
def test_lista_usuarios_retorna_json_com_id_e_nome():
    resposta = client.get("/users")

    assert resposta.status_code == 200
    assert resposta.headers["content-type"] == "application/json"

    usuarios = resposta.json()
    assert isinstance(usuarios, list)
    for usuario in usuarios:
        assert "id" in usuario
        assert "name" in usuario
```

### Caso Especial: Lista Vazia

Uma lista vazia (`[]`) é um sucesso válido:

```python
def test_lista_vazia_continua_sendo_sucesso(monkeypatch):
    """Sem usuarios a resposta e 200 com [], nunca 404."""
    monkeypatch.setattr("app.main.USERS", [])

    resposta = client.get("/users")

    assert resposta.status_code == 200
    assert resposta.json() == []
```

**Por quê?** Porque não ter dados não é um erro — é uma resposta válida.

---

## Missão 02: POST /users — Request Body e Validação

### O que é POST?

GET **pega** dados do servidor. POST **envia** dados **para** o servidor.

```
GET /users        → "me mostre os usuários"
POST /users       → "crie um novo usuário com esses dados"
```

### Request Body

O "corpo" da requisição é os dados que você manda:

```json
{
  "name": "Maria Silva",
  "password": "senha123"
}
```

### Validação com Pydantic

Pydantic é uma biblioteca que **verifica** os dados antes de usar.

```python
from pydantic import BaseModel, Field, field_validator

class UserCreate(BaseModel):
    name: str = Field(min_length=1)
    password: str = Field(min_length=6)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("name must not be empty")
        return normalized

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < 6:
            raise ValueError("password must be at least 6 characters")
        return value
```

**O que cada linha faz:**

- `BaseModel`: a classe que define a estrutura dos dados
- `Field(min_length=1)`: o campo `name` deve ter no mínimo 1 caractere
- `@field_validator("name")`: função que valida o campo `name`
- `value.strip()`: remove espaços antes e depois
- `raise ValueError(...)`: se falhar a validação, devolve erro 422

### Implementação: POST /users

```python
@app.post("/users", status_code=201)
def create_user(user: UserCreate) -> dict[str, str | int]:
    """Cria um novo usuário."""
    next_id = max((u["id"] for u in USERS), default=0) + 1
    new_user = {"id": next_id, "name": user.name}
    USERS.append(new_user)
    return new_user
```

**O que acontece:**

1. Cliente envia JSON com `name` e `password`
2. Pydantic valida os dados
3. Se inválido → retorna **422** e explica por quê
4. Se válido → executa a função
5. Gera um novo `id` (máximo atual + 1)
6. Cria o usuário novo
7. Adiciona à lista
8. Retorna os dados do novo usuário com status **201**

### Testando POST /users

**Sucesso — nome e senha válidos:**
```bash
curl -X POST http://127.0.0.1:8000/users \
  -H "Content-Type: application/json" \
  -d '{"name":"Maria Silva","password":"senha123"}'
```

Resposta:
```json
{
  "id": 1,
  "name": "Maria Silva"
}
```
Status: **201**

**Erro — nome vazio:**
```bash
curl -X POST http://127.0.0.1:8000/users \
  -H "Content-Type: application/json" \
  -d '{"name":"","password":"senha123"}'
```

Resposta:
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "name"],
      "msg": "name must not be empty"
    }
  ]
}
```
Status: **422**

**Erro — senha curta:**
```bash
curl -X POST http://127.0.0.1:8000/users \
  -H "Content-Type: application/json" \
  -d '{"name":"Maria Silva","password":"123"}'
```

Status: **422**

### Testes de POST /users

```python
def test_cria_usuario_com_nome_valido(monkeypatch):
    """Testa criação com dados corretos."""
    monkeypatch.setattr("app.main.USERS", [{"id": 1, "name": "Ada Lovelace"}])

    resposta = client.post("/users", json={"name": "Grace Hopper", "password": "senha123"})

    assert resposta.status_code == 201
    assert resposta.json() == {"id": 2, "name": "Grace Hopper"}


def test_nao_cria_usuario_com_nome_vazio():
    """Testa rejeição de nome vazio."""
    resposta = client.post("/users", json={"name": "", "password": "senha123"})

    assert resposta.status_code == 422


def test_nao_cria_usuario_com_senha_curta():
    """Testa rejeição de senha com menos de 6 caracteres."""
    resposta = client.post("/users", json={"name": "Maria", "password": "123"})

    assert resposta.status_code == 422
```

---

## A Interface (Frontend)

### HTML + JavaScript

Enquanto a API é o **backend** (servidor), o HTML é o **frontend** (o que você vê no navegador).

```html
<form id="form-usuario">
  <label for="name">Nome</label>
  <input id="name" name="name" type="text" placeholder="Digite o nome" required />
  <label for="password">Senha</label>
  <input id="password" name="password" type="password" placeholder="Mínimo 6 caracteres" required />
  <button type="submit">Cadastrar</button>
</form>
```

### Enviando dados com fetch()

O JavaScript pega os dados do formulário e envia para a API:

```javascript
const aviso = document.getElementById("aviso");
const form = document.getElementById("form-usuario");
const inputNome = document.getElementById("name");
const inputSenha = document.getElementById("password");

form.addEventListener("submit", (evento) => {
  evento.preventDefault();

  const nome = inputNome.value.trim();
  const senha = inputSenha.value.trim();
  
  if (!nome) {
    aviso.textContent = "Digite um nome válido";
    return;
  }
  
  if (!senha || senha.length < 6) {
    aviso.textContent = "Senha deve ter no mínimo 6 caracteres";
    return;
  }

  // Envia para a API
  fetch("/users", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ name: nome, password: senha }),
  })
    .then((resposta) => {
      if (!resposta.ok) {
        throw new Error("erro no cadastro");
      }
      inputNome.value = "";
      inputSenha.value = "";
      aviso.textContent = "usuário cadastrado com sucesso";
    })
    .catch(() => {
      aviso.textContent = "erro ao cadastrar usuário";
    });
});
```

**O que acontece:**

1. Usuário digita nome e senha e clica "Cadastrar"
2. JavaScript pega os valores dos `<input>`
3. Valida localmente (nome não vazio, senha com 6+ caracteres)
4. Se inválido, mostra mensagem de erro
5. Se válido, chama `fetch()` para enviar um POST para `/users`
6. Servidor recebe, valida com Pydantic, e cria o usuário
7. JavaScript recebe a resposta e mostra mensagem de sucesso

---

## Fluxo Completo: Do Frontend ao Backend e Volta

```
NAVEGADOR                                 SERVIDOR (FastAPI)
┌──────────────────┐
│ Usuário digita:  │
│ Nome: Maria      │
│ Senha: 123456    │
└────────┬─────────┘
         │
         ├─→ JavaScript valida (min. 6 chars)
         │
         ├─→ fetch() envia POST /users
              {
                "name": "Maria",
                "password": "123456"
              }
         │
         └──────────────────────────→ FastAPI recebe
                                      ├─→ Pydantic valida
                                      ├─→ UserCreate(name="Maria", password="123456")
                                      ├─→ create_user() executa
                                      ├─→ Gera id = 1
                                      ├─→ Salva em USERS
                                      ├─→ Retorna 201 Created
                                      │   {
                                      │     "id": 1,
                                      │     "name": "Maria"
                                      │   }
         ┌─────────────────────────←── Resposta volta
         │
         ├─→ JavaScript recebe status 201
         │
         ├─→ Limpa os inputs
         │
         └─→ Mostra "usuário cadastrado com sucesso"
```

---

## Resumo das Diferenças

| Aspecto | GET /users | POST /users |
|---------|-----------|-----------|
| **Método HTTP** | GET | POST |
| **Dados enviados** | Nenhum (apenas URL) | Body JSON |
| **Validação** | Nenhuma | Pydantic valida |
| **Status sucesso** | 200 OK | 201 Created |
| **Status erro** | 404 Not Found | 422 Unprocessable Entity |
| **Retorna** | Lista de usuários | Usuário criado |
| **Testa com** | Navegador, `curl`, `client.get()` | `curl -X POST`, Swagger, `client.post()` |

---

## Rodando o Projeto

### Instalar e rodar

```bash
uv sync
uv run uvicorn app.main:app --reload
```

Abra: http://127.0.0.1:8000

### Rodar testes

```bash
uv run pytest -q
```

Esperado: 8 testes passando

### Ver documentação automática

```
http://127.0.0.1:8000/docs
```

Nela você pode:
- Ver todas as rotas
- Ver o que cada rota espera
- Testar as rotas direto do navegador

---

## Perguntas Frequentes

### Por que `password` não aparece na resposta do POST?

Porque a função retorna apenas `name` e `id`. A senha é armazenada (em um projeto real, seria hash/criptografia), mas não é retornada para o cliente.

### Por que status 201 e não 200?

Status 200 significa "OK, operação concluída". Status 201 significa "OK, **recurso criado**". Usar o código correto ajuda o cliente a entender o que aconteceu.

### Pydantic valida só o nome e senha?

Neste projeto, sim. Pydantic valida **todos** os campos definidos no modelo. Você pode adicionar mais regras:

```python
class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=6)
    email: str  # novo campo
```

### Como a API sabe se o usuário existe?

Neste projeto, não sabe. A lista `USERS` começa vazia e só tem o que foi cadastrado. Em um banco de dados real, seria possível fazer buscas.

### E se dois usuários tiverem o mesmo nome?

Aqui, é permitido. Em um projeto real, você adicionaria validação para evitar duplicatas:

```python
@field_validator("name")
@classmethod
def validate_name_unique(cls, value: str) -> str:
    if any(u["name"] == value for u in USERS):
        raise ValueError("nome já existe")
    return value
```

---

## Desafios para Você

1. **Adicionar email ao cadastro** — Inclua um campo `email` na validação e garantir que tenha "@"

2. **Listar por ID** — Criar uma rota `GET /users/{id}` que retorna um usuário específico

3. **Atualizar usuário** — Criar uma rota `PUT /users/{id}` que modifica um usuário existente

4. **Deletar usuário** — Criar uma rota `DELETE /users/{id}` que remove um usuário

5. **Banco de dados real** — Substituir a lista `USERS` por um banco PostgreSQL (Missão 03!)

---

## Recursos Úteis

- [FastAPI - Documentação Oficial](https://fastapi.tiangolo.com/)
- [Pydantic - Validação de Dados](https://docs.pydantic.dev/)
- [HTTP Status Codes](https://developer.mozilla.org/pt-BR/docs/Web/HTTP/Status)
- [JSON - MDN Web Docs](https://developer.mozilla.org/pt-BR/docs/Learn/JavaScript/Objects/JSON)

