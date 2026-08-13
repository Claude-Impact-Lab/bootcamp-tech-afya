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

## Conceitos

- Tabela: conjunto de registros do mesmo tipo.
- Coluna: atributo, como `name` ou `email`.
- Linha: um usuário salvo.
- Chave primária: `id` único de cada usuário.
- Migration: versão controlada da estrutura do banco.

## Próxima aula

1. Instalar ou disponibilizar uma instância PostgreSQL.
2. Criar o banco `usermanager`.
3. Configurar `DATABASE_URL` sem salvar senha real no Git.
4. Executar `uv run alembic upgrade head`.
5. Trocar gradualmente a lista `USERS` por consultas e transações SQLAlchemy.

Não execute a migration antes de confirmar que o PostgreSQL está disponível e que a
URL aponta para o banco correto.
