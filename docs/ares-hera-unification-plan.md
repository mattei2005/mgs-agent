# Plano de Unificação Hera → Ares

> Status: migração aplicada; finalizer detached preparado para desativação, restart e readback
> Dono executivo: Rodolfo Mattei
> Executor/orquestrador: Zeus
> Data: 2026-07-12
> Objetivo: manter somente Ares como agente operacional de Creative Ops + Growth/Media Buying, preservando rollback e histórico da Hera.

## 1. Decisão executiva

Ares passa a ser dono do ciclo completo:

```text
pedido/upload humano
→ brief/criação/variações
→ tratamento e sanitização
→ naming e inventário
→ Drive/status/reserva
→ conciliação com Meta
→ seleção para teste
→ campanha
→ performance/ROI
→ aprendizado criativo
```

A separação deixa de ser entre agentes e passa a ser entre módulos internos e permissões:

- Creative Ops: criação, tratamento, naming, Drive, inventário e referência Meta Library.
- Campaign Ops: contas, campanhas, relatórios, testes, performance e ROI.
- Permissões: acesso criativo não ignora gates de credencial, billing, budget ou produção crítica.

## 2. Estado confirmado antes da migração

- `ares-gateway.service`: enabled + active.
- `hera-gateway.service`: enabled + active.
- SOUL/config live e versionados de ambos: idênticos por `cmp`.
- Ares custom MGS: 7 skills Growth, 91 arquivos no diretório custom Growth.
- Hera custom MGS principal: `creative-brief-handoff` e `meta-library-reference-intake`; a categoria Creative contém também skills vendor/genéricas que não devem ser copiadas cegamente.
- Dados Ares: `/root/mgs-agent/data/ares/`, 8.245 arquivos, ~1,13 GB.
- Dados Hera: `/root/mgs-agent/data/hera/`, 292 arquivos, ~257 MB.
- Perfil persistente Meta Library da Hera: ~12.146 arquivos, ~496 MB.
- Artefatos Meta Library da Hera: 200 arquivos, ~50 MB.
- `sync-souls.sh` sincroniza Ares e Hera separadamente.
- Ares já possui automações de taxonomia, Drive, sanitização e campanhas; Hera concentra intake natural, produção criativa, Meta Library e contexto humano.
- Existem divergências reais entre documentos Hera/Ares sobre P_ORIENT, preservação/movimento do RAW, dono do naming e handoff. Elas serão reconciliadas, não copiadas literalmente.

## 3. Estrutura-alvo do Ares

```text
/root/.hermes/profiles/ares/
├── SOUL.md
├── config.yaml
├── skills/
│   ├── growth/
│   │   ├── paid-acquisition-operations/
│   │   ├── creative-operations-mgs/
│   │   ├── creative-taxonomy-mgs/
│   │   ├── meta-library-reference-intake/
│   │   ├── meta-ads-governance-guardrails/
│   │   ├── meta-ads-account-visualization/
│   │   ├── meta-ads-intraday-operations/
│   │   ├── direct-traffic-cbo-operations/
│   │   └── meta-openzedfinanzas-replacement-clone/
│   └── creative/                  # capacidades genéricas realmente necessárias
├── browser-profiles/
│   ├── meta-library-chromium/
│   └── youtube-chromium/
├── browser-profile-backups/
└── artifacts/
    └── meta-library/

/root/mgs-agent/data/ares/
├── meta-ads/
├── creative-inventory/
└── creative-ops/
    ├── inventory/
    ├── intake/
    ├── ready/
    ├── upload-manual/
    ├── references/
    └── migration-manifest.json
```

## 4. Fonte única de estado criativo

O inventário unificado deve representar uma única linhagem por conceito/asset:

```text
asset_id
original_filename
canonical_filename
source_manager
requested_by
created_by
vertical
country
language
strategy
ad_account_id
source_drive_id
asset_drive_id
original_checksum
clean_checksum
perceptual_fingerprint
format
angle
person
orientation
p_orient
variant
width
height
aspect_ratio
placement_fit
metadata_clean
status
reservation_status
ares_eligible
used_by
campaign_owner
meta_ad_id
meta_creative_id
meta_image_hash
meta_video_id
effective_object_story_id
first_seen_at
last_reconciled_at
performance_label
notes
```

Regras de segurança:

- Upload de gestor começa reservado e `ares_eligible=false` até liberação/conciliação.
- `01_READY` significa pronto tecnicamente, não prova ineditismo.
- Antes de seleção/write: conciliar Drive × Meta por IDs/hashes/linhagem/comparação visual.
- Silêncio do gestor não libera o asset.
- Original e tratado nunca podem ser testados como se fossem conceitos independentes sem decisão expressa.

