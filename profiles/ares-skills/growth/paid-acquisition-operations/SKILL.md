---
name: paid-acquisition-operations
description: "Operações de aquisição paga/ads para MGS: estruturar operações piloto, taxonomia de criativos, Drive de assets, inventário, credenciais read-only/controlled-write, e guardrails antes de Meta/Google Ads em produção."
version: 1.3.2
author: Ares
license: internal
metadata:
  hermes:
    tags: [ads, growth, meta-ads, google-drive, creatives, taxonomy, mgs]
---

# Paid Acquisition Operations — MGS/Ares

Use esta skill quando Rodolfo pedir para estruturar, auditar ou operacionalizar campanhas pagas, criativos, Drive, inventário, tracking ou integrações Meta/Google Ads. O padrão é **processo primeiro, credencial depois, execução por último**.

## Pedidos naturais e modelos reutilizáveis

- Trate horário e status escritos no pedido como parâmetros daquele pedido, não como padrões permanentes. Um valor usado em exemplo só vira default quando o contrato ativo da operação disser isso explicitamente.
- Quando a conta estiver inequivocamente resolvida, aceite `timezone da conta de anúncio`; não obrigue o gestor a repetir `America/...` no modelo. Preserve exatamente data, hora e status solicitados.
- Mantenha o pedido humano no nível da intenção: modo, fonte quando aplicável, mídia/copy a preservar ou substituir, tracking, budget, início e status. Não transforme `source_ad_id`, `creative_id` ou `effective_object_story_id` em campos que o gestor precise escolher; Ares resolve esses IDs pela rota da conta.
- No resultado técnico, reporte separadamente lineage (`source_ad_id`), identidade do pacote (`creative_id`) e post/prova social (`effective_object_story_id`). Se a conta exigir lineage para serving, explique isso uma vez sem mudar silenciosamente a intenção comercial nem autorizar reutilização de mídia no modo de criativos novos.

## Arquitetura e tempo de execução

Use um único Campaign Engine para a mecânica universal de criar do zero, duplicar, clonar, quota, recovery e readback. Separe naming, UTM, Page/pixel, evento, copy, mídia, schedule e pós-processamento em adapters/runners/contratos por família ou operação; relatórios, ROI e otimização ficam fora do executor. Não crie um novo major ou fork por nicho quando um adapter retrocompatível resolve.

Antes de iniciar um pedido cronometrado ou produtivo, conclua onboarding da conta, registro do runner, estrutura Drive, reconciliação do inventário, calibração do payload e smoke offline. Setup nunca entra no hot path. Quando existir runner da operação, use-o em vez de construir manifests e recoveries manualmente.

Meça e reporte separadamente:

```text
Engine/API         primeiro write até readback terminal de cada campanha
End-to-end         autorização EXECUTAR até fechamento do gate após pós-processamento
Preparação         preflight, seleção/reserva, download, variantes e upload
Pós-processamento  readback final, Drive, inventário e gate
```

Para benchmark comparável, mantenha modos, fontes, quantidade de ads, budgets e estado de mídia equivalentes. Determine mídia fresca pela ausência de `account_id + asset_id + checksum` no registry, não por `01_READY`; um registry hit torna o benchmark misto e deve ser declarado. Se a copy fonte for específica e faltar mídia fresca semanticamente compatível, preserve copy×criativo e rotule o mix em vez de trocar produto para melhorar o tempo.

Nunca chame a operação de rápida usando apenas o tempo interno do Engine quando o gestor esperou por preflight, mídia ou pós-processamento. Responda perguntas de velocidade com a conclusão primeiro: meta atingida ou não, tempo anterior, tempo atual/faixa, economia absoluta e percentual; detalhe arquitetura somente se o operador pedir.

## Política global de limites internos de budget

Enquanto `data/ares/meta-ads/policies/global-budget-limit-policy.json` estiver `INACTIVE_UNTIL_EXPLICIT_REACTIVATION`, nenhum cap, piso, envelope, pool ou teto interno de budget pode bloquear ou reduzir um pedido autorizado em qualquer conta de anúncio. O budget exato continua obrigatório e sujeito à autoridade vigente; pre-read e readback permanecem obrigatórios. Billing, `account_spend_limit`, credenciais e automatic scaling continuam separados. Valores históricos locais ficam apenas para auditoria. Só Rodolfo pode reativar a política explicitamente.

