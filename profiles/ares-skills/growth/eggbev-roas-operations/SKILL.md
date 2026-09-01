---
name: eggbev-roas-operations
description: "Opera ciclos Corte e ROAS da Eggbev BOT."
version: 1.0.0
author: Rodolfo Mattei, Ares
license: internal
platforms: [linux]
metadata:
  hermes:
    tags: [eggbev, meta-ads, roas, intraday, bot]
    related_skills: [meta-ads-intraday-operations]
---

# Eggbev ROAS Operations

Rota funcional dos ciclos Corte e ROAS da operação `Eggbev-US-CC-EN-BOT`.

## When to Use

Use para pedidos e ciclos da thread `1541578606076231750`, incluindo configuração, execução, relatório, diagnóstico e recovery.

## Fontes canônicas

- Prompt exato: `data/ares/discord/thread-prompts/1541578606076231750.txt`
- Contrato da rota: `discord.route_contracts.roas_cycle` e `roas_cycle_policy` em `data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT.json`
- Conta: `data/ares/meta-ads/accounts/1034081997659047.json`
- Runner: `scripts/ares-eggbev-roas-cycle.py`
- Helper: `scripts/ares-eggbev-roas-common.py`
- Audit/state: somente o run e state mais recentes dessa rota

## Disclosure progressivo

1. Leia o prompt e os dois nós de política acima; não carregue o contrato inteiro.
2. Para estado atual, consulte runner, state e audit mais recentes, depois Meta e Smart Bidding vivas.
3. Carregue `meta-ads-intraday-operations` somente para mudança de governança, scheduler ou contrato transversal.
4. Nunca carregar Campaign Engine v3: esta rota não cria nem clona campanhas.

## Procedimento

1. Identificar ciclo/fase e período ET.
2. Validar Meta, Smart Bidding, UTM/Page, freshness e conflitos antes de qualquer write.
3. Produzir plano idempotente por anúncio/campanha conforme a fase ativa.
4. Executar somente o escopo autorizado, com pre-read e GET após cada mudança.
5. Renderizar e validar o relatório da rota.
6. Em falha parcial, reconciliar e continuar o mesmo run sem replay cego.

## Guardrails

- **Reativação fail-closed por Page:** Fase 3, recovery e qualquer ativação manual consultam `page_eligibility_policy` + denylist canônica. Page com qualquer histórico de restrição nunca é reativada; campanha, conjunto e anúncios ficam fora, e o operador recebe o motivo. A regra não impede cortes/pausas.
- Fonte indisponível, stale ou irreconciliável significa zero write e alerta.
- Alteração de threshold ou automação segue os gates do contrato.
- Criação/alteração de cron segue `context/cron-scheduling-policy.md` e exige inventário global antes do minuto ser escolhido.

## Verification

- ciclo e período corretos;
- ações e zero-writes explicados;
- readbacks completos;
- relatório entregue na thread fixa sem duplicação.
