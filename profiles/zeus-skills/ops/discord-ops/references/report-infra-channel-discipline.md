# REPORT-INFRA channel discipline

Use this when a task modifies scripts, skills, plugin code, config, data files, cron, SOUL/AGENT, or other MGS infra and needs an infra record.

## Rule

Do not paste raw `[REPORT-INFRA]` blocks into Rodolfo's operational task thread. That thread should contain only the clean task answer.

Infra records belong in `#alerts-infra` / the dedicated infra flow. If a report was accidentally posted inline, repost the same reports to `#alerts-infra` and acknowledge only the repost status in the operational thread.

## Current helper

Use:

```bash
/root/mgs-agent/scripts/send-report-infra-embed.sh \
  --action modificada \
  --type plugin/skill \
  --path '/exact/path' \
  --reason 'why this changed' \
  --evidence 'validation, commit, hash, or HTTP 204'
```

The helper reads the `Discord Webhook - Alerts Infra Channel` item from 1Password and returns `OK: REPORT-INFRA embed enviado (HTTP 204)` on success.

## Thread response pattern

After posting to `#alerts-infra`, respond in the original operational thread with only a concise status, for example:

`Feito. Enviei os N REPORT-INFRA no #alerts-infra. Validação: webhook HTTP 204 nos N envios.`

Do not duplicate the full report body in that thread.
