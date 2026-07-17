# Hermes controlled update — report delivery and backup/live comparison hardening (2026-06-15)

## Trigger

Use this note for MGS Hermes updates, especially when Rodolfo asks whether the promised backup/patch/config comparison was actually performed.

## What went wrong

During two controlled Hermes updates, the workflow created backups, snapshots, patch guard logs, py_compile evidence and gateway status, but it did **not** fully execute the promised post-update comparison against the backup before reporting success. Zeus also restarted its own gateway and initially failed to deliver a clean final report without Rodolfo prompting again with screenshots.

Rodolfo classified this as inadmissible. The operational lesson is durable:

> An update is not complete merely because `HEAD == origin/main`, patch guard passed, and gateways are active. It is complete only after the final report is delivered and the MGS critical surface has been compared to the backup/pre-state.

## Required behavior for future updates

For every Hermes update, the final workflow must produce and report these classes of evidence:

1. **Backup created before mutation**
   - Full profile backup path and size.
   - Backup must not be committed to Git.

2. **Pre-update snapshot**
   - Hermes HEAD/origin/behind.
   - Local diff/status and untracked files.
   - Sanitized profile config/auth surface.
   - Gateway/systemd and cron snapshots.
   - Patch dry-run against upstream.

3. **Fail-closed patch policy**
   - If canonical MGS patches drift against upstream, stop before mutation unless `ALLOW_PATCH_DRIFT=1` is explicitly justified after manual review/port.
   - Do not silently continue just because invariants appear present.

4. **Post-update MGS surface comparison**
   - Compare live `config.yaml`, `SOUL.md`, and sanitized `auth.json` for Zeus/Atena/Ares/agente legado against the pre-update backup.
   - Validate profile provider/model/auth presence without printing secrets.
   - Validate MGS invariants in Hermes files after patch guard.
   - Record explicit artifacts such as:
     - `post-profiles-sanitized.txt`
     - `post-backup-live-profile-compare.txt`
     - `post-readonly-invariants.txt`

5. **Runtime validation**
   - `py_compile` of critical files.
   - Patch guard final result.
   - Gateway active/running status after restart if restart was requested.

6. **Report delivery independent of Zeus session survival**
   - Write `final-report.md` before any gateway restart.
   - Send the report directly to the Discord update thread from the script/finalizer when possible.
   - If Zeus returns via checkpoint/recovery, the first response must read the latest report and confirm/deliver it, not re-run side effects.

## Backup/live comparison scope

Minimum profile files:

```text
/root/.hermes/profiles/zeus/config.yaml
/root/.hermes/profiles/zeus/SOUL.md
/root/.hermes/profiles/zeus/auth.json   # sanitized comparison only
/root/.hermes/profiles/atena/config.yaml
/root/.hermes/profiles/atena/SOUL.md
/root/.hermes/profiles/atena/auth.json  # sanitized comparison only
/root/.hermes/profiles/ares/config.yaml
/root/.hermes/profiles/ares/SOUL.md
/root/.hermes/profiles/ares/auth.json   # sanitized comparison only
/root/.hermes/profiles/legacy-agent/config.yaml
/root/.hermes/profiles/legacy-agent/SOUL.md
/root/.hermes/profiles/legacy-agent/auth.json   # sanitized comparison only
```

For `auth.json`, compare sanitized structure only: active provider, provider keys, auth mode, and token presence/length booleans. Never print access tokens, refresh tokens, passwords, API keys, bot tokens, application passwords, or raw credential values.

## Reporting standard

When Rodolfo asks whether the comparison was done, answer directly:

```text
Na hora: sim/não/parcial.
Agora: verificado ou pendente.
Resultado: OK / drift encontrado / bloqueado.
Evidência: report dir + artifact names.
```

Do not overclaim. If a comparison was performed retroactively, label it as retroactive. If a step was missing from the original flow, say so explicitly and patch the workflow before claiming future updates are safe.

## Discord UX lesson

Do not allow update threads to become a stream of raw tool traces as the primary user-visible output. For long/restart-bearing updates, prefer a background/finalizer pattern and post one clean executive report. Raw logs belong in artifacts; the Discord message should summarize status, changed files, drift/corrections, gateway state, and where evidence lives.
