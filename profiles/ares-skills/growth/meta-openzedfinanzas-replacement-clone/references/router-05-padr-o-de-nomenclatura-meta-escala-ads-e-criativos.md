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
