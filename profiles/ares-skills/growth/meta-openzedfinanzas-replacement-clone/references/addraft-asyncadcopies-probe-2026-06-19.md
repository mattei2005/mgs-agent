# AdDraft / asyncadcopies probe — clone perfeito Elena 7/1 — 2026-06-19

## Contexto

Rodolfo explicou que na UI o fluxo correto parece ser: duplicar campanha → abrir em edição/draft → ajustar attribution → publicar. Ares investigou a rota API equivalente para evitar rebuild manual direto.

## Descoberta principal

Endpoint de cópia assíncrona existe no Graph quando chamado por POST:

```text
POST /act_<ACCOUNT_ID>/asyncadcopies
```

Probe sem parâmetros retornou:

```text
(#100) The parameter ad_object_ids is required
```

Com `ad_object_ids=[<campaign_id>]`, `deep_copy=true`, `status_option=PAUSED`, a API respondeu:

```text
(#100) The parameter addraft_id is required
```

Ou seja: para o fluxo assíncrono que replica a lógica de edição/draft, a API exige um `addraft_id`.

## Tentativa de criar AdDraft

Endpoint descoberto:

```text
POST /act_<ACCOUNT_ID>/addrafts
```

Probe sem `name` retornou:

```text
(#100) The parameter name is required
```

Tentativa com `name` retornou:

```text
code    | 3
message | Application does not have the capability to make this API call.
```

Audit:

```text
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-addraft-asyncadcopies-20260619T075000Z.json
```

## Conclusão operacional

A hipótese de Rodolfo está correta: o fluxo de clone perfeito 7/1 provavelmente passa por um draft interno (`addraft_id`) e depois `asyncadcopies`, não por `POST /campaigns` + `POST /adsets` manual.

Bloqueio atual não é payload de attribution; é capacidade do app/API:

```text
Rota                           | Status
-------------------------------|------------------------------------------------
POST /act/asyncadcopies         | existe, mas exige addraft_id
POST /act/addrafts              | existe, mas app atual não tem capability
Rebuild manual /adsets 7/1      | falha 1885501
Adset update depois de criado   | falha 1504040
```

Próximos caminhos:

1. Se Rodolfo exigir 100% API: obter app/acesso com capability para `addrafts`/draft API ou outro mecanismo oficial de draft.
2. Se aceitar automação operacional mas não API pura: usar Ads Manager UI/browser para criar o draft/duplicação e validar via API depois.
3. Não chamar clone 1-day click de perfeito.
