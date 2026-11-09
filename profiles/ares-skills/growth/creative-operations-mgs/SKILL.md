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
- **Entrada simples, lote e contexto humano explícito** → `references/flat-upload-intake.md`; inclui a continuação mecânica determinística autorizada em `1567021305822314609` via o mesmo `complete`, sem bombeador paralelo nem pausa por fase. Resolver o binding vivo antes de aplicar a hierarquia histórica. Lote IMG, VID ou misto e execução resumível → `references/mixed-media-drive-intake-ready-legacy.md`.
- **Entrega final em pasta de gestor após arquivo/READY** → `references/manager-folder-delivery.md`; autorização permanente e limitada em `data/ares/creative-ops/manager-delivery-policy.json`, sem novo OK do CEO para pedidos explícitos equivalentes.
- **Padrão de pastas para todos os gestores: Exclusivos/Usados** → fonte canônica `context/creative-manager-storage-standard.md` e bindings `data/ares/creative-ops/manager-storage-standard.json`. Resolver IDs pelo helper, não por pasta homônima solta na raiz; o fluxo novo é `CRIATIVOS/<OP>/<IMG|VID>/<NOME> - Exclusivos` antes do uso e `<NOME> - Usados` após readback real. Sem reclassificar histórico pelo nome.
- **Asset tecnicamente inválido/branco em UPLOAD MANUAL** → `references/upload-manual-technical-rejection-gate.md`
- **Renomeação segura Drive + local + inventário, com rollback** → `references/safe-rename-and-rollback.md`

## Regra unificada

Ares é dono das duas etapas. A transição entre Creative Ops e Campaign Ops ocorre pelo inventário/estado compartilhado, não por handoff entre bots.