## Guided Meta setup — standing interaction rule

When Rodolfo asks for step-by-step Meta dashboard setup:

1. Use plain operational language and give **one atomic action per turn**: exact button/value, nearest wrong option, then stop.
2. State what is already complete before the next click. Never reopen **Edit**, repeat a wizard, or request another screenshot merely to reconfirm a choice just created and visually read back.
3. Accept an unambiguous operator confirmation such as “approved” for a binary state. Ask for a screenshot only when the exact page, status, owner, permission set, or visible error materially changes the next action.
4. If the operator lands on the wrong page, correct only the navigation. Do not advance the workflow.
5. Translate protocol details into the action Rodolfo must take; after he authorizes backend work, execute it and ask only for an ownership/domain decision that cannot be safely discovered. Do not make him choose OAuth implementation details.
6. Never ask the operator to reveal an App Secret, token, cookie, authorization code, or other credential.

For the configuration wizard load `references/meta-business-login-user-token-setup.md`; for token architecture load `references/meta-facebook-login-for-business-token-selection.md`; for Authorization Code callback implementation load `references/meta-facebook-login-for-business-callback.md`.

## Progressive disclosure — mandatory

1. Identify the exact operational branch below.
2. Load one route pack first; load another only when the first requires it or live evidence changes the branch.
3. Search the selected reference or exact source symbol before opening broader ranges.
4. Never load every reference or historical case study “for context.”
5. Reduce tool output above roughly 5 KB before another broad lookup.

Completion criterion: only the procedure and evidence required for the current action are loaded.

## Operational route packs

- **Replicar uma estratégia em vários sites/contas** → `references/strategy-family-operation-contract-and-thread-projection.md`
- **Interpretar pedidos naturais de criação por canal/operação** → `references/natural-campaign-request-contracts.md`
- **Criar/clonar campanhas Meta, lotes e alta escala** → `meta-campaign-engine-v3/SKILL.md`
- **Configurar OAuth/Facebook Login for Business para tokens de anunciantes** → `references/meta-business-login-user-token-setup.md`
- **Princípios → Caminho oficial: Canva Connect API** → `references/route-pack-01.md`
- **Fallback Canva local + intake atual `MGS-AGENTS/CRIATIVOS/UPLOAD MANUAL`** → `references/route-pack-02.md`
- **Precedentes históricos de `UPLOAD_CANVAS` + Meta Ads intraday** → `references/route-pack-03.md`
- **Regras de decisão de campanha → Referências** → `references/route-pack-04.md`
- **OAuth Meta, comparar apps/permissões/tier, escolher token ou decidir cutover** → `references/meta-facebook-login-for-business-token-selection.md`
- **Callback segura, Authorization Code, troca e validação do token** → `references/meta-facebook-login-for-business-callback.md`

Campaign Engine v3 é o único executor novo. `paid-acquisition-operations` continua dona do processo/guardrails gerais e não deve criar um runner alternativo por thread ou operação.

## Limpeza de campanhas de teste

Quando houver autorização explícita para excluir campanhas de teste e devolver assets:

1. Faça GET dos IDs exatos, filhos e Insights antes da exclusão; em caso de resposta ambígua, reconcilie antes de repetir qualquer write.
2. Confirme `configured_status=DELETED` e `effective_status=DELETED` por campanha.
3. Derive assets devolvíveis das atribuições/test history das campanhas com mídia nova; não devolva mídia apenas herdada por `pure_clone`, pois ela continua ligada à fonte.
4. Confirme ausência de uso em campanhas não deletadas. Asset com entrega real segue classificação/reteste; zero entrega pode voltar ao pool técnico.
5. Mova no Shared Drive com readback de `driveId`, parent e `trashed=false`; preserve histórico, limpe somente a atribuição corrente e restaure reserva do gestor com `ares_eligible=false`.
6. Não inferir autorização para excluir a mídia da library Meta. Essa exclusão é separada e exige reconciliação de dependências.
7. Reporte contagens no escopo da operação/vertical, não o inventário global.

## Context-efficiency guardrails

- Stop and re-plan after more than three overlapping reads of the same file.
- Keep this main file as a routing layer; preserve detailed procedures in route packs.
- Validate the real runtime result before reporting success.
