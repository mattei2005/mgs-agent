# Discord mobile table + REPORT-INFRA pitfalls — Ares Meta crons

Context: Rodolfo corrected two operational issues during Ares Meta cron maintenance:

1. A `[REPORT-INFRA]` was posted with the thread-creating helper, opening an unwanted thread in the infra/alerts channel.
2. The intraday table rendered badly in Discord because it was too wide and got split into multiple parts (`Parte 1 de 3`, `Parte 2 de 3`, etc.).

## Lessons

### REPORT-INFRA must not create threads

For Ares REPORT-INFRA messages, use the webhook helper:

```bash
/root/mgs-agent/scripts/ares-report-infra.sh
```

Do **not** use:

```bash
/root/mgs-agent/scripts/ares-discord-post-with-thread.py
```

unless posting into an already-approved existing operation thread with `--thread-id`. REPORT-INFRA belongs as a plain channel message, not a new thread.

Validation pattern:

```bash
printf '[REPORT-INFRA] test\n' | /root/mgs-agent/scripts/ares-report-infra.sh --dry-run
```

### Mobile-first tables for Discord

Avoid wide rows in cron messages. Discord mobile will make them unreadable, and the chunker may split the table into parts.

Prefer compact display-only columns while preserving full raw data in audit JSON.

```text
Bad display                          Better display
------------------------------------ -----------------
REC-20260622-1742-001                REC001
Elena Santana - ES - ESP - 013       Elena ES ESP 013
Ação sugerida                        Ação
Learning <3d; regra acionou (...)    Learning<3d; R2
```

Recommended output target for normal intraday checkpoint:

```text
REC    | Campanha         | PG       | Início     | Spend | MO | CPMO | Ação     | Motivo          | Status
-------|------------------|----------|------------|-------|----|------|----------|-----------------|-------
REC001 | Elena ES ESP 013 | pg_22091 | 20/06/2026 | 14.41 | 4  | 3.6  | OBSERVAR | Learning<3d; R2 | ACTIVE
```

## Validation before enabling/posting

- `python3 -m py_compile /root/mgs-agent/scripts/ares-meta-cron-runner.py`
- Run the runner to a temp file.
- Dry-run through `/root/mgs-agent/scripts/ares-discord-post-with-thread.py --dry-run --thread-id <operation-thread-id>`.
- Confirm `chunks=1` for normal checkpoint messages where feasible.
- Confirm no Meta write occurred; formatting changes do not need campaign/budget write approval.
