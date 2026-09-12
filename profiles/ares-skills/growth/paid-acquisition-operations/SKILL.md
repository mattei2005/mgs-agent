---
name: paid-acquisition-operations
description: "Operações de aquisição paga/ads para MGS: estruturar operações piloto, taxonomia de criativos, Drive de assets, inventário, credenciais read-only/controlled-write, e guardrails antes de Meta/Google Ads em produção."
version: 1.2.0
author: Ares
license: internal
metadata:
  hermes:
    tags: [ads, growth, meta-ads, google-drive, creatives, taxonomy, mgs]
---

# Paid Acquisition Operations — MGS/Ares

Use esta skill quando Rodolfo pedir para estruturar, auditar ou operacionalizar campanhas pagas, criativos, Drive, inventário, tracking ou integrações Meta/Google Ads. O padrão é **processo primeiro, credencial depois, execução por último**.

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
- **OAuth Meta / Facebook Login for Business e escolha de token** → `references/meta-facebook-login-for-business-token-selection.md`
- **Callback segura, Authorization Code, troca e validação do token** → `references/meta-facebook-login-for-business-callback.md`

Campaign Engine v3 é o único executor novo. `paid-acquisition-operations` continua dona do processo/guardrails gerais e não deve criar um runner alternativo por thread ou operação.

## Context-efficiency guardrails

- Stop and re-plan after more than three overlapping reads of the same file.
- Keep this main file as a routing layer; preserve detailed procedures in route packs.
- Validate the real runtime result before reporting success.
