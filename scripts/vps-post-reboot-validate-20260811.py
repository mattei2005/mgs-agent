#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

BASE = Path("/root/mgs-agent")
BACKUP = Path("/root/.hermes/secure-backups/vps-maintenance/20260810T235019-0400")
PRE_PATH = BACKUP / "pre-state.json"
TX_PATH = BACKUP / "apt-transaction.json"
RESULT_PATH = BACKUP / "post-reboot-validation.json"
LOG_PATH = BACKUP / "post-reboot-validator.log"
INVENTORY = BASE / "data/infra-inventory.json"
AUDIT = BASE / "logs/events-audit.jsonl"
UNIT = Path("/etc/systemd/system/mgs-vps-post-reboot-20260811.service")
THREAD_ID = "1536567182824308839"
AUTH_MESSAGE_ID = "1536581988322906142"
EXPECTED_KERNEL = "6.8.0-137-generic"
REPORT_CHANNEL = "1498132022634483894"
DISCORD_POST = BASE / "scripts/discord-bot-post.py"
REPORT_HELPER = BASE / "scripts/send-report-infra-embed.sh"
READY_HELPER = BASE / "scripts/check-gateway-ready.py"


def now_et() -> str:
    return datetime.now(ZoneInfo("America/New_York")).isoformat(timespec="seconds")


def log(message: str) -> None:
    line = f"[{now_et()}] {message}\n"
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())


def run(args: list[str], *, timeout: int = 120, check: bool = False) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if check and result.returncode != 0:
        raise RuntimeError(f"command failed rc={result.returncode}: {args[0]}")
    return result


def atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_name, mode)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def service_state(unit: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for prop in ("ActiveState", "SubState", "MainPID", "NRestarts", "ExecMainStatus"):
        value = run(["systemctl", "show", "-p", prop, "--value", unit]).stdout.strip()
        result[prop] = int(value or "0") if prop in {"MainPID", "NRestarts", "ExecMainStatus"} else value
    return result


def validate_gateway(name: str, offset: int) -> dict[str, Any]:
    unit = f"{name}-gateway.service"
    agent_log = f"/root/.hermes/profiles/{name}/logs/agent.log"
    result = run(
        [
            str(READY_HELPER),
            "--service", unit,
            "--log", agent_log,
            "--offset", str(offset),
            "--timeout", "180" if name == "zeus" else "120",
            "--poll", "2",
        ],
        timeout=200 if name == "zeus" else 140,
    )
    try:
        payload = json.loads(result.stdout or "{}")
    except Exception:
        payload = {"reason": "invalid_readiness_json"}
    payload["ok"] = result.returncode == 0
    return payload


def refresh_apt() -> tuple[bool, str]:
    last = ""
    for attempt in range(1, 4):
        result = run(["apt-get", "update"], timeout=240)
        last = (result.stdout + result.stderr)[-2000:]
        if result.returncode == 0:
            return True, f"attempt={attempt}"
        time.sleep(15)
    return False, last[-500:]


def apt_candidates() -> list[str]:
    result = run(["apt", "list", "--upgradable"], timeout=120)
    return [line for line in result.stdout.splitlines() if "/" in line and not line.startswith("Listing")]


def post_thread(content: str) -> dict[str, object]:
    payload = json.dumps({"content": content}, ensure_ascii=False)
    result = subprocess.run(
        [str(DISCORD_POST), "--channel-id", THREAD_ID],
        input=payload,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return {"ok": result.returncode == 0, "receipt": (result.stdout or result.stderr).strip()[:300]}


def send_report(overall: bool, evidence: str) -> dict[str, object]:
    result = run(
        [
            str(REPORT_HELPER),
            "--action", "modificada",
            "--type", "pacotes/kernel/reboot/script/data",
            "--path", "/usr (17 pacotes); kernel 6.8.0-137; /root/mgs-agent/scripts/vps-post-reboot-validate-20260811.py; /root/mgs-agent/data/infra-inventory.json; checkpoint vps-maintenance-20260811",
            "--reason", "Atualização controlada da VPS autorizada por Rodolfo, reboot para carregar kernel 137 e validação pós-boot durável; Hermes permaneceu fora do escopo.",
            "--evidence", evidence[:1000],
            "--color", "3066993" if overall else "15158332",
        ],
        timeout=60,
    )
    return {"ok": result.returncode == 0, "receipt": (result.stdout or result.stderr).strip()[:400]}


def update_inventory(result: dict[str, Any]) -> None:
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    maintenance = {
        "authorization_message_id": AUTH_MESSAGE_ID,
        "source_thread_id": THREAD_ID,
        "backup": str(BACKUP),
        "result": str(RESULT_PATH),
        "packages_updated": 17,
        "kernel": result["kernel"],
        "overall": "PASS" if result["overall"] else "FAIL",
        "esm_apps_residual": result.get("esm_apps_residual", 0),
        "hermes_unchanged": result["checks"].get("hermes_unchanged", False),
        "validated_at": result["validated_at"],
    }
    found_vps = False
    found_monarx = False
    for item in inventory.get("runtime_artifacts", []):
        if item.get("id") == "vps-maintenance-20260802":
            item["latest_maintenance_20260811"] = maintenance
            item["updated_at"] = result["validated_at"]
            found_vps = True
        if item.get("id") == "vps-monarx-update-20260719":
            item["latest_update_20260811"] = {
                "version_before": "4.3.54-master",
                "version_after": "4.3.56-master",
                "service": result["services"].get("monarx-agent.service", {}),
                "overall": "PASS" if result["checks"].get("packages_exact") and result["checks"].get("services_active") else "FAIL",
                "validated_at": result["validated_at"],
            }
            item["updated_at"] = result["validated_at"]
            found_monarx = True
    if not found_vps or not found_monarx:
        raise RuntimeError(f"inventory targets missing vps={found_vps} monarx={found_monarx}")
    inventory["updated_at"] = result["validated_at"]
    atomic_json(INVENTORY, inventory)


def append_audit(event: str, detail: dict[str, object]) -> None:
    record = {
        "ts": now_et(),
        "agent": "zeus",
        "event": event,
        "requested_by": "Rodolfo Mattei",
        "authorization_message_id": AUTH_MESSAGE_ID,
        "source_thread_id": THREAD_ID,
        **detail,
    }
    with AUDIT.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def update_checkpoint(result: dict[str, Any]) -> dict[str, object]:
    state = "PASS: VPS atualizada e reboot validado" if result["overall"] else "FAIL: " + str(result["first_failure"])
    next_step = "Nenhum; manutenção encerrada. ESM Apps permanece decisão separada." if result["overall"] else "Investigar o gate pós-boot indicado no resultado."
    proc = run(
        [
            str(BASE / "scripts/mgs-knowledge-control.py"),
            "checkpoint-upsert",
            "--id", "vps-maintenance-20260811",
            "--agent", "zeus",
            "--thread-id", THREAD_ID,
            "--objective", "Atualizar 17 pacotes da VPS, rebootar para kernel 6.8.0-137 e validar pós-boot",
            "--state", state,
            "--next-step", next_step,
            "--source", f"discord:{THREAD_ID}#{AUTH_MESSAGE_ID}",
        ],
        timeout=60,
    )
    return {"ok": proc.returncode == 0, "receipt": (proc.stdout or proc.stderr).strip()[:300]}


def cleanup_unit() -> None:
    run(["systemctl", "disable", UNIT.name], timeout=30)
    try:
        UNIT.unlink()
    except FileNotFoundError:
        pass
    run(["systemctl", "daemon-reload"], timeout=30)


def main() -> int:
    log("START durable post-reboot validation")
    pre = json.loads(PRE_PATH.read_text(encoding="utf-8"))
    tx = json.loads(TX_PATH.read_text(encoding="utf-8"))["packages"]
    current_boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    kernel = run(["uname", "-r"], check=True).stdout.strip()

    gateways: dict[str, Any] = {}
    for name in ("ares", "atena", "zeus"):
        gateways[name] = validate_gateway(name, int(pre["agent_log_offsets"].get(name, 0)))

    services = {
        unit: service_state(unit)
        for unit in (
            "ares-gateway.service", "atena-gateway.service", "zeus-gateway.service",
            "monarx-agent.service", "qemu-guest-agent.service", "cron.service", "mgs-autocommit.service",
        )
    }
    apt_refresh_ok, apt_refresh_detail = refresh_apt()
    candidates = apt_candidates() if apt_refresh_ok else ["apt_refresh_failed"]
    versions: dict[str, str] = {}
    package_errors: list[dict[str, str]] = []
    for row in tx:
        actual = run(["dpkg-query", "-W", "-f=${Version}", row["package"]]).stdout.strip()
        versions[row["package"]] = actual
        if actual != row["candidate"]:
            package_errors.append({"package": row["package"], "actual": actual, "expected": row["candidate"]})

    tmp_stat = Path("/tmp").stat()
    tmp_ok = tmp_stat.st_uid == 0 and tmp_stat.st_gid == 0 and (tmp_stat.st_mode & 0o7777) == 0o1777
    failed_units = [line for line in run(["systemctl", "--failed", "--no-legend"]).stdout.splitlines() if line.strip()]
    holds = [line for line in run(["apt-mark", "showhold"]).stdout.splitlines() if line.strip()]
    dpkg_audit = run(["dpkg", "--audit"]).stdout.strip()
    journal_errors = [
        line for line in run(["journalctl", "-b", "-p", "0..3", "--no-pager", "-q"], timeout=120).stdout.splitlines()
        if line.strip() and line.strip() != "-- No entries --"
    ]
    needrestart = run(["needrestart", "-b"], timeout=120).stdout
    kcur = next((line.split(":", 1)[1].strip() for line in needrestart.splitlines() if line.startswith("NEEDRESTART-KCUR:")), "")
    kexp = next((line.split(":", 1)[1].strip() for line in needrestart.splitlines() if line.startswith("NEEDRESTART-KEXP:")), "")
    launcher = run(["readlink", "-f", "/root/.local/bin/hermes"], check=True).stdout.strip()
    head = run(["git", "-C", pre["hermes_repo"], "rev-parse", "HEAD"], check=True).stdout.strip()

    esm_apps = 0
    pro = run(["pro", "security-status", "--format", "json"], timeout=180)
    if pro.returncode == 0:
        try:
            esm_apps = int(json.loads(pro.stdout).get("summary", {}).get("num_esm_apps_updates", 0))
        except Exception:
            esm_apps = -1

    checks = {
        "boot_changed": current_boot != pre["boot_id"],
        "kernel_expected": kernel == EXPECTED_KERNEL,
        "reboot_marker_absent": not Path("/var/run/reboot-required").exists(),
        "packages_exact": not package_errors,
        "apt_refresh": apt_refresh_ok,
        "apt_candidates_zero": not candidates,
        "holds_zero": not holds,
        "dpkg_audit_clean": not dpkg_audit,
        "failed_units_zero": not failed_units,
        "journal_priority_0_3_zero": not journal_errors,
        "tmp_root_1777": tmp_ok,
        "kernel_needrestart_agrees": kcur == EXPECTED_KERNEL and kexp == EXPECTED_KERNEL,
        "services_active": all(s["ActiveState"] == "active" and int(s["MainPID"]) > 0 for s in services.values()),
        "gateways_discord_ready": all(bool(g.get("ok")) for g in gateways.values()),
        "hermes_unchanged": launcher == pre["hermes_launcher"] and head == pre["hermes_head"],
    }
    first_failure = next((name for name, ok in checks.items() if not ok), "")
    result: dict[str, Any] = {
        "validated_at": now_et(),
        "overall": all(checks.values()),
        "first_failure": first_failure,
        "authorization_message_id": AUTH_MESSAGE_ID,
        "source_thread_id": THREAD_ID,
        "backup": str(BACKUP),
        "boot_id_before": pre["boot_id"],
        "boot_id_after": current_boot,
        "kernel": kernel,
        "checks": checks,
        "packages": versions,
        "package_errors": package_errors,
        "apt_refresh": apt_refresh_detail,
        "apt_candidates": candidates,
        "holds": holds,
        "dpkg_audit": dpkg_audit,
        "failed_units": failed_units,
        "journal_priority_0_3_count": len(journal_errors),
        "journal_priority_0_3_tail": journal_errors[-10:],
        "needrestart_kernel_current": kcur,
        "needrestart_kernel_expected": kexp,
        "gateways": gateways,
        "services": services,
        "hermes_launcher": launcher,
        "hermes_head": head,
        "esm_apps_residual": esm_apps,
    }
    atomic_json(RESULT_PATH, result)
    append_audit("vps_maintenance_post_reboot_validation", {
        "overall": result["overall"],
        "first_failure": first_failure,
        "kernel": kernel,
        "packages_exact": checks["packages_exact"],
        "apt_candidates": len(candidates),
        "esm_apps_residual": esm_apps,
        "result_path": str(RESULT_PATH),
    })

    governance_errors: list[str] = []
    try:
        update_inventory(result)
    except Exception as exc:
        governance_errors.append("inventory:" + type(exc).__name__)
    checkpoint = update_checkpoint(result)
    if not checkpoint["ok"]:
        governance_errors.append("checkpoint")

    evidence = (
        f"overall={'PASS' if result['overall'] else 'FAIL'}; kernel={kernel}; boot_changed={checks['boot_changed']}; "
        f"17/17 pacotes={checks['packages_exact']}; apt_pending={len(candidates)}; holds={len(holds)}; "
        f"dpkg_clean={checks['dpkg_audit_clean']}; failed_units={len(failed_units)}; journal_p0_3={len(journal_errors)}; "
        f"gateways_ready={checks['gateways_discord_ready']}; Hermes_unchanged={checks['hermes_unchanged']}; "
        f"ESM_Apps_residual={esm_apps}; backup={BACKUP}; result={RESULT_PATH}."
    )
    report = send_report(bool(result["overall"] and not governance_errors), evidence)
    if not report["ok"]:
        governance_errors.append("report_infra")

    if result["overall"] and not governance_errors:
        content = (
            "Sim, VPS concluída e validada.\n\n"
            f"- Kernel ativo: `{kernel}`; reboot marker removido.\n"
            "- 17/17 pacotes nas versões autorizadas; APT pendente 0, holds 0 e dpkg limpo.\n"
            "- Zeus, Atena, Ares, Monarx, QEMU, cron e auto-commit ativos.\n"
            "- Hermes permaneceu no mesmo launcher e commit.\n"
            f"- Residual separado: {esm_apps} correções ESM Apps exigem decisão sobre Ubuntu Pro.\n"
            f"- REPORT-INFRA: {report['receipt']}"
        )
    else:
        pending = first_failure or ",".join(governance_errors) or "validação desconhecida"
        content = (
            f"Não, a manutenção da VPS ainda tem uma pendência: `{pending}`.\n\n"
            f"Kernel observado: `{kernel}`. Pacotes divergentes: {len(package_errors)}. "
            f"APT pendente: {len(candidates)}. Failed units: {len(failed_units)}. "
            f"Resultado preservado em `{RESULT_PATH}`."
        )
    thread_post = post_thread(content)
    result["governance_errors"] = governance_errors
    result["report_infra"] = report
    result["thread_post"] = thread_post
    atomic_json(RESULT_PATH, result)

    try:
        cleanup_unit()
    except Exception as exc:
        log("WARN unit cleanup failed: " + type(exc).__name__)
    log(f"DONE overall={result['overall']} governance_errors={governance_errors}")
    return 0 if result["overall"] and not governance_errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
