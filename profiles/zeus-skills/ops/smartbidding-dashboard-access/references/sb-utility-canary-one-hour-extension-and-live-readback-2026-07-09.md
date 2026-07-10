# SB Utility canary — live readback + temporary 1h extension (2026-07-09)

## Trigger

Rodolfo asks which of the 11 Utility canary templates are still unresolved, then asks to keep the cron running longer to try to resolve the remaining messages.

## Live readback pattern

Before answering unresolved-template status, query the live SB Broadcast Template state for the exact canary target list, not the local state file alone. Local `utility-canary-approval-state.json` is useful for history but may lag or include prior cycles.

The canary target set observed in this session:

- `Teste-CA-CC-EN-Financeadx-Varya Stonebridge-1102378912948290-22028`
- `Teste-DE-CC-DE-Newsoun-Ramona Dreher-1029582290242361-19329`
- `Teste-GB-CC-EN-Zytiva-Sabrina Ellsworth-1179604071896296-22064`
- `Teste-ES-CC-ES-Openzed-Elena Santana-990898360783030-22091`
- `Teste-MX-CC-ES-Financeadx-Carolina Cruz-1025593570646416-19333`
- `Teste-US-CAR-EN-Fincgriffin-Trust Car Offers-1033507496517692-22079`
- `Teste-US-CC-EN-Newsoun-Iona Brookfield-952051961334613-19225`
- `Teste-US-CC-ES-Newsoun-Carla Ramírez-873273395865880-13992`
- `Teste-US-JOB-ES-Spe-Maria Tisocco-177067078834007-8283`
- `Teste-ZA-CC-EN-Financeadx-Margaret Smith-699254556615476-5459`
- `Teste-AR-CC-ES-Financeadx-Teresa Camacho-1063903433472026-19337`

Known status at the time of the readback: only these two were still unresolved, both `19 verde / 1 vermelho`:

- `Teste-US-CC-EN-Newsoun-Iona Brookfield-952051961334613-19225`
- `Teste-US-JOB-ES-Spe-Maria Tisocco-177067078834007-8283`

## Temporary 1-hour extension pattern

If Rodolfo asks to run the canary cron “for one more hour”:

1. List Hermes cron jobs first. Do not assume the old temporary job ID still exists; it may already be completed/absent.
2. If no active temporary Utility canary job exists, create a new script-only Hermes cron:
   - `script`: `utility-canary-approval-loop.sh`
   - `no_agent`: `true`
   - `schedule`: `every 5m`
   - `repeat`: `12`
   - `deliver`: `discord:1522487422510694450`
   - `workdir`: `/root/mgs-agent`
3. Check safety flags before creating/running when relevant:
   - `/root/mgs-agent/data/utility-canary-loop.paused`
   - `/root/mgs-agent/data/utility-canary-loop.completed`
   - `/tmp/utility-canary-approval-loop.lock`
4. After creating/modifying the cron, update `/root/mgs-agent/data/infra-inventory.json` and append an audit event to `/root/mgs-agent/logs/events-audit.jsonl` before reporting done.

## Reporting shape

Keep the operational reply short:

- cron ID
- cadence/repeat duration
- delivery channel
- next run time
- script path
- say inventory was updated

Do not paste `[REPORT-INFRA]` into the operational thread. Follow Zeus channel policy: infra report/inventory handling happens out of the main task reply.