- Original e tratado pertencem à mesma linhagem. Reuploads exatos também se vinculam a ela: contabilizar fontes recebidas separadamente de destinos READY únicos e não consumir uma nova variante para uma duplicata. Calcular o progresso por `source_drive_id` do conjunto congelado, incluindo os vínculos estruturados de duplicatas; contar somente as linhas primárias do inventário subestima fontes concluídas e pode provocar reprocessamento.
- Toda conclusão de intake inclui contagens verificadas, link do destino final efetivo e o mapa exato `nome original → nome final` de cada fonte, inclusive reuploads duplicados; separar IMG/VID quando o lote for grande, sem anexos não solicitados.
- Quando o pedido autorizar entrega em pasta de gestor, validar primeiro o tratado em READY e depois mover esse mesmo Drive ID para a pasta exata solicitada, sem criar um segundo candidato. Registrar o parent final real e manter os originais no LEGACY da operação; auditar e comunicar a pasta do gestor como destino final, não afirmar que o tratado continua fisicamente em READY. Receita: `references/mixed-media-drive-intake-ready-legacy.md`.
- Encerrar pelo estado auditado do lote, não pelo término isolado de preparação ou upload. Separar explicitamente registro, QA/sanitização local, entrega remota e conclusão canônica: `clean=true` local não comprova upload ou movimento, e scheduler habilitado não comprova execução futura nem entrega. Em atualização parcial, informar a fase verificada, o que falta e a localização real dos originais; apresentar o destino ainda não validado somente como previsto. Contar como entregue ao gestor somente a fonte com recibo de entrega e parent final verificados: `intake-state.completed` pode avançar antes do finalizador de Exclusivos. Separar tratados, arquivados e efetivamente entregues para não antecipar a contagem humana. No fluxo de preservação same-ID, exigir também a retirada verificada dos originais do staging antes de anunciar movimento integral, inclusive nos reuploads: o clean existente pode estar permanente enquanto o novo RAW ainda aguarda manutenção. Tratar `raw_preserved_staging_pending_maintenance` ou qualquer prova `permanent_verified=false` como camada pendente, mesmo com request/claim completo. Correlacionar cada processo à sua fase e ao manifesto; uma notificação atrasada de fase já consumida não reabre o intake nem exige repetir a resposta final.
- Conduzir o pedido inteiro pelo executor canônico e pelo conjunto congelado de fontes: continuar os batches do mesmo request sem esperar deliberadamente outra janela do scheduler. Usar a continuação mecânica já implantada, sem criar bombeadores auxiliares nem loops de disparo do cron; esses acompanhadores podem concorrer com o dono e exibir progresso defasado. Consultar o request e os claims canônicos para comunicar progresso, não apenas o arquivo ou stdout de um acompanhador. Antes de retomar, identificar também o dono do lock de escrita indicado pelo manifesto/checkpoint: um coordenador pode importar o executor sem expor seu nome na linha de comando; ausência do processo esperado não comprova lane livre. Calcular concluídos e pendentes pela interseção dos IDs congelados com as fontes completas desse request; o campo global `pending` do monitor pode incluir outros pedidos e não é o saldo desta conversa. Receita: `references/flat-upload-intake.md`.
- No intake manual, registrar também a conclusão no `intake-state.json` canônico antes de declarar o fluxo concluído; `state.json` próprio ou `final-audit.json` sozinho não libera a retirada. Usar `ares_manual_intake_completion.py` para o manifesto suportado e conferir `intake-completion.json`; receita na referência de arquivo 30 TB. Se faltar vínculo/prova, preservar staging e reportar a pendência, sem inventar claim nem relaxar o controlador.
- Upload de gestor inicia `RESERVADO_PELO_GESTOR` e `ares_eligible=false`.
- `01_READY` prova prontidão técnica, não ineditismo.
- Pedido geral de Kelly com país/vertical/língua, lote identificado e instrução de aplicar regras/organizar, sem gestor destinatário ou exclusividade, segue `common`: `MGS-ARQUIVO/CRIATIVOS/<OP>/IMG/01_READY` para imagem e `.../VID/01_READY` para vídeo. Não exigir um gestor destinatário nem usar o nome da remetente para entregar em `KELLY - Exclusivos`. A identificação interna de origem/gestor no helper não altera esse destino nem libera reservas. Entrega própria de gestor ou destinatário expresso segue `exclusive`; ambiguidade real, reupload e reserva preexistente mantêm seus gates. Receita e exemplos: `references/flat-upload-intake.md`.
- Antes de seleção/write, conciliar Drive × Meta.
- Nunca tratar material de Ad Library como asset final sem transformação/aprovação. Antes de reservar ou pre-stagear arquivos de uma pasta de gestor, conferir também a proveniência live (`properties`/`appProperties`) e a linhagem canônica: nome humano, mudança de pasta, owner corporativo e `clean=true` não promovem referência a criativo final. Se `reference_only=true` persistir sem prova de uma versão final aprovada, preservar os arquivos e pedir a versão final ou autorização para uma adaptação real; não apagar a marcação nem cadastrar uma nova linhagem para contornar o gate. Receita: `references/drive-meta-asset-identity-and-manager-reservation.md`.
- Limpar da VPS a mídia transitória somente após a conclusão canônica e a auditoria do destino final do backend ativo. No Shared Drive, validar ID, `driveId`, tamanho e hashes; no arquivo permanente, validar separadamente ID lógico, provider, atalho de estoque, parent autorizado, bytes/hashes e vínculo RAW→clean. Na preservação same-ID, distinguir três provas: original nativo preservado, RAW arquivado com seu atalho de estoque e clean arquivado com seu atalho. O original nativo pode ficar na árvore de preservação consolidada enquanto o estoque RAW ocupa `99_LEGACY`; validar a primeira localização pelos recibos nativos, não exigir que ambos compartilhem o mesmo parent nem mover novamente o original para satisfazer essa suposição. Não exigir `driveId` de Shared Drive para mídia My Drive validada pelo contrato vigente. Persistir antes o manifesto compacto, a auditoria e o mapa de nomes em armazenamento operacional durável; limitar a limpeza aos diretórios e arquivos exatos do pedido, sem symlinks e sem writer ativo, preservando evidências de qualquer membro ainda não verificado.
- Falha ou ausência de qualquer readback preserva a cópia local e exige escalação; nunca inferir upload por nome, fila ou tentativa concluída.
- A limpeza local nunca inclui `/root/.hermes/profiles/ares/browser-profiles/meta-library-chromium`, o lock do coletor, cookies/sessão, `/root/mgs-agent/tools/meta-library-collector` nem o Playwright Chromium 1228 usado pelo Library.