## 5. Migração por blocos

### Bloco A — Backups e manifestos

- Snapshot dos SOULs, configs, skills custom, dados Hera, perfil Meta Library, artefatos, scripts e unit files.
- Manifestos SHA-256/size antes da migração.
- Nenhum delete.

### Bloco B — Ares SOUL e mapas

- Reescrever Ares como agente unificado Creative Ops + Growth/Media Buying.
- Remover dependência operacional de handoff Hera ↔ Ares.
- Manter módulos e gates de permissão explícitos.
- Atualizar `ares-operational-map.md` para criação, intake, Meta Library, Drive, campanhas e performance.

### Bloco C — Skills

- Criar `creative-operations-mgs` a partir do conhecimento válido de `creative-brief-handoff`.
- Migrar `meta-library-reference-intake` para Ares e atualizar paths/variáveis.
- Reconciliar `creative-taxonomy-mgs` com as regras mais recentes de Creative Ops.
- Preservar referências históricas úteis; marcar handoffs Hera/Ares como legado.
- Não copiar automaticamente todas as skills vendor/genéricas da categoria Creative da Hera.

### Bloco D — Dados e runtimes criativos

- Copiar dados Hera para `data/ares/creative-ops/` com manifesto e readback.
- Migrar perfil persistente Meta Library, snapshots e artefatos para o profile Ares.
- Preservar os originais no profile Hera durante o período de rollback.
- Atualizar coletores e wrappers para paths/variáveis Ares.

### Bloco E — Scripts e automações

- Criar versões Ares dos scripts Hera produtivos ainda necessários.
- Atualizar defaults de `mgs-grok-generate.py`, Meta Library, YouTube, monitores, updates e sync.
- Manter wrappers antigos somente como compatibilidade/rollback, sem rota ativa.
- Atualizar inventário de infra e documentação de crons.

### Bloco F — MGS OS e permissões

Atualizar, no mínimo:

- `context/mgs-os-map.md`
- `context/company-os.md`
- `context/areas.md`
- `context/agent-map.md`
- `context/routes.md`
- `context/team.md`
- `context/processes.md`
- `context/acquisition.md`
- `context/permissions-matrix.md`
- `context/sources-of-truth.md`
- `docs/mgs-structure-inventory.md`
- `data/authorized-users.json`

O registro de autorização do Ares deve conter Rodolfo, Geizian, Icaro, Isliago, Joe, Kelly e Nicolas. Budget write continua subordinado aos gates explícitos do SOUL/matriz.

### Bloco G — Validação Ares

- YAML/JSON/Python/shell syntax.
- Links e referências de skills.
- Secret scan das linhas adicionadas.
- Live/versioned `cmp`.
- Manifesto de dados pré/pós.
- Smoke read-only de inventário criativo.
- Smoke de Meta Library sem expor sessão/credenciais.
- Smoke de sanitização.
- Smoke read-only Meta Ads.
- Gateway Ares reiniciado pelo finalizer seguro e validado conectado.

### Bloco H — Desativação Hera

Somente após Ares aprovado:

- parar e desabilitar `hera-gateway.service`;
- remover Hera das rotas/sync/monitores ativos;
- manter unit file e profile arquivados para rollback inicialmente;
- não apagar canal Discord, histórico, logs, dados ou perfil nesta fase;
- marcar Hera como `inactive_archived` no inventário/autorização.

### Bloco I — Encerramento

- Audit log append-only.
- Git diff/check/status e auto-push validado.
- REPORT-INFRA em embed no `#alerts-infra`.
- Mensagem formal ao Ares informando a nova responsabilidade.
- Relatório executivo final com evidência, falhas e rollback.

## 6. Gates críticos

Antes de aplicar mudanças em skills de outros agentes, systemd ou desativação, usar a confirmação adicional do Critical Subset definida em `AGENT.md`.

A desativação não inclui exclusão definitiva. Qualquer delete futuro exige uma autorização crítica própria após período de estabilidade.

## 7. Rollback

Se qualquer smoke falhar:

1. manter/religar Hera;
2. restaurar Ares SOUL/config/skills pelos backups;
3. restaurar scripts/rotas pelos manifestos;
4. manter dados criativos novos preservados para reconciliação, sem sobrescrever histórico;
5. validar ambos os gateways e registrar falha parcial.
