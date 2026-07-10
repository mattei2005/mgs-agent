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
## Nomenclatura operacional: scale vs replacement

Separar escala normal de replacement. Para campanha nova de escala, continuar a sequência simples da página/operação; para substituição de campanha ruim, usar `RPL`.

```text
Tipo                  | Padrão
----------------------|------------------------------------------------------------
Scale normal           | <Nome página> - <País> - <Idioma> - (<pg_id>) - <seq>
Replacement            | <Nome página> - <País> - <Idioma> - (<pg_id>) - RPL - <YYYYMMDD> - <seq>
```

Exemplos:

```text
Elena Santana - ES - ESP - (pg_22091) - 21
Patricia Flores - US - ESP - (pg_22069) - RPL - 20260619 - 01
```

Notas:
- `RPL` identifica replacement, não escala normal.
- `YYYYMMDD` é a data programada de início no timezone da conta.
- `seq` começa em `01`.
- Não reutilizar o sufixo numérico antigo da loser como identidade operacional do replacement.
- Não usar `DUP` em produção; `DUP` é apenas rótulo técnico/teste e deve ser limpo ou evitado em objetos finais.

### Nomenclatura recomendada para adsets, ads e adcreatives

```text
Object       | Pattern
-------------|------------------------------------------------------------
Adset        | CJ01 - <FORMAT> - <ANGLE_GROUP>
Ad           | AD<NN> - <FORMAT> - <ANGLE> - <P_ORIENT> - <VARIANT>
AdCreative   | CC_<COUNTRY>_<LANG>_<FORMAT>_<ANGLE>_<P_ORIENT>_<VARIANT>
```

Exemplo Elena:

```text
Adset      | CJ01 - VID - MIX
Ad 1       | AD01 - VID - LIMITE_ALTO - NV - 001
Ad 2       | AD02 - VID - LIMITE_ALTO - NV - 002
Ad 3       | AD03 - VID - LIMITE_ALTO - NV - 003
Creative  | CC_ES_ESP_VID_LIMITE_ALTO_NV_001
```

Antes de renomear objetos ativos, gerar inventário read-only + contact sheets + plano `old_name -> new_name` e pedir aprovação explícita de Rodolfo. Referência: `references/elena-naming-standard-and-readonly-plan-2026-06-19.md`.
## Padrão de nomenclatura Meta — escala, ads e criativos

Para operação padronizada Ares 1x3 em OpenzedFinanzas/Elena:

```text
Nível       | Padrão
------------|------------------------------------------------------------
Campanha    | <Nome página> - <País> - <Idioma> - (<pg_id>) - <SEQ>
Conjunto    | CJ01 - <FORMAT> - <ANGLE_GROUP>
Anúncio     | AD<NN> - <FORMAT> - <ANGLE> - <P_ORIENT> - <VARIANT>
Adcreative  | CC_<COUNTRY>_<LANG>_<FORMAT>_<ANGLE>_<P_ORIENT>_<VARIANT>_C<SEQ>
Replacement | <Nome página> - <País> - <Idioma> - (<pg_id>) - RPL - <YYYYMMDD> - <seq>
```

Exemplo Elena validado:

```text
Campanha   | Elena Santana - ES - ESP - (pg_22091) - 1
Conjunto   | CJ01 - VID - MIX
Anúncio    | AD01 - VID - LIMITE_ALTO - NV - 001
Adcreative | CC_ES_ESP_VID_LIMITE_ALTO_NV_001_C01
```

Pitfalls validados em 2026-06-19:
- Antes de rename em massa, gerar inventário read-only e plano `old_name → new_name`, classificar criativo por thumbnail/frame/texto/video title e salvar audit em `data/ares/meta-ads/audit/naming/`.
- `adcreative` não aceita GET com `effective_status/status`; validar com fields `id,name`.
- Nomes de `adcreative` repetidos podem falhar com `Invalid parameter`/`1487229`; adicionar sufixo de instância/campanha (`_C01`, `_C02`...) mantendo o prefixo taxonômico.
- Para criativos Elena atuais, video titles `NV - Criativo 3 - Openzed - EspanholES - Feed/Storie` + visual de cartão/600/6000/CTA justificaram `CC_ES_ESP_VID_LIMITE_ALTO_NV_00X_CYY`.
- Detalhes de execução, evidência visual/API e formato de audit: `references/meta-naming-standard-elena-2026-06-19.md`.