## Invariantes atuais de intake e naming

- Quando o solicitante corrigir a origem ou disser que os criativos já estão na pasta do gestor, atualizar imediatamente o entendimento para **tratar os arquivos existentes**, sem anunciar nova entrega/movimentação como objetivo. Conferir a pasta exata, separar mídia pendente de assets já registrados e manter o destino solicitado. Antes de pedir qualquer realocação ao usuário, validar o percurso completo de entrada, tratamento e entrega final; resolver um gate de entrada não comprova que o destino pedido é suportado. Uma passagem técnica pelo intake não muda o objetivo do pedido: não oferecer READY como substituição de uma pasta de gestor explicitamente solicitada para contornar uma deficiência da implementação. Não prometer tratamento antes do preflight nem pedir reenvio quando basta mover os mesmos arquivos.
- Antes de abrir um novo lote para arquivos pendentes, consultar o checkpoint e o manifesto existentes e reconciliar o conjunto por IDs e hashes atuais. Uma nova thread ou a mesma quantidade de arquivos não prova lote novo: preservar o manifesto original quando os mesmos arquivos forem confirmados e registrar a nova origem de continuação separadamente, evitando outro executor ou linhagens duplicadas.
- Entrada canônica: o mesmo `UPLOAD MANUAL` (`1ARBvLammWUHuAclNmcriwkkgeedKryBd`) diretamente no Drive MGS. Com `ares_flat_intake.policy()` ativo, receber arquivos diretamente nessa pasta e registrar operação/gestor/destino pelo pedido humano, conforme `references/flat-upload-intake.md`; não exigir nem recriar subpastas de nichos/gestores. A organização definitiva pertence aos 30 TB. O antigo binding de 114 slots permanece histórico, não é rota nova. `MGS-AGENTS/CRIATIVOS/UPLOAD MANUAL`, a pasta homônima arquivada e `UPLOAD_CANVAS` não são entradas vigentes.
- `GEIZIAN` contém cópias de conveniência para upload do gestor e fica fora do pool/inventário canônico.
- `LIBRARY META` contém referências; nunca é fonte automática de asset final.
- Persistir o plano completo de um lote antes do primeiro write e retomar pelos mesmos IDs, hashes e nomes reservados; uma interrupção não autoriza recalcular variantes nem repetir uploads já confirmados. Receita e gates: `references/mixed-media-drive-intake-ready-legacy.md`.
- `P_ORIENT` final aceita somente `PV`, `NV`, `PH`, `NH`; square/feed 1:1 usa `PH/NH`. Definir presença humana por asset e ampliar a imagem original quando detalhes pequenos ou revisões conflitantes impedirem uma decisão segura; a visão geral do lote não substitui essa conferência.
- Idioma explícito do pedido define a operação; um sufixo divergente no filename exige conferência da mídia real, não troca automática de idioma nem pergunta baseada só no nome. Registrar separadamente idioma observado e rótulo original; texto misto não autoriza tradução/adaptação. Detalhamento no passo de classificação de `references/mixed-media-drive-intake-ready-legacy.md`.
- Para país BR, “Português” sem qualificador usa `LANG=BR`; `LANG=PT` exige português de Portugal explícito.
- Antes de mudar regras, scripts ou estrutura do Drive fora da autorização delimitada já vigente, apresentar o plano exato e obter aprovação. Para pedidos explícitos equivalentes de entrega em pasta de gestor e recuperação da mesma rota, consultar `data/ares/creative-ops/manager-delivery-policy.json` e aplicar a autorização permanente vigente, sem pedir novamente ao CEO. Separar autoridade de prontidão técnica: uma falha de implementação não revoga a autorização do pedido nem justifica trocar seu destino; corrigir a camada necessária dentro do escopo aprovado, preservando os gates críticos. Se Rodolfo declarar sua auditoria manual do Drive como final, não aplicar limpeza automática sobre ela.

## Guardrails

- Skills criativas não autorizam sozinhas campaign write, budget, billing ou credencial; carregar a skill Campaign Ops e validar autoridade.
- Não produzir final sem validar referência/provider essencial.
- Não mover/deletar/sobrescrever fora do fluxo autorizado.
- Não declarar upload, limpeza, geração ou campanha sem readback real.
