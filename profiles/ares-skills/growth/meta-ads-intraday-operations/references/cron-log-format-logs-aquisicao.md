# Formato de logs dos crons Meta — logs-aquisicao

Contexto validado em sessão com Rodolfo: os logs dos crons de aquisição precisam ser legíveis, com título contextual e colunas fixas. Isto vale para os crons `intraday R1-R5` e `reativar-todas` da operação OpenzedFinanzas-CC-ES, e deve ser reaproveitado para novas contas/operações Meta quando aplicável.

## Título

Usar sempre:

```text
<nome da conta> — <YYYY-MM-DD> — <HH:MM TZ da conta> — <tipo do cron>
```

Exemplo:

```text
OpenzedFinanzas-ES-CC-ES-03 — 2026-06-17 — 21:55 CEST — Reativar-todas Meta — dry-run
```

## Colunas base

```text
PG ID | País/Vertical | Regra usada | Status
```

Regras de preenchimento:

- `PG ID`: extrair do nome da campanha quando houver padrão `(pg_12345)`; exibir como `pg_12345`.
- `País/Vertical`: país vem do nome da campanha quando houver padrão como `- US -`; vertical vem da operação/config (`CC`, etc.). Formato: `US / CC`.
- `Regra usada`:
  - Intraday: incluir número + descrição curta, ex. `R4 — LOWEST_COST with MO >= 2, CPMO > USD 2.00 and spend >= USD 8.00`.
  - Reativar-todas: usar apenas `reativar-todas`. Não escrever `fora R1-R5`; Rodolfo corrigiu que isso polui a coluna e a rotina separada já fica clara no título.
- `Status`: usar `effective_status` atual da Meta, ex. `PAUSED`.

## Política de emissão

- Intraday continua silencioso quando não houver ação candidata ou erro.
- Reativar-todas em dry-run emite tabela quando houver campanhas pausadas candidatas.
- Nunca expor token Meta; logs podem mencionar somente item/campo/len se necessário.
- Enquanto em dry-run, explicitar no texto curto que nenhum write foi executado.

## Exemplo validado

```text
OpenzedFinanzas-ES-CC-ES-03 — 2026-06-17 — 21:55 CEST — Reativar-todas Meta — dry-run

PG ID    | País/Vertical | Regra usada    | Status
---------|---------------|----------------|-------
pg_22068 | US / CC       | reativar-todas | PAUSED
pg_22037 | US / CC       | reativar-todas | PAUSED
```
