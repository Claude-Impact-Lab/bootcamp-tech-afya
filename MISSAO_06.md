# Missão 06 — Validar CRM + UF

## Regras locais implementadas

- CRM é obrigatório e aceita somente algarismos.
- UF é normalizada para maiúsculas.
- UF deve pertencer à lista oficial das 27 siglas brasileiras.
- A combinação `CRM + UF` é única no PostgreSQL.
- O mesmo número de CRM pode existir em UFs diferentes.
- Uma duplicidade devolve `409 Conflict`.

## Separação de responsabilidades

Esta missão valida formato e consistência local. Ela não afirma que o profissional
existe ou que sua inscrição está ativa. Essa confirmação dependerá do serviço oficial
do CFM e será isolada em um adapter na missão 07.

## Migration

A migration `0003` cria a constraint única `uq_doctors_crm_uf` na tabela `doctors`.
