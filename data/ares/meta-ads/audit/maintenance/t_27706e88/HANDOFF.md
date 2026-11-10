# HANDOFF — coordenação reconciliada; entrega permanece separada

## Resultado verificado

Manutenção **concluída**, exclusivamente de coordenação e preparação pré-write. O único dono da entrega das **28 cópias** continua sendo **t_4ac36ea1**. Esta etapa não criou, ativou, pausou ou corrigiu campanhas e não publicou conclusão na thread operacional.

A decisão de Rodolfo `1569530861022355457` foi relida por GET com autor `344196393512075265` na thread `1558134703565967394`; o literal coincide com o recibo da origem. A autorização de Nicolas e os GETs do takeover, pedido original e emenda de orçamento também foram revalidados. O recorte é o pedido separado e a reconciliação estritamente necessária, não uma aprovação de arquitetura global.

## Lote antigo preservado

- Request `shein-1569456380065222707`: 9 campanhas 102–110 e 9 conjuntos ACTIVE; 16/18 anúncios ACTIVE. AD02 das 104/108 continuam PAUSED/WITH_ISSUES, código 2490468. Não há motivo específico de política no feedback retornado.
- Orçamentos externos preservados: 103=3500 minor USD; demais oito=4375. Ativação atribuída ao relato de Nicolas; autoria do delta de orçamento não comprovada.
- State/phase `ACTIVATION_PENDING`, core, activation checkpoint e manifest histórico permanecem byte a byte preservados. Não foi emitido COMPLETE ou QA final fictício nem liberada/transferida reserva.
- O recibo imutável instalado em `data/ares/meta-ads/state/shein-campaigns/queue/manual-takeovers/shein-1569456380065222707.json` encerra somente a coordenação. A lease tem classificação `MANUAL_TAKEOVER_COORDINATION_CLOSED`, `blocks_readers=false`, vínculo SHA256 ao recibo e `qa_certified=false`. Não integra `queue.TERMINAL`.
- Runner, Engine, activation/staging, preparo/pós-processamento de mídia, lease/readers, fila/worker/notificação e prova tipada reconhecem o contrato. Recibo inválido e retomada automática do request antigo falham fechados. A transação é idempotente; uma falha parcial retoma somente a camada ausente.

## Primeiro input efetivo — USD30, mesmos IDs e relógio

**Não usar os seis inputs históricos USD45 citados no opening post.** Eles estão preservados, mas supersedidos pela emenda de Nicolas `1569505674847854603`, reafirmada por Rodolfo. Os seis inputs efetivos estão em:

`/root/mgs-agent/data/ares/meta-ads/audit/shein/campaigns/intake/shein-1569495587005530205/budget-revision-1569505674847854603/`

Primeiro input exato:

`/root/mgs-agent/data/ares/meta-ads/audit/shein/campaigns/intake/shein-1569495587005530205/budget-revision-1569505674847854603/049-request.json`

SHA256: `cc7bdaa1c6d22e5e024b856e0d7267b39eddd237d7c0d71fbfa7ddf3120cf14f`.

- Mesmo subrequest `shein-1569495587005530205-c049`; fonte `120251050287740629`; quantidade 4; horário **10/11/2026 00:03 EST**.
- PREPARED/job foram reconciliados sob locks e receipt de emenda. Os seals anteriores foram preservados em backup, não editados para passarem. O dry-run central gerou preparação nova USD30: `DRY_RUN_OK`, 4 alvos PAUSED para QA, destino ACTIVE futuro, bundles 2+2, próximo número observado 111. Numeração deve ser novamente conciliada no execute normal.
- `execution_started_at=2026-11-09T23:35:07.760000+00:00` e `enqueued_at` originais preservados. Nenhum engine checkpoint ou objeto novo deste pedido foi criado.
- Os seis inputs USD45 e o manifest PREPARED45 foram exercitados contra os guards instalados e rejeitados. USD30 é exclusivo das 28 cópias novas, total USD840/dia. Herde cada lance da sua fonte viva; não transportar USD0,90 nem outro bid do lote antigo.
- Job049 permanece `WAITING`, `attempts=0`, `notification=null`, `maintenance_hold` presente, `dispatch_owner=foreground`, `delivery_owner=ares`. O cache histórico de dependencies do job não foi forçado; o takeover canônico o recalcula. O worker existente foi recarregado, sem novo cron/serviço; só este job protegido estava pendente.

