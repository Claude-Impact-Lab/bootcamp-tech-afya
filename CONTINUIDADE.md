# Continuidade do aprendizado — User Manager

Atualizado em: 14/08/2026

## Onde paramos

- Branch atual: `missao-02`
- Último commit publicado: `7dc5239 feat: persiste usuarios no PostgreSQL`
- Missão 01 (`GET /users`): concluída e publicada.
- Missão 02 (`POST /users` + Pydantic): implementação principal concluída e publicada.
- A evolução da missão 02 foi salva e publicada: pré-cadastro, dados pessoais, senha
  protegida por hash, confirmação simulada de e-mail, login de usuário, sessão de
  administrador, página de congratulações com marca AFYA e interface responsiva.
- A página inicial oferece três caminhos: usuário, administrador e realizar cadastro.
- Missão 03 concluída: PostgreSQL 16 instalado, migration aplicada e rotas usando
  SQLAlchemy no banco real.
- Validação atual: `18 passed` com um aviso de depreciação vindo de uma dependência.

## Estado do salvamento

- Branch local e remota sincronizadas em `origin/missao-02`.
- As alterações funcionais estão salvas no GitHub.
- Os usuários ainda ficam em memória e desaparecem ao reiniciar o servidor; isso é
  proposital até a missão 03.
- O acesso pelo celular funciona na mesma rede Wi-Fi enquanto o servidor estiver
  ligado. Um link público permanente ainda exige hospedagem.

## Progresso das 10 missões

| Missão | Situação | Próxima ação |
|---|---|---|
| 01 — `GET /users` | Concluída | Apenas preservar os testes |
| 02 — `POST /users` | Concluída, testada e publicada | Aguardar revisão do instrutor |
| 03 — PostgreSQL | Concluída, testada e publicada | Preservar migration e testes isolados |
| 04 — `PUT` e `DELETE` | Não iniciada | Após persistência |
| 05 — User + Doctor | Não iniciada | Após CRUD persistente |
| 06 — CRM + UF | Não iniciada | Após entidade Doctor |
| 07 — Integração CFM | Não iniciada | Criar adapter externo |
| 08 — Falhas do CFM | Não iniciada | Timeout, retry e estado pendente |
| 09 — Testes e mocks | Não iniciada | Isolar completamente o CFM nos testes |
| 10 — Publicação | Não iniciada | Deploy, README e apresentação |

## Próxima sessão

1. Rodar `git status` e `uv run pytest -q`.
2. Confirmar que o serviço `postgresql-x64-16` está ativo.
3. Iniciar o FastAPI com a variável `DATABASE_URL` do Windows.
4. Conferir os comentários do Pull Request nº 6.
5. Começar a missão 04 com `PUT`, `DELETE` e idempotência.

## Comando para retomar com uma nova conversa

> Leia `CONTINUIDADE.md`, confira o Git e os testes, e continue meu treinamento a
> partir da missão 04. Confirme PostgreSQL, Git e testes antes de alterar código.
> Ensine passo a passo; não entregue código sem explicar.
