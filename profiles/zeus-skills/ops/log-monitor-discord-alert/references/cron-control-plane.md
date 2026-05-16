# Cron Control Plane — MGS pattern

Session-derived pattern for improving cron visibility without adding LLM cost.

## When to use

Use when Rodolfo asks what crons exist, whether cron infra can be improved, or when cron inventory is unclear.

## Validated approach

1. Back up root crontab before any edit:
   ```bash
   ts=$(date +%Y%m%d-%H%M%S)
   crontab -l > /root/mgs-agent/data/crontab-backup-pre-<change>-${ts}.txt
   ```
2. Remove obsolete commented `DEPRECATED` cron entries when their scripts already live under `scripts/deprecated/` and replacement is documented.
3. Create/read a deterministic inventory script instead of relying on manual summaries:
   - `/root/mgs-agent/scripts/cron-control-plane.py`
   - read-only by default
   - outputs JSON (`--json`) and Markdown (`--markdown`)
   - `--write-doc` atomically writes `/root/mgs-agent/docs/CRONS.md`
4. Add a daily cron to regenerate the document:
   ```cron
   10 8 * * * flock -n /var/lock/cron_control_plane.lock /root/mgs-agent/scripts/cron-control-plane.py --write-doc >> /root/mgs-agent/logs/cron-control-plane.log 2>&1
   ```
5. Standardize `flock -n` on all MGS root-crontab entries to prevent overlapping executions.
6. Run `infra-discovery.sh` after cron changes so `/root/mgs-agent/data/infra-inventory.json` reflects reality.
7. Append an explicit event to `/root/mgs-agent/logs/events-audit.jsonl` with artifacts and authorization context.

## Validation checklist

```bash
python3 -m py_compile /root/mgs-agent/scripts/cron-control-plane.py
/root/mgs-agent/scripts/cron-control-plane.py --json | python3 -m json.tool >/dev/null
grep -q 'Crons sem `flock`: nenhum' /root/mgs-agent/docs/CRONS.md
crontab -l | grep -q 'DEPRECATED 2026-04-26' && exit 1 || true
crontab -l | grep -c '/root/mgs-agent/scripts/'
crontab -l | grep -c 'flock -n .* /root/mgs-agent/scripts/'
```

Expected after full standardization: MGS script cron count equals MGS flock count.

## Reporting style

For Rodolfo, report as an operational before/after table:

```text
Mudança                         | Status
--------------------------------|------------------------------------------------------------
Crons deprecated comentados      | Removidos do root crontab
Cron Control Plane               | Criado: /root/mgs-agent/scripts/cron-control-plane.py
Documento de crons               | Criado: /root/mgs-agent/docs/CRONS.md
Flock em crons MGS               | Padronizado: N/N crons agora usam flock -n
Infra inventory                  | Regenerado
Audit log                        | Registrado
```

## Pitfalls

- Do not use shell heredoc inside command substitution to rewrite crontab. Use backup → intermediate file → validation → `crontab <file>`.
- Treat deletion-like cleanup crons (`cleanup-discord-threads.sh`, `housekeeping-bak-cleanup.sh`) as high-risk in the inventory even if already approved/running.
- If auto-commit is active, status may clear within seconds; verify via `git log --oneline` if `git status` is already clean.
