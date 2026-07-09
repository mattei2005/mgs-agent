# DTR↔SB Phase 1 — `SB sem DTR nao Blocked` column D actions (2026-07-08)

## Context

Rodolfo pointed Zeus to column D of Sheet `1VNz7l1soafiju0v89H0IfaKJHcgioVjUw6nXyORl9oI`, `gid=860481715`, tab `Fase 1 - SB sem DTR nao Blocked`.

Live CSV readback showed column D header:

```text
ACOES A SE FAZER
```

## Durable rule

For this tab, column D is the operator action column. Do not classify rows only from the tab name or stale pending logic; read column D and apply its action semantics before reporting or planning writes.

Observed values and meaning:

- `FEITO - PAGINA DELETADA DO SEGURADOR E DELETADA DA DASH DA SB` → already resolved; do not count as pending.
- `IGNORAR TOTALMENTE DO SISTEMA TODO DA MGS` → global ignore candidate; add/confirm in `/root/mgs-agent/data/mgs-global-page-ignore-list.json` before future DTR/SB audits and exclude from all MGS operations.
- `ESTA NO DTR SIM, VERIFICAR` → not an SB orphan by default; verify live DTR/Bot by `FB_PAGE_ID` first, then `PAGE_ID/PG`, before deleting/blocking/ignoring.

## Current readback snapshot from column D

Rows visible on 2026-07-08:

```text
Teresa Camacho    PAGE_ID 19337  D=FEITO - PAGINA DELETADA DO SEGURADOR E DELETADA DA DASH DA SB
Daniella Rosário  PAGE_ID 8341   D=IGNORAR TOTALMENTE DO SISTEMA TODO DA MGS
Sofia Ramirez     PAGE_ID 5461   D=ESTA NO DTR SIM, VERIFICAR
Maria José        PAGE_ID 1122   D=IGNORAR TOTALMENTE DO SISTEMA TODO DA MGS
Aurora Jiménez    PAGE_ID 702    D=IGNORAR TOTALMENTE DO SISTEMA TODO DA MGS
Bruna Herrera     PAGE_ID 499    D=IGNORAR TOTALMENTE DO SISTEMA TODO DA MGS
Isadora Torres    PAGE_ID 109    D=IGNORAR TOTALMENTE DO SISTEMA TODO DA MGS
Marta Sanchez     PAGE_ID 107    D=IGNORAR TOTALMENTE DO SISTEMA TODO DA MGS
Emilia Montoya    PAGE_ID 106    D=IGNORAR TOTALMENTE DO SISTEMA TODO DA MGS
Isabel Núñez      PAGE_ID 101    D=IGNORAR TOTALMENTE DO SISTEMA TODO DA MGS
```

## Follow-up direct instruction — 2026-07-09

Rodolfo explicitly instructed that all nine listed pages from this tab must be ignored totally by the MGS system in future sweeps, including the row whose column D said `FEITO - PAGINA DELETADA...`:

```text
1063903433472026  pg_19337
823864334141386   pg_8341
380536875150328   pg_1122
346856805184271   pg_702
352775804588457   pg_499
323736617490470   pg_109
330353400164437   pg_107
334015689799757   pg_106
392418553945157   pg_101
```

Operational effect: every future DTR/SB audit, Bot scan, SB registration plan, schedule/backfill, restricted-page scan, page-health scan, and pending report must load `/root/mgs-agent/data/mgs-global-page-ignore-list.json` and exclude these pages by `FB_PAGE_ID` first, then by `bot_user + PAGE_ID/PG`. Do not surface them as pending/actionable unless Rodolfo explicitly removes the ignore.

## Pitfall

Earlier references emphasized column E for global ignore in `Fase 1 - DTR sem SB`. That does not transfer blindly to `Fase 1 - SB sem DTR nao Blocked` (`gid=860481715`): here the action text is in column D, and Rodolfo can also override/extend the ignore list by direct message.
