---
name: meta-openzedfinanzas-replacement-clone
description: "Clone/replacement da campanha OpenzedFinanzas Meta Ads: estrutura real da campanha Patricia Flores loser, nomenclatura RPL, seleção de criativos vencedores, budget USD 25 e validações de clone."
version: 1.0.0
author: Ares
license: internal
metadata:
  hermes:
    tags: [meta-ads, replacement, clone, openzedfinanzas, campaign-structure, mgs]
---

# Meta OpenzedFinanzas Replacement Clone

Use esta skill quando Rodolfo pedir para clonar/replacement de campanhas da conta Meta `OpenzedFinanzas-ES-CC-ES-03`.

## Conta/operação

```text
Campo              | Valor
-------------------|---------------------------------------------
Account ID         | 1356770869843984
Operação           | OpenzedFinanzas-CC-ES
Timezone           | Europe/Madrid
Métrica Europa     | MO = complete_registration
Custo              | CPMO = spend / MO
HOA alvo           | USD 2.00
Teto operação      | USD 300/dia
Reserva testes     | 20% = USD 60/dia
Budget campanha    | Máximo USD 25/dia inicialmente
```

## Campanha loser mapeada

Fonte real: `/root/mgs-agent/data/ares/meta-ads/audit/clone/inspect-campaign-120248290564280604.json`.

```text
Campo                  | Valor
-----------------------|--------------------------------------------------
Campaign ID            | 120248290564280604
Nome                   | Patricia Flores - US - ESP - (pg_22069) - 2
Status                 | ACTIVE
Objective              | OUTCOME_SALES
Buying type            | AUCTION
Bid strategy           | LOWEST_COST_WITHOUT_CAP
Budget original        | daily_budget=10000 cents (USD 100)
Special ad category    | FINANCIAL_PRODUCTS_SERVICES
Start original         | 2026-06-11T04:02:00+0200
Page token no nome     | pg_22069
```

## Estrutura real da campanha

```text
Adset ID             | Nome                   | Destination | Optimization         | Billing
---------------------|------------------------|-------------|----------------------|------------
120248290564350604   | Conjunto 01 - VÍDEOS   | MESSENGER   | OFFSITE_CONVERSIONS  | IMPRESSIONS
120248290564260604   | Conjunto 02 - IMAGENS  | MESSENGER   | OFFSITE_CONVERSIONS  | IMPRESSIONS
```

Targeting observado nos adsets:

```text
Campo                 | Valor
----------------------|------------------------------------------
País                  | ES
Idade                 | 18-65
Location types        | home, recent
Brand safety          | FACEBOOK_RELAXED, AN_RELAXED
Advantage audience    | targeting_automation.advantage_audience=1
Promoted object       | pixel_id 629060785934493, COMPLETE_REGISTRATION
Page ID promoted      | 1063171606876651
Attribution           | 7d click + 1d view
```

## Nomenclatura de replacement

Padrão criado para identificar trocas:

```text
<Nome página> - <País> - <Idioma> - (<pg_id>) - RPL - <YYYYMMDD> - <seq>
```

Exemplo:

```text
Patricia Flores - US - ESP - (pg_22069) - RPL - 20260619 - 01
```

Notas:
- `RPL` identifica replacement.
- `YYYYMMDD` é a data programada de início no timezone da conta.
- `seq` começa em `01`.
- Não reutilizar o sufixo numérico antigo da loser como identidade operacional do clone.

## Regras de clone

1. Clone deve ser criado PAUSED inicialmente, salvo autorização explícita para ACTIVE.
2. Start time deve ser o dia seguinte às `01:00` no timezone da conta.
3. Campaign daily budget nunca pode passar de `USD 25` inicialmente (`daily_budget=2500` cents).
4. Clonar estrutura do zero: campanha nova, adset novo, criativo/ad novo.
5. Selecionar exatamente 3 criativos vencedores da conta inteira, não só da campanha/página.
6. Ranking inicial de criativo vencedor: menor CPMO nos últimos 3 dias, com `spend >= USD 5` e `MO >= 2`.
7. Clone usa a mesma página/promoted object da loser, mas os criativos podem vir de outra campanha/página se forem vencedores da conta.
8. Depois do clone validado, loser deve ser deletada se a API permitir; se não permitir delete, arquivar/pausar.
9. Antes de reportar sucesso, validar com GET: campanha criada, status, budget, adsets e exatamente 3 ads.
10. Salvar audit em `/root/mgs-agent/data/ares/meta-ads/audit/clone/`.

## Script canônico

```bash
/root/mgs-agent/scripts/ares-meta-replacement-clone.py \
  --account-id 1356770869843984 \
  --operation-id OpenzedFinanzas-CC-ES \
  --loser-campaign-id 120248290564280604 \
  --daily-budget-usd 25
```

Dry-run:

```bash
/root/mgs-agent/scripts/ares-meta-replacement-clone.py --dry-run
```

## Criativos vencedores do dry-run inicial

Dry-run real salvo em `/root/mgs-agent/data/ares/meta-ads/audit/clone/clone-dry-run-20260618T035853Z.json`:

```text
Source campaign                                 | Source ad ID        | Creative ID       | Spend | MO | CPMO
------------------------------------------------|---------------------|-------------------|-------|----|------
Patricia Flores - US - ESP - (pg_22069) - 4     | 120248290564590604  | 1878134753167706  | 9.36  | 7  | 1.34
Patricia Flores - US - ESP - (pg_22069) - 1     | 120248290297210604  | 1018755007258886  |107.96 |70  | 1.54
Patricia Flores - US - ESP - (pg_22069) - 3     | 120248290564610604  | 1829542905087157  |101.34 |58  | 1.75
```

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

## Pitfalls

- Se a Meta retornar `code=31/subcode=3858385`, parar: a conta precisa de autenticação humana no Ads Manager antes de criar/modificar anúncios.
- A campanha original tem budget USD 100; replacement precisa forçar USD 25, nunca copiar o budget original.
- Criativos Advantage/DCO podem rejeitar recriação de `asset_feed_spec`; script tenta criar novo adcreative e, se a Meta recusar, usa fallback com `creative_id` existente para manter a campanha PAUSED construída. Reportar fallback explicitamente.
- Não ativar a campanha no ato do clone. Começar PAUSED e validar estrutura.
- Não deletar/arquivar loser antes de clone e validação.
- Não imprimir token Meta nem payload com token em logs.
