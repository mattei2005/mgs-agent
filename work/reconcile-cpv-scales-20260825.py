#!/usr/bin/env python3
import fcntl
import importlib.util
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SP = ZoneInfo("America/Sao_Paulo")
BASE = Path("/root/mgs-agent")
PROFILE = Path("/root/.hermes/profiles/ares")
STATE = PROFILE / "state/creditoparaveiculo-intraday-actions.json"
LOCK = PROFILE / "state/creditoparaveiculo-intraday-actions.lock"
COMMON = BASE / "scripts/ares-meta-common.py"
AUDIT_ROOT = BASE / "data/ares/meta-ads/audit/automated-actions/Creditoparaveiculo-BR-CAR-BR"
META_ITEM = "Creditoparaveiculo-BR-CAR-BR-13-G006 - FB Account"
TARGETS = {
    "2026-08-25:08:120250888205860632:scale_budget": {
        "campaign_id": "120250888205860632",
        "expected_minor": 3300,
        "requested_minor": 4290,
    },
    "2026-08-25:08:120250888205850632:scale_budget": {
        "campaign_id": "120250888205850632",
        "expected_minor": 3000,
        "requested_minor": 3300,
    },
}


def atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    tmp.replace(path)
    dfd = os.open(path.parent, os.O_DIRECTORY)
    try:
        os.fsync(dfd)
    finally:
        os.close(dfd)


def load_common():
    spec = importlib.util.spec_from_file_location("ares_meta_common_recovery", COMMON)
    if not spec or not spec.loader:
        raise RuntimeError("cannot load Meta common")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def get_campaign(common, token: str, campaign_id: str) -> dict:
    status, payload, _ = common.graph_get(
        campaign_id,
        token,
        {"fields": "id,name,status,effective_status,configured_status,daily_budget,updated_time"},
    )
    if status != 200 or not isinstance(payload, dict) or payload.get("error"):
        raise RuntimeError(f"Meta readback failed for {campaign_id}: HTTP {status}")
    return payload


def main() -> None:
    now = datetime.now(SP)
    stamp = now.strftime("%Y%m%dT%H%M%S%z")
    common = load_common()
    token, _ = common.get_token_from_1password(META_ITEM, force_refresh=False)
    readbacks = {cfg["campaign_id"]: get_campaign(common, token, cfg["campaign_id"]) for cfg in TARGETS.values()}

    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open("a+") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        state = json.loads(STATE.read_text())
        applied = state.get("applied") or {}
        before_entries = {}
        for key, cfg in TARGETS.items():
            entry = applied.get(key)
            if not isinstance(entry, dict):
                raise RuntimeError(f"missing action state: {key}")
            if entry.get("status") != "write_unconfirmed_hold":
                raise RuntimeError(f"unexpected action state for {key}: {entry.get('status')}")
            if int(entry.get("expected_minor")) != cfg["expected_minor"] or int(entry.get("requested_minor")) != cfg["requested_minor"]:
                raise RuntimeError(f"state amount mismatch for {key}")
            live = readbacks[cfg["campaign_id"]]
            if int(live.get("daily_budget")) != cfg["requested_minor"]:
                raise RuntimeError(f"live budget is neither the requested recovery target for {key}")
            if str(live.get("status") or "").upper() != "ACTIVE":
                raise RuntimeError(f"campaign is not ACTIVE during scale recovery: {key}")
            before_entries[key] = dict(entry)

        backup_dir = BASE / "backups" / f"ares-cpv-action-state-recovery-{stamp}"
        backup_dir.mkdir(parents=True, exist_ok=False)
        backup_path = backup_dir / STATE.name
        shutil.copy2(STATE, backup_path)

        verified_at = datetime.now(SP).isoformat()
        for key, cfg in TARGETS.items():
            applied[key] = {
                **applied[key],
                "status": "executed",
                "recovered_by_get": True,
                "verified_at_sp": verified_at,
                "recovery_readback": readbacks[cfg["campaign_id"]],
            }
        state["updated_at_sp"] = verified_at
        atomic_write(STATE, state)
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)

    persisted = json.loads(STATE.read_text())
    post_readbacks = {cfg["campaign_id"]: get_campaign(common, token, cfg["campaign_id"]) for cfg in TARGETS.values()}
    checks = {}
    for key, cfg in TARGETS.items():
        entry = (persisted.get("applied") or {}).get(key) or {}
        live = post_readbacks[cfg["campaign_id"]]
        checks[key] = {
            "state_executed": entry.get("status") == "executed",
            "recovered_by_get": entry.get("recovered_by_get") is True,
            "live_status": live.get("status"),
            "live_effective_status": live.get("effective_status"),
            "live_daily_budget_minor": int(live.get("daily_budget")),
            "expected_live_daily_budget_minor": cfg["requested_minor"],
            "verified": (
                entry.get("status") == "executed"
                and entry.get("recovered_by_get") is True
                and str(live.get("status") or "").upper() == "ACTIVE"
                and str(live.get("effective_status") or "").upper() == "ACTIVE"
                and int(live.get("daily_budget")) == cfg["requested_minor"]
            ),
        }
    if not all(item["verified"] for item in checks.values()):
        raise RuntimeError("post-recovery verification failed")

    audit_path = AUDIT_ROOT / f"recovery-actions-{stamp}.json"
    audit = {
        "schema_version": "1.0",
        "kind": "automated_action_readback_recovery",
        "operation_id": "Creditoparaveiculo-BR-CAR-BR",
        "created_at_sp": datetime.now(SP).isoformat(),
        "scope": "reconcile two already-applied 08:00 scale writes after transient effective_status=IN_PROCESS readback",
        "meta_writes": 0,
        "original_action_audit": str(AUDIT_ROOT / "actions-20260825T110059820400Z.json"),
        "state_path": str(STATE),
        "backup_path": str(backup_path),
        "before_entries": before_entries,
        "initial_live_readbacks": readbacks,
        "after_checks": checks,
        "token_report": {"item": META_ITEM, "len": len(token), "value_exposed": False},
        "all_verified": True,
    }
    atomic_write(audit_path, audit)
    audit_readback = json.loads(audit_path.read_text())
    if audit_readback.get("all_verified") is not True or len(audit_readback.get("after_checks") or {}) != 2:
        raise RuntimeError("audit readback failed")

    print(json.dumps({
        "ok": True,
        "state": str(STATE),
        "backup": str(backup_path),
        "audit": str(audit_path),
        "checks": checks,
        "meta_writes": 0,
        "token_item": META_ITEM,
        "token_len": len(token),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
