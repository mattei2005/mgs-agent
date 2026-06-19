# Elena naming standard and read-only rename plan — 2026-06-19

Context: Rodolfo asked to standardize naming before scaling campaigns and replacements, including campaign, adset, ad, and creative names. Ares inventoried the active Elena operation read-only before any rename.

## Validated account state

```text
Operation       | OpenzedFinanzas-CC-ES
Page            | Elena Santana / pg_22091
Campaigns       | 20
Adsets          | 20
Ads             | 60
Unique creatives| 60
Structure       | 1 campaign / 1 adset / 3 ads
Budget          | USD 25 per campaign
```

Read-only artifacts were generated under:

```text
/root/mgs-agent/data/ares/meta-ads/audit/naming/elena-20260619/
```

Key files:

```text
elena-creative-inventory-readonly.{json,csv}
elena-naming-plan-readonly.{json,csv}
contact-sheet-1.jpg
contact-sheet-2.jpg
contact-sheet-3.jpg
video-metadata-readonly.json
```

## Naming decision

For normal scale campaigns, continue the sequence rather than using technical suffixes:

```text
<Nome página> - <País> - <Idioma> - (<pg_id>) - <seq>
```

Example:

```text
Elena Santana - ES - ESP - (pg_22091) - 21
```

For replacements, use `RPL` only when replacing a bad campaign:

```text
<Nome página> - <País> - <Idioma> - (<pg_id>) - RPL - <YYYYMMDD> - <seq>
```

Example:

```text
Elena Santana - ES - ESP - (pg_22091) - RPL - 20260620 - 01
```

Avoid `DUP` in production naming. `DUP` is a technical/test label only and should not remain in live production unless the user explicitly asks.

## Recommended object naming

```text
Object       | Pattern
-------------|------------------------------------------------------------
Campaign     | <PAGE> - <COUNTRY> - <LANG> - (<PG_ID>) - <SEQ>
Adset        | CJ01 - <FORMAT> - <ANGLE_GROUP>
Ad           | AD<NN> - <FORMAT> - <ANGLE> - <P_ORIENT> - <VARIANT>
AdCreative   | CC_<COUNTRY>_<LANG>_<FORMAT>_<ANGLE>_<P_ORIENT>_<VARIANT>
Replacement  | campaign uses RPL; ads may append RPL only if needed for clarity
```

For Elena current assets, the read-only plan classified the 60 creatives as:

```text
FORMAT       | VID
ANGLE        | LIMITE_ALTO
P_ORIENT     | NV
VARIANTS     | 001 / 002 / 003 per campaign triplet
```

Suggested examples:

```text
Adset      | CJ01 - VID - MIX
Ad 1       | AD01 - VID - LIMITE_ALTO - NV - 001
Ad 2       | AD02 - VID - LIMITE_ALTO - NV - 002
Ad 3       | AD03 - VID - LIMITE_ALTO - NV - 003
Creative 1 | CC_ES_ESP_VID_LIMITE_ALTO_NV_001
Creative 2 | CC_ES_ESP_VID_LIMITE_ALTO_NV_002
Creative 3 | CC_ES_ESP_VID_LIMITE_ALTO_NV_003
```

## Classification method

1. Pull campaigns/adsets/ads/adcreatives via Meta API read-only.
2. Save inventory to JSON/CSV before proposing any rename.
3. Download all `thumbnail_url` images and generate contact sheets.
4. Pull video metadata by `video_id` when present; titles can carry useful original creative taxonomy.
5. Use visual + metadata evidence before assigning `ANGLE` and `P_ORIENT`.
6. Build `old_name -> new_name` plan for campaigns/adsets/ads/adcreatives.
7. Do not execute Meta rename until Rodolfo approves the plan.
8. After approval, update names by API and validate with GET before reporting success.

## Pitfalls

- Do not rename active Meta objects directly from intuition; first generate and show the old→new plan.
- Do not infer angle only from generic ad text like `TARJETA DE CRÉDITO DISPONIBLE`; combine thumbnail/contact sheet and video metadata.
- Campaign names may already be clean enough; prioritize adset/ad/adcreative names when campaign names are sequential and clear.
- AdCreative names may repeat by normalized asset variant across campaigns; that is useful for analysis. The `creative_id` remains the unique Meta identifier.
- Treat `DUP` as a temporary execution artifact, not a production taxonomy.
