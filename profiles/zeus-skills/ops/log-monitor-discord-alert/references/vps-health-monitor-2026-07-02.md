# VPS Health Monitor — MGS pattern (2026-07-02)

## When to use

Use this pattern when Rodolfo asks for VPS-level monitoring/alerts, especially CPU/RAM/disk/inodes/load/reboot/service availability. This is different from the existing MGS operational monitors that watch Hermes agents, crons, Git auto-push, tool loops, Honcho, Yoast, etc.

## Validated implementation shape

Created a dedicated monitor:

- Script: `/root/mgs-agent/scripts/monitor-vps-health.py`
- State: `/root/mgs-agent/data/vps-health-state.json`
- Log: `/root/mgs-agent/logs/monitor-vps-health.log`
- Cron: `*/5 * * * * flock -n /var/lock/monitor_vps_health.lock /root/mgs-agent/scripts/monitor-vps-health.py --channel-id <target_channel_or_thread_id> >> /root/mgs-agent/logs/monitor-vps-health.log 2>&1`
- Default target used in the session: `1522444367292268565`

Validated checks:

- `python3 -m py_compile /root/mgs-agent/scripts/monitor-vps-health.py`
- `monitor-vps-health.py --dry-run --channel-id <target>`
- One real silent run to create state and confirm `issues=0`, without sending a test alert when VPS is healthy.
- Regenerate `/root/mgs-agent/docs/CRONS.md` with `cron-control-plane.py --write-doc`.
- Regenerate `/root/mgs-agent/data/infra-inventory.json` with `infra-discovery.sh`.
- Append an audit event / post REPORT-INFRA when tools/channel access allow it.

## Recommended thresholds

```text
Signal                  Warning             Critical
----------------------  ------------------  ------------------
Disk /                  >= 75%              >= 85%
Inodes /                >= 80%              >= 90%
RAM available           <= 1.5GB            <= 750MB
Load 15min              >= 2.0              >= 4.0
Recent reboot           uptime < 15 min     warning
MGS backups dir         >= 25GB             >= 35GB
MGS services inactive   n/a                 critical
```

Services to check by default:

- `zeus-gateway`
- `atena-gateway`
- `ares-gateway`
- `legacy-agent-gateway`
- `mgs-autocommit`

## Alerting behavior

- Silent on OK.
- Alert only on anomaly or recovery.
- Use state-file anti-spam (recommended 6h) keyed by issue.
- Mention Rodolfo only for critical alerts; warning-level alerts can be non-push unless the user requested otherwise.
- Send via Zeus Bot to a specific channel/thread when the user says “crie aqui <id>”. Interpret the ID as the target Discord channel/thread ID unless context clearly says otherwise.

## Pitfalls

- **Nunca conte pacotes a partir de linhas genéricas de `apt list --upgradable` com stderr mesclado.** O `apt` emite o warning de CLI instável e `Listing...`; um parser que só ignora a primeira linha pode reportar 2 pacotes quando existem 0. Para contagem estável, usar `apt-get -s upgrade` e contar somente linhas iniciadas por `Inst `.
- **Todo alerta/relatório VPS que exibe atualizações deve renovar o índice APT imediatamente antes do POST.** Rodar `apt-get -o Acquire::Retries=1 update -qq` com timeout e então simular o upgrade. Não fazer isso em cada ciclo silencioso de 5 minutos. Se o refresh falhar, publicar estado `indisponível` em vez de reutilizar contagem em cache como atual.
- Existing cron monitors do not necessarily cover raw VPS resource health. `monitor-service-restarts.sh` catches restart patterns but not “service inactive right now”, disk pressure, memory pressure, inode pressure, or recent reboot.
- Do not send a fake/smoke Discord alert if current health is OK unless Rodolfo explicitly asks for a test notification. Validate with dry-run + real silent state creation.
- Updating crontab/script/data/docs is infra: update `docs/CRONS.md`, `infra-inventory.json`, and REPORT-INFRA/audit before declaring completion.
- Add the new script to `cron-control-plane.py` descriptions/risk dictionaries, otherwise `docs/CRONS.md` will show “não classificado”.
