---
name: meta-ads-intraday-operations
description: "Operação intraday Meta Ads do Ares: reativar-todas, cortes determinísticos R1-R5, carência TEST, logs e auditoria para campanhas Messenger/chatbot."
version: 1.0.0
author: Ares
license: internal
metadata:
  hermes:
    tags: [meta-ads, intraday, campaigns, messenger, growth, mgs]
---

# Meta Ads Intraday Operations — Ares/MGS

Use esta skill quando Rodolfo pedir estrutura, execução, revisão ou manutenção dos crons Meta Ads intraday do Ares.

## Escopo atual do piloto

```text
Campo                         | Valor
------------------------------|------------------------------------------------------------
Operação                      | OpenzedFinanzas-CC-ES
Conta piloto                  | 1356770869843984
Canal                         | Messenger
Nível de ação                 | Campaign somente
Cortes intraday               | A cada 30 minutos via cron determinístico na VPS
Reativar-todas                | 00:30 no timezone da conta Meta via cron determinístico
Budget referência             | USD 300/dia; 20% (USD 60/dia) reservado para teste de criativos
Carência TEST                 | Nome contém TEST => não pausar/excluir por 3 dias
Log intraday                  | Só quando houver ação/erro; resumido no canal dedicado
Write                         | Desabilitado até aprovação explícita de Rodolfo
```

## Estrutura canônica

```text
/root/mgs-agent/data/ares/meta-ads/accounts/      # configs por conta
/root/mgs-agent/data/ares/meta-ads/operations/    # configs por operação país+vertical
/root/mgs-agent/data/ares/meta-ads/rules/         # rulesets R1-R5 + reativar-todas
/root/mgs-agent/data/ares/meta-ads/state/         # carência TEST, exclusões, estado local
/root/mgs-agent/data/ares/meta-ads/cache/         # cache para reduzir chamadas Meta API
/root/mgs-agent/data/ares/meta-ads/audit/         # logs auditáveis
/root/mgs-agent/data/ares/meta-ads/reports/       # relatórios
/root/mgs-agent/data/ares/meta-ads/permissions/   # permissionamento/guardrails
```

Scripts iniciais / cron:

```text
/root/mgs-agent/scripts/ares-meta-common.py
/root/mgs-agent/scripts/ares-meta-auth-check.py
/root/mgs-agent/scripts/ares-meta-intraday-runner.py
/root/mgs-agent/scripts/ares-meta-cron-runner.py                 # intraday + reativar-todas dry-run/no-write
/root/mgs-agent/scripts/ares-meta-token-expiry-alert.py          # watchdog de expiração do Token Meta API
/root/.hermes/profiles/ares/scripts/ares-meta-intraday-cron.sh   # wrapper Hermes script-only
/root/.hermes/profiles/ares/scripts/ares-meta-reactivate-all-cron.sh
/root/.hermes/profiles/ares/scripts/ares-meta-token-expiry-alert.sh
```

## Regras operacionais

1. Intraday e reativar-todas são determinísticos e devem rodar como cron/script na VPS; skill é documentação/contexto operacional, não runtime.
2. R1-R5 são slots plugáveis por operação, não hardcoded por conta; para conta/Business Manager em USD, thresholds ficam em USD.
3. Em operações Europa/GDPR, usar `MO = actions.complete_registration` e `CPMO = spend / MO` como norte intraday, porque a Meta pode não expor subscribe de forma confiável. Não usar `subs/CPS` como métrica primária dessas operações.
4. Cortes e reativações ocorrem somente em nível de campanha.
5. Campanhas com `TEST` no nome têm carência de 3 dias usando `created_time` da Meta; fallback é `first_seen_at` local; durante essa carência ficam imunes a todas as regras R1-R5.
6. COST_CAP não pausa por regra de custo (`CPS`/`CPMO`); o bid cap controla custo. Regra de custo aplica pausa só quando a condição/bid strategy permitir, especialmente LOWEST_COST.
6. Reativar-todas pode ter lista de exclusão, mas ela começa vazia e Ares deve perguntar antes de adicionar algo.
7. Teto diário de USD 300 é referência/log/base para orçamento; 20% (USD 60) fica reservado para testes de criativos novos quando houver espaço de budget.
8. Log intraday no Discord deve ser resumido e enviado só quando houver ação/erro, salvo Rodolfo mudar a política.
9. Logs dos crons Meta em `logs-aquisicao` devem usar título com `nome da conta — dia — horário no timezone da conta — tipo do cron` e tabela alinhada com estas colunas base: `PG ID`, `Nome da página`, `País/Vertical`, `Regra usada`, `Status`. Extrair `PG ID` do padrão `(pg_12345)` no nome da campanha e `Nome da página` do trecho inicial antes de ` - <país> - `. Em `Regra usada`, intraday deve mostrar o identificador e a descrição curta (`R1 — ...`, `R2 — ...`, `R3 — ...`, `R4 — ...`, `R5 — ...`). O cron diário separado deve mostrar só `reativar-todas` — não rotular como `fora R1-R5`, porque a distinção já está no tipo do cron/título.
10. Intraday R1-R5 e HOA são camadas separadas e devem coexistir inicialmente. HOA roda como camada de gestor/tráfego nos checkpoints 08:00, 12:00, 15:00, 18:00 e 22:00 no timezone da conta, usando MO/CPMO em operações Europa/GDPR.

