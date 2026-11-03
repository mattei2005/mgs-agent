---
name: creative-taxonomy-mgs
description: "Taxonomia operacional de criativos MGS para aquisição paga: nomenclatura de arquivos, campos obrigatórios, P_ORIENT, inventário, status, validação e regras de classificação antes de usar assets em campanhas."
version: 1.0.2
author: Ares
license: internal
metadata:
  hermes:
    tags: [mgs, ads, creatives, taxonomy, naming, drive, meta-ads]
    related_skills: [paid-acquisition-operations]
---

# Creative Taxonomy MGS

## Entrada, arquivo e continuação vigentes

Entrada vigente: arquivos diretamente em UPLOAD MANUAL no MGS; _PROCESSAMENTO é temporário. Estoque permanente nos 30 TB, resolvido por ares_archive_storage/ares_archive_locations; não exigir driveId de Shared Drive em My Drive. Pedido geral da Kelly sem destinatário segue common/IMG ou VID/01_READY; entrega própria/gestor expresso segue Exclusivos e uso real confirmado segue Usados. Preservar RAW, mesmos IDs, bytes, reservas, elegibilidade e duplicatas. Agentes usam somente SA canônica; transporte owner isolado não é fallback de identidade. Upload não autoriza campanha ou exclusão. Rota: `creative-operations-mgs/references/flat-upload-intake.md`. Após tratamento/QA do batch de até quatro fontes, executar o mesmo complete; archive_ready e mechanical_only exigem essa continuação, não SILENT antecipado. Ler o monitor atual e continuar imediatamente os próximos blocos do mesmo request quando elegíveis, sem esperar outra janela de 15 minutos. Retomar apenas a camada faltante, preservar primeiras provas/horários e writer único; não criar outro cron, follow_archive ou tratamento duplicado. Cooldown/limite real mantém checkpoint e retomada canônica; não prometer duração fixa nem declarar concluído um saldo pendente. Casos upload-canvas-* são histórico, não outro executor nem instrução para reconstruir pastas antigas.

## Progressive disclosure — mandatory

1. Identify the exact operational branch below.
2. Load one route pack first; load another only when the first requires it or live evidence changes the branch.
3. Search the selected reference or exact source symbol before opening broader ranges.
4. Never load every reference or historical case study “for context.”
5. Reduce tool output above roughly 5 KB before another broad lookup.

Completion criterion: only the procedure and evidence required for the current action are loaded.

## Operational route packs

- **Objetivo → Status e ciclo de vida** → `references/route-pack-01.md`
- **Entrada operacional unificada → Inventário mínimo** → `references/route-pack-02.md`
- **Procedimento seguro de classificação → Pitfalls comuns** → `references/route-pack-03.md`
- **Referências internas** → `references/route-pack-04.md`

## Context-efficiency guardrails

- Stop and re-plan after more than three overlapping reads of the same file.
- Keep this main file as a routing layer; preserve detailed procedures in route packs.
- Validate the real runtime result before reporting success.
