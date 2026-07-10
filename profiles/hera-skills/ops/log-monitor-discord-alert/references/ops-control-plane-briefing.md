# MGS Ops Control Plane + Manual Briefing Pattern

Use this pattern when Rodolfo asks for an executive view of MGS operations before enabling new scheduled alerts.

## Validated approach

1. Start with a read-only collector script that aggregates live operational state:
   - systemd services for Zeus/Atena/Ares and supporting services
   - `systemctl --failed`
   - crons/stale-log state
   - pending approvals and pending REPORT-INFRA state
   - git status/head/recent commits
   - disk usage
   - recent agent `errors.log` tails, labeled as observations rather than blockers
2. Provide both human text and `--json` output so later automation can reuse the same source of truth.
3. Add a separate manual briefing renderer that consumes the JSON and emits Discord-safe Markdown using monospaced aligned tables.
4. Keep the first briefing mode manual/on-demand. Do not schedule a cron immediately; let Rodolfo review the signal/noise for 1–2 days before activating delivery.
5. If the user gates an agent (e.g. “leave Atena last”), exclude it explicitly and print the scope in the report. If the user later corrects that gate, include it and validate scope in JSON and text.

## Local runtime artifact rule

Briefing outputs such as `data/*-latest.md` and `data/*-latest.json` are runtime snapshots, not canonical inventory. Add them to `.gitignore` before repeated runs. If the auto-commit watcher already tracked them, remove from git tracking with:

```bash
git -C /root/mgs-agent rm --cached data/<snapshot>.md data/<snapshot>.json
```

Keep the files on disk for operational use, but avoid versioning their churn.

## Reporting shape

Use three sections:

```text
Service         Sinal  Detalhe
--------------  -----  --------------------------
zeus-gateway    OK     active | r=0 | pid=...
atena-gateway   OK     active | r=0 | pid=...
ares-gateway    OK     active | r=0 | pid=...
mgs-autocommit  OK     active | r=0 | pid=...
```

```text
Área          Sinal    Detalhe
------------  -------  -------------------------
Crons         OK       jobs=19 stale=0
Autorizações  OK       pendentes=0
REPORT-INFRA  OK       pendentes=0
Git dirty     OK       branch=main head=...
Disco         OK       51% usado
```

```text
Agente  Sinal  Observação
------  -----  ---------------------------------
zeus    OBS    N achado(s) no tail de errors.log
atena   OBS    N achado(s) no tail de errors.log
ares    OBS    N achado(s) no tail de errors.log
```

`errors.log` findings are `OBS`, not automatic incidents, unless correlated with active failed services, stale jobs, repeated restarts, or current user impact.
