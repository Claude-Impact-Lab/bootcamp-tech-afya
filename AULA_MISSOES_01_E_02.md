# Aula de revisão — Missões 01 e 02

Projeto: **User Manager**  
Branch do aluno: **`thiago-duque`**

## 1. Visão geral do que construímos

O projeto começou como uma aplicação FastAPI simples e evoluiu para um cadastro de
usuários com consulta, validação, pré-cadastro, senha protegida, confirmação simulada
de e-mail, login e testes automatizados.

As duas missões estudadas foram:

| Missão | Requisito principal | Conceitos |
|---|---|---|
| 01 | Criar `GET /users` | rota, JSON e status HTTP |
| 02 | Criar `POST /users` | request body e validação com Pydantic |

Importante: senha, confirmação de e-mail, login administrativo e página de parabéns
foram evoluções adicionais. O núcleo da missão 02 era receber e validar o corpo de uma
requisição `POST`.

---

## 2. Histórico real dos commits

Os commits contam a evolução do projeto em pequenas entregas:

```text
3021d35 feat: cria GET /users e exibe a lista na tela
cd724e8 feat: exibe o total de usuarios na tela
caeec30 feat: destaca os usuarios em pre-cadastro na tela
7c78344 feat: cria cadastro de usuarios com POST
cf3be7e feat: amplia cadastro e acesso de usuarios
df02ed1 docs: atualiza estado da missao 02
```

### O que cada commit representa

1. `3021d35`: implementação central da missão 01.
2. `cd724e8`: a interface passa a contar os usuários recebidos da API.
3. `caeec30`: separação visual de usuários ativos e pré-cadastros.
4. `7c78344`: implementação central da missão 02.
5. `cf3be7e`: evolução com dados pessoais, senha, login, e-mail e nova interface.
6. `df02ed1`: documentação para recuperar o contexto do aprendizado.

Os mesmos commits foram levados por avanço direto (*fast-forward*) para a branch
`thiago-duque`. A branch `missao-02` foi preservada.

---

# Parte I — Missão 01: `GET /users`

## 3. O que é uma rota?

Uma rota liga um endereço HTTP a uma função Python. No FastAPI:

```python
@app.get("/users")
def list_users(request: Request) -> list[dict]:
    users = USERS if is_admin(request) else [
        user for user in USERS if user["status"] == "ativo"
    ]
    return [public_user(user) for user in users]
```

O decorator `@app.get("/users")` diz:

> Quando alguém fizer uma requisição GET para `/users`, execute `list_users`.

## 4. O que é `GET`?

`GET` é usado para consultar informações. Ele não deveria criar, editar nem apagar
dados.

Exemplo:

```http
GET /users
```

Resposta JSON:

```json
[
  {
    "id": 1,
    "name": "Ana Lucia",
    "status": "ativo"
  }
]
```

## 5. JSON

JSON é o formato usado para transportar os dados entre navegador e API. Uma lista
Python vira um array JSON; um dicionário Python vira um objeto JSON.

```python
return [{"id": 1, "name": "Ana Lucia"}]
```

## 6. Status HTTP da missão 01

Quando a consulta funciona, o FastAPI devolve `200 OK`.

Se não houver usuários, a API devolve:

```json
[]
```

com status `200`, não `404`. A coleção `/users` existe; ela apenas está vazia.

## 7. Como o navegador utiliza a rota

O JavaScript chama a API com `fetch`:

```javascript
fetch("/users")
  .then((resposta) => resposta.json())
  .then((usuarios) => {
    usuarios.forEach(exibirUsuario);
  });
```

Fluxo:

```text
Navegador -> GET /users -> FastAPI -> lista JSON -> navegador atualiza o HTML
```

## 8. Teste da missão 01

```python
def test_users_retorna_a_lista_em_json():
    resposta = client.get("/users")

    assert resposta.status_code == 200
    assert isinstance(resposta.json(), list)
```

O teste prova duas coisas: a rota responde com sucesso e o corpo é uma lista JSON.

---

# Parte II — Missão 02: `POST /users`

