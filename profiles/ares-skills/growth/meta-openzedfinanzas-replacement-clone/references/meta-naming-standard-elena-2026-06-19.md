# Meta naming standard — Elena/OpenzedFinanzas execution note (2026-06-19)

## Scope

Rodolfo asked to standardize naming for active Elena campaigns in `OpenzedFinanzas-ES-CC-ES-03` so scale/replacement work stays organized.

Read-only inventory first, then approved controlled write:

```text
Campaigns | 20
Adsets    | 20
Ads       | 60
Creatives | 60 unique adcreative objects
```

## Recommended taxonomy

```text
Nível       | Padrão
------------|------------------------------------------------------------
Campanha    | <Nome página> - <País> - <Idioma> - (<pg_id>) - <SEQ>
Conjunto    | CJ01 - <FORMAT> - <ANGLE_GROUP>
Anúncio     | AD<NN> - <FORMAT> - <ANGLE> - <P_ORIENT> - <VARIANT>
Adcreative  | CC_<COUNTRY>_<LANG>_<FORMAT>_<ANGLE>_<P_ORIENT>_<VARIANT>_C<SEQ>
Replacement | <Nome página> - <País> - <Idioma> - (<pg_id>) - RPL - <YYYYMMDD> - <seq>
```

Elena result:

```text
Campaign   | Elena Santana - ES - ESP - (pg_22091) - 1..20
Adset      | CJ01 - VID - MIX
Ad 1       | AD01 - VID - LIMITE_ALTO - NV - 001
Ad 2       | AD02 - VID - LIMITE_ALTO - NV - 002
Ad 3       | AD03 - VID - LIMITE_ALTO - NV - 003
Creative   | CC_ES_ESP_VID_LIMITE_ALTO_NV_00X_CYY
```

## Classification evidence

- Meta creative text: `TARJETA DE CRÉDITO DISPONIBLE`.
- Visual thumbnails/contact sheets showed card + `600/6000` value + CTA `OBTENER TARJETA` on the visible frames.
- Video titles returned by Graph API were consistently `NV - Criativo 3 - Openzed - EspanholES - Feed/Storie - N.mp4`.
- Therefore initial angle was `LIMITE_ALTO`, format `VID`, orientation `NV`.

## API pitfalls

1. Do not rename blind. Build a read-only plan with `old_*` and `new_*`, then get approval.
2. `adcreative` GET does **not** support `effective_status/status`; validate adcreative with fields `id,name` only.
3. Meta rejected repeated adcreative names for some objects with `Invalid parameter` / subcode `1487229`. Add unique instance suffix (`_C01`, `_C02`, ...), while preserving the taxonomy prefix.
4. After write, validate via fresh GET across campaign/adset/ad/creative edges and count issues before reporting success.

## Audit pattern

Store outputs under:

```text
/root/mgs-agent/data/ares/meta-ads/audit/naming/<operation-date>/
```

Useful artifacts:

```text
elena-creative-inventory-readonly.json/csv
contact-sheet-1.jpg .. contact-sheet-N.jpg
video-metadata-readonly.json
elena-naming-plan-readonly.json/csv
elena-naming-plan-readonly-v2-unique-creatives.json/csv
elena-naming-apply-<timestamp>.json
```

## Communication

For Rodolfo, report counts and final patterns, not raw JSON. If a first write partially fails but leaves some objects renamed, continue with a corrected plan and report both partial audit and final audit.
