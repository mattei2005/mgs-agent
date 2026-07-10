## Tentativa real 2026-06-18

A tentativa controlada de clone foi executada com criação PAUSED e budget `daily_budget=2500` (USD 25). Resultado:

```text
Etapa                     | Resultado
--------------------------|--------------------------------------------------
Campanha PAUSED           | criada com sucesso em tentativas parciais
Adsets PAUSED             | criados após ajustar special_ad_category_country=ES e attribution 1d click
Adcreative novo           | Meta rejeitou recriação DCO por link messenger_doc como externo
Ad com creative existente | Meta bloqueou por pending account authentication
Bloqueio final            | code=31, subcode=3858385, Ads Manager exige autenticar conta
Limpeza                   | campanhas parciais foram marcadas DELETED e verificadas via GET
```

Audits:

```text
/root/mgs-agent/data/ares/meta-ads/audit/clone/clone-attempt-20260618T035944Z.json
/root/mgs-agent/data/ares/meta-ads/audit/clone/clone-attempt-20260618T040046Z.json
/root/mgs-agent/data/ares/meta-ads/audit/clone/clone-attempt-20260618T040141Z.json
/root/mgs-agent/data/ares/meta-ads/audit/clone/cleanup-partial-120248889706550604.json
/root/mgs-agent/data/ares/meta-ads/audit/clone/cleanup-partial-120248889834980604.json
/root/mgs-agent/data/ares/meta-ads/audit/clone/cleanup-partial-120248889873410604.json
```

Nova tentativa com até 3 alternativas em `/root/mgs-agent/scripts/ares-meta-clone-troubleshoot-3alts.py` confirmou o bloqueio:

```text
Alternativa | Método                                      | Resultado
------------|---------------------------------------------|-------------------------------
1           | build exato: campaign + adsets + 3 ads       | bloqueou em create_ad code=31/subcode=3858385
2           | Meta native campaign copies endpoint         | bloqueou code=100/subcode=1885194
3           | campaign+adset manual + ad copies endpoint   | bloqueou ad copy code=100/subcode=3858504
```

Auditoria: `/root/mgs-agent/data/ares/meta-ads/audit/clone/clone-troubleshoot-3alts-20260618T041137Z.json`.
Campanhas parciais criadas nas alternativas 1 e 3 foram marcadas `DELETED` e verificadas via GET. Não tentar novas variações até a conta ser autenticada no Ads Manager ou Rodolfo confirmar outro usuário/token/ad account.

Próximo clone real depende de Rodolfo/usuário autenticando a conta no Ads Manager para remover o pending action.
