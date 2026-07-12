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
- **Sanitização, origem e consumidores** → `references/route-pack-03.md`
- **Naming, imagem estática e providers** → `references/route-pack-04.md`
- **Vídeo, referência e backend gates** → `references/route-pack-05.md`
- **Transição Creative Ops → Campaign Ops, reserva e QA** → `references/route-pack-06.md`
- **Identidade Drive × Meta, download do tratado e reserva de gestor** → `references/drive-meta-asset-identity-and-manager-reservation.md`
- **Lote misto IMG/VID em UPLOAD MANUAL** → `references/mixed-media-drive-intake-ready-legacy.md`

## Regra unificada

Ares é dono das duas etapas. A transição entre Creative Ops e Campaign Ops ocorre pelo inventário/estado compartilhado, não por handoff entre bots.

- Original e tratado pertencem à mesma linhagem.
- Upload de gestor inicia `RESERVADO_PELO_GESTOR` e `ares_eligible=false`.
- `01_READY` prova prontidão técnica, não ineditismo.
- Antes de seleção/write, conciliar Drive × Meta.
- Nunca tratar material de Ad Library como asset final sem transformação/aprovação.

## Guardrails

- Skills criativas não autorizam sozinhas campaign write, budget, billing ou credencial; carregar a skill Campaign Ops e validar autoridade.
- Não produzir final sem validar referência/provider essencial.
- Não mover/deletar/sobrescrever fora do fluxo autorizado.
- Não declarar upload, limpeza, geração ou campanha sem readback real.
