#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

BASE = Path("/root/mgs-agent")
BACKUP = Path("/root/.hermes/secure-backups/vps-maintenance/20260910T194957Z-vps-new-security10")
PRE = BACKUP / "reboot-pre-state.json"
PREFLIGHT = BACKUP / "reboot-preflight.json"
RESULT = BACKUP / "post-reboot-validation.json"
LOG = BACKUP / "post-reboot-control.log"
ARTIFACT_HASHES = BACKUP / "reboot-artifacts.sha256"
ROLLBACK_HASHES = BACKUP / "sha256sum.txt"
UNIT = Path("/etc/systemd/system/mgs-vps-post-reboot-20260910.service")
UNIT_NAME = UNIT.name
CLOSE_UNIT = "mgs-vps-reboot-close-20260910"
THREAD_ID = "1547446145339490354"
PACKAGE_AUTH_ID = "1547695482942394378"
REBOOT_AUTH_ID = "1547762841384128594"
CHECKPOINT_ID = "zeus-vps-hermes-update-20260909"
EXPECTED_KERNEL = "6.8.0-139-generic"
EXPECTED_HERMES_VERSION = "Hermes Agent v0.21.1 (2026.9.7)"
EXPECTED_PACKAGES = {
    "libc-devtools": "2.39-0ubuntu8.9",
    "libc6-dev": "2.39-0ubuntu8.9",
    "libc-dev-bin": "2.39-0ubuntu8.9",
    "libc6": "2.39-0ubuntu8.9",
    "libc-bin": "2.39-0ubuntu8.9",
    "locales": "2.39-0ubuntu8.9",
    "php8.3-readline": "8.3.6-0ubuntu0.24.04.11",
    "php8.3-opcache": "8.3.6-0ubuntu0.24.04.11",
    "php8.3-cli": "8.3.6-0ubuntu0.24.04.11",
    "php8.3-common": "8.3.6-0ubuntu0.24.04.11",
}
SERVICES = (
    "ares-gateway.service",
    "atena-gateway.service",
    "zeus-gateway.service",
    "monarx-agent.service",
    "qemu-guest-agent.service",
    "cron.service",
    "mgs-autocommit.service",
)
INVENTORY = BASE / "data/infra-inventory.json"
AUDIT = BASE / "logs/events-audit.jsonl"
DISCORD_POST = BASE / "scripts/discord-bot-post.py"
REPORT_HELPER = BASE / "scripts/send-report-infra-embed.sh"
READY_HELPER = BASE / "scripts/check-gateway-ready.py"
KNOWLEDGE = BASE / "scripts/mgs-knowledge-control.py"
PATCH_GUARD = BASE / "scripts/ensure-hermes-mgs-patches.sh"
REGRESSION = BASE / "scripts/run-hermes-post-upstream-regression.sh"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def now_et() -> str:
    return datetime.now(ZoneInfo("America/New_York")).isoformat(timespec="seconds")