## 9. Diferença entre `GET` e `POST`

| Método | Objetivo | Exemplo |
|---|---|---|
| `GET` | Consultar | Listar usuários |
| `POST` | Criar | Cadastrar usuário |

Uma requisição `POST` envia dados no corpo (*request body*):

```json
{
  "first_name": "Maria",
  "last_name": "Souza",
  "age": 28,
  "email": "maria@exemplo.com",
  "password": "senha-segura",
  "password_confirmation": "senha-segura"
}
```

## 10. Modelo Pydantic

O modelo `UserCreate` define o formato e as regras dos dados:

```python
class UserCreate(BaseModel):
    first_name: str | None = Field(default=None, min_length=2, max_length=50)
    last_name: str | None = Field(default=None, min_length=2, max_length=50)
    age: int | None = Field(default=None, ge=0, le=130)
    email: str | None = Field(
        default=None,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    )
    password: str | None = Field(default=None, min_length=8, max_length=128)
    password_confirmation: str | None = Field(default=None, min_length=8, max_length=128)
```

O Pydantic transforma JSON em um objeto Python validado. Se algum valor desrespeitar
as regras, a função da rota nem começa a executar: o FastAPI responde `422`.

## 11. Validação entre dois campos

Senha e confirmação precisam ser iguais:

```python
@model_validator(mode="after")
def validate_password_confirmation(self):
    if self.password is not None and self.password != self.password_confirmation:
        raise ValueError("As senhas nao conferem.")
    return self
```

Essa é uma regra que depende de mais de um campo, por isso usamos `model_validator`.

## 12. Rota de criação

```python
@app.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(request: Request, user: UserCreate) -> dict:
    next_id = max(
        (registered_user["id"] for registered_user in USERS),
        default=0,
    ) + 1

    new_user = {
        "id": next_id,
        "name": " ".join(
            part for part in (user.first_name, user.last_name) if part
        ),
        "age": user.age,
        "email": user.email,
        "status": "pre_cadastro",
    }

    USERS.append(new_user)
    return public_user(new_user)
```

Passos da função:

1. Calcula o próximo `id`.
2. Monta um dicionário com os dados do usuário.
3. Define o status inicial.
4. Adiciona o usuário à lista em memória.
5. Devolve uma versão pública do usuário.

## 13. Por que `201 Created`?

`200 OK` significa sucesso genérico. `201 Created` comunica com mais precisão que um
novo recurso foi criado.

```python
status_code=status.HTTP_201_CREATED
```

## 14. Pré-cadastro e cadastro completo

Quando faltam dados:

```text
pre_cadastro
```

Quando todos os campos foram preenchidos:

```text
aguardando_confirmacao_email
```

Depois que o link de confirmação é usado:

```text
ativo
```

Esses estados representam o ciclo de vida do cadastro.

## 15. Proteção da senha

A senha não é salva em texto puro. Criamos um salt aleatório e calculamos um hash:

```python
def hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        bytes.fromhex(salt),
        200_000,
    ).hex()
```

Armazenamos `password_hash` e `password_salt`, nunca a senha original.

## 16. Dados privados

A função `public_user` impede que informações sensíveis saiam pela API:

```python
def public_user(user: dict) -> dict:
    private_fields = {"confirmation_token", "password_hash", "password_salt"}
    return {key: value for key, value in user.items() if key not in private_fields}
```

Essa separação evita expor token e hash no JSON.

## 17. Login posterior

Criamos `POST /users/login`. Ele:

1. Procura o e-mail.
2. Calcula o hash da senha informada.
3. Compara o resultado com o hash salvo.
4. Verifica se o e-mail foi confirmado.
5. Cria um cookie de sessão se o acesso for válido.

## 18. Confirmação simulada de e-mail

O projeto gera um token e cria um link para `/users/confirm`. O e-mail não é enviado
de verdade; ele fica em `EMAIL_OUTBOX` para permitir testes sem serviço externo.

## 19. Interface e página de congratulações

A tela inicial possui três opções:

- Usuário.
- Administrador.
- Realizar cadastro.

