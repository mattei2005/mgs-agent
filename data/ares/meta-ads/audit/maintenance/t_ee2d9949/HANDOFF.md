# HANDOFF — manutenção da fila Mavroa018

## Resultado e limite

Coordenação reparada; **nenhuma campanha executada/ativada nesta manutenção**. Dono único da entrega: `t_f4bacf0f`. Mesmos request, input, conta, manifests, IDs e relógio. Nenhuma mensagem na thread operacional; REPORT-INFRA é separado.

- Request: `shein-1570314359530459327`.
- Input literal: `/root/mgs-agent/data/ares/meta-ads/audit/shein/campaigns/intake/shein-1570314359530459327/request.json`.
- Conta: `937846586033361`, Mavroa G006, USD / America/New_York.
- Pedido humano: fonte018 ×10, USD85/dia por campanha, 12/novembro/2026 01:00 EST, lance herdado95minor.
- Job continua WAITING, attempts0, notificationnull, maintenance_hold=true, dispatch_owner=foreground, delivery_owner=ares. As dependências históricas gravadas antes da manutenção são preservadas como histórico; `dependencies(request,account)`/`--inspect` atuais retornam `[]`. Só o takeover canônico do card de entrega atualizará ownership/dependências persistidas e retirará o hold.

## Causa real, não hipótese

O receipt manual original é válido e seus pins continuam idênticos. O GET mostrou alterações comerciais externas posteriores ao receipt:104/adset120251118523710629 bid_amount90→105;105/campaign120251118520690629 daily_budget4375→12300;107/campaign120251118543350629 daily_budget4375→12100. Esses três deltas explicam a falha de `scheduling_identity` e a exceção de `manual.verify_live`. Não era fonte018 stale, sessão/credencial ou ausência de mídia.

Adicionalmente,107/AD01=120251118559060629 está PAUSED/WITH_ISSUES1487083;104/108AD02 mantêm2490468. Histórico102–110 hoje tem9campanhas e9adsetsACTIVE,15/18adsACTIVE,3PAUSED. Status/review já eram mutáveis na projeção anterior; não causaram o gate comercial. Autoria dos novos budgets/bid não foi inferida. Não restaurar valores nem retomar writer/QA/ativação históricos.

## Correção central delimitada

Módulo `ares_campaign_v3.shein_manual_observation` registra receipt imutável + grant por digest, exclusivamente sucessor×predecessor. Registro sob locks/CAS/backups, GET das mensagens originais de takeover e autoridade live do sucessor. `shein_manual_takeover.verify_live(...,resume_request=request)` exige igualdade com essa observação; sem ela, o comparador anterior continua estrito. `SourceMediaProof.validate` confere também digest/grant. Não há novo writer nem edição de manifest/clock, e o receipt original não foi reescrito.

- Receipt original preservado: `data/ares/meta-ads/state/shein-campaigns/queue/manual-takeovers/shein-1569456380065222707.json` (SHA256 `9fec5f0d438ced38c84b52f3cec7c6b94c72f1a3103cd0ef1fdd889cbaf6b641`).
- Nova observação: `data/ares/meta-ads/state/shein-campaigns/queue/manual-observations/shein-1570314359530459327/shein-1569456380065222707.json` (SHA256 `c77daac47a4180e8a742d097f32a6288609cac89acc474a2d114193e88af17aa`).
- Grant: `data/ares/meta-ads/policies/shein-manual-coordination-observations.json`.
- Só budget/lance observados entram na observação; qualquer outro delta de estratégia/horário/nome/ID/creative/mídia, DELETED/ARCHIVED ou mudança comercial posterior permanece bloqueante. Não estende takeover para outro request.
- Reviewc3/006–007 e suas reservas permanecem intactos e inertes; nenhum terminal COMPLETE/QA artificial.

## Fonte e efeitos parciais confirmados por GET

Fonte018=120250998192240629, adset120250998193160629, bid95; anúncios120250998194980629 e120250998195030629. Assets reais:
- `asset_d75782c94fcb106fb38b`, `SHEIN_US_ES_IMG_CHAQUETAS_GRATIS_NV_003.jpg`, image_hash `ed8fd58ef6c3ca8257b165db4ccf614c`.
- `asset_38289922a19e380bc05e`, `SHEIN_US_ES_IMG_CHAQUETAS_GRATIS_NV_004.jpg`, image_hash `4cb7f55a385f503d5d78a395c5f54585`.

Reservas continuam do request histórico terminal `shein-1565747351543480374`; nenhuma transferência. Prova tipada fresca confirmou disjunção de mídia final e aliases dos predecessores manual+c3, locks/lease válidos e dependencies[]. TTL120s: **não reutilizar o snapshot como autorização futura**.

