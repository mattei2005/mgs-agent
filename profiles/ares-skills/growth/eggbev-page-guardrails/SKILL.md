---
name: eggbev-page-guardrails
description: "Opera limites e restrições de página da Eggbev BOT."
version: 1.0.0
author: Rodolfo Mattei, Ares
license: internal
platforms: [linux]
metadata:
  hermes:
    tags: [eggbev, meta-ads, leads, page-guardrails, bot]
    related_skills: [meta-ads-intraday-operations]
---

# Eggbev Page Guardrails

Rota funcional para limite de leads e restrições por Page da operação `Eggbev-US-CC-EN-BOT`.

## When to Use

Use para pedidos, alertas e runs da thread `1543312825890381865`, inclusive diagnóstico de mapping, freshness e pausas fail-closed.

## Fontes canônicas

- Prompt exato: `data/ares/discord/thread-prompts/1543312825890381865.txt`
- Contrato da rota: `discord.route_contracts.page_lead_guardrail`, `page_lead_guardrail` e `page_restriction_guardrail` em `data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT.json`
- Conta: `data/ares/meta-ads/accounts/1034081997659047.json`
- Runner LEADS: `scripts/ares-eggbev-page-lead-guardrail.py`
- Runner restrição: `scripts/ares-eggbev-page-restriction-guardrail.py`
- Audit/state: somente o run e state mais recentes de cada guardrail

## Disclosure progressivo

1. Leia o prompt e apenas os três nós da rota.
2. Para diagnóstico, abra o audit mais recente e agregue motivos; não despeje o JSON completo.
3. Consulte Meta e Smart Bidding vivas antes de afirmar que o bloqueio persiste.
4. Carregue `meta-ads-intraday-operations` apenas para alteração de cron ou governança transversal.

## Reconciliação e freshness

- Reconciliação prova que `UTM_CAMPAIGN`, `FB_PAGE_ID`, Page/creative Meta e campanha pertencem à mesma linha operacional.
- Freshness prova, por timestamp de atualização aceito, que a leitura Smart Bidding tem no máximo duas horas.
- `timestamp=null`, campo ausente, valor futuro ou idade acima do limite torna a fonte não verificável/stale.
- Quando mapping ou freshness falha, nenhuma campanha daquele conjunto é elegível para write; isso é degradação fail-closed, não prova de campanha ruim.

## Procedimento

1. Fazer pre-read Meta e Smart Bidding.
2. Reconciliar campanha, UTM e Page exatas.
3. Validar timestamp e idade.
4. Planejar somente campanhas inequivocamente elegíveis.
5. Executar um POST de status por alvo e confirmar por GET.
6. Persistir audit e entregar alerta curto com readback.

## Guardrails

- Match parcial/ambíguo ou freshness não verificável = zero write.
- Nunca substituir `LEADS` por `LEADS_TOTAL`.
- Não reativar automaticamente.
- Criação/alteração de cron segue `context/cron-scheduling-policy.md` e exige inventário global de minutos.

## Verification

- contagem por motivo fecha com as campanhas avaliadas;
- zero write em qualquer degradação de fonte;
- pausas confirmadas por GET;
- alerta e fallback de entrega reconciliados.
