# MGS VPS decommission + documentation cleanup (Hetzner → Hostinger, 2026-06-19)

Use this reference after a full VPS migration when Rodolfo asks whether the old VPS can be deleted and whether references should be removed from company docs.

## Decommission green-light checklist

Before telling Rodolfo an old VPS can be deleted, verify the old host is not serving production. If direct SSH from Zeus is unavailable, accept Rodolfo-provided console output only for the specific checks below and label the limitation.

Minimum checks on the old VPS console:

```bash
hostname
crontab -l
systemctl is-active zeus-gateway atena-gateway ares-gateway legacy-agent-gateway
pgrep -af 'hermes|gateway'
```

Green light only if:

- Hostname/IP match the old VPS, not the current production VPS.
- Root crontab is empty or operationally irrelevant.
- Zeus/Atena/Ares/agente legado gateways are `inactive`/disabled.
- `pgrep -af 'hermes|gateway'` returns no live Hermes/gateway processes.
- Current production VPS has been separately validated healthy.

Recommended response shape: separate `current production` from `old standby`, then state the deletion recommendation. Keep rollback/file-history risk explicit but concise.

## Documentation cleanup rule

Do **not** globally delete every old-provider reference. Split references by purpose:

```text
Reference type                         Action
─────────────────────────────────────  ─────────────────────────────────────
Operational current-state docs          Update to current production host/IP
Runbooks/checklists saying “current”     Update to current production host/IP
Pending-task database/current backlog    Update or close stale Hetzner tasks
Infra inventory/runtime data             Regenerate/update from live host
Audit logs, changelogs, imports          Preserve as history
Migration logs/backups                   Preserve unless cleanup is explicitly approved
1Password/console credentials            Archive/rename later; don't destroy during docs cleanup
```

Operational files touched in this session:

- `/root/mgs-agent/CLAUDE.md` — host line changed from old Hetzner IP to Hostinger `2.25.165.171` / `srv1767265`, while preserving the old host as decommissioned context.
- `/root/mgs-agent/data/pendencias.db.json` — infra category changed from Hetzner to Hostinger; stale Hetzner snapshot task reframed as confirmation of old VPS deletion; Mac SSH task pointed to Hostinger.
- `/root/mgs-agent/docs/PENDENCIAS.md` — regenerated from the JSON database with `scripts/pendencia-render-md.sh`.
- `/root/mgs-agent/data/infra-inventory.json` — regenerated with `scripts/infra-discovery.sh`.
- `/root/mgs-agent/logs/events-audit.jsonl` — append audit entry.
- `#alerts-infra` — post `[REPORT-INFRA]` because docs/data/infra inventory changed.

## Validation pattern

After editing current-state docs:

1. Validate JSON (`python3 -m json.tool data/pendencias.db.json`).
2. Regenerate derived docs (`./scripts/pendencia-render-md.sh`).
3. Regenerate inventory (`./scripts/infra-discovery.sh`) when infra/data changed.
4. Review diff for accidental historical deletion.
5. Append audit log.
6. Post REPORT-INFRA and ack after processing.

## Pitfall

Do not rewrite changelogs, Discord thread imports, old migration logs, or audit entries just because they mention Hetzner or the old IP. Those are historical evidence. The goal is to prevent future agents/scripts from using the old VPS as the current production host, not to erase migration history.
