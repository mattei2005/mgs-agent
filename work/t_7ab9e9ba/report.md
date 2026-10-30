# IMG SHEIN — manutenção central t_7ab9e9ba

## Resultado e limite

Suporte incremental a imagens estáticas instalado na rota central, sem trocar o writer, credencial, guard, conta, budget, início aprovado ou SLA. Esta manutenção não executou campanha, upload, reserva de mídia ou write Meta/Drive. Ares permanece executor/atendimento da origem e continua em `t_8f7a90a8`.

**Não confundir suporte instalado/testado com a aceitação live do pedido.** O prestage real, o dry-run/plan com hashes reais, as prévias Meta de todos os anúncios e o readback ACTIVE ainda pertencem à execução de Ares. A origem permanece `shein-1565747351543480374`; o intake não foi reescrito.

## Problema, causa e correção

1. Intake e preparação só reconheciam VID/MP4. O upload/reconciliation usava advideos; aceitar PNG apenas na regex enviaria imagens para uma rota errada. Agora o formato é estritamente tipado: IMG PNG/JPG/JPEG estático segue adimages; VID segue a implementação anterior.
2. Registry, MediaSpec e prevalidation exigiam vertical_video_id/associação de vídeo. Agora a imagem usa account+asset+checksum+image_hash com edge/associação de imagem; consumidores legados continuam video-only por padrão. IMG de substituição é restrito a SHEIN.
3. Compiler só gerava video_data e sourcing de vídeo. Agora gera link_data/image_hash, preservando a identidade/CTA/configuração da fonte e a copy, agrupamento, budget, bid e destino/tracking do pedido.
4. Readback, QA e inventário assumiam vídeo. Agora conferem hash exato inclusive na recuperação do core, imagem estática renderizada e MD5 Drive atual; mantêm pastas do gestor, IDs e histórico. Uma prévia de vídeo não satisfaz um slot IMG.
5. Ativação continua exclusivamente na barreira PAUSED→QA global→activate_verified do core. Nenhuma exceção de status/guard/SLA foi criada. Intent de upload de imagem precede o POST; resposta perdida exige reconciliação por nome/hash, sem replay cego.

## Evidências exercitadas

- Mensagem humana original e pai/thread lidos por API; autoridade live de Nicolas confirmada novamente. Fonte 002 lida na conta exata: campanha `120250750964580629`, um adset e dois anúncios.
- 16/16 arquivos reais baixados somente em scratch e validados: SHA256, MD5/tamanho Drive e inventário, clean=true, PNG/JPEG estático, nome/pasta/linhagem exatos.
- GET account-scoped adimages retornou HTTP200 com paginação completa, sob o guard Ares inalterado. Nenhum POST live foi testado nesta manutenção.
- Input real + fonte viva passaram o replay de compiler/prevalidation/plan, mantendo 8 campanhas × 2 imagens, USD25/dia cada, USD200/dia no lote, COST_CAP e bid_amount95, textos literais e início original 2026-10-30 11:45 ET. **Esse replay usou registry de imagens sintético isolado e não salvou manifest executável; não é um plan live de mídia pronta.**
- Pacote instalado: 491 testes passaram + 295 subtests; 21 testes IMG novos incluem tipos mistos, negativos, upload ambíguo/idempotência, prepare→registry→handoff→inventário, Chromium real em localhost e ativação status-only com bloqueio de hash divergente.
- Três casos legados foram excluídos explicitamente após reprodução no baseline intocado: fixture Shared Drive antiga sob topology 30TB; expectativa do token CPV retirado; expectativa de wrapper antigo de leitores CPV. Follow-up separado `t_418fdc5d`; não são motivo para reverter políticas vigentes.
- Publicação inicial via troca atômica de diretório, rollback preservado. Ajuste posterior apenas nos rótulos de checks de prevalidation para não declarar associação de vídeo em um manifest somente IMG; suíte instalada reexecutada com 491/491.
- Readback final antes de liberar Ares: intake com hash preservado, 16 linhagens ainda sem reserva, nenhum state desse runner nem checkpoint desse request no core. Esses fatos são da manutenção, não uma previsão sobre a retomada posterior.

## Arquivos e recibos

- Código: `scripts/ares_campaign_v3/{image_prestage,media_registry,schema,prevalidation,shein_grouped_media,shein_general,shein_media_handoff,shein_single_clone,shein_qa,creative_media}.py`.
- Teste: `tests/test_shein_image_media.py`.
- Recibos em `work/t_7ab9e9ba/`: `deployment-receipt.json`, `pytest-installed.json`, `real-image-bytes.json`, `real-input-contract-replay.json`, `adimages-readonly.json`, `final-readback.json`, `report-infra-readback.json`. Falhas de baseline e tentativas iniciais de bootstrap de testes também estão preservadas nessa pasta.
- Rollback original: `work/t_7ab9e9ba/rollback/20261030T154736Z/ares_campaign_v3`. Se Ares já iniciou, reconciliar request/registry/IDs antes de qualquer rollback; não apagar registros IMG nem voltar o código cegamente com transação em andamento.
- Inventário: runtime artifact `shein-static-images-central-t_7ab9e9ba`; audit append-only registrado.
- REPORT-INFRA único verificado: https://discord.com/channels/1185714635991679006/1498132022634483894/1565754746873188458 — content vazio, um embed, sem mentions/thread.
- Aprendizado próprio salvo e relido: skill Zeus `meta-ads-api-operations/references/shein-static-image-prestage.md`. Skills de Ares não foram editadas; a anotação anterior de falta de capacidade é histórica frente ao código agora instalado.

## Handoff obrigatório a Ares

Reconciliar novamente efeitos, autoridade e a fonte; usar somente o intake original em `prepare-media --confirm-execute`, o request-ready real em `campaign --dry-run` e depois a execução já autorizada no runner central. Não executar scripts de replay/teste nem usar hashes sintéticos. Não declarar sucesso antes de todas as 16 imagens/textos, oito campanhas, budgets/bids, UTMs/numeração, inventário, prévias renderizadas e status finais passarem. O horário literal agora deve ser tratado pela política canônica de início explícito vencido no mesmo dia, com audit e relógio/SLA original; não editar o intake nem inventar nova autorização por este handoff. Eventual rejeição live permanece recuperável no mesmo request/IDs e PAUSED até QA válido.
