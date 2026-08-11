---
name: creative-operations-mgs
description: Use quando Ares receber pedidos de criação, adaptação, tratamento, referência, naming, sanitização, inventário ou organização de criativos MGS antes e durante o ciclo de campanhas.
version: 2.0.0
author: MGS Digital Corp
license: Proprietary
metadata:
  hermes:
    tags: [mgs, ares, creative-ops, brief, imagem, video, drive, inventory, campaigns]
    related_skills: [creative-taxonomy-mgs, meta-library-reference-intake, paid-acquisition-operations]
---

# Creative Operations MGS — Ares

## Progressive disclosure — mandatory

1. Identifique a ramificação operacional exata.
2. Carregue primeiro um único route pack; outro somente se o primeiro exigir ou a evidência mudar a rota.
3. Procure o símbolo/fonte exata antes de busca ampla.
4. Não carregue todos os casos históricos “por contexto”.
5. Reduza outputs acima de aproximadamente 5 KB antes de outra leitura ampla.

Critério de conclusão: asset/estado real validado e apenas o procedimento necessário carregado.

## Rotas operacionais

- **Pedido natural, brief, copy e produção criativa** → `references/route-pack-01.md`
- **Status, Drive, READY/LEGACY e rastreabilidade** → `references/route-pack-02.md`
- **Controle de uploads externos, exclusão e drift de permissões no Shared Drive MGS** → `references/my-drive-collaborator-control-and-deletion.md`
- **Migração para Shared Drive, preflight de entitlement, piloto e escolha do Google Workspace** → `references/shared-drive-migration-and-workspace-plans.md`; evidência Enterprise Essentials validada → `references/shared-drive-enterprise-essentials-pilot-2026-07-15.md`; implementação full-root com checkpoint, move/copy, backup e cutover → `references/shared-drive-full-root-controlled-migration-2026-07-15.md`
- **Sanitização, origem e consumidores** → `references/route-pack-03.md`
- **Naming, imagem estática e providers** → `references/route-pack-04.md`
- **Vídeo, referência e backend gates** → `references/route-pack-05.md`
- **Transição Creative Ops → Campaign Ops, reserva e QA** → `references/route-pack-06.md`
- **Identidade Drive × Meta, download do tratado e reserva de gestor** → `references/drive-meta-asset-identity-and-manager-reservation.md`
- **Lote misto IMG/VID em UPLOAD MANUAL** → `references/mixed-media-drive-intake-ready-legacy.md`
- **Asset tecnicamente inválido/branco em UPLOAD MANUAL** → `references/upload-manual-technical-rejection-gate.md`
- **Renomeação segura Drive + local + inventário, com rollback** → `references/safe-rename-and-rollback.md`

## Regra unificada

Ares é dono das duas etapas. A transição entre Creative Ops e Campaign Ops ocorre pelo inventário/estado compartilhado, não por handoff entre bots.

- Original e tratado pertencem à mesma linhagem.
- Upload de gestor inicia `RESERVADO_PELO_GESTOR` e `ares_eligible=false`.
- `01_READY` prova prontidão técnica, não ineditismo.
- Antes de seleção/write, conciliar Drive × Meta.
- Nunca tratar material de Ad Library como asset final sem transformação/aprovação.
- Depois que o asset final estiver no Shared Drive `MGS-AGENTS`, excluir da VPS a mídia e o workdir transitórios somente após readback do ID, `driveId`, tamanho, MD5/SHA e registro da linhagem/inventário. Preservar apenas o manifesto compacto necessário à auditoria.
- Falha ou ausência de qualquer readback preserva a cópia local e exige escalação; nunca inferir upload por nome, fila ou tentativa concluída.
- A limpeza local nunca inclui `/root/.hermes/profiles/ares/browser-profiles/meta-library-chromium`, o lock do coletor, cookies/sessão, `/root/mgs-agent/tools/meta-library-collector` nem o Playwright Chromium 1228 usado pelo Library.

## Invariantes atuais de intake e naming

- Entrada canônica: `MGS-AGENTS/CRIATIVOS/UPLOAD MANUAL`; `UPLOAD_CANVAS` é apenas histórico e não deve ser recriada.
- `GEIZIAN` contém cópias de conveniência para upload do gestor e fica fora do pool/inventário canônico.
- `LIBRARY META` contém referências; nunca é fonte automática de asset final.
- `P_ORIENT` final aceita somente `PV`, `NV`, `PH`, `NH`; square/feed 1:1 usa `PH/NH`.
- Para país BR, “Português” sem qualificador usa `LANG=BR`; `LANG=PT` exige português de Portugal explícito.
- Antes de mudar regras, scripts ou estrutura do Drive, apresentar o plano exato e obter aprovação. Se Rodolfo declarar sua auditoria manual do Drive como final, não aplicar limpeza automática sobre ela.

## Guardrails

- Skills criativas não autorizam sozinhas campaign write, budget, billing ou credencial; carregar a skill Campaign Ops e validar autoridade.
- Não produzir final sem validar referência/provider essencial.
- Não mover/deletar/sobrescrever fora do fluxo autorizado.
- Não declarar upload, limpeza, geração ou campanha sem readback real.
