# Aula e roteiro de apresentação — Missões 07 e 08

## O problema

Ao cadastrar um médico, o sistema precisa consultar o Conselho Federal de
Medicina usando CRM e UF. Como esse serviço é externo, ele pode responder,
demorar ou ficar indisponível. Nosso sistema não pode perder o cadastro por
causa disso.

## Missão 07 — Integração com o CFM

Criamos `app/cfm.py`, um **adapter** que isola os detalhes externos. A aplicação
chama apenas `find_doctor(crm, uf)`; ela não precisa conhecer o XML.

O adapter segue o manual oficial:

- SOAP 1.1 sobre HTTPS;
- corpo e resposta em XML;
- cabeçalhos `Content-Type: text/xml; charset=utf-8` e `SOAPAction: ""`;
- autenticação pela variável de ambiente `CFM_ACCESS_KEY`;
- leitura de `codigoErro` mesmo quando o CFM devolve HTTP 200;
- código `8101` significa médico não encontrado;
- códigos `2010`, `2030` e `2040` são falhas temporárias.

Nenhuma chave secreta foi gravada no Git. Sem a chave oficial, a arquitetura
continua demonstrável e segura, marcando a consulta como pendente.

## Missão 08 — CFM indisponível

O cliente usa timeout de 3 segundos e no máximo duas tentativas. A segunda
tentativa ocorre somente para falhas temporárias, como timeout, erro de rede,
HTTP diferente de 200, XML inválido ou códigos transitórios do CFM.

Se as tentativas falharem:

1. o médico continua salvo no PostgreSQL;
2. recebe o estado `VALIDATION_PENDING`;
3. pode ser validado depois por `POST /doctors/{id}/validate-cfm`.

Se o CFM encontrar o profissional, o estado muda para `VALIDATED` e o sistema
salva nome oficial, situação, tipo de inscrição e horário da validação. Se o
CRM/UF não existir, o estado fica `NOT_FOUND`.

## Banco de dados

A migration `0004` acrescenta à tabela `doctors`:

- `cfm_validation_status`;
- `cfm_validated_at`;
- `cfm_name`;
- `cfm_registration_status`;
- `cfm_registration_type`.

## Como explicar em um minuto

> Na Missão 7 eu integrei o sistema ao Web Service oficial do CFM por meio de
> um adapter. O CFM usa SOAP e XML, então essa complexidade ficou isolada do
> restante da aplicação. Na Missão 8 eu tratei a dependência externa com
> timeout e retry limitado. Se o CFM estiver fora do ar, o médico não é perdido:
> ele fica como VALIDATION_PENDING e pode ser validado novamente. Assim, o
> sistema é resiliente, mantém os segredos fora do código e pode ser testado sem
> depender do serviço real.

## Demonstração sugerida

1. Abra `/docs`.
2. Cadastre um usuário e copie seu `id`.
3. Use `POST /users/{user_id}/doctor` com CRM e UF.
4. Mostre `cfm_validation_status: VALIDATION_PENDING` sem a chave oficial.
5. Mostre `POST /doctors/{doctor_id}/validate-cfm` para a nova tentativa.
6. Explique que os testes substituem o CFM por respostas simuladas.

## Resultado

- 33 testes aprovados.
- Integração real preparada para receber a chave contratada do CFM.
- Nenhum teste acessa o serviço externo.
- Próxima etapa: Missão 09, ampliando testes e mocks.