Runner ENGINE_PENDING; core IN_PROGRESS; bundles1–3COMPLETE; bundle4shells_normalized. GET independente confirmou8campanhas160–167,8adsets e16adsPAUSED; cada campanha8500minor/dia, COST_CAP95 e start_time`2026-11-12T01:00:00-0500`. Esses oito IDs devem permanecer:
`120251175905590629,120251175905550629,120251175911210629,120251175911330629,120251175917120629,120251175917110629,120251175922190629,120251175922180629`.

**Bundle4 já tem4ads vivos NÃO persistidos em ad_ids no checkpoint:**
-166/c120251175922190629/adset120251175922450629: ads120251175924860629(src120250998194980629),120251175924680629(src120250998195030629).
-167/c120251175922180629/adset120251175922360629: ads120251175924700629(src120250998194980629),120251175925210629(src120250998195030629).

Não editar checkpoint aqui nem repetir `/copies` cegamente. O core deve reconciliar por slot/lineage e completar exclusivamente camadas ausentes. O readback parcial não certifica QA.

## Retomada exata — executar apenas no card de entrega

```bash
cd /root/mgs-agent
PYTHONPATH=/root/mgs-agent/scripts python3 -m ares_campaign_v3.shein_request_queue --inspect /root/mgs-agent/data/ares/meta-ads/audit/shein/campaigns/intake/shein-1570314359530459327/request.json
# Exigir dependencies=[] e prova tipada recém-gerada. Não remover holds/depêndencias à mão.
PYTHONPATH=/root/mgs-agent/scripts python3 -m ares_campaign_v3.shein_request_queue --take-foreground /root/mgs-agent/data/ares/meta-ads/audit/shein/campaigns/intake/shein-1570314359530459327/request.json
# Readback do job: FOREGROUND_OWNED, dispatch_ownerforeground, notificationnull; dono únicoares.
python3 /root/mgs-agent/scripts/ares-shein-campaigns.py campaign --input /root/mgs-agent/data/ares/meta-ads/audit/shein/campaigns/intake/shein-1570314359530459327/request.json --dry-run
# Após DRY_RUN_OK: runner original. Timeoutforeground>=600s; não repetir180s.
python3 /root/mgs-agent/scripts/ares-shein-campaigns.py campaign --input /root/mgs-agent/data/ares/meta-ads/audit/shein/campaigns/intake/shein-1570314359530459327/request.json --confirm-execute
```

O horário01:00 já passou durante esta manutenção. **Os oito conjuntos existem com esse início: não aplicar buffer novo, resealar manifest ou mudar seus horários como se o pedido ainda não tivesse writes.** Preservar selos/relógio e deixar a rota central classificar a continuação/slots faltantes; qualquer incompatibilidade precisa de diagnóstico real, não edição de input. A regra de atraso técnico não expira autorização, mas também não autoriza mudança material de horário.

Só encerrar após10/10campanhas e20ads completos, QA semântico+renderizado por IDs, ativações/readback centrais e preservação dos16ads anteriores. Entrega única na origem e blocoIris permanecem responsabilidade de`t_f4bacf0f`; não chamar notificação individual do worker.

## Evidência e testes

Pasta:`data/ares/meta-ads/audit/maintenance/t_ee2d9949/`. Arquivos: `historical-live.json`, `historical-diff.json`, `source-and-partial-live.json`, `observation-registration.json`, `source-media-after.json`, `installation.json`, `preservation-before.json`, `tests-summary.json`, JUnits baseline/final e `report-infra-readback.json`.

10testes novos passaram, cobrindo binding exato, ausência de autoridade/grant, CAS, locks, lease concorrente, reservas/mídia compartilhada, TTL/digest, imutabilidade, crash receipt→grant/idempotência e replay histórico com manifest atual válido. Regressões não introduziram falhas:1subteste legado foi reproduzido no baseline porque sua fixtureSimpleNamespace não contém`operation` exigido por um guard anterior. O novo teste com manifest adequadamente formado confirmou o fence real doEngine; não afrouxamos guard nem alteramos essa fixture histórica.

REPORT-INFRA1570320303370932336 confirmado por GET, content vazio,1embed,semmentions/semthread. Inventário:`ares-shein-manual-observation-t_ee2d9949`; registro:`ARES-SHEIN-MANUAL-OBSERVATION-1570314359530459327`. Procedimento salvo na skillSHEIN, `references/campaign-runtime-recovery.md`, com readback real.
