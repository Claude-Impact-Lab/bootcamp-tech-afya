# Missão 03 — Persistir no PostgreSQL

## O problema que vamos resolver

Hoje os usuários ficam na lista `USERS`. Quando o servidor reinicia, os novos dados
somem. Persistir significa salvar os registros fora da memória do Python.

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

## Conceitos

- Tabela: conjunto de registros do mesmo tipo.
- Coluna: atributo, como `name` ou `email`.
- Linha: um usuário salvo.
- Chave primária: `id` único de cada usuário.
- Migration: versão controlada da estrutura do banco.

## Próxima aula

1. Criar uma dependência FastAPI que abre e fecha uma sessão SQLAlchemy.
2. Migrar `GET /users` da lista `USERS` para um `SELECT` no PostgreSQL.
3. Migrar `POST /users` para um `INSERT` com transação.
4. Adaptar os testes para um banco de teste isolado.
5. Remover a lista `USERS` quando nenhuma rota depender mais dela.

Não execute a migration antes de confirmar que o PostgreSQL está disponível e que a
URL aponta para o banco correto.
