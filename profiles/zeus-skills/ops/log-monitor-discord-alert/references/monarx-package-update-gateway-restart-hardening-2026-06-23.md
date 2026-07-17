# Monarx package update causing Hermes gateway restart — hardening pattern

## Trigger

Use when `monitor-service-restarts.sh` reports a Zeus/Atena/Ares/agente legado gateway restart near a package-manager maintenance window, especially Monarx on Hostinger.

Observed case: Ares restarted at Tue 2026-06-23 04:20 EDT. Root cause was the system cron `/etc/cron.d/monarx-update` running:

```bash
20 4 * * 2 root apt-get update -qq && apt-get install -y -qq monarx-agent monarx-protect monarx-protect-autodetect > /dev/null 2>&1
```

Apt upgraded `monarx-agent` and systemd/needrestart context coincided with `ares-gateway.service` receiving SIGTERM. Ares recovered, but the alert looked mysterious because the monitor only showed `ActiveEnterTimestamp` changed.

## Triage steps

1. Check the affected service window:
   - `systemctl show <svc>.service -p ActiveEnterTimestamp -p NRestarts -p Result -p MainPID`
   - `journalctl -u <svc>.service --since '<start-10m>' --until '<start+10m>' --no-pager -o short-iso`
2. Check package/update context in the same window:
   - `/var/log/apt/history.log`
   - `/var/log/apt/term.log`
   - `/var/log/dpkg.log`
   - `/var/log/syslog` for `/etc/cron.d/monarx-update`, PackageKit, needrestart, or systemctl reloads.
3. Check whether other gateways restarted. If only one gateway moved, classify as targeted/side-effect; if all moved, look for planned MGS finalizer or update job.
4. Verify current health: Zeus/Atena/Ares/agente legado/mgs-autocommit active and no restart loop.

## Hardening pattern

### 1. Classify external cron as known maintenance

Document `/etc/cron.d/monarx-update` as an external/system cron in `docs/CRONS.md` and make `cron-control-plane.py` preserve it across regeneration. It is not in root crontab, so a root-only cron inventory misses it.

### 2. Protect Hermes gateways from package-manager auto-restarts

Create `/etc/needrestart/conf.d/mgs-hermes-gateways.conf`:

```perl
# MGS Digital Corp — protect Hermes Discord gateways from package-manager auto-restarts.
# Package maintenance may update OS/security packages, but Zeus/Atena/Ares/agente legado gateways
# should restart only via /root/mgs-agent/scripts/mgs-gateway-restart-safe.sh or explicit operator action.

$nrconf{override_rc}->{qr(^zeus-gateway\.service$)} = 0;
$nrconf{override_rc}->{qr(^atena-gateway\.service$)} = 0;
$nrconf{override_rc}->{qr(^ares-gateway\.service$)} = 0;
$nrconf{override_rc}->{qr(^legacy-agent-gateway\.service$)} = 0;
```

Validate:

```bash
perl -c /etc/needrestart/conf.d/mgs-hermes-gateways.conf
needrestart -r l -b 2>/tmp/needrestart.err | grep -E 'zeus-gateway|atena-gateway|ares-gateway|legacy-agent-gateway' || echo 'OK no Hermes gateways listed'
```

### 3. Enrich service restart alerts with cause inference

Patch `monitor-service-restarts.sh` so when `ActiveEnterTimestamp` changes it inspects a small journal window around the new start. If it sees `monarx-agent`, `monarx-update`, or `apt-get install.*monarx`, include a `Causa provável` field in the Discord embed:

```text
Monarx weekly package update (/etc/cron.d/monarx-update) detectado na janela do restart. Classificar como manutenção conhecida se ocorrer terça 04:20 EDT.
```

Fallbacks:
- package/needrestart evidence → `Atualização de pacote/needrestart detectada...`
- no evidence → `Causa não identificada automaticamente; investigar journal...`

## Validation checklist before reporting done

- `bash -n /root/mgs-agent/scripts/monitor-service-restarts.sh`
- `python3 -m py_compile /root/mgs-agent/scripts/cron-control-plane.py` if edited
- `perl -c /etc/needrestart/conf.d/mgs-hermes-gateways.conf`
- `python3 -m json.tool /root/mgs-agent/data/infra-inventory.json`
- `MGS_DRY_RUN=1 MGS_SERVICE_RESTART_STATE_FILE=/tmp/service-restart-test-state.json MGS_SERVICE_RESTART_LOG_DIR=/tmp/service-restart-test-logs /root/mgs-agent/scripts/monitor-service-restarts.sh`
- confirmar estaticamente que `monitor-service-restarts.sh` não contém `op item get`; o envio real usa o bot Zeus via API Discord
- `systemctl is-active zeus-gateway.service atena-gateway.service ares-gateway.service legacy-agent-gateway.service mgs-autocommit.service`
- `needrestart -r l -b` does not list Hermes gateways

## Reporting

This changes infra/config/data/docs. Before final response:

- update `data/infra-inventory.json`
- append `events-audit.jsonl`
- post `[REPORT-INFRA]` and then ack `✅ Registrado. Inventário atualizado.`
- clearly state whether any gateway was restarted. In this hardening pattern, no gateway restart is required.
