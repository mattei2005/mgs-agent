---
name: eggbev-page-guardrails
description: "Opera limites e restrições de página da Eggbev BOT."
version: 1.0.1
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
- Contrato da rota: `discord.route_contracts.page_lead_guardrail`, `page_lead_guardrail`, `page_restriction_guardrail` e `zero_pixel_result_guardrail` em `data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT.json`
- Conta: `data/ares/meta-ads/accounts/1034081997659047.json`
- Runner LEADS: `scripts/ares-eggbev-page-lead-guardrail.py`
- Runner restrição: `scripts/ares-eggbev-page-restriction-guardrail.py`
- Runner fallback de pixel: `scripts/ares-eggbev-zero-pixel-guardrail.py` — retido para auditoria/retomada, mas com etapa e write suspensos desde 2026-09-02 03:55 ET por Nicolas
- Audit/state: somente o run e state mais recentes de cada guardrail
- Denylist permanente de elegibilidade: `data/ares/meta-ads/state/Eggbev-US-CC-EN-BOT/restricted-page-denylist.json`; sincronizada pelo monitor a partir de `history.pages + active` e consumida antes de criar, clonar ou reativar

## Disclosure progressivo

1. Leia o prompt e apenas os quatro nós da rota.
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

- LEADS usa ticks físicos `08:16/20:16` para horas lógicas `08:00/20:00`; a restrição DTR usa `:03/:08/.../:58`, stagger de 30 segundos e o lock comum `roas-cycle.lock`, serializando os writers Eggbev sem fila duplicada.
- **Fallback pós-03:00 suspenso:** Nicolas suspendeu a etapa em 2026-09-02 03:55 ET. Ela foi removida do wrapper compartilhado, está com `stage_enabled=false`, `write_enabled=false` e schedule disabled; o cron de cinco minutos executa somente a restrição DTR. Não avaliar nem pausar campanha por zero pixel até nova instrução explícita de gestor autorizado.
- Em eventual retomada, preservar a política fail-closed: campanha configurada/efetivamente ACTIVE, spend do dia estritamente `> US$2`, zero `offsite_conversion.fb_pixel_custom` de `eggbev-pv-u` e `promoted_object` exato (`pixel_id`, `OTHER`, `eggbev-pv-u`) em todos os ad sets ativos. Exatamente US$2 não pausa; qualquer resultado mantém; mapping divergente = no write + alerta.
- Match parcial/ambíguo ou freshness não verificável = zero write.
- `LEADS` é o saldo dinâmico de leads ativos da Page: novas entradas aumentam o valor e desinscrições podem reduzi-lo. `LEADS_TOTAL` é cumulativo/histórico e nunca substitui `LEADS` no limite, na pausa ou na elegibilidade.
- Espaço restante até 5.000 LEADS é somente contexto para o gestor. Budget manual considera também Purchase ROAS, custo por resultado, resultados, budget, spend, CPM, CTR, CPC e padrão histórico; nunca derivar fórmula ou escala automática de LEADS isoladamente.
- LEADS e restrição DTR não reativam automaticamente. As duas campanhas pausadas historicamente pelo zero-pixel foram reativadas uma única vez por correção pontual autorizada por Nicolas; isso não cria regra automática.
- Criação/alteração de cron segue `context/cron-scheduling-policy.md` e exige inventário global de minutos.

## Verification

- contagem por motivo fecha com as campanhas avaliadas;
- zero write em qualquer degradação de fonte;
- pausas confirmadas por GET;
- alerta e fallback de entrega reconciliados.
