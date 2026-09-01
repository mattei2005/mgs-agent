---
name: eggbev-campaign-cloning
description: "Clona campanhas Eggbev BOT pelo Engine v3."
version: 1.0.0
author: Rodolfo Mattei, Ares
license: internal
platforms: [linux]
metadata:
  hermes:
    tags: [eggbev, meta-ads, campaign-cloning, bot]
    related_skills: [meta-campaign-engine-v3]
---

# Eggbev Campaign Cloning

Rota funcional para duplicar campanhas da operação `Eggbev-US-CC-EN-BOT`. Não cobre criação do zero nem outras operações.

## When to Use

Use para pedidos na thread `1543333373945053184`, intake de duplicação, configuração, manifest, execução ou recovery de clone.

## Fontes canônicas

- Prompt exato: `data/ares/discord/thread-prompts/1543333373945053184.txt`
- Contrato da rota: `discord.route_contracts.campaign_cloning` em `data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT.json`
- Contrato v3: `data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT-v3.json`
- Conta: `data/ares/meta-ads/accounts/1034081997659047.json`
- Configuração: `scripts/ares-eggbev-clone-config-report.py`
- Executor: `meta-campaign-engine-v3`

## Disclosure progressivo

1. Leia o prompt e somente `discord.route_contracts.campaign_cloning`.
2. Para configuração, execute o relatório próprio; não leia o contrato inteiro.
3. Feche modo, fontes, quantidade, budget e campos específicos da Page ou mídia.
4. Carregue `meta-campaign-engine-v3` apenas ao montar/prevalidar o manifest.
5. Nunca procurar outro writer ou script por semelhança.

## Procedimento

1. Fazer preflight vivo da campanha-fonte, hierarquia, lineage e colisão de `DUPnn`.
2. Consultar `page_eligibility_policy` e a denylist canônica para a Page efetiva do clone — inclusive `pure_clone` que preserva a Page. Se ela já teve qualquer restrição registrada, fazer zero write e solicitar outra Page; nunca clonar mantendo Page restrita.
3. Classificar exatamente `pure_clone`, `clone_prestaged` ou modo permitido no contrato vivo.
3. Preservar ou substituir campos somente conforme o modo escolhido.
4. Materializar manifest, apresentar resumo e aguardar o OK do request.
5. Executar exclusivamente pelo Engine v3.
6. Confirmar campanha, ad set, anúncios, tracking, Page, mídia/copy, budget, status e start time por GET.

## Guardrails

- `clone_page_switch` permanece fail-closed quando não estiver em `supported_modes`.
- Falha parcial inicia recovery readback-first no mesmo request.
- Cron não integra a transação. Qualquer cron futuro segue `context/cron-scheduling-policy.md`.

## Verification

- fonte e modo persistidos;
- próximo `DUPnn` livre confirmado no runtime;
- nenhum shell ou anúncio duplicado por retry;
- readback consolidado completo antes de concluir.
