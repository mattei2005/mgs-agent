# DTR/Bot ↔ SmartBidding PAGE ID audit — ID-first correction lessons (2026-07-06)

## Context

During a DTR/Bot ↔ SmartBidding registration audit, Rodolfo corrected multiple false-positive classifications caused by treating `USER_LOGIN`, segurador/profile name, and `PAGE_NAME` as stronger signals than the actual page IDs.

This reference applies to **registration/cadastro audits** between DigitalTRChat/Bot pages and SmartBidding `Accounts > Messenger > Page`.

## Canonical field meanings

### Bot/DTR

- Bot user/login = DigitalTRChat credential/email.
- Segurador = account selected inside the Bot before listing pages.
- Page card exposes:
  - small PG / `PAGE_ID` generated when the page is linked in Bot/DTR;
  - large Facebook `FB_PAGE_ID`;
  - page name and email as context only.

### SmartBidding `Accounts > Messenger > Page`

- `LOGIN` / `USER_LOGIN` = bot user email.
- `PAGE ID` / `PAGE_ID` = small PG ID.
- `FB PAGE ID` / `FB_PAGE_ID` = large Facebook page ID.
- `UTM CAMPAIGN` / `UTM_CAMPAIGN` must be `pg_<PAGE_ID>`.
- `PAGE NAME` is visual/context only for this audit.
- There is no reliable `Segurador` column in the SB Page table for this validation; do **not** require or infer it.

## Correct audit order

For each DTR page:

1. Search SB globally by `FB_PAGE_ID` first.
2. If no FB match, search SB globally by small `PAGE_ID` / PG.
3. Do **not** use `PAGE_NAME` to decide existence or divergence.
4. Once an SB row is found by ID, validate only:
   - SB `LOGIN` equals DTR bot user;
   - SB `PAGE_ID` equals DTR PG;
   - SB `FB_PAGE_ID` equals DTR large FB ID;
   - SB `UTM_CAMPAIGN` equals `pg_<DTR PAGE_ID>`.
5. Only label `not found in SB` when neither global `FB_PAGE_ID` nor global `PAGE_ID` exists in SB.

## Correct buckets

Use buckets like:

```text
OK_LOGIN_PAGE_ID_FB_UTM
IDS_UTM_OK_LOGIN_DIVERGE_OU_VAZIO
FB_PAGE_ID_OK_PAGE_ID_DIVERGE
PAGE_ID_OK_FB_PAGE_ID_DIVERGE
EXISTE_NA_SB_COM_DIVERGENCIA_UTM_CAMPAIGN
NAO_ENCONTRADO_NA_SB_POR_FB_NEM_PG
AMBIGUO_FB_DUPLICADO_NA_SB
AMBIGUO_PAGE_ID_DUPLICADO_NA_SB
```

Avoid buckets such as `PAGE_NAME diverges` or `segurador diverges` in the main registration audit. If page names are needed, create a separate human-audit sheet and label it as visual-only.

## SmartBidding correction rules

If `FB_PAGE_ID` matches a single SB row but `PAGE_ID`/PG differs, Rodolfo approved updating SB:

- set `PAGE_ID` to DTR PG;
- set `UTM_CAMPAIGN` to `pg_<DTR PG>`;
- keep `FB_PAGE_ID` unchanged;
- read back the row and validate all three fields.

If only `UTM_CAMPAIGN` differs and IDs match, update only `UTM_CAMPAIGN` to `pg_<PAGE_ID>` and validate.

Do **not** auto-fix duplicated/conflicting ID cases. If the same `FB_PAGE_ID` maps to multiple PGs or the target PG already exists on another SB row, skip and report for manual decision.

## Sheet/reporting guidance

When writing manual verification sheets, include DTR and SB side-by-side columns:

```text
Categoria
Match por
DTR Bot user
DTR Segurador
DTR Página
DTR PAGE_ID/PG
DTR FB_PAGE_ID
DTR Facebook URL
DTR UTM esperado
DTR Email página
DTR raw
SB LOGIN
SB Página
SB PAGE_ID/PG
SB FB_PAGE_ID
SB UTM_CAMPAIGN
SB Status
SB Company
SB Domain
SB ID
Diff LOGIN
Diff PAGE_ID
Diff FB_PAGE_ID
Diff UTM
```

Rodolfo may manually verify tabs; make the classification and raw IDs obvious. Avoid ambiguous labels like `user/seg difere` when `segurador` is not an SB validation field.

## Pitfalls corrected

- Same IDs with empty SB `USER_LOGIN` should be classified as `LOGIN difere/vazio`, not as missing or segurador mismatch.
- Page names can repeat across seguradores and can differ by Unicode/accent normalization; names are not validation keys.
- Segurador is useful to collect DTR pages but not a required SB Pages comparison field.
- A page found globally in SB under a different `LOGIN` is not `missing in SB`; it is an association/login issue.
