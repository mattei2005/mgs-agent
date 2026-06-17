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
Budget referência             | R$1.500/dia convertido pelo USD/BRL do dia; não pausar por teto
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

Scripts iniciais:

```text
/root/mgs-agent/scripts/ares-meta-common.py
/root/mgs-agent/scripts/ares-meta-auth-check.py
/root/mgs-agent/scripts/ares-meta-intraday-runner.py
```

## Regras operacionais

1. Intraday e reativar-todas são determinísticos e devem rodar como cron/script na VPS; skill é documentação/contexto operacional, não runtime.
2. R1-R5 são slots plugáveis por operação, não hardcoded por conta; para conta/Business Manager em USD, thresholds ficam em USD.
3. Em operações Europa/GDPR, usar `MO = actions.complete_registration` e `CPMO = spend / MO` como norte intraday, porque a Meta pode não expor subscribe de forma confiável. Não usar `subs/CPS` como métrica primária dessas operações.
4. Cortes e reativações ocorrem somente em nível de campanha.
4. Campanhas com `TEST` no nome têm carência de 3 dias usando `created_time` da Meta; fallback é `first_seen_at` local; durante essa carência ficam imunes a todas as regras R1-R5.
5. COST_CAP não pausa por CPS; o bid cap controla custo. Regra de CPS aplica pausa só quando a condição/bid strategy permitir, especialmente LOWEST_COST.
6. Reativar-todas pode ter lista de exclusão, mas ela começa vazia e Ares deve perguntar antes de adicionar algo.
7. Teto diário de R$1.500 é referência/log/base para testes de criativos; não pausar tudo ao bater o teto.
8. Log intraday no Discord deve ser resumido e enviado só quando houver ação/erro, salvo Rodolfo mudar a política.

## Defaults R1-R5 atuais — OpenzedFinanzas-CC-ES / Europa / USD

```text
Regra | Condição                                                   | Ação
------|------------------------------------------------------------|--------------------
R1    | MO = 0 e spend > USD 5.00                                  | pausar campanha
R2    | MO > 0 e CPMO > USD 3.25                                   | pausar campanha
R3    | MO = 1 e spend > USD 5.00                                  | pausar campanha
R4    | LOWEST_COST + MO >= 2 + CPMO > USD 3.00 + spend >= USD 8.00| pausar campanha
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

## Pitfalls

- Não inferir CPS sem validar qual campo da Meta corresponde ao subscriber real.
- Não confundir timezone do VPS com timezone da conta; crons finais devem respeitar a conta.
- Não pausar campanha TEST dentro dos 3 dias mesmo se regra disparar.
- Não usar teto de R$1.500 como kill switch; por decisão atual ele é referência para planejamento e deve ser convertido usando USD/BRL do dia porque a conta está em USD.
- Não enviar log a cada 30 minutos se nada aconteceu.
- Não transformar guardrails em fluxo separado: eles devem ser validações dentro dos scripts que leem/executam ações na conta.
