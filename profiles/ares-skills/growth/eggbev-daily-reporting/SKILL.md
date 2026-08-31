---
name: eggbev-daily-reporting
description: "Gera relatórios Diário da Eggbev BOT."
version: 1.0.0
author: Rodolfo Mattei, Ares
license: internal
platforms: [linux]
metadata:
  hermes:
    tags: [eggbev, meta-ads, daily, reporting, bot]
    related_skills: [meta-ads-intraday-operations]
---

# Eggbev Daily Reporting

Rota read-only para Diário e relatórios sob demanda da operação `Eggbev-US-CC-EN-BOT`.

## When to Use

Use para pedidos na thread `1541578596253175858`, configuração do Diário, relatório atual, ontem ou data específica.

## Fontes canônicas

- Prompt exato: `data/ares/discord/thread-prompts/1541578596253175858.txt`
- Contrato da rota: `discord.route_contracts.daily_reporting` e `daily_reporting_policy` em `data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT.json`
- Conta: `data/ares/meta-ads/accounts/1034081997659047.json`
- Configuração: `scripts/ares-eggbev-daily-config-report.py`
- Relatório: `scripts/ares-eggbev-daily-report.py`

## Disclosure progressivo

1. Leia o prompt e somente os dois nós de política acima.
2. Configuração: execute `python3 scripts/ares-eggbev-daily-config-report.py --check`.
3. Relatório: execute o runner com `--period today`, `yesterday` ou `YYYY-MM-DD`.
4. Não carregue umbrella Eggbev, Engine v3 ou outras rotas.
5. Carregue `meta-ads-intraday-operations` apenas para mudança de governança/scheduler.

## Procedimento

1. Fixar período, timezone ET e moeda USD.
2. Buscar Meta e Smart Bidding vivas no momento do pedido.
3. Reconciliar período, UTM, Page, campanha e freshness.
4. Renderizar todas as linhas elegíveis sem limite silencioso.
5. Validar métricas, paginação e ausência de write.
6. Publicar somente quando a rota/autorização correspondente estiver ativa.

## Guardrails

- Ausência, ambiguidade ou staleness vira `N/D`, nunca zero inventado.
- Diário não cria, clona, corta, reativa ou altera budget.
- O desenho de horário não autoriza cron/post automático.
- Qualquer cron futuro segue `context/cron-scheduling-policy.md`.

## Verification

- runner read-only retornou o período pedido;
- fontes e freshness declaradas;
- nenhuma métrica histórica foi reutilizada como atual;
- runtime de cron/post reportado conforme readback real.
