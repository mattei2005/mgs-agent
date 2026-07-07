# DTR/SB PAGE ID Step 1 fresh audit + Google Sheet rebuild — 2026-07-06

## Trigger

Use this when Rodolfo asks to redo/finalize **Step 1** of the Bot/DigitalTRChat ↔ SmartBidding PAGE ID registration audit, especially after he says he deleted/cleared the Google Sheet tabs and wants a fresh audit from zero before moving to Step 2.

## Durable lessons from the session

1. **Live from zero, no snapshots as source of truth.**
   - Re-scan all DigitalTRChat bot users from 1Password.
   - Log into every DTR user.
   - Iterate every top-bar segurador/account.
   - Enumerate current DTR page cards.
   - Re-fetch SmartBidding live `/company` + full `/campaigns/Messenger` under all `digital-trust` + `digital-trust-2` child publishers.

2. **Correct match order for this PAGE ID audit.**
   - Primary: global `FB_PAGE_ID` across full SB scope.
   - Fallback: global `PAGE_ID` / PG across full SB scope.
   - Do **not** pre-filter SB rows by `USER_LOGIN` before matching.
   - Do **not** use `PAGE_NAME` as a match key; names repeat and Unicode/accent differences cause false positives.
   - After a match is found, validate only:
     - `LOGIN` / `USER_LOGIN`;
     - `PAGE_ID`;
     - `FB_PAGE_ID`;
     - `UTM_CAMPAIGN = pg_<PAGE_ID>`.

3. **Separate DTR→SB and SB→DTR outputs.**
   - DTR→SB answers: “every page currently in Bot/DTR, is it correctly registered in SB?”
   - SB→DTR answers: “rows in SB for audited scope that are not present in current Bot/DTR.”
   - Do not mix reverse inventory (`SB sem Bot/DTR`) into the primary DTR→SB problem count unless clearly labeled.

4. **When Sheet tabs were deleted, recreate them by name.**
   - Do not rely on old `gid`s surviving after Rodolfo deletes tabs.
   - Use Sheets API `addSheet` to recreate stable semantic tabs.
   - Then capture the new `gid`s from spreadsheet metadata.
   - Write each tab and validate by readback row count before reporting success.

## Recommended Sheet tabs for Step 1

Create/recreate these tabs in the target Sheet:

```text
00 Resumo
01 OK LOGIN PAGE FB UTM
02 Login difere
03 PAGE_ID FB difere
04 UTM difere
05 Nao encontrado SB
06 Ambiguo SB
07 SB sem Bot DTR
08 Duplicidades
```

Minimum readback report per tab:

```text
Tab name | expected rows | readback rows | direct URL with gid
```

## Executive report shape

Use a short Discord report like:

```text
Auditoria PAGE ID — Bot/DTR ↔ SmartBidding
Atualizado: YYYY-MM-DD HH:MM EDT

Escopo
Usuários DigitalTRChat no 1Password: N
Logins DTR OK: N/N
Seguradores lidos no DTR: N
Páginas lidas no Bot/DTR: N
Publishers SB lidos: N
Rows live SB: N
Rows SB dos usuários auditados: N

Resultado DTR → SB
OK: N
Login divergente: N
PAGE_ID/FB_PAGE_ID divergente: N
UTM divergente: N
Não encontrado na SB: N
Ambíguo: N
Duplicidades: N

Resultado SB → DTR
Existe na SB e não no Bot/DTR: N
```

Then list the Sheet URL and only the most important tab URLs/counts. Avoid flooding Rodolfo with every row in Discord.

## Pitfalls corrected

- Earlier false `NO_SB_MATCH` counts came from filtering SB rows by `USER_LOGIN` before matching. Never do that for this audit.
- Earlier “matches by PAGE_NAME global” were too permissive for Step 1. Treat page name as visual context only.
- If Rodolfo is trying to “finalizar Passo 1 e ir pro Passo 2”, keep the answer executive: what blocks Step 2, what is clean, and where the rows are in the Sheet.
- If tabs were deleted, old `gid` links are stale. Report the newly created tab URLs from readback metadata.
