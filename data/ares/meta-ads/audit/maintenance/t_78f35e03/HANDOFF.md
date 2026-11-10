# HANDOFF — t_78f35e03 → t_4ac36ea1

## Resultado e autoridade

Manutenção técnica central concluída; **não é entrega de campanhas**. Mesma solicitação `shein-1569495587005530205`, mesma conta `937846586033361`, mesmo relógio. GET novo confirmou Nicolas `1569495587005530205`, emenda `1569505674847854603` (USD30 somente28 novas) e Rodolfo `1569530861022355457`; áudio `1569532436344213514` confirmado por ID/autor/anexo, sem inventar nova transcrição. Provas em `authority-get.json`.

**049 já concluída: não reexecutar nem take-foreground nela.** Ares permanece único executor das24 restantes e único dono da resposta consolidada28 na origem `1558134703565967394`. Zeus não executou campanha, takeover, Meta/Drivewrites nem publicou na origem.

## Defeito e correção

Baseline real `--inspect`010 retinha `shein-1569456380065222707`. O scan recursivo `_media(state)` incluía `state.source`: fonte010/`120250944872190629`, hashes/imagens/posts/stems que nunca foram as mídias finais102–110. A interseção com o snapshot integral não era compartilhamento real.

`shein_decision_wait.materialized_media` agora projeta anúncios finais de `manifest.campaigns[].ads`, falhando fechado se faltar cobertura/identidade. `inert_for` soma separadamente reservas/vínculos reais de inventário e identidades históricas live validadas, mantendo expansão transitiva. O drift check em `shein_source_media.resolve` usa a MESMA projeção final para impedir aceitar mudança live para uma antiga fonte não materializada. Não foi mudado `_media`, alias expansion, locks, leases, reserva, provas ou TTL120s.

## Aceitação verificada

- 125 testes instalados PASS;9 novos testes de regressão. Inclui fixture reduzida com identidades reais010 versus9campaigns/18ads finais, seleção explícita e pure_clone, reserva real, compartilhamento final/alias transitivo, drift para fonte antiga, cobertura ausente, lock/lease ativos, digest alterado e TTL vencido.
- Os6 inputs EFETIVOS USD30 tiveram deps=[] por leitura real; fontes049/010/025/098/056/100, quantidades4/4/4/6/6/4, total28/USD840, início `2026-11-10T00:03:00-05:00`.049 teve `source_media.resolve` explícito READ_ONLY apesar do short-circuit terminal da fila: sem replay.
- Ads reais das fontes:049=2,010=2,025=2,098=2,056=2,100=3. Não presumir2 na fonte100.
- 21 arquivos protegidos com SHA256 idênticos: snapshots/manifest seals/recibo manual/reviewc3/checkpoints/activation/inputs/jobs/inventário. Manual continua `ACTIVATION_PENDING`, QAfalse,9campaigns/18ads; c3 `POSTPROCESS_PENDING` e review mantido.104/108 e budgets externos não alterados.
- Job010 continua WAITING,maintenance_hold+dispatch_owner=foreground,attempts0,notificationnull. Nenhum hold removido. Worker canônico ativo; sem restart ou novo cron.
- Instalação5arquivos com backup/CAS sob locks próprios de dispatch/job/account/lease/inventory. `installation.json` contém hashes e rollback.125 testes, inspeções finais e manifesto instalado verificados novamente.
- REPORT-INFRA `1569545035559735307`, GET confirmado em `report-infra-readback.json`: canal alerts-infra,embed,content vazio,sem mentions/sem thread. Inventário `ares-shein-historical-media-projection-t_78f35e03`; checkpoint `ZEUS-MAINT-t_78f35e03` via helper canônico/validate OK.

## Retomada EXCLUSIVA pelo Ares

Provas guardadas não são cache autorizante: TTL120s. No próprio profile Ares, gerar um **novo** inspect e exigir deps=[]; só então comando canônico take-foreground. Não remover hold manualmente, não mudar HERMES_PROFILE de Zeus para se passar por Ares, não executar049 novamente.

```
PYTHONPATH=/root/mgs-agent/scripts python3 -m ares_campaign_v3.shein_request_queue --inspect /root/mgs-agent/data/ares/meta-ads/audit/shein/campaigns/intake/shein-1569495587005530205/budget-revision-1569505674847854603/010-request.json
PYTHONPATH=/root/mgs-agent/scripts python3 -m ares_campaign_v3.shein_request_queue --take-foreground /root/mgs-agent/data/ares/meta-ads/audit/shein/campaigns/intake/shein-1569495587005530205/budget-revision-1569505674847854603/010-request.json
python3 /root/mgs-agent/scripts/ares-shein-campaigns.py campaign --input /root/mgs-agent/data/ares/meta-ads/audit/shein/campaigns/intake/shein-1569495587005530205/budget-revision-1569505674847854603/010-request.json --dry-run
python3 /root/mgs-agent/scripts/ares-shein-campaigns.py campaign --input /root/mgs-agent/data/ares/meta-ads/audit/shein/campaigns/intake/shein-1569495587005530205/budget-revision-1569505674847854603/010-request.json --confirm-execute
```

Após QA/estado terminal exato010, avançar sequencialmente025,098,056,100 pelos mesmos inputs revisionados30 (não pelos históricos45), mesmos IDs e horário. Reconciliar estado/readback antes de retomar; nenhuma cópia adicional ou writer alternativo. Se nova dependência real surgir, respeitar gate e diagnosticar, sem bypass. Fazer QA/render/readback final das28, atualizar agregador/checkpoint e publicar UMA conclusão na origem conforme pedido de Rodolfo `1569542062724878379`. Nada de resposta parcial de infraestrutura.

## Lição persistida e handoff de skill

Procedimento salvo/readback na skill **do Zeus** `meta-ads-api-operations`, referência `references/shein-request-queue-decision-waits.md`, seção Historical final-media projection. Nenhuma skill de outro profile foi editada. Ares deve incorporar no seu procedimento pertinente a mesma distinção fonte não materializada versus mídia final+reservas e apontar para os testes instalados `tests/test_shein_source_media.py`, `tests/test_shein_decision_wait.py` e fixture `tests/fixtures/shein-historical-source010-media.json`, seguindo seu próprio gate. Não requer nova autorização comercial.

## Arquivos verificáveis

Diretório canônico: `/root/mgs-agent/data/ares/meta-ads/audit/maintenance/t_78f35e03/`.

- `final-readback.json`: seis linhas, hashes/hold/review e zero writes.
- `source-media-{049,010,025,098,056,100}.json`: provas live obtidas no aceite; não reutilizar apósTTL.
- `installation.json`, `source-before.json`, `before/`, `protected-before.json`.
- `authority-get.json`, `audit-event.json`, `report-infra-readback.json`.
- `HANDOFF.md` (este documento).

As provas anteriores do diagnóstico/hold/049 são duráveis no intake `delivery-t_4ac36ea1/`; não depender do scratch.
