# B001–B010 App Roles Recount Table — 2026-07-03

Use this reference when Rodolfo asks to “recontar isso” while pointing at the B001–B010 reconciliation table.

## Required live refresh

Before producing the recount, run the app-role monitor in validation mode so the local state reflects current Meta `/roles` without sending alerts or writing the sheet:

```bash
cd /root/mgs-agent
MGS_META_APP_ROLES_DRY_RUN=1 \
MGS_META_APP_ROLES_SYNC_SHEET_REMOVED=0 \
/root/.hermes/profiles/zeus/scripts/meta-app-roles-watch.sh \
  >/tmp/meta-app-roles-dryrun.out \
  2>/tmp/meta-app-roles-dryrun.err
```

Then read:

- runtime roles from `/root/mgs-agent/data/meta-app-role-monitor-state.json`;
- sheet intent from live CSV export of spreadsheet `1sTkBE6RQPQ3obq1j6m8RSu_22beEUbZjkQ-OttI01XY`, gid `562940072`.

## Table semantics

The user expects the same columns as the screenshot:

```text
Canal | Planilha | API atual | Falta na API | Sobra API | Removidos acumulados
```

Definitions:

- `Planilha`: count of sheet rows whose `NO APP` maps to the app/channel. Include rows marked `Removidos acumulado = X`; this is total operational intent, not only active/non-removed rows.
- `API atual`: raw current Meta role count returned for that app in state after the dry-run refresh. This includes the owner/creator profile, because that is how the monitor’s current role count is displayed.
- `Falta na API`: sheet rows for that app whose `USUARIO` or normalized `Segurador` is not present in current Meta roles.
- `Sobra API`: current Meta roles not found in the sheet for that app, excluding the known owner/creator profile for that app. Owner profiles are cosmetic exceptions, not cleanup candidates.
- `Removidos acumulados`: count of sheet rows for that app where column `Removidos acumulado` is `X`. Use the sheet column, not the state `cumulative_removed`, when reproducing this table.

## Canonical owner exceptions

Exclude these from `Sobra API`:

```text
B001    Dale Kuhlman
B002    Lola Lilliana
B003    Siyam Mia
B004    Mst Lija
B005-2  Wana Hsh
B006    Mic Vb
B007    พรชนิตว์ ฑีฆะวัฒน์
B008    Phạm Minh Thiện
B009    Hindawan Pratama
B010    Lorraynii Criistiinii
```

## Matching rule

Match sheet rows to Meta roles by either:

1. sheet `USUARIO` equals Meta role `id`; or
2. normalized sheet `Segurador` equals normalized Meta role `name`.

Normalize names with lowercase, accent removal, non-alphanumeric collapsed to single spaces.

## Response style

Return only the updated table and 1–3 bullets of executive interpretation. Do not explain the whole monitor unless Rodolfo asks.

Example final shape:

```text
Canal    Planilha   API atual   Falta na API   Sobra API   Removidos acumulados
B001     ...
...
TOTAL    ...
```

Then short bullets:

- `Antes: faltavam X; agora: faltam Y.`
- `Sobra API: Z.`
- `Planilha agora tem N linhas no escopo.`
