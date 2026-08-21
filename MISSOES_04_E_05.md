# Missões 04 e 05 — CRUD e relacionamento User + Doctor

## Missão 04: edição e exclusão

Foram adicionadas duas operações ao recurso `users`:

- `PUT /users/{id}` substitui nome, idade e e-mail editáveis.
- `DELETE /users/{id}` remove o registro e responde `204 No Content`.

As duas operações são idempotentes: repetir o mesmo `PUT` mantém o mesmo estado e
repetir o `DELETE` mantém o usuário ausente, ainda com resposta `204`.

O `PUT` responde `404` para um identificador inexistente e `409` quando o novo e-mail
já pertence a outro usuário.

## Missão 05: User + Doctor

A tabela `doctors` foi criada pela migration `0002`. Cada registro possui:

- `user_id`: chave estrangeira para `users.id`;
- `crm` e `uf`: identificação profissional;
- `specialty`: especialidade opcional.

A restrição `unique` em `user_id` estabelece uma relação um-para-um: um usuário pode
ter no máximo um cadastro de médico. A exclusão do usuário também exclui o médico
relacionado.

Rotas adicionadas:

- `POST /users/{id}/doctor` cria o cadastro profissional;
- `GET /doctors` lista os médicos.

Nesta missão `crm` e `uf` recebem apenas validação estrutural. As regras de formato,
UF permitida e validade profissional pertencem à missão 06.

## Verificação

```bash
uv run alembic upgrade head
uv run pytest -q
```

Resultado atual: 24 testes aprovados.
