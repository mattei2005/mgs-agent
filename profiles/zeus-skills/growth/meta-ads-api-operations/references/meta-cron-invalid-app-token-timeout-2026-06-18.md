# Ares Meta cron timeout / invalid app token handling — 2026-06-18

Use this reference when Ares Meta cron jobs spam `#logs-aquisicao` with timeout/error messages, especially job `Ares Meta intraday R1-R5 dry-run` or scripts under `/root/.hermes/profiles/ares/scripts/`.

## Symptom observed

Discord channel `#logs-aquisicao` (`1516887105543077949`) showed repeated messages:

```text
Cron job 'Ares Meta intraday R1-R5 dry-run' failed:
Script timed out after 120s: /root/.hermes/profiles/ares/scripts/ares-meta-intraday-cron.sh
```

Relevant jobs:

```text
aa9e01a5ec4a  Ares Meta intraday R1-R5 dry-run     every 30m
c6c737070d3f  Ares Meta reativar-todas dry-run     daily
0598c0dc469f  Ares Meta HOA gestor read-only 4d    scheduled checkpoints
```

All deliver to `discord:1516887105543077949`.

## Diagnosis pattern

1. Confirm the job metadata:

```bash
hermes -p ares cron list
# or inspect /root/.hermes/profiles/ares/cron/jobs.json
```

2. Run the script manually in read-only mode. It should not write to Meta; it only reads and writes local audit.

```bash
cd /root/mgs-agent
timeout 125 /root/.hermes/profiles/ares/scripts/ares-meta-intraday-cron.sh >/tmp/ares-cron.out 2>/tmp/ares-cron.err
```

3. If it times out, probe the token/app boundary with a direct Graph GET using the 1Password token internally only. Never print token values.

Durable observed failure:

```text
HTTP 400
OAuthException code 190
message: Error validating application. Application has been deleted.
```

Interpretation: this is not a Hostinger/VPS migration failure. The Meta app/token backing `Token Meta API` is invalid/deleted. Retrying the cron will only produce channel spam until the token is replaced.

## Immediate containment

Pause Meta cron jobs that depend on the invalid token. Do this before further debugging if they are spamming Discord:

```bash
hermes -p ares cron pause aa9e01a5ec4a
hermes -p ares cron pause c6c737070d3f
hermes -p ares cron pause 0598c0dc469f
```

Then verify:

```bash
hermes -p ares cron list
pgrep -af 'ares-meta-(cron-runner|intraday|hoa|reactivate)' || true
```

Expected safe state:

```text
jobs paused
ares-gateway active
0 hanging Meta cron processes
```

Update `paused_reason` in jobs.json if needed so future operators understand why the jobs are paused.

## Do not over-fix the wrong layer

Do not restart all agents, change Hostinger networking, or rewrite the cron runner just because the cron timed out. First determine whether Meta is returning a token/app error.

If the manual script returns quickly with the `OAuthException code 190` error, the fix is credential/app replacement, not infrastructure.

## Required next step

Rodolfo or an authorized operator must replace/update the 1Password item:

```text
Vault: MGS Conteúdo
Item: Token Meta API
Field: credential
```

with a valid token from an active Meta app.

After replacement:

1. Run read-only Graph GET probe.
2. Run `ares-meta-intraday-cron.sh` manually.
3. Confirm it exits before scheduler timeout and writes an audit.
4. Resume paused jobs one by one.
5. Watch `#logs-aquisicao` for one scheduled cycle.

## REPORT-INFRA

Changing `/root/.hermes/profiles/ares/cron/jobs.json` is cron/config infra. Send REPORT-INFRA when pausing/resuming or editing these jobs.
