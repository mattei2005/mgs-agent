# DTR/Bot ↔ SmartBidding PAGE ID audit rerun/reporting — 2026-07-06

## Context

Rodolfo asked to update and resend a prior PAGE ID audit report shown as a screenshot skeleton. The task was a live registration consistency audit between DigitalTRChat/Bot and SmartBidding, not a page-health/restriction workflow.

## Correct execution pattern

Use the existing all-1Password PAGE ID audit runner when available:

```bash
cd /root/mgs-agent
set -a
source .env 2>/dev/null || true
set +a
xvfb-run -a /tmp/sb-venv/bin/python /root/mgs-agent/work/dtr-sb-id-audit-all-1p-20260705.py
```

Operational rules:

- Scope is all DigitalTRChat users discovered from 1Password, not the migration sheet.
- Query Bot/DTR live for every user and every top-bar segurador/account.
- Query SmartBidding live (`Accounts > Messenger > Page`) under current MGS scope.
- Compare `USER_LOGIN`, segurador/profile, `PAGE_ID`, `FB_PAGE_ID`, and `PAGE_NAME`.
- This is read-only unless Rodolfo explicitly asks for correction.
- In Discord/#alerts-infra, do not use `notify_on_complete=true`; wait/poll manually and return the consolidated report only.

## Report shape Rodolfo expects

When resending this audit report, mirror the compact executive structure from the screenshot:

```text
Auditoria PAGE ID — Bot/DTR ↔ SmartBidding
Atualizado: YYYY-MM-DD HH:MM EDT

Escopo
- Usuários DigitalTRChat no 1Password: N
- Logins DTR OK: X/Y
- Seguradores lidos no DTR: N
- Páginas lidas no DTR/Bot: N

SmartBidding
- Publishers lidos: N
- Rows live em Accounts > Page: N
- Rows dos usuários auditados: N

Resultado
- Matches OK: N
- Problemas encontrados: N
- Duplicidades detectadas: N

Quebra dos problemas
- Existe no Bot/DTR e não na SB: N
- Existe na SB e não no Bot/DTR: N
- Existe nos dois mas diverge: N
  - PAGE_NAME divergente: N
  - PAGE_ID + SEGURADOR divergente: N

Duplicidade detectada
- [user/profile/page details]

Top concentrações — NO_SB_MATCH
- user: N
...
```

If a prior report is visible in the conversation, include only a short delta when useful (for example, `problemas caíram de 579 para 468; divergências de 161 para 28`). Do not paste raw JSON/CSV content into Discord; provide paths.

## Known-good output from this rerun

The 2026-07-06 live rerun produced:

- 88 1Password DigitalTRChat users.
- 88/88 DTR logins OK.
- 226 DTR seguradores/accounts.
- 2,914 DTR/Bot pages.
- 46 SB publishers.
- 3,218 SB live Page rows.
- 2,524 SB rows for audited users.
- 2,472 OK matches.
- 468 issues: 414 `NO_SB_MATCH`, 28 `DIVERGENTE`, 26 `NO_DTR_MATCH`.
- Divergence field split: 26 `PAGE_NAME`, 2 `PAGE_ID + SEGURADOR`.
- 1 duplicate: `disparoscliquet@gmail.com`, `FB_PAGE_ID=696521396874142`, Eva Ontiveros, DTR PAGE_IDs `4962` and `5210` under different seguradores.

Generated artifacts:

- `/root/mgs-agent/reports/dtr-sb-id-audit-all-1p-20260705-232615.json`
- `/root/mgs-agent/reports/dtr-sb-id-audit-all-1p-issues-20260705-232615.csv`

These counts are a session result, not a future expected baseline. Always re-query live for a new report.
