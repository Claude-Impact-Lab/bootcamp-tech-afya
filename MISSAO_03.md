# Missão 03 — Persistir no PostgreSQL

## O problema que vamos resolver

Antes desta missão, os usuários ficavam na lista `USERS`. Quando o servidor
reiniciava, os novos dados sumiam. Persistir significa salvar os registros fora da
memória do Python; agora eles ficam no PostgreSQL.

## Fundação criada

- SQLAlchemy: traduz objetos Python em comandos SQL.
- Psycopg: conecta a aplicação ao PostgreSQL.
- Alembic: registra mudanças na estrutura do banco por migrations.
- `app/database.py`: conexão, engine e sessões.
- `app/models.py`: modelo da tabela `users`.
- `migrations/versions/0001_create_users.py`: primeira migration.
- `.env.example`: exemplo da variável `DATABASE_URL`.

## Banco local conectado em 13/08/2026

- PostgreSQL 16 instalado como serviço local.
- Serviço `postgresql-x64-16` com inicialização automática.
- Autenticação local protegida por `SCRAM-SHA-256`.
- Senha forte guardada na variável de ambiente `DATABASE_URL` do usuário do Windows.
- Banco `usermanager` criado.
- Migration `0001` aplicada com sucesso.
- Tabelas existentes: `alembic_version` e `users`.
- Arquivos `.env` e diretórios locais do PostgreSQL protegidos pelo `.gitignore`.

## Rotas migradas para o PostgreSQL

- `GET /users`: executa `SELECT` e respeita a visão de administrador.
- `POST /users`: executa `INSERT`, `COMMIT` e atualiza o objeto com `refresh`.
- `POST /users/login`: busca o usuário pelo e-mail no banco.
- `GET /users/confirm`: atualiza confirmação e status com transação.
- E-mail duplicado devolve `409 Conflict`.
- A antiga lista `USERS` foi removida.
- Cada requisição recebe uma sessão SQLAlchemy que é fechada automaticamente.

## Testes e prova de persistência

- Os testes usam SQLite temporário em memória e nunca alteram o banco real.
- 18 testes automatizados passam.
- Um usuário temporário foi criado pela API, encontrado depois do servidor reiniciar e
  removido em seguida. Essa prova confirma a persistência ponta a ponta.

## Conceitos

- Tabela: conjunto de registros do mesmo tipo.
- Coluna: atributo, como `name` ou `email`.
- Linha: um usuário salvo.
- Chave primária: `id` único de cada usuário.
- Migration: versão controlada da estrutura do banco.

## Missão 03 concluída

O requisito central foi atendido: os usuários agora permanecem no PostgreSQL mesmo
quando o servidor reinicia. A próxima etapa do treinamento é a missão 04, com `PUT`,
`DELETE` e idempotência.

Não execute a migration antes de confirmar que o PostgreSQL está disponível e que a
URL aponta para o banco correto.
