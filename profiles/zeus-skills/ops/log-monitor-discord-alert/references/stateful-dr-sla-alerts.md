# Stateful disaster-recovery SLA alerts

Use the canonical collector `scripts/mgs-offsite-backup.py monitor` for read-only diagnostics and `scripts/mgs-dr-sla-alert.py` for scheduled notifications. Keep backup production, restore validation and notification state separate.

- Run the notification adapter through the profile-local `scripts/mgs-offsite-backup-monitor.sh`. The native cron API rejects absolute runner paths: register the relative wrapper filename, even when the canonical implementation lives under `/root/mgs-agent/scripts`.
- Keep the existing schedule and `no_agent=true`; deliver normal script stdout locally because the adapter posts its own structured embeds directly to `#alerts-infra`. Use that exact channel for notification transport failures too. Do not let the scheduler duplicate successful embeds into the creation thread.
- Send on the first unhealthy observation, suppress identical repeats, send changed conditions once, and publish one green recovery without mentions only after canonical predicates are healthy. A recovery of SLA predicates does not prove every application/database was materialized or that residue/headroom is safe.
- Persist a successful POST's message ID and pending transition before exact-target GET readback. Retry that GET, not the POST, when verification fails; otherwise a transport/readback failure can duplicate alerts or falsely close an incident. Preserve active state until delivery/readback succeeds.
- Test healthy silence, first failure, unchanged dedupe, changed failure, recovery-once, transport failure preservation and POST-success/GET-failure recovery against an isolated mock endpoint. Verify channel, bot authorization, payload fields and mentions. Exercise the real deployed wrapper twice and read back the exact live recovery embed.
- Reconcile the original incident's checkpoint and cleanup gate before launching another restore. A prior successful restore plus a pending destructive residue gate is not authorization for another writer or broad deletion.

Implementation: `/root/mgs-agent/scripts/mgs-dr-sla-alert.py`; tests: `/root/mgs-agent/tests/test_mgs_dr_sla_alert.py`; state: `/root/mgs-agent/data/mgs-dr-sla-alert-state.json`.
