# Continuidade do aprendizado — User Manager

Atualizado em: 21/08/2026

## Onde paramos

- Branch atual: `thiago-duque`
- Último commit publicado: `2672bed docs: atualiza continuidade apos missao 03`
- Missão 01 (`GET /users`): concluída e publicada.
- Missão 02 (`POST /users` + Pydantic): implementação principal concluída e publicada.
- A evolução da missão 02 foi salva e publicada: pré-cadastro, dados pessoais, senha
  protegida por hash, confirmação simulada de e-mail, login de usuário, sessão de
  administrador, página de congratulações com marca AFYA e interface responsiva.
- A página inicial oferece três caminhos: usuário, administrador e realizar cadastro.
- Missão 03 concluída: PostgreSQL 16 instalado, migration aplicada e rotas usando
  SQLAlchemy no banco real.
- Missão 04 concluída: edição com `PUT`, exclusão com `DELETE` e comportamento
  idempotente coberto por testes.
- Missão 05 concluída: entidade `Doctor`, relação um-para-um com `User` e exclusão
  em cascata.
- Migration `0002` aplicada ao PostgreSQL local.
- Missão 06 concluída: CRM numérico, UF brasileira válida e unicidade de `CRM + UF`.
- Migration `0003` aplicada ao PostgreSQL local.
- Validação atual: `29 passed` com um aviso de depreciação vindo de uma dependência.

## Estado do salvamento

- As missões 04 e 05 foram revisadas e estão prontas para publicação.
- Usuários e médicos ficam persistidos no PostgreSQL.
- O acesso pelo celular funciona na mesma rede Wi-Fi enquanto o servidor estiver
  ligado. Um link público permanente ainda exige hospedagem.

## Progresso das 10 missões

| Missão | Situação | Próxima ação |
|---|---|---|
| 01 — `GET /users` | Concluída | Apenas preservar os testes |
| 02 — `POST /users` | Concluída, testada e publicada | Aguardar revisão do instrutor |
| 03 — PostgreSQL | Concluída, testada e publicada | Preservar migration e testes isolados |
| 04 — `PUT` e `DELETE` | Concluída e testada | Preservar testes de idempotência |
| 05 — User + Doctor | Concluída e testada | Preservar relação e cascade |
| 06 — CRM + UF | Concluída e testada | Preservar regras e constraint única |
| 07 — Integração CFM | Não iniciada | Criar adapter externo |
| 08 — Falhas do CFM | Não iniciada | Timeout, retry e estado pendente |
| 09 — Testes e mocks | Não iniciada | Isolar completamente o CFM nos testes |
| 10 — Publicação | Não iniciada | Deploy, README e apresentação |

## Próxima sessão

1. Revisar as rotas das missões 04, 05 e 06 em `/docs`.
2. Confirmar os 29 testes.
3. Iniciar a missão 07 sem scraping, usando o webservice oficial do CFM.
4. Isolar o CFM em um adapter com contrato `find_doctor(crm, uf)`.

## Comando para retomar com uma nova conversa

> Leia `CONTINUIDADE.md`, confira o Git e os testes, e continue meu treinamento a
> partir da missão 07. Confirme PostgreSQL, Git e testes antes de alterar código.
> Ensine passo a passo; não entregue código sem explicar.