Quando o cadastro está completo, o JavaScript redireciona:

```javascript
window.location.href =
  `/congratulations?name=${encodeURIComponent(usuario.name)}`;
```

A página seguinte mostra uma mensagem de parabéns e a imagem AFYA.

## 20. Testes da missão 02

Os testes verificam casos como:

- Cadastro válido retorna `201`.
- Sobrenome curto retorna `422`.
- E-mail inválido retorna `422`.
- Senhas diferentes retornam `422`.
- Senha não aparece na resposta nem é guardada em texto puro.
- Cadastro incompleto fica como pré-cadastro.
- Confirmação ativa o usuário.
- Usuário confirmado consegue entrar.
- Página de congratulações contém nome e imagem.

Resultado ao concluir a missão:

```text
17 passed
```

---

# Parte III — Git e branches

## 21. O que é uma branch?

Uma branch é uma linha separada de desenvolvimento. Trabalhamos inicialmente na
`missao-02` e levamos o resultado para a branch pessoal `thiago-duque`.

Situação final:

```text
main
  └── commits da missão 01
        └── commits da missão 02
              ├── missao-02
              └── thiago-duque
```

## 22. Comandos Git usados

```bash
git status
git add arquivo
git commit -m "feat: descricao"
git push origin missao-02
git switch thiago-duque
git merge --ff-only missao-02
git push origin thiago-duque
```

### Significado

- `git status`: mostra o estado atual.
- `git add`: prepara mudanças para o commit.
- `git commit`: cria um ponto no histórico.
- `git push`: envia commits ao GitHub.
- `git switch`: troca de branch.
- `git merge --ff-only`: avança uma branch sem criar commit de merge desnecessário.

---

# Parte IV — Limitação atual e próxima missão

Os dados ainda ficam na lista `USERS`, na memória do Python. Ao reiniciar o servidor,
novos cadastros desaparecem.

Isso é esperado nas missões 01 e 02. A missão 03 resolverá esse problema com:

- PostgreSQL.
- Tabela de usuários.
- SQL.
- Chave primária.
- Migrations.

---

# Parte V — Exercícios para estudar

## Exercício 1

Explique com suas palavras por que uma lista vazia em `GET /users` retorna `200`, e
não `404`.

## Exercício 2

Qual é a diferença entre o corpo da requisição e o corpo da resposta?

## Exercício 3

Altere mentalmente a regra de idade para permitir somente maiores de 18 anos. Qual
parâmetro do `Field` mudaria?

## Exercício 4

Por que a senha não pode ser armazenada diretamente na lista?

## Exercício 5

Explique a diferença entre `200`, `201`, `401`, `403` e `422`.

## Exercício 6

Desenhe o fluxo:

```text
formulário -> POST /users -> Pydantic -> USERS -> resposta JSON
```

## Exercício 7

Rode os testes e escolha um deles para explicar linha por linha:

```bash
uv run pytest -q
```

---

# Parte VI — Perguntas de revisão com respostas curtas

1. **O que a missão 01 pedia?**  
   Criar `GET /users` e aprender rotas, JSON e status HTTP.

2. **O que a missão 02 pedia?**  
   Criar `POST /users`, receber request body e validar com Pydantic.

3. **Quem devolve `422`?**  
   FastAPI/Pydantic quando o corpo não respeita o modelo.

4. **Por que usamos `201` no POST?**  
   Porque um novo recurso foi criado.

5. **Onde os usuários estão guardados agora?**  
   Em memória, na lista `USERS`.

6. **Qual missão salvará os dados definitivamente?**  
   Missão 03, com PostgreSQL.

---

# Prompt para continuar estudando no ChatGPT

Copie e envie junto com este arquivo:

> Use a aula `AULA_MISSOES_01_E_02.md` como base. Seja meu professor de Python e
> FastAPI. Faça uma pergunta por vez, espere minha resposta, corrija de forma simples
> e peça para eu explicar os códigos com minhas palavras. Comece pela missão 01 e só
> avance para a missão 02 quando eu demonstrar que entendi GET, JSON e status 200.

