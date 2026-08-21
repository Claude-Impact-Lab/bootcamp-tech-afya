# Continuidade do aprendizado — User Manager

Atualizado em: 21/08/2026

## Onde paramos

- Branch atual: `thiago-duque`
- Último commit publicado antes das missões 07 e 08: `a30741b feat: valida CRM e UF de medicos`
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
- Missão 07 concluída: adapter SOAP 1.1 para o Web Service oficial do CFM,
  configurado por variáveis de ambiente e sem scraping.
- Missão 08 concluída: timeout, duas tentativas para falhas temporárias, estado
  `VALIDATION_PENDING` e rota para tentar novamente.
- Migration `0004` criada para armazenar o resultado da validação do CFM.
- Validação atual: `33 passed` com um aviso de depreciação vindo de uma dependência.

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
| 07 — Integração CFM | Concluída e testada | Configurar chave oficial quando fornecida pelo CFM |
| 08 — Falhas do CFM | Concluída e testada | Preservar timeout, retry limitado e pendência |
| 09 — Testes e mocks | Parcialmente iniciada | Ampliar cenários sem chamar o CFM real |
| 10 — Publicação | Não iniciada | Deploy, README e apresentação |

## Próxima sessão

1. Apresentar as missões 07 e 08 usando `MISSOES_07_E_08.md`.
2. Revisar as novas rotas e campos em `/docs`.
3. Iniciar a missão 09 ampliando testes e mocks do CFM.

## Comando para retomar com uma nova conversa

> Leia `CONTINUIDADE.md`, confira o Git e os testes, e continue meu treinamento a
> partir da missão 09. Confirme PostgreSQL, Git e testes antes de alterar código.
> Ensine passo a passo; não entregue código sem explicar.
