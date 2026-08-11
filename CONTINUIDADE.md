# Continuidade do aprendizado — User Manager

Atualizado em: 11/08/2026

## Onde paramos

- Branch atual: `missao-02`
- Último commit publicado: `7c78344 feat: cria cadastro de usuarios com POST`
- Missão 01 (`GET /users`): concluída e publicada.
- Missão 02 (`POST /users` + Pydantic): implementação principal concluída e publicada.
- Trabalho local posterior ao último commit: pré-cadastro, dados pessoais, confirmação
  simulada de e-mail, sessão de administrador, tela atualizada e novos testes.
- Validação atual: `14 passed` com um aviso de depreciação vindo de uma dependência.

## Alterações locais ainda não salvas em commit

- `app/main.py`
- `app/templates/index.html`
- `tests/test_main.py`

Essas mudanças pertencem à evolução da missão 02 e devem ser revisadas com calma antes
de criar o próximo commit. Os usuários ainda ficam em memória e desaparecem ao
reiniciar o servidor; isso é proposital até a missão 03.

## Progresso das 10 missões

| Missão | Situação | Próxima ação |
|---|---|---|
| 01 — `GET /users` | Concluída | Apenas preservar os testes |
| 02 — `POST /users` | Concluída no núcleo; evolução local em revisão | Revisar, explicar e versionar mudanças locais |
| 03 — PostgreSQL | Não iniciada | Modelar tabela, configurar banco e migrations |
| 04 — `PUT` e `DELETE` | Não iniciada | Após persistência |
| 05 — User + Doctor | Não iniciada | Após CRUD persistente |
| 06 — CRM + UF | Não iniciada | Após entidade Doctor |
| 07 — Integração CFM | Não iniciada | Criar adapter externo |
| 08 — Falhas do CFM | Não iniciada | Timeout, retry e estado pendente |
| 09 — Testes e mocks | Não iniciada | Isolar completamente o CFM nos testes |
| 10 — Publicação | Não iniciada | Deploy, README e apresentação |

## Próxima sessão

1. Rodar `git status` e `uv run pytest -q`.
2. Revisar juntos o fluxo criado na missão 02, especialmente segurança, regras de
   pré-cadastro e confirmação de e-mail.
3. Corrigir o que for necessário sem começar PostgreSQL prematuramente.
4. Criar commit e publicar a evolução da missão 02 somente após o aluno conseguir
   explicar as mudanças.
5. Começar a missão 03 com uma explicação curta de banco relacional, tabela `users`,
   chave primária e migrations.

## Comando para retomar com uma nova conversa

> Leia `CONTINUIDADE.md`, confira o Git e os testes, e continue meu treinamento a
> partir da revisão final da missão 02. Ensine passo a passo; não entregue código sem
> explicar.
