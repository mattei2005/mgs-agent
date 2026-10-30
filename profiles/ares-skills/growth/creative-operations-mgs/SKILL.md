---
name: creative-operations-mgs
description: Use quando Ares receber pedidos de criação, adaptação, tratamento, referência, naming, sanitização, inventário ou organização de criativos MGS antes e durante o ciclo de campanhas.
version: 2.0.3
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
- **Arquivo 30 TB, fechamento manual e retirada do staging** → `references/shared-drive-30tb-archive-queue.md`; consultar as flags e a autorização vivas. Ares não exclui mídia: a retirada pertence exclusivamente ao controlador SA autorizado.
- **Controle de uploads externos, exclusão e drift de permissões no Shared Drive MGS** → `references/my-drive-collaborator-control-and-deletion.md`
- **Migração para Shared Drive, preflight de entitlement, piloto e escolha do Google Workspace** → `references/shared-drive-migration-and-workspace-plans.md`; evidência Enterprise Essentials validada → `references/shared-drive-enterprise-essentials-pilot-2026-07-15.md`; implementação full-root com checkpoint, move/copy, backup e cutover → `references/shared-drive-full-root-controlled-migration-2026-07-15.md`
- **Sanitização, origem e consumidores** → `references/route-pack-03.md`
- **Naming, imagem estática e providers** → `references/route-pack-04.md`
- **Vídeo, referência e backend gates** → `references/route-pack-05.md`
- **Google Ads Transparency, download e análise de library externa** → `references/google-ads-transparency-reference-intake.md`
- **Transição Creative Ops → Campaign Ops, reserva e QA** → `references/route-pack-06.md`
- **Identidade Drive × Meta, download do tratado e reserva de gestor** → `references/drive-meta-asset-identity-and-manager-reservation.md`
- **Lote IMG, VID ou misto em UPLOAD MANUAL, incluindo execução resumível** → `references/mixed-media-drive-intake-ready-legacy.md`
- **Asset tecnicamente inválido/branco em UPLOAD MANUAL** → `references/upload-manual-technical-rejection-gate.md`
- **Renomeação segura Drive + local + inventário, com rollback** → `references/safe-rename-and-rollback.md`

## Regra unificada

Ares é dono das duas etapas. A transição entre Creative Ops e Campaign Ops ocorre pelo inventário/estado compartilhado, não por handoff entre bots.

- Original e tratado pertencem à mesma linhagem. Reuploads exatos também se vinculam a ela: contabilizar fontes recebidas separadamente de destinos READY únicos e não consumir uma nova variante para uma duplicata.
- Toda conclusão de intake inclui contagens verificadas, link do destino final efetivo e o mapa exato `nome original → nome final` de cada fonte, inclusive reuploads duplicados; separar IMG/VID quando o lote for grande, sem anexos não solicitados.
- Quando o pedido autorizar entrega em pasta de gestor, validar primeiro o tratado em READY e depois mover esse mesmo Drive ID para a pasta exata solicitada, sem criar um segundo candidato. Registrar o parent final real e manter os originais no LEGACY da operação; auditar e comunicar a pasta do gestor como destino final, não afirmar que o tratado continua fisicamente em READY. Receita: `references/mixed-media-drive-intake-ready-legacy.md`.
- Encerrar pelo estado auditado do lote, não pelo término isolado de preparação ou upload. Correlacionar cada processo à sua fase e ao manifesto; uma notificação atrasada de fase já consumida não reabre o intake nem exige repetir a resposta final.
- No intake manual, registrar também a conclusão no `intake-state.json` canônico antes de declarar o fluxo concluído; `state.json` próprio ou `final-audit.json` sozinho não libera a retirada. Usar `ares_manual_intake_completion.py` para o manifesto suportado e conferir `intake-completion.json`; receita na referência de arquivo 30 TB. Se faltar vínculo/prova, preservar staging e reportar a pendência, sem inventar claim nem relaxar o controlador.
- Upload de gestor inicia `RESERVADO_PELO_GESTOR` e `ares_eligible=false`.
- `01_READY` prova prontidão técnica, não ineditismo.
- Antes de seleção/write, conciliar Drive × Meta.
- Nunca tratar material de Ad Library como asset final sem transformação/aprovação.
- Depois que o asset final estiver no Shared Drive `MGS-AGENTS`, excluir da VPS a mídia e o workdir transitórios somente após readback do ID, `driveId`, tamanho, MD5/SHA e registro da linhagem/inventário. Preservar apenas o manifesto compacto necessário à auditoria.
- Falha ou ausência de qualquer readback preserva a cópia local e exige escalação; nunca inferir upload por nome, fila ou tentativa concluída.
- A limpeza local nunca inclui `/root/.hermes/profiles/ares/browser-profiles/meta-library-chromium`, o lock do coletor, cookies/sessão, `/root/mgs-agent/tools/meta-library-collector` nem o Playwright Chromium 1228 usado pelo Library.

## Invariantes atuais de intake e naming

- Quando o solicitante corrigir a origem ou disser que os criativos já estão na pasta do gestor, atualizar imediatamente o entendimento para **tratar os arquivos existentes**, sem anunciar nova entrega/movimentação como objetivo. Conferir a pasta exata, separar mídia pendente de assets já registrados e manter o destino solicitado; uma passagem técnica pelo intake, quando realmente necessária e comprovada pelo gate vivo, não muda o objetivo do pedido. Não prometer tratamento antes de validar o transporte necessário nem afirmar que o usuário precisa reenviar os arquivos quando basta movê-los.
- Antes de abrir um novo lote para arquivos pendentes, consultar o checkpoint e o manifesto existentes e reconciliar o conjunto por IDs e hashes atuais. Uma nova thread ou a mesma quantidade de arquivos não prova lote novo: preservar o manifesto original quando os mesmos arquivos forem confirmados e registrar a nova origem de continuação separadamente, evitando outro executor ou linhagens duplicadas.
- Entrada canônica: `MGS-AGENTS/CRIATIVOS/UPLOAD MANUAL`; `UPLOAD_CANVAS` é apenas histórico e não deve ser recriada.
- `GEIZIAN` contém cópias de conveniência para upload do gestor e fica fora do pool/inventário canônico.
- `LIBRARY META` contém referências; nunca é fonte automática de asset final.
- Persistir o plano completo de um lote antes do primeiro write e retomar pelos mesmos IDs, hashes e nomes reservados; uma interrupção não autoriza recalcular variantes nem repetir uploads já confirmados. Receita e gates: `references/mixed-media-drive-intake-ready-legacy.md`.
- `P_ORIENT` final aceita somente `PV`, `NV`, `PH`, `NH`; square/feed 1:1 usa `PH/NH`. Definir presença humana por asset e ampliar a imagem original quando detalhes pequenos ou revisões conflitantes impedirem uma decisão segura; a visão geral do lote não substitui essa conferência.
- Para país BR, “Português” sem qualificador usa `LANG=BR`; `LANG=PT` exige português de Portugal explícito.
- Antes de mudar regras, scripts ou estrutura do Drive, apresentar o plano exato e obter aprovação. Se Rodolfo declarar sua auditoria manual do Drive como final, não aplicar limpeza automática sobre ela.

## Guardrails

- Skills criativas não autorizam sozinhas campaign write, budget, billing ou credencial; carregar a skill Campaign Ops e validar autoridade.
- Não produzir final sem validar referência/provider essencial.
- Não mover/deletar/sobrescrever fora do fluxo autorizado.
- Não declarar upload, limpeza, geração ou campanha sem readback real.