## Dependências e prova real

`--inspect` instalado retornou **dependencies=[]** para o input efetivo049. A prova fresca tipada `PURE_CLONE_SOURCE_MEDIA_READ_ONLY_V1` foi gerada por GET e validou a fonte/mídia/inventário, o predecessor manual e o review histórico `shein-1565261967260647536-c3`. Histórico c3, seu review e pins permanecem intactos; nenhuma campanha histórica foi executada ou alterada e nenhum review foi herdado.

Prova: `data/ares/meta-ads/state/shein-campaigns/queue/source-media/shein-1569495587005530205-c049.json`. TTL **120 segundos**; não é autorização cacheada ou reserva. O dono da entrega precisa gerar prova fresca outra vez imediatamente antes do takeover/runner.

## Comando canônico do dono da entrega

**Esta manutenção NÃO executou `--take-foreground` nem `--confirm-execute`.** O card t_4ac36ea1 executa:

```text
PYTHONPATH=/root/mgs-agent/scripts python3 -m ares_campaign_v3.shein_request_queue --inspect /root/mgs-agent/data/ares/meta-ads/audit/shein/campaigns/intake/shein-1569495587005530205/budget-revision-1569505674847854603/049-request.json
PYTHONPATH=/root/mgs-agent/scripts python3 -m ares_campaign_v3.shein_request_queue --take-foreground /root/mgs-agent/data/ares/meta-ads/audit/shein/campaigns/intake/shein-1569495587005530205/budget-revision-1569505674847854603/049-request.json
python3 /root/mgs-agent/scripts/ares-shein-campaigns.py campaign --input /root/mgs-agent/data/ares/meta-ads/audit/shein/campaigns/intake/shein-1569495587005530205/budget-revision-1569505674847854603/049-request.json --dry-run
```

Somente após deps vazias, prova fresca, autoridade/gates live, ownership confirmado e `DRY_RUN_OK`, o dono da entrega usa o mesmo runner/input com `--confirm-execute`. Avançar sequencialmente às fontes **010x4, 025x4, 098x6, 056x6, 100x4**, sempre nos inputs revisionados, só depois de terminal/QA/render/readback da linha anterior. Nenhum original USD45 autoriza execução.

Critérios: mesmos IDs se surgirem efeitos parciais; criar apenas a camada ausente; manter horário futuro explícito e política canônica se efetivamente vencer; QA integral de todos os ads, status/budget3000/bids e readback das 28 campanhas; agregador por linha; uma conclusão consolidada na origem só depois da entrega real. Não repetir manutenção, não criar novo grafo/cron/writer, não retomar 102–110/c3 e não emitir notices individuais.

## Testes, hashes e audit

- Regressão instalada de aceitação: **209 testes + 135 subtestes aprovados**, incluindo 29 testes do contrato novo, JSON roundtrip real, crash/reentrada, approval/CAS/locks, lease concorrente, mídia/reserva compartilhada, silêncio do worker, bloqueio dos entrypoints e orçamento supersedido.
- Suite ampla do Engine: 66 passam; 8 fixtures legadas de clone sem creative slots já falhavam no baseline pela política permanente de features. Mesmos 8 IDs/erros em staging, zero falha nova. Um teste legado de omissões também falha no baseline inalterado; não foi usado como aceitação verde nem corrigido fora do escopo.
- Houve um defeito de projeção tuple/list observado na verificação idempotente real. Diagnóstico provou JSON equivalente, sem drift Meta; corrigida somente a projeção para arrays JSON e acrescentado teste do extrator real. O primeiro receipt/lease permaneceram intactos; não houve replay de campanha.
- Hashes de todos os **13 arquivos instalados**, backups/CAS, regressões, recibos humanos, dry-run30, preservation e aceitação real: `/root/mgs-agent/data/ares/meta-ads/audit/maintenance/t_27706e88/attempt2/`.
- Recibo principal: `attempt2/acceptance-readback.json`; instalação: `attempt2/installation.json`; emenda: `prewrite-backup/` e `attempt2/prewrite-reconciliation.json`.
- REPORT-INFRA e registry/checkpoints são vinculados no handoff estruturado do card. Não postar este relatório de manutenção como resultado de campanha.