def log(message: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"[{now_et()}] {message}\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(LOG, 0o600)


def run(args: list[str], *, timeout: int = 120, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, env=env)


def atomic_json(path: Path, payload: object, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing_mode = path.stat().st_mode & 0o777 if path.exists() else mode
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_name, existing_mode)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def append_audit(event: str, detail: dict[str, Any]) -> None:
    record = {
        "ts": now_utc(),
        "agent": "zeus",
        "event": event,
        "requested_by": "Rodolfo Mattei",
        "package_authorization_message_id": PACKAGE_AUTH_ID,
        "reboot_authorization_message_id": REBOOT_AUTH_ID,
        "source_thread_id": THREAD_ID,
        **detail,
    }
    with AUDIT.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def service_state(unit: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for prop in ("LoadState", "ActiveState", "SubState", "MainPID", "NRestarts", "ExecMainStatus", "ExecMainStartTimestamp"):
        proc = run(["systemctl", "show", "-p", prop, "--value", unit], timeout=20)
        value = proc.stdout.strip()
        result[prop] = int(value or "0") if prop in {"MainPID", "NRestarts", "ExecMainStatus"} else value
    return result


def installed_packages() -> dict[str, str]:
    result: dict[str, str] = {}
    for package in EXPECTED_PACKAGES:
        proc = run(["dpkg-query", "-W", "-f=${Version}", package], timeout=30)
        result[package] = proc.stdout.strip() if proc.returncode == 0 else ""
    return result


def apt_simulation(action: str) -> tuple[bool, int]:
    proc = run(["apt-get", "-s", "-o", "Debug::NoLocking=1", action], timeout=240)
    count = len(re.findall(r"^Inst ", proc.stdout, re.MULTILINE))
    return proc.returncode == 0, count


def failed_units() -> list[str]:
    proc = run(["systemctl", "--failed", "--no-legend", "--plain"], timeout=30)
    return [line for line in proc.stdout.splitlines() if line.strip()]


def runtime_identity() -> dict[str, str]:
    launcher = str(Path("/root/.local/bin/hermes").resolve())
    repo = str(Path(launcher).parents[2])
    head = run(["git", "-C", repo, "rev-parse", "HEAD"], timeout=30).stdout.strip()
    version_proc = run([launcher, "--version"], timeout=60)
    version = next((line.strip() for line in version_proc.stdout.splitlines() if line.strip()), "")
    return {"launcher": launcher, "repo": repo, "head": head, "version": version}


def verify_hash_manifest(path: Path) -> bool:
    proc = run(["sha256sum", "-c", str(path)], timeout=300)
    return proc.returncode == 0


def checkpoint(state: str, next_step: str, source: str) -> dict[str, Any]:
    proc = run([
        str(KNOWLEDGE), "checkpoint-upsert",
        "--id", CHECKPOINT_ID,
        "--agent", "zeus",
        "--thread-id", THREAD_ID,
        "--objective", "Atualizar VPS e Hermes pelo plano controlado canônico, com rollback, ativação segura e validação completa",
        "--state", state,
        "--next-step", next_step,
        "--source", source,
    ], timeout=90)
    return {"ok": proc.returncode == 0, "receipt": (proc.stdout or proc.stderr).strip()[:300]}


def update_inventory(payload: dict[str, Any], status: str) -> None:
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    matched = False
    for item in inventory.get("runtime_artifacts", []):
        if item.get("id") != CHECKPOINT_ID:
            continue
        matched = True
        item["status"] = status
        item["vps_status"] = status
        item["updated_at"] = now_utc()
        item["reboot_required"] = not bool(payload.get("checks", {}).get("reboot_marker_absent"))
        item["services_pending_restart"] = 0 if payload.get("checks", {}).get("needrestart_services_zero") else item.get("services_pending_restart")
        item.setdefault("new_apt_scope", {})["reboot_authorization_message_id"] = REBOOT_AUTH_ID
        item["new_apt_scope"]["post_reboot_result"] = str(RESULT)
        item["post_reboot_validation"] = {
            "status": status,
            "validated_at": payload.get("validated_at"),
            "result": str(RESULT),
            "boot_id_before": payload.get("boot_id_before"),
            "boot_id_after": payload.get("boot_id_after"),
            "kernel": payload.get("kernel"),
            "checks_passed": sum(1 for value in payload.get("checks", {}).values() if value),
            "checks_total": len(payload.get("checks", {})),
            "first_failure": payload.get("first_failure", ""),
            "report_infra": payload.get("report_infra"),
            "thread_post": payload.get("thread_post"),
            "temporary_unit_cleanup": payload.get("temporary_unit_cleanup"),
        }
        break
    if not matched:
        raise RuntimeError("inventory target missing")
    inventory["updated_at"] = now_utc()
    atomic_json(INVENTORY, inventory, mode=0o644)


def freeze() -> int:
    runtime = runtime_identity()
    services = {unit: service_state(unit) for unit in SERVICES}
    pre = {
        "schema_version": 1,
        "created_at": now_utc(),
        "thread_id": THREAD_ID,
        "package_authorization_message_id": PACKAGE_AUTH_ID,
        "reboot_authorization_message_id": REBOOT_AUTH_ID,
        "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
        "kernel": run(["uname", "-r"], timeout=30).stdout.strip(),
        "reboot_required": Path("/var/run/reboot-required").exists(),
        "packages": installed_packages(),
        "services": services,
        "agent_log_offsets": {
            name: Path(f"/root/.hermes/profiles/{name}/logs/agent.log").stat().st_size
            for name in ("ares", "atena", "zeus")
        },
        "tmp": {
            "uid": Path("/tmp").stat().st_uid,
            "gid": Path("/tmp").stat().st_gid,
            "mode": oct(Path("/tmp").stat().st_mode & 0o7777),
        },
        "hermes": runtime,
    }
    atomic_json(PRE, pre)
    log("pre-reboot state frozen")
    return 0


def preflight(*, record: bool = True) -> tuple[bool, dict[str, Any]]:
    pre = json.loads(PRE.read_text(encoding="utf-8"))
    runtime = runtime_identity()
    packages = installed_packages()
    up_ok, up_count = apt_simulation("upgrade")
    full_ok, full_count = apt_simulation("full-upgrade")
    services = {unit: service_state(unit) for unit in SERVICES}
    unit_enabled = run(["systemctl", "is-enabled", UNIT_NAME], timeout=30)
    unit_active = run(["systemctl", "is-active", UNIT_NAME], timeout=30)
    tmp = Path("/tmp").stat()
    checks = {
        "same_boot_before_dispatch": Path("/proc/sys/kernel/random/boot_id").read_text().strip() == pre["boot_id"],
        "kernel_expected": run(["uname", "-r"], timeout=30).stdout.strip() == EXPECTED_KERNEL,
        "reboot_marker_present": Path("/var/run/reboot-required").exists(),
        "packages_exact": packages == EXPECTED_PACKAGES,
        "apt_upgrade_zero": up_ok and up_count == 0,
        "apt_full_upgrade_zero": full_ok and full_count == 0,
        "dpkg_audit_clean": not run(["dpkg", "--audit"], timeout=60).stdout.strip(),
        "holds_zero": not run(["apt-mark", "showhold"], timeout=30).stdout.strip(),
        "failed_units_zero": not failed_units(),
        "services_active": all(value["ActiveState"] == "active" and int(value["MainPID"]) > 0 for value in services.values()),
        "tmp_root_1777": tmp.st_uid == 0 and tmp.st_gid == 0 and (tmp.st_mode & 0o7777) == 0o1777,
        "hermes_frozen": runtime == pre["hermes"],
        "rollback_hashes": verify_hash_manifest(ROLLBACK_HASHES),
        "artifact_hashes": verify_hash_manifest(ARTIFACT_HASHES),
        "validator_enabled": unit_enabled.returncode == 0 and unit_enabled.stdout.strip() == "enabled",
        "validator_inactive": unit_active.stdout.strip() == "inactive",
    }
    payload = {
        "checked_at": now_utc(),
        "overall": all(checks.values()),
        "first_failure": next((name for name, ok in checks.items() if not ok), ""),
        "checks": checks,
        "packages": packages,
        "services": services,
        "runtime": runtime,
        "apt_upgrade_candidates": up_count,
        "apt_full_upgrade_candidates": full_count,
    }
    if record:
        atomic_json(PREFLIGHT, payload)
        log(f"preflight overall={payload['overall']} first_failure={payload['first_failure']}")
    return bool(payload["overall"]), payload


def dispatch() -> int:
    ok, payload = preflight(record=True)
    if not ok:
        append_audit("vps_reboot_dispatch_blocked", {"first_failure": payload["first_failure"], "preflight": str(PREFLIGHT)})
        return 1
    receipt = checkpoint(
        "reboot_dispatched_pending_post_boot_validation",
        "Aguardar reboot e validador durável; não repetir o reboot sem reconciliar o resultado",
        f"discord:thread:{THREAD_ID}#{REBOOT_AUTH_ID};preflight:{PREFLIGHT}",
    )
    if not receipt["ok"]:
        return 1
    append_audit("vps_reboot_dispatched", {
        "boot_id_before": json.loads(PRE.read_text(encoding="utf-8"))["boot_id"],
        "kernel": EXPECTED_KERNEL,
        "expected_packages": EXPECTED_PACKAGES,
        "preflight": str(PREFLIGHT),
        "validator_unit": str(UNIT),
    })
    log("reboot dispatch gate passed")
    return 0


def refresh_apt() -> tuple[bool, str]:
    last = ""
    for attempt in range(1, 4):
        proc = run(["apt-get", "update"], timeout=300)
        last = f"attempt={attempt} rc={proc.returncode}"
        if proc.returncode == 0:
            return True, last
        time.sleep(15 * attempt)
    return False, last


def gateway_ready(name: str, offset: int) -> dict[str, Any]:
    timeout = 420 if name == "zeus" else 240
    proc = run([
        str(READY_HELPER),
        "--service", f"{name}-gateway.service",
        "--log", f"/root/.hermes/profiles/{name}/logs/agent.log",
        "--offset", str(offset),
        "--timeout", str(timeout),
        "--poll", "2",
    ], timeout=timeout + 30)
    try:
        payload = json.loads(proc.stdout or "{}")
    except Exception:
        payload = {"reason": "invalid_readiness_json"}
    payload["ok"] = proc.returncode == 0 and bool(payload.get("ready"))
    return payload


def save_command_log(name: str, proc: subprocess.CompletedProcess[str]) -> None:
    path = BACKUP / name
    path.write_text((proc.stdout or "") + (proc.stderr or ""), encoding="utf-8")
    os.chmod(path, 0o600)


def validate() -> int:
    log("START post-reboot runtime validation")
    pre = json.loads(PRE.read_text(encoding="utf-8"))
    current_boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    kernel = run(["uname", "-r"], timeout=30).stdout.strip()
    gateways = {name: gateway_ready(name, int(pre["agent_log_offsets"][name])) for name in ("ares", "atena", "zeus")}
    services = {unit: service_state(unit) for unit in SERVICES}
    packages = installed_packages()
    apt_refresh_ok, apt_refresh_detail = refresh_apt()
    up_ok, up_count = apt_simulation("upgrade") if apt_refresh_ok else (False, -1)
    full_ok, full_count = apt_simulation("full-upgrade") if apt_refresh_ok else (False, -1)
    holds = run(["apt-mark", "showhold"], timeout=30).stdout.strip()
    dpkg_audit = run(["dpkg", "--audit"], timeout=60).stdout.strip()
    failures = failed_units()
    journal = run(["journalctl", "-b", "-p", "0..3", "--no-pager", "-q"], timeout=180)
    journal_errors = [line for line in journal.stdout.splitlines() if line.strip() and line.strip() != "-- No entries --"]
    need = run(["needrestart", "-b"], timeout=180).stdout
    kcur = next((line.split(":", 1)[1].strip() for line in need.splitlines() if line.startswith("NEEDRESTART-KCUR:")), "")
    kexp = next((line.split(":", 1)[1].strip() for line in need.splitlines() if line.startswith("NEEDRESTART-KEXP:")), "")
    svc_rows = [line for line in need.splitlines() if line.startswith("NEEDRESTART-SVC:")]
    tmp = Path("/tmp").stat()
    runtime = runtime_identity()

    gateway_runtime: dict[str, Any] = {}
    for name in ("ares", "atena", "zeus"):
        pid = int(services[f"{name}-gateway.service"]["MainPID"])
        exe = str(Path(f"/proc/{pid}/exe").resolve()) if pid > 0 and Path(f"/proc/{pid}/exe").exists() else ""
        gateway_runtime[name] = {"pid": pid, "exe": exe, "in_expected_runtime": exe.startswith(pre["hermes"]["repo"] + "/.venv/")}

    config_ok: dict[str, bool] = {}
    for profile in ("root", "ares", "atena", "zeus"):
        env = os.environ.copy()
        env["HERMES_HOME"] = "/root/.hermes" if profile == "root" else f"/root/.hermes/profiles/{profile}"
        proc = run([runtime["launcher"], "config", "check"], timeout=120, env=env)
        config_ok[profile] = proc.returncode == 0
        save_command_log(f"post-reboot-config-{profile}.log", proc)

    auth_ok: dict[str, bool] = {}
    for profile in ("ares", "atena", "zeus"):
        env = os.environ.copy()
        env["HERMES_HOME"] = f"/root/.hermes/profiles/{profile}"
        proc = run([runtime["launcher"], "auth", "status", "openai-codex"], timeout=120, env=env)
        low = ((proc.stdout or "") + (proc.stderr or "")).lower()
        auth_ok[profile] = proc.returncode == 0 and "logged in" in low and "migration notice" not in low
        save_command_log(f"post-reboot-auth-{profile}.log", proc)

    guard_env = os.environ.copy()
    guard_env.update({"REPO": runtime["repo"], "PYBIN": str(Path(runtime["repo"]) / ".venv/bin/python"), "LOG": str(BACKUP / "post-reboot-patch-guard.log")})
    guard = run([str(PATCH_GUARD)], timeout=1200, env=guard_env)
    save_command_log("post-reboot-patch-guard.stdout", guard)

    regression_env = os.environ.copy()
    regression_env.update({"REPO": runtime["repo"], "PYBIN": str(Path(runtime["repo"]) / ".venv/bin/python"), "LOG": str(BACKUP / "post-reboot-regression.log")})
    regression = run([str(REGRESSION)], timeout=1200, env=regression_env)
    save_command_log("post-reboot-regression.stdout", regression)

    smoke_ok: dict[str, bool] = {}
    for profile in ("ares", "atena", "zeus"):
        marker = f"MGS_POST_REBOOT_20260910_{profile.upper()}_OK"
        env = os.environ.copy()
        env["HERMES_HOME"] = f"/root/.hermes/profiles/{profile}"
        proc = run([runtime["launcher"], "-z", f"Respond exactly {marker} and nothing else."], timeout=420, env=env)
        text = (proc.stdout or "") + (proc.stderr or "")
        last = next((line.strip() for line in reversed(text.splitlines()) if line.strip()), "")
        smoke_ok[profile] = proc.returncode == 0 and text.count(marker) == 1 and last == marker
        save_command_log(f"post-reboot-smoke-{profile}.log", proc)

    git_status = run(["git", "-C", runtime["repo"], "status", "--porcelain"], timeout=60)
    checks = {
        "boot_changed": current_boot != pre["boot_id"],
        "kernel_expected": kernel == EXPECTED_KERNEL,
        "reboot_marker_absent": not Path("/var/run/reboot-required").exists(),
        "packages_exact": packages == EXPECTED_PACKAGES,
        "apt_refresh": apt_refresh_ok,
        "apt_upgrade_zero": up_ok and up_count == 0,
        "apt_full_upgrade_zero": full_ok and full_count == 0,
        "holds_zero": not holds,
        "dpkg_audit_clean": not dpkg_audit,
        "failed_units_zero": not failures,
        "journal_priority_0_3_zero": journal.returncode == 0 and not journal_errors,
        "tmp_root_1777": tmp.st_uid == 0 and tmp.st_gid == 0 and (tmp.st_mode & 0o7777) == 0o1777,
        "kernel_needrestart_agrees": kcur == EXPECTED_KERNEL and kexp == EXPECTED_KERNEL,
        "needrestart_services_zero": not svc_rows,
        "services_active": all(value["ActiveState"] == "active" and value["SubState"] == "running" and int(value["MainPID"]) > 0 for value in services.values()),
        "gateways_discord_ready": all(value.get("ok") for value in gateways.values()),
        "gateway_runtime_exact": all(value["in_expected_runtime"] for value in gateway_runtime.values()),
        "hermes_frozen": runtime == pre["hermes"] and runtime["version"].startswith(EXPECTED_HERMES_VERSION),
        "config_4_4": all(config_ok.values()),
        "auth_3_3": all(auth_ok.values()),
        "patch_guard": guard.returncode == 0,
        "regression": regression.returncode == 0,
        "smokes_3_3": all(smoke_ok.values()),
        "git_clean": git_status.returncode == 0 and not git_status.stdout.strip(),
        "rollback_hashes": verify_hash_manifest(ROLLBACK_HASHES),
        "artifact_hashes": verify_hash_manifest(ARTIFACT_HASHES),
    }
    first_failure = next((name for name, ok in checks.items() if not ok), "")
    result: dict[str, Any] = {
        "schema_version": 1,
        "validated_at": now_utc(),
        "overall_runtime": all(checks.values()),
        "overall": False,
        "first_failure": first_failure,
        "boot_id_before": pre["boot_id"],
        "boot_id_after": current_boot,
        "kernel": kernel,
        "checks": checks,
        "packages": packages,
        "apt_refresh": apt_refresh_detail,
        "apt_upgrade_candidates": up_count,
        "apt_full_upgrade_candidates": full_count,
        "holds": holds.splitlines() if holds else [],
        "dpkg_audit": dpkg_audit,
        "failed_units": failures,
        "journal_priority_0_3_count": len(journal_errors),
        "journal_priority_0_3_tail": journal_errors[-10:],
        "needrestart_kernel_current": kcur,
        "needrestart_kernel_expected": kexp,
        "needrestart_services": svc_rows,
        "services": services,
        "gateways": gateways,
        "gateway_runtime": gateway_runtime,
        "hermes": runtime,
        "configs": config_ok,
        "auth": auth_ok,
        "smokes": smoke_ok,
        "patch_guard_rc": guard.returncode,
        "regression_rc": regression.returncode,
        "temporary_unit_cleanup": {"status": "pending"},
        "report_infra": {"status": "pending"},
        "thread_post": {"status": "pending"},
    }
    atomic_json(RESULT, result)
    append_audit("vps_post_reboot_runtime_validation", {
        "status": "pass" if result["overall_runtime"] else "fail",
        "first_failure": first_failure,
        "result": str(RESULT),
        "kernel": kernel,
        "checks_passed": sum(1 for value in checks.values() if value),
        "checks_total": len(checks),
    })

    governance_errors: list[str] = []
    try:
        update_inventory(result, "validated_pending_cleanup" if result["overall_runtime"] else "failed_pending_cleanup")
    except Exception as exc:
        governance_errors.append("inventory:" + type(exc).__name__)
    cp = checkpoint(
        "validated_pending_cleanup" if result["overall_runtime"] else f"post_boot_failed:{first_failure}",
        "Executar fechamento externo, remover unidade temporária, registrar REPORT-INFRA e publicar resultado",
        str(RESULT),
    )
    if not cp["ok"]:
        governance_errors.append("checkpoint")
    disable = run(["systemctl", "disable", UNIT_NAME], timeout=60)
    if disable.returncode != 0:
        governance_errors.append("disable_validator")

    close = run([
        "systemd-run", "--quiet", f"--unit={CLOSE_UNIT}", "--on-active=10s",
        "--property=Type=oneshot", "--property=TimeoutStartSec=600",
        "/usr/bin/python3", str(Path(__file__).resolve()), "close",
    ], timeout=60)
    if close.returncode != 0:
        governance_errors.append("schedule_closure")
    result["governance_errors_before_cleanup"] = governance_errors
    result["closure_scheduled"] = close.returncode == 0
    atomic_json(RESULT, result)
    log(f"runtime validation done overall={result['overall_runtime']} first_failure={first_failure} closure_scheduled={result['closure_scheduled']}")
    return 0 if close.returncode == 0 else 1


def load_discord_token() -> str:
    env_path = Path("/root/.hermes/profiles/zeus/.env")
    for raw in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == "DISCORD_BOT_TOKEN":
            return value.strip().strip('"').strip("'")
    raise RuntimeError("discord token unavailable")


def discord_readback(channel_id: str, message_id: str, *, expected_content: str | None = None, expect_embed: bool = False) -> dict[str, Any]:
    token = load_discord_token()
    request = urllib.request.Request(
        f"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}",
        headers={"Authorization": "Bot " + token, "User-Agent": "MGS-Zeus/1.0"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        data = json.loads(response.read().decode("utf-8"))
    ok = str(data.get("id")) == message_id and str(data.get("channel_id")) == channel_id
    if expected_content is not None:
        ok = ok and data.get("content") == expected_content
    if expect_embed:
        ok = ok and data.get("content") == "" and len(data.get("embeds") or []) == 1 and not data.get("mentions") and not data.get("attachments")
    return {"ok": ok, "message_id": message_id, "channel_id": channel_id, "embed_count": len(data.get("embeds") or []), "content_empty": data.get("content") == ""}


def post_payload(channel_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    last = ""
    for attempt in range(1, 4):
        proc = subprocess.run([str(DISCORD_POST), "--channel-id", channel_id], input=json.dumps(payload, ensure_ascii=False), capture_output=True, text=True, timeout=45)
        last = (proc.stdout or proc.stderr).strip()
        match = re.search(r"message_id=(\d+)", last)
        if proc.returncode == 0 and match:
            message_id = match.group(1)
            try:
                readback = discord_readback(channel_id, message_id, expected_content=payload.get("content"))
            except Exception as exc:
                readback = {"ok": False, "error": type(exc).__name__}
            if readback.get("ok"):
                return {"ok": True, "attempt": attempt, "receipt": last, "readback": readback}
        time.sleep(5 * attempt)
    return {"ok": False, "receipt": last}


def send_report(result: dict[str, Any], cleanup_ok: bool) -> dict[str, Any]:
    checks = result.get("checks", {})
    evidence = (
        f"runtime={'PASS' if result.get('overall_runtime') else 'FAIL'}; cleanup={'PASS' if cleanup_ok else 'FAIL'}; "
        f"boot_changed={checks.get('boot_changed')}; kernel={result.get('kernel')}; pacotes_10_10={checks.get('packages_exact')}; "
        f"APT={result.get('apt_upgrade_candidates')}/{result.get('apt_full_upgrade_candidates')}; dpkg={checks.get('dpkg_audit_clean')}; "
        f"gateways={checks.get('gateways_discord_ready')}; Hermes_v0.21.1={checks.get('hermes_frozen')}; "
        f"guard={checks.get('patch_guard')}; regressao={checks.get('regression')}; auth={checks.get('auth_3_3')}; smokes={checks.get('smokes_3_3')}; result={RESULT}"
    )
    args = [
        str(REPORT_HELPER),
        "--action", "modificada",
        "--type", "pacotes/reboot/config-temporária/data",
        "--path", "/usr (10 pacotes); reboot da VPS; /etc/systemd/system/mgs-vps-post-reboot-20260910.service (criada e removida); /root/mgs-agent/data/{infra-inventory.json,agent-checkpoints.json}",
        "--reason", "Fechamento da atualização VPS + Hermes autorizada por Rodolfo, com reboot exigido pelo libc6 e validação pós-boot durável.",
        "--evidence", evidence[:1000],
        "--color", "3066993" if result.get("overall_runtime") and cleanup_ok else "15158332",
    ]
    last = ""
    for attempt in range(1, 4):
        proc = run(args, timeout=90)
        last = (proc.stdout or proc.stderr).strip()
        match = re.search(r"message_id=(\d+)", last)
        if proc.returncode == 0 and match:
            message_id = match.group(1)
            try:
                readback = discord_readback("1498132022634483894", message_id, expect_embed=True)
            except Exception as exc:
                readback = {"ok": False, "error": type(exc).__name__}
            if readback.get("ok"):
                return {"ok": True, "attempt": attempt, "receipt": last, "readback": readback}
        time.sleep(5 * attempt)
    return {"ok": False, "receipt": last}


def final_message(result: dict[str, Any], all_ok: bool) -> str:
    checks = result.get("checks", {})
    if all_ok:
        return (
            "**Resultado:** 100% concluído e validado.\n\n"
            "**VPS:** reboot concluído em novo boot; kernel `6.8.0-139-generic`; 10/10 pacotes nas versões autorizadas; APT `0`, dpkg/holds/failed units limpos.\n"
            "**Hermes:** v0.21.1 ativo; Zeus, Atena e Ares reconectados; configs `4/4`, OAuth independente `3/3`, smokes `3/3`, patch guard e regressão aprovados após o reboot.\n"
            "**Benefícios da atualização:** melhorias de confiabilidade e manutenção da v0.21.1 estão ativas; patches MGS e OAuths independentes foram preservados.\n"
            f"**Backups:** rollback validado e preservado em `{BACKUP}`; o backup parcial de 9,87 GB também foi preservado, conforme o escopo sem exclusões.\n"
            "**Limpeza:** unidade temporária de validação removida; nenhuma exclusão de backup executada.\n"
            "**Serviços:** Zeus, Atena, Ares, Monarx, QEMU, cron e auto-commit ativos.\n"
            "**Pendência:** nenhuma para a atualização.\n"
            f"**Evidência:** `{RESULT}`; REPORT-INFRA validado por readback."
        )
    failure = result.get("first_failure") or ",".join(result.get("governance_errors", [])) or "fechamento_desconhecido"
    return (
        f"**Resultado:** não, a atualização ainda tem uma pendência: `{failure}`.\n\n"
        f"**VPS:** kernel observado `{result.get('kernel', 'desconhecido')}`; APT pendente `{result.get('apt_upgrade_candidates', '?')}`.\n"
        f"**Hermes:** v0.21.1 detectado `{checks.get('hermes_frozen')}`; gateways prontos `{checks.get('gateways_discord_ready')}`.\n"
        "**Benefícios da atualização:** não declarados como integralmente ativos enquanto existir gate vermelho.\n"
        f"**Backups:** preservados em `{BACKUP}`.\n"
        "**Limpeza:** nenhuma exclusão de backup executada.\n"
        "**Serviços:** consultar o primeiro gate vermelho no resultado durável.\n"
        f"**Pendência:** `{failure}`.\n"
        f"**Evidência:** `{RESULT}`."
    )


def close() -> int:
    log("START post-reboot governance closure")
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    cleanup_errors: list[str] = []
    run(["systemctl", "disable", UNIT_NAME], timeout=60)
    try:
        UNIT.unlink(missing_ok=True)
    except Exception as exc:
        cleanup_errors.append("unlink_unit:" + type(exc).__name__)
    reload_proc = run(["systemctl", "daemon-reload"], timeout=60)
    reset_proc = run(["systemctl", "reset-failed"], timeout=60)
    time.sleep(2)
    load_state = run(["systemctl", "show", "-p", "LoadState", "--value", UNIT_NAME], timeout=30).stdout.strip()
    active_state = run(["systemctl", "is-active", UNIT_NAME], timeout=30).stdout.strip()
    remaining_failed = failed_units()
    cleanup_ok = reload_proc.returncode == 0 and reset_proc.returncode == 0 and load_state == "not-found" and active_state == "inactive" and not remaining_failed and not cleanup_errors
    result["temporary_unit_cleanup"] = {
        "status": "cleaned_after_validation" if cleanup_ok else "failed",
        "load_state": load_state,
        "active_state": active_state,
        "failed_units": remaining_failed,
        "errors": cleanup_errors,
    }

    governance_errors = list(result.get("governance_errors_before_cleanup", []))
    if not cleanup_ok:
        governance_errors.append("unit_cleanup")
    preliminary_ok = bool(result.get("overall_runtime")) and cleanup_ok and not governance_errors
    result["overall"] = preliminary_ok
    result["governance_errors"] = governance_errors
    atomic_json(RESULT, result)

    try:
        update_inventory(result, "completed_validated" if preliminary_ok else "post_reboot_failed")
    except Exception as exc:
        governance_errors.append("inventory_final:" + type(exc).__name__)
    cp = checkpoint(
        "completed_validated" if preliminary_ok and not governance_errors else "post_reboot_failed:" + (result.get("first_failure") or ",".join(governance_errors)),
        "Nenhum; manutenção encerrada." if preliminary_ok and not governance_errors else "Investigar o primeiro gate vermelho preservado no resultado pós-boot.",
        str(RESULT),
    )
    if not cp["ok"]:
        governance_errors.append("checkpoint_final")

    report = send_report(result, cleanup_ok)
    if not report["ok"]:
        governance_errors.append("report_infra")
    result["report_infra"] = report
    all_ok = bool(result.get("overall_runtime")) and cleanup_ok and not governance_errors and report["ok"]
    result["overall"] = all_ok
    result["governance_errors"] = governance_errors
    message = final_message(result, all_ok)
    thread_post = post_payload(THREAD_ID, {"content": message})
    result["thread_post"] = thread_post
    if not thread_post["ok"]:
        result["overall"] = False
        result["governance_errors"].append("thread_post")
    result["closed_at"] = now_utc()
    atomic_json(RESULT, result)

    try:
        update_inventory(result, "completed_validated" if result["overall"] else "post_reboot_failed")
    except Exception as exc:
        result["governance_errors"].append("inventory_receipt:" + type(exc).__name__)
        result["overall"] = False
        atomic_json(RESULT, result)
    append_audit("vps_reboot_governance_closure", {
        "status": "pass" if result["overall"] else "fail",
        "runtime_pass": result.get("overall_runtime"),
        "cleanup_pass": cleanup_ok,
        "report_readback": bool(report.get("ok")),
        "thread_readback": bool(thread_post.get("ok")),
        "governance_errors": result.get("governance_errors", []),
        "result": str(RESULT),
    })
    log(f"DONE overall={result['overall']} governance_errors={result.get('governance_errors', [])}")
    return 0 if result["overall"] else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("freeze", "preflight", "dispatch", "validate", "close"))
    args = parser.parse_args()
    if args.mode == "freeze":
        return freeze()
    if args.mode == "preflight":
        ok, payload = preflight(record=True)
        print(json.dumps({"overall": ok, "first_failure": payload["first_failure"], "evidence": str(PREFLIGHT)}, ensure_ascii=False))
        return 0 if ok else 1
    if args.mode == "dispatch":
        return dispatch()
    if args.mode == "validate":
        return validate()
    return close()


if __name__ == "__main__":
    raise SystemExit(main())
