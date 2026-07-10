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
