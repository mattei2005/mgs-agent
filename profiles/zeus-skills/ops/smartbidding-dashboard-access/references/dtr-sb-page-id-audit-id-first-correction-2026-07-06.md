# DTR/Bot ↔ SmartBidding PAGE ID audit — ID-first correction (2026-07-06)

## Why this reference exists

During a DTR/Bot ↔ SmartBidding registration audit, the first reports were misleading because the comparison logic over-weighted fields that are not validation keys for `Accounts > Messenger > Page`.

Rodolfo corrected the model:

- The Facebook `FB_PAGE_ID` (large number) is unique per Facebook page.
- The DTR/Bot `PAGE_ID` / small PG ID is also unique for the page record created when linking the page in the Bot.
- Page name is not a validation key. It can repeat across seguradores/users and can differ by Unicode/accent rendering.
- Segurador/profile name is not a validation key in SB `Accounts > Page`; that table does not expose a segurador column equivalent to DTR's selected account.

## Correct validation keys

For each DTR page card, compare against SB `Accounts > Messenger > Page` with this order:

1. `FB_PAGE_ID` global across the full SB Page table.
2. `PAGE_ID` / small PG global across the full SB Page table.
3. Once a row is found by ID, validate fields:
   - SB `LOGIN` / backend `USER_LOGIN` equals DTR Bot user.
   - SB `PAGE_ID` equals DTR small PG ID.
   - SB `FB_PAGE_ID` equals DTR large Facebook Page ID.
   - SB `UTM_CAMPAIGN` equals `pg_<DTR PAGE_ID>`.
4. Ignore DTR segurador for SB validation unless Rodolfo explicitly asks to audit DTR account placement. SB Page table does not have a comparable segurador field.
5. Ignore `PAGE_NAME` for match/validation. Include it only as visual context.

## Classification buckets to use

Use these buckets for reporting counts/sheets:

```text
OK_LOGIN_PAGE_ID_FB_UTM
  LOGIN + PAGE_ID + FB_PAGE_ID + UTM_CAMPAIGN all match.

IDS_UTM_OK_LOGIN_DIVERGE_OU_VAZIO
  PAGE_ID + FB_PAGE_ID + UTM_CAMPAIGN match, but SB LOGIN differs or is blank.
  Do not call this “segurador divergence”.

FB_PAGE_ID_OK_PAGE_ID_DIVERGE
  Same Facebook page exists in SB by FB_PAGE_ID, but the small PG/PAGE_ID differs.

PAGE_ID_OK_FB_PAGE_ID_DIVERGE
  Same small PG/PAGE_ID exists in SB, but FB_PAGE_ID differs.

EXISTE_NA_SB_COM_DIVERGENCIA_UTM_CAMPAIGN
  IDs and LOGIN may match but UTM_CAMPAIGN is not `pg_<PAGE_ID>`.

NAO_ENCONTRADO_NA_SB_POR_FB_NEM_PG
  Only use this after both global FB_PAGE_ID and global PAGE_ID searches fail.
```

## What not to do

- Do not classify as `NO_SB_MATCH` just because `USER_LOGIN + PAGE_ID` does not match; search global IDs first.
- Do not use page name as a fallback match for the main operational count.
- Do not mark a row divergent because DTR segurador differs from an SB field; SB Pages has no equivalent segurador column.
- Do not call `SB USER_LOGIN` blank a segurador mismatch. Label it as `LOGIN vazio/diferente`.
- Do not present ambiguous name matches as operational evidence.

## Correct count from the corrected pass

On the corrected 2026-07-06 pass:

```text
DTR/Bot pages read:          2,914
SB Page rows read:           3,237
SB publishers scope:            56

OK_LOGIN_PAGE_ID_FB_UTM:                         2,514
IDS_UTM_OK_LOGIN_DIVERGE_OU_VAZIO:                 178
FB_PAGE_ID_OK_PAGE_ID_DIVERGE:                       71
EXISTE_NA_SB_COM_DIVERGENCIA_UTM_CAMPAIGN:            1
NAO_ENCONTRADO_NA_SB_POR_FB_NEM_PG:                 150
```

The earlier numbers `397` and `366` for “exists in DTR/Bot and not in SB” were invalid because the comparison logic used same-user matching and/or page-name fallback before properly applying global ID matching.

## Sheet-writing notes

When writing analysis tabs for Rodolfo, include both DTR and SB ID columns side-by-side:

- DTR Bot user
- DTR PAGE_ID/PG
- DTR FB_PAGE_ID
- SB LOGIN / USER_LOGIN
- SB PAGE_ID/PG
- SB FB_PAGE_ID
- SB UTM_CAMPAIGN
- classification bucket
- differences limited to `LOGIN`, `PAGE_ID`, `FB_PAGE_ID`, `UTM_CAMPAIGN`

Do not include segurador as a divergence column unless the task is explicitly about DTR account/segurador placement.
