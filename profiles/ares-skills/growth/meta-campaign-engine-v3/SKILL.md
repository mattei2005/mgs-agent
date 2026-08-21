---
name: meta-campaign-engine-v3
description: "Executa campanhas Meta em lotes determinísticos v3."
version: 3.0.8
author: Rodolfo Mattei, Ares, Zeus
license: internal
platforms: [linux]
metadata:
  hermes:
    tags: [mgs, ares, meta-ads, campaign-engine, batch, high-scale]
    related_skills: [direct-traffic-cbo-operations, paid-acquisition-operations]
---

# Meta Campaign Engine v3 — MGS/Ares

Motor central e versionado de Campaign Ops. O agente interpreta o pedido e materializa um manifest; o executor cria/clona campanhas sem `Searching`, edição de código ou descoberta de rota dentro do hot path.

## When to use

Use para:

- criar ou clonar campanhas Meta;
- executar lotes em uma ou várias contas;
- usar mídia pre-stageada na library da Meta;
- medir throughput, quota e readback por lane;
- migrar uma operação do executor v2.

Não use para editar credencial, billing, app permissions, pixel crítico, ChatPion, quiz, SMS Funnel ou WordPress.

## Fontes canônicas

```text
Config v3       /root/mgs-agent/data/ares/meta-ads/engine-v3/config.json
Operações       /root/mgs-agent/data/ares/meta-ads/operations/*-v3.json
Media registry  /root/mgs-agent/data/ares/meta-ads/engine-v3/media-registry.json
Executor         /root/mgs-agent/scripts/ares-campaign-engine-v3.py
Runner diário CPV /root/mgs-agent/scripts/ares-creditoparaveiculo-v3-daily.py
Módulos          /root/mgs-agent/scripts/ares_campaign_v3/
Audits           /root/mgs-agent/data/ares/meta-ads/engine-v3/audit/
State/lanes      /root/mgs-agent/data/ares/meta-ads/engine-v3/state/
```

## Progressive disclosure

1. Arquitetura, lanes, batch e segurança → `references/architecture-and-runtime.md`.
2. Contrato do manifest e comandos → `references/manifest-and-commands.md`.
3. Migração e rollback v2→v3 → `references/migration-v2-to-v3.md`.
4. Pesquisa da Meta → `references/official-meta-sources.md`.

Carregue somente a referência do branch atual.

## Invariantes

1. Hot path: pedido → manifest → um executor determinístico → readback final.
2. Zero busca ampla, skill discovery, patch, teste ou criação de cron durante execução.
3. Bundle padrão: duas campanhas da mesma conta.
4. Lanes independentes por `app_key + ad_account_id`; nunca misturar contas no mesmo bundle.
5. `pure_clone` reutiliza os creatives/mídias existentes da campanha fonte e não depende do v3 media registry. `clone_prestaged` exige três mídias `ready` por campanha antes do manifest; o próprio pedido autorizado pode fazer pre-stage/upload/readback e registrar os IDs antes de materializar. O planner divide qualquer pedido de 1–100 campanhas em bundles 2+2+…+1 por conta.
6. Um outer Graph batch de readback por bundle; zero GET intermediário.
7. Cap local inicial: soft 100, hard 120; headers vivos da Meta são persistidos por lane.
8. Canário técnico explícito nasce `PAUSED`; pedido normal de produção usa `ACTIVE` com `start_time` futuro após manifest selado e validação dos guards.
9. `prevalidated=true`, `config.enabled=true`, `write_enabled=true` e `--confirm-execute` são gates independentes.
10. V2 permanece rollback congelado; nenhum legado é apagado durante a migração inicial.

## How to run

Validação e plan são read-only:

```text
python3 /root/mgs-agent/scripts/ares-campaign-engine-v3.py validate --manifest <manifest>
python3 /root/mgs-agent/scripts/ares-campaign-engine-v3.py plan --manifest <manifest>
python3 /root/mgs-agent/scripts/ares-creditoparaveiculo-v3-daily.py --offline-smoke
python3 /root/mgs-agent/scripts/ares-creditoparaveiculo-v3-daily.py --dry-run --operational-date YYYY-MM-DD
```

O runner diário CPV tem gate de início às 17:00 São Paulo e permite retomar o mesmo request fora da janela quando o state estiver `PARTIAL_DEFERRED_QUOTA` ou em outro estágio resumível. `--dry-run` faz somente plano live/read-only; `--offline-smoke` usa transporte fake e zero rede. O wrapper v3 só pode substituir o job legado depois da revisão independente do Zeus; até então, o cron de criação permanece pausado e o v2 continua rollback isolado.

A execução real está ativa sob `development_access`. Cada pedido autorizado de campanha fornece o `--confirm-execute` operacional, mas não altera os gates estruturais. O guard inicial é **por lane**: em uma conta, o primeiro bundle daquela conta é guardado/fail-closed; em várias contas, o primeiro bundle de cada `app_key + ad_account_id` pode iniciar em paralelo pelo `ThreadPoolExecutor`. Não existe canário global único antes das outras lanes; os bundles seguintes de cada lane obedecem à própria quota.

## Verification

- manifest válido e digestado;
- dry-run mostra duas campanhas por bundle;
- `intermediate_get_calls=0`;
- lanes separadas por conta;
- média/p95 por estágio no audit;
- nenhuma credencial no manifest/audit;
- GET final confirma IDs, estrutura, budget, status e `start_time`;
- audit diário preserva ordem estável e registra `duration_ms` + contadores sanitizados para `meta_preflight`, `drive_preflight`, `reconciliation`, `asset_selection`, `prestage`, `manifest_prevalidation`, `engine`, `postprocess` e total;
- Token é resolvido cache-first pelo helper canônico; runner/cron nunca usa `force_refresh=True` por padrão;
- antes do execute, nomes exatos do manifest não colidem com campanhas live não deletadas fora do mapeamento idempotente do mesmo request;
- títulos de pre-stage incluem `asset_id + checksum curto`, e o registry confirma `account + asset + checksum + IDs` por readback;
- falhas após possível side effect ficam `READBACK_DEFERRED`/`POSTPROCESS_PENDING`, nunca `FAILED` fora do gate;
- REPORT-INFRA para qualquer mudança estrutural.

## Pitfalls

- Alterar 60→120 sem reduzir GET/validate/upload não cria escala.
- Graph batch reduz round-trips, não quota lógica.
- `IN_PROCESS` é post-processing, não falha terminal.
- Mídia crua não entra na transação: primeiro pre-stage, depois manifest.
- Advanced Access por permission, Marketing API Full Access e asset assignment são gates diferentes.
