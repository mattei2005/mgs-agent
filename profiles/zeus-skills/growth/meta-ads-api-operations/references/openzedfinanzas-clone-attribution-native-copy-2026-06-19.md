# OpenzedFinanzas clone fidelity — attribution 7/1 vs native copy (2026-06-19)

## Context

Rodolfo reviewed the Ares thread `1516267365934043236` about OpenzedFinanzas Meta Ads cloning. Ares had successfully created/activated/paused campaign, adset, and ads for Elena Santana, then created a full structural clone:

```text
Source campaign: Elena Santana - ES - ESP - (pg_22091) - 4
Clone shape:     1 campaign / 2 adsets / 6 ads / PAUSED
```

But the clone was not accepted as final because one critical field diverged:

```text
Field        Source                         Clone
------------ ------------------------------ ----------------
Attribution  7-day click + 1-day view       1-day click
```

Rodolfo's correction: a “clone” must be a faithful clone. A functional rebuild that changes attribution is not complete.

## Durable lessons

### 1. Clone is not create-from-zero

For this class of task, do not treat generic campaign creation as clone. There are two separate modes:

```text
Mode                         Purpose
---------------------------- ------------------------------------------------
Replacement Ares padrão      1 campaign / 1 adset / 3 ads / USD 25 / PAUSED
Clone fiel                   Mirror source campaign/adsets/ads writable fields
```

When the user says “clonar do jeitinho que é”, use clone fiel.

### 2. Do not declare attribution divergence inevitable too early

Ares/Zeus suspected Meta may reject `7-day click + 1-day view` on new creation, but the next session must first rule out payload mistakes:

```text
1. GET source adset fields:
   attribution_spec, attribution_setting, use_unified_attribution_setting
2. GET clone adset with the same fields.
3. Inspect scripts for hardcoded `CLICK_THROUGH window_days=1`.
4. Test one PAUSED adset with `attribution_setting=7d_click_1d_view`.
5. If needed, test `use_unified_attribution_setting=true` with that attribution setting.
```

Only after these fail should the agent call the divergence a true Meta/API limitation.

### 3. Native/async copy is likely the correct clone-fiel route

Native/async copy may preserve internal Meta metadata that manual rebuild cannot express. It should be investigated as the primary path for perfect clone fidelity.

But the decision tree is:

```text
If rebuild with attribution_setting 7/1 works
  -> Fix manual clone payload and continue.
If native/async copy works and preserves 7/1
  -> Promote native/async copy to clone-fiel route.
If public API blocks native/async copy but Ads Manager UI duplicates correctly
  -> Fallback is AdsPower/UI automation, not accepting a non-identical clone.
```

### 4. No System User path

Rodolfo explicitly removed System User from scope. Do not recommend it as the solution for this task. Use user/app token + app permissions + real asset access.

## Message template used to align Ares

```text
Ares, alinhamento do Zeus a pedido do Rodolfo sobre o clone Elena 100%.

Minha leitura: sua recomendação de investigar native/async copy faz sentido como caminho principal, mas não trate isso como único caminho nem aceite o clone atual como final.

Ponto central:
- O clone atual é funcional, mas NÃO é clone perfeito porque mudou attribution de `7-day click + 1-day view` para `1-day click`.
- Isso precisa ser tratado como pendência crítica de fidelidade, não como divergência inevitável ainda.

Hipótese técnica principal:
- Pode ser que a rota manual/rebuild esteja usando o campo errado/legado.
- `attribution_spec` pode estar vindo no GET da source, mas para criação nova a Meta pode esperar `attribution_setting=7d_click_1d_view` e/ou `use_unified_attribution_setting`.
- Se alguma rota do script estiver hardcoded com `CLICK_THROUGH window_days=1`, ela já está forçando o erro.

Ordem recomendada:
1. Fazer GET do source adset Elena e do clone adset com estes campos: `attribution_spec`, `attribution_setting`, `use_unified_attribution_setting`.
2. Testar rebuild isolado de 1 adset PAUSED usando `attribution_setting=7d_click_1d_view`, sem criar ads.
3. Se falhar, testar `use_unified_attribution_setting=true` junto.
4. Em paralelo/depois, corrigir native/async copy para tentar preservar metadados internos da Meta.
5. Comparar GET source vs clone campo a campo.
6. Só declarar clone 100% quando os campos graváveis baterem, principalmente attribution.

Sobre native/async copy:
- Sim, provavelmente é o melhor caminho para preservar 7/1, porque a Meta pode carregar metadados internos que o create manual não expõe.
- Mas antes de concluir que só UI/AdsPower resolve, prove que a API rejeita `attribution_setting=7d_click_1d_view` na criação controlada.

Se native/async copy funcionar e vier com 7/1, promova esse fluxo para clone fiel oficial.
Se native/async copy bloquear por API/app/tier e a UI duplica normal, aí sim o fallback real vira AdsPower/UI automation.

Não continuar criando clone 1-day como se estivesse resolvido. Ele é apenas prova funcional.
```

## Related artifacts mentioned in-session

- Discord thread: `1516267365934043236`
- Source account: `OpenzedFinanzas-ES-CC-ES-03`
- Ad account: `1356770869843984`
- Source campaign: `Elena Santana - ES - ESP - (pg_22091) - 4`
- Key scripts to inspect for hardcoded attribution:
  - `/root/mgs-agent/scripts/ares-meta-replacement-clone-videoid.py`
  - `/root/mgs-agent/scripts/ares-meta-replacement-clone.py`
  - any native/async copy probe scripts under `/root/mgs-agent/scripts/`