## Defaults R1-R5 atuais — OpenzedFinanzas-CC-ES / Europa / USD

```text
Regra | Condição                                                   | Ação
------|------------------------------------------------------------|--------------------
R1    | MO = 0 e spend > USD 5.00                                  | pausar campanha
R2    | MO > 0 e CPMO > USD 3.25                                   | pausar campanha
R3    | MO = 1 e spend > USD 5.00                                  | pausar campanha
R4    | LOWEST_COST + MO >= 2 + CPMO > USD 2.00 + spend >= USD 8.00| pausar campanha
R5    | campanha pausada + MO >= 2 + CPMO < USD 2.50               | reativar campanha
```

Exceções: campanha `TEST` com menos de 3 dias ativos é imune a todas as regras; `COST_CAP` não pausa por regra de custo.

## Métricas Meta atuais

```text
Métrica | Definição
--------|------------------------------------------------------------
MO      | actions.complete_registration
CPMO    | spend / MO
```

Em operações Europa/GDPR, `MO/CPMO` são a métrica primária do intraday porque a informação de subscribe pode não aparecer de forma confiável na Meta. Se `MO = 0`, `CPMO` fica nulo/não comparável.

Para operações fora da Europa onde subscribe é confiável, usar mapping separado de `subs/CPS` conforme operação específica, sem misturar com o ruleset Europa.

## Formato de log dos crons

Quando configurar ou ajustar crons Meta Ads do Ares (`intraday` e `reativar-todas`), o log operacional deve ir para o canal `logs-aquisicao` quando configurado para a operação. O formato preferido por Rodolfo é uma tabela curta, com título contendo conta, dia e horário da conta.

```text
<Nome da conta> — <YYYY-MM-DD> — <HH:MM TZ> — <Tipo do cron>

PG ID    | País/Vertical | Regra usada    | Status
---------|---------------|----------------|-------
pg_22068 | US / CC       | reativar-todas | PAUSED
```

Regras de formatação:
- Extrair `PG ID` do nome da campanha quando houver padrão `(pg_12345)`.
- `País/Vertical`: país do nome da campanha quando disponível + vertical da operação.
- `Regra usada`: `R1`–`R5` no intraday; `reativar-todas` no cron diário.
- `Status`: `effective_status` atual da campanha.
- Se não houver ação candidata nem erro, o cron fica silencioso e salva apenas audit JSON local.
- Sempre declarar `dry_run_no_write` no audit enquanto controlled-write não estiver aprovado; não precisa poluir a tabela principal com essa coluna.

## Segurança e autorização

- Nunca expor token Meta no chat.
- Token atual esperado no 1Password: item `Token Meta API`.
- Começar com leitura/dry-run; `ads_management`/write só depois de aprovação explícita.
- No piloto, só Rodolfo autoriza alteração de campanha.
- Budget/billing continuam fora de automação e exigem confirmação/double-confirm conforme política MGS.
- Antes de reportar sucesso de pausa/reativação, validar com GET na Meta API.

## Checklist para avanço de fase

```text
Fase | Critério
-----|-----------------------------------------------------------------
0    | Estrutura local criada e validada
1    | Token lido do 1Password sem exposição e conta lida read-only
2    | Métrica CPS mapeada nos insights Meta
3    | R1-R5 definidas por Rodolfo e rodando dry-run
4    | Canal Discord de log configurado
5    | Controlled-write aprovado explicitamente
```

## Referências

- `references/openzedfinanzas-cc-es-pilot.md` — decisões, estrutura criada, validações read-only e lições reutilizáveis do primeiro piloto Meta Messenger.
- `references/threshold-calibration.md` — método read-only de baixa carga para analisar mês da conta e sugerir thresholds R1-R5 sem pedir payload pesado da Meta API.
- `references/openzedfinanzas-cron-logging-2026-06-17.md` — detalhe da configuração dos crons intraday/reativar-todas e formato de tabela corrigido por Rodolfo para `logs-aquisicao`.
- `references/threshold-calibration.md` — método read-only de baixa carga para analisar mês da conta e sugerir thresholds R1-R5 sem pedir payload pesado da Meta API.
- `references/cron-log-format-logs-aquisicao.md` — formato validado por Rodolfo para logs dos crons Meta em `logs-aquisicao`: título conta/dia/horário e colunas `PG ID`, `País/Vertical`, `Regra usada`, `Status`.

## Pitfalls

- Não inferir CPS sem validar qual campo da Meta corresponde ao subscriber real.
- Não confundir timezone do VPS com timezone da conta; crons finais devem respeitar a conta.
- Não pausar campanha TEST dentro dos 3 dias mesmo se regra disparar.
- Não usar teto de R$1.500 como kill switch; por decisão atual ele é referência para planejamento e deve ser convertido usando USD/BRL do dia porque a conta está em USD.
- Não enviar log a cada 30 minutos se nada aconteceu.
- Não transformar guardrails em fluxo separado: eles devem ser validações dentro dos scripts que leem/executam ações na conta.
