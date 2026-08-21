---
name: meta-campaign-engine-v3
description: "Executa campanhas Meta em lotes determinísticos v3."
version: 3.0.1
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
5. `clone_prestaged`: três mídias `ready` por campanha antes do manifest; o planner divide qualquer pedido de 1–100 campanhas em bundles 2+2+…+1 por conta.
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
```

A execução real está ativa sob `development_access`. Cada pedido autorizado de campanha fornece o `--confirm-execute` operacional, mas não altera os gates estruturais; o primeiro bundle do primeiro pedido é tratado como canário guardado/fail-closed e os demais seguem a quota da lane.

## Verification

- manifest válido e digestado;
- dry-run mostra duas campanhas por bundle;
- `intermediate_get_calls=0`;
- lanes separadas por conta;
- média/p95 por estágio no audit;
- nenhuma credencial no manifest/audit;
- GET final confirma IDs, estrutura, budget, status e `start_time`;
- REPORT-INFRA para qualquer mudança estrutural.

## Pitfalls

- Alterar 60→120 sem reduzir GET/validate/upload não cria escala.
- Graph batch reduz round-trips, não quota lógica.
- `IN_PROCESS` é post-processing, não falha terminal.
- Mídia crua não entra na transação: primeiro pre-stage, depois manifest.
- Advanced Access por permission, Marketing API Full Access e asset assignment são gates diferentes.
