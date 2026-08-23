#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fcntl
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

BASE = Path("/root/mgs-agent")
PROFILE = Path("/root/.hermes/profiles/ares")
if str(BASE / "scripts") not in sys.path:
    sys.path.insert(0, str(BASE / "scripts"))

from ares_campaign_v3.adapters import build_cpv_manifest
from ares_campaign_v3.daily_cpv import (
    ACCOUNT_ID,
    SP,
    DailyBlocked,
    DailyPaths,
    LiveDailyBackend,
    active_budget_minor,
    assignments_from_readback,
    atomic_json,
    campaign_name_collisions,
    enforce_budget_cap,
    load_json,
    next_campaign_numbers,
    release_inventory,
    reserve_inventory,
    select_assets,
    stock_counts,
    update_inventory_assignments,
    utc_now,
    validate_engine_config,
    validate_hierarchy,
    verify_reconciliation,
)
from ares_campaign_v3.engine import CampaignEngine
from ares_campaign_v3.media_registry import MediaRegistry
from ares_campaign_v3.prevalidation import prevalidate_payload
from ares_campaign_v3.schema import Manifest
from ares_campaign_v3.transport import FakeBatchTransport

REQUEST_ID = "cpv-c20-advideos-canary-20260823"
STATE_PATH = BASE / "data/ares/meta-ads/engine-v3/state/cpv-c20-advideos-canary-20260823.json"
LOCK_PATH = BASE / "data/ares/meta-ads/engine-v3/state/cpv-c20-advideos-canary-20260823.lock"
AUDIT_PATH = BASE / "data/ares/meta-ads/engine-v3/audit/canary/cpv-c20-advideos-canary-20260823.json"
WORK_ROOT = PROFILE / "work/creditoparaveiculo-c20-advideos-canary"
OPERATION_LOCK = PROFILE / "state/creditoparaveiculo-operation.lock"
ACTION_LOCK = PROFILE / "state/creditoparaveiculo-intraday-actions.lock"
FIRST_LOCK = PROFILE / "state/creditoparaveiculo-first-delivery-guardrail.lock"
PERFORMANCE_STATE = PROFILE / "state/creditoparaveiculo-performance-guardrails.json"
FIRST_STATE = PROFILE / "state/creditoparaveiculo-first-delivery-guardrail.json"
AUTH_KEY = "c20_advideo_canary_20260823"
THREAD_SOURCE = "discord:thread:1540939724636819507"


def inventory_rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def authorization(operation: dict[str, Any]) -> dict[str, Any]:
    routine = operation.get("daily_new_campaign_routine") or {}
    auth = routine.get(AUTH_KEY) or {}
    if (
        str(auth.get("status") or "") != "authorized_pending_runtime_tests_live_preflight"
        or auth.get("authorized_by") != "Rodolfo Mattei"
        or auth.get("authorization_source") != THREAD_SOURCE
        or int(auth.get("campaign_number") or 0) != 20
        or float(auth.get("budget_usd") or 0) != 30.0
        or int(auth.get("creative_count") or 0) != 3
        or str(auth.get("creation_hold_override") or "").startswith("this C20 canary only") is not True
    ):
        raise DailyBlocked("authorization", "C20 canary authorization contract is missing or drifted")
    if ((routine.get("creation_hold") or {}).get("enabled")) is not True:
        raise DailyBlocked("authorization", "general creation hold must remain enabled during the C20 canary")
    return auth


def exact_c20_absent(campaigns: list[dict[str, Any]]) -> None:
    live = []
    for row in campaigns:
        status = str(row.get("effective_status") or row.get("status") or "").upper()
        if status in {"ARCHIVED", "DELETED"}:
            continue
        name = str(row.get("name") or "")
        if "b01fb13c20" in name:
            live.append({"id": row.get("id"), "name": name, "status": status})
    if live:
        raise DailyBlocked("campaign_collision", "a live C20 already exists", {"campaigns": live})


def canary_paths() -> DailyPaths:
    return DailyPaths(
        state=STATE_PATH,
        lock=LOCK_PATH,
        audit_root=AUDIT_PATH.parent,
        work_root=WORK_ROOT,
    )


def preflight_and_select(backend: LiveDailyBackend, paths: DailyPaths, now_sp: datetime) -> dict[str, Any]:
    operation = load_json(paths.operation)
    auth = authorization(operation)
    config = load_json(paths.config)
    validate_engine_config(config)
    meta = backend.meta_preflight()
    exact_c20_absent(meta["campaigns"])
    numbers = next_campaign_numbers(meta["campaigns"], 1, operation)
    if numbers != [20]:
        raise DailyBlocked("campaign_numbering", "the authorized canary must be exactly C20", {"numbers": numbers})
    budget = enforce_budget_cap(meta["campaigns"], 1, operation)
    if int(budget.get("selected_count") or 0) != 1 or int(budget.get("initial_minor") or 0) != 3000:
        raise DailyBlocked("budget_cap", "C20 must fit exactly one USD30 campaign", budget)
    drive_info = backend.drive_preflight()
    drive = drive_info["drive"]
    rows = inventory_rows(paths.inventory)
    reconciliation = backend.refresh_reconciliation(rows, drive, now_sp)
    selected = select_assets(
        rows,
        {str(row.get("id") or "") for row in drive.get("files") or [] if row.get("location") == "01_READY"},
        3,
        reconciliation=reconciliation,
    )
    verified = verify_reconciliation(paths.reconciliation, selected, now_sp)
    return {
        "operation": operation,
        "authorization": auth,
        "config": config,
        "meta": meta,
        "budget": budget,
        "drive_info": drive_info,
        "drive": drive,
        "inventory": rows,
        "selected": selected,
        "reconciliation": verified,
    }


def bounded_hierarchy(backend: LiveDailyBackend, campaign_id: str, manifest: Manifest) -> dict[str, Any]:
    latest: dict[str, Any] = {}
    validation: dict[str, Any] = {}
    for attempt in range(1, 13):
        latest = backend.hierarchy_readback(campaign_id)
        validation = validate_hierarchy(latest, manifest.campaigns[0])
        if validation.get("valid") is True:
            return {"attempt": attempt, "readback": latest, "validation": validation}
        if attempt < 12:
            time.sleep(5)
    raise DailyBlocked("readback", "C20 hierarchy/creative readback did not become valid", validation)


def creative_utm_readback(backend: LiveDailyBackend, assignments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not backend.token:
        raise DailyBlocked("readback", "Meta advertiser token is not initialized")
    requests_ = [
        {
            "name": str(row["creative_id"]),
            "path": str(row["creative_id"]),
            "params": {
                "fields": "id,name,status,effective_object_story_id,asset_feed_spec,object_story_spec,issues_info"
            },
        }
        for row in assignments
    ]
    status, responses, _ = backend.common.graph_batch_get(backend.token, requests_)
    if status != 200 or not isinstance(responses, list):
        raise DailyBlocked("readback", "C20 creative batch readback failed", {"http": status})
    result = []
    for response in responses:
        body = response.get("body") or {}
        raw = json.dumps(body, ensure_ascii=False)
        valid = (
            int(response.get("code") or 0) == 200
            and str(body.get("status") or "").upper() == "ACTIVE"
            and bool(str(body.get("effective_object_story_id") or ""))
            and not body.get("issues_info")
            and "b01fb13c20" in raw
            and "b01fb13c20g01" in raw
            and "b01fb13c08" not in raw
        )
        result.append(
            {
                "creative_id": str(response.get("name") or ""),
                "http": int(response.get("code") or 0),
                "status": body.get("status"),
                "effective_object_story_id": body.get("effective_object_story_id"),
                "utm_valid": valid,
            }
        )
    if len(result) != 3 or not all(row["utm_valid"] for row in result):
        raise DailyBlocked("readback", "C20 creative/UTM readback failed", {"creatives": result})
    return result


def update_local_states(campaign_id: str, audit_path: Path, now_sp: datetime) -> None:
    OPERATION_LOCK.parent.mkdir(parents=True, exist_ok=True)
    with OPERATION_LOCK.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        operation = load_json(canary_paths().operation)
        auth = operation["daily_new_campaign_routine"][AUTH_KEY]
        allowed = operation["management_scope"]["autonomous_action_scope"].setdefault("allowed_campaigns", {})
        allowed["20"] = {
            "campaign_id": campaign_id,
            "cycle_start_date": now_sp.date().isoformat(),
            "source": "c20_advideo_canary_readback",
            "authorized_by": "Rodolfo Mattei",
            "authorization_source": THREAD_SOURCE,
            "readback_audit": str(audit_path),
            "request_id": REQUEST_ID,
        }
        operation["campaign_numbering_policy"]["next_required_campaign_number"] = 21
        auth.update(
            status="completed_active_readback_validated",
            campaign_id=campaign_id,
            completed_at_sp=now_sp.isoformat(),
            readback_audit=str(audit_path),
        )
        operation["updated_at"] = now_sp.isoformat()
        atomic_json(canary_paths().operation, operation)
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    with ACTION_LOCK.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        performance = load_json(PERFORMANCE_STATE)
        performance.setdefault("campaigns", {})[campaign_id] = {
            "campaign_id": campaign_id,
            "campaign_number": "20",
            "cycle_start_date": now_sp.date().isoformat(),
            "morning_estimated_roi": {},
            "consecutive_16h_failures": 0,
            "terminal": False,
            "source": "c20_advideo_canary_readback",
            "authorized_by": "Rodolfo Mattei",
            "readback_audit": str(audit_path),
            "updated_at_sp": now_sp.isoformat(),
        }
        performance["updated_at_sp"] = now_sp.isoformat()
        atomic_json(PERFORMANCE_STATE, performance)
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    with FIRST_LOCK.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        first = load_json(FIRST_STATE)
        first.setdefault("targets", {})[campaign_id] = {
            "campaign_id": campaign_id,
            "campaign_number": "20",
            "cycle_start_date": now_sp.date().isoformat(),
            "status": "completed",
            "watcher_completed": True,
            "completion_reason": "Rodolfo authorized immediate C20 advideos canary observation without automatic late-start pause",
            "release_reason": "authorized_advideos_canary_observe_only",
            "released_by": "Rodolfo Mattei",
            "release_source": THREAD_SOURCE,
            "released_at_sp": now_sp.isoformat(),
            "readback_audit": str(audit_path),
        }
        first["status"] = "idle_c20_canary_observe_only"
        first["updated_at_sp"] = now_sp.isoformat()
        atomic_json(FIRST_STATE, first)
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def run(*, dry_run: bool, execute: bool) -> dict[str, Any]:
    now_sp = datetime.now(SP)
    paths = canary_paths()
    backend = LiveDailyBackend(paths)
    preflight = preflight_and_select(backend, paths, now_sp)
    selected = preflight["selected"]
    selected_public = [str(row.get("canonical_filename") or "") for row in selected]
    if dry_run:
        result = {
            "status": "DRY_RUN_OK",
            "request_id": REQUEST_ID,
            "campaign_number": 20,
            "budget": preflight["budget"],
            "selected_assets": selected_public,
            "drive_counts": preflight["drive"].get("counts") or {},
            "reconciliation": preflight["reconciliation"],
            "side_effects": {"inventory": False, "media_upload": False, "campaign_write": False, "drive_move": False},
        }
        atomic_json(AUDIT_PATH.with_name(AUDIT_PATH.stem + "-dry-run.json"), result)
        return result
    if not execute:
        raise DailyBlocked("authorization", "execute mode was not confirmed")

    paths.lock.parent.mkdir(parents=True, exist_ok=True)
    with paths.lock.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        prior_attempt: dict[str, Any] | None = None
        if STATE_PATH.exists():
            prior = load_json(STATE_PATH)
            if prior.get("status") == "COMPLETE":
                return {**prior, "idempotent_readback": True}
            prior_audit = load_json(AUDIT_PATH) if AUDIT_PATH.exists() else {}
            retryable_media_only = (
                prior.get("status") == "FAILED"
                and prior.get("manual_reconciliation_required") is False
                and ((prior_audit.get("side_effects") or {}).get("campaign_write")) is False
            )
            if not retryable_media_only:
                raise DailyBlocked("resume", "existing nonterminal C20 state requires manual reconciliation", prior)
            prior_attempt = {
                "state": prior,
                "audit_stage": prior_audit.get("stage"),
                "failure": prior_audit.get("failure"),
                "side_effects": prior_audit.get("side_effects"),
            }
        audit: dict[str, Any] = {
            "schema_version": 3,
            "kind": "cpv_c20_advideos_canary",
            "request_id": REQUEST_ID,
            "authorized_by": "Rodolfo Mattei",
            "authorization_source": THREAD_SOURCE,
            "created_at_sp": now_sp.isoformat(),
            "stage": "PREFLIGHT_VALIDATED",
            "side_effects": {"inventory": False, "media_upload": False, "campaign_write": False, "drive_move": False},
            "budget": preflight["budget"],
            "selected_assets": selected_public,
            "reconciliation": preflight["reconciliation"],
            "attempt_history": [prior_attempt] if prior_attempt else [],
        }
        atomic_json(AUDIT_PATH, audit)
        selected_ids = {str(row.get("asset_id") or "") for row in selected}
        campaign_write_started = False
        try:
            reserve_inventory(paths.inventory, preflight["inventory"], selected, AUDIT_PATH)
            audit["side_effects"]["inventory"] = True
            state = {
                "schema_version": 3,
                "status": "ASSETS_RESERVED",
                "request_id": REQUEST_ID,
                "selected_asset_ids": sorted(selected_ids),
                "campaign_number": 20,
                "updated_at_utc": utc_now(),
            }
            atomic_json(STATE_PATH, state)

            registry = MediaRegistry(paths.registry)
            audit["side_effects"]["media_upload"] = True
            audit["stage"] = "MEDIA_UPLOAD_IN_FLIGHT"
            atomic_json(AUDIT_PATH, audit)
            prepared = backend.prepare_and_prestage(selected, preflight["drive"], WORK_ROOT, registry)
            if len(prepared) != 3 or not all(
                (item.get("registry") or {}).get("association_verified") is True
                and (item.get("registry") or {}).get("upload_edge") == "ad_account_advideos"
                for item in prepared
            ):
                raise DailyBlocked("prestage", "C20 requires three ad-account-associated media pairs")
            audit["prepared_assets"] = [
                {"asset_id": item["asset_id"], "clean": item["clean"], "square": item["square_readback"], "registry": item["registry"]}
                for item in prepared
            ]
            audit["stage"] = "MEDIA_READY_ASSOCIATED"
            atomic_json(AUDIT_PATH, audit)
            state.update(status="MEDIA_READY_ASSOCIATED", updated_at_utc=utc_now())
            atomic_json(STATE_PATH, state)

            start_time = (datetime.now(SP) + timedelta(minutes=10)).replace(second=0, microsecond=0)
            assets_payload = [
                {
                    "asset_id": str(row["asset_id"]),
                    "checksum": str(row["clean_checksum"]),
                    "canonical_filename": str(row["canonical_filename"]),
                }
                for row in selected
            ]
            templates = load_json(paths.templates).get("templates") or []
            draft = build_cpv_manifest(
                registry=registry,
                asset_refs=assets_payload,
                campaign_numbers=[20],
                operational_date=now_sp.date().isoformat(),
                request_id=REQUEST_ID,
                creative_templates=templates,
                status="ACTIVE",
                start_time=start_time.isoformat(),
            )
            sealed = prevalidate_payload(draft, registry)
            manifest = Manifest.from_dict(sealed)
            manifest_dir = WORK_ROOT / "manifest"
            manifest_dir.mkdir(parents=True, exist_ok=True)
            atomic_json(manifest_dir / "draft.json", draft)
            atomic_json(manifest_dir / "sealed.json", sealed)
            plan = CampaignEngine(
                preflight["config"],
                transport_factory=lambda account: FakeBatchTransport(account),
            ).dry_run(manifest)
            if plan.get("campaign_count") != 1 or plan.get("writes") != 0:
                raise DailyBlocked("plan", "C20 engine plan is invalid", plan)
            collisions = campaign_name_collisions(manifest, preflight["meta"]["campaigns"], set())
            if collisions:
                raise DailyBlocked("campaign_collision", "C20 manifest name collision", {"collisions": collisions})
            audit.update(stage="MANIFEST_SEALED", start_time_sp=start_time.isoformat(), manifest_digest=sealed["prevalidation"]["content_digest"], plan=plan)
            atomic_json(AUDIT_PATH, audit)
            state.update(status="MANIFEST_SEALED", start_time_sp=start_time.isoformat(), manifest_digest=sealed["prevalidation"]["content_digest"], updated_at_utc=utc_now())
            atomic_json(STATE_PATH, state)

            campaign_write_started = True
            audit["side_effects"]["campaign_write"] = True
            audit["stage"] = "ENGINE_IN_FLIGHT"
            atomic_json(AUDIT_PATH, audit)
            engine_result = backend.execute_engine(sealed, preflight["config"])
            campaign_ids = [str(item) for item in engine_result.get("campaign_ids") or []]
            if engine_result.get("status") != "COMPLETE_FUTURE_ACTIVE" or len(campaign_ids) != 1:
                raise DailyBlocked("engine", "C20 engine did not complete exactly one ACTIVE campaign", engine_result)
            campaign_id = campaign_ids[0]
            state.update(status="READBACK_IN_FLIGHT", campaign_id=campaign_id, updated_at_utc=utc_now())
            atomic_json(STATE_PATH, state)
            audit.update(stage="READBACK_IN_FLIGHT", engine_result=engine_result, campaign_id=campaign_id)
            atomic_json(AUDIT_PATH, audit)

            hierarchy = bounded_hierarchy(backend, campaign_id, manifest)
            assignments = assignments_from_readback(manifest, campaign_ids, {campaign_id: hierarchy["readback"]})
            creatives = creative_utm_readback(backend, assignments)

            drive_by_asset = {str(row.get("asset_id") or ""): row for row in selected}
            drive_rows = {str(row.get("id") or ""): row for row in preflight["drive"].get("files") or []}
            moves: dict[str, dict[str, Any]] = {}
            audit["side_effects"]["drive_move"] = True
            audit["stage"] = "POSTPROCESS_IN_FLIGHT"
            atomic_json(AUDIT_PATH, audit)
            for assignment in assignments:
                source_asset = drive_by_asset[assignment["asset_id"]]
                drive_row = drive_rows[str(source_asset["asset_drive_id"])]
                moves[str(source_asset["asset_drive_id"])] = backend.move_asset(drive_row)
            latest_inventory = inventory_rows(paths.inventory)
            update_inventory_assignments(paths.inventory, latest_inventory, assignments, moves, AUDIT_PATH)
            finished_sp = datetime.now(SP)
            update_local_states(campaign_id, AUDIT_PATH, finished_sp)

            post_meta = backend.meta_preflight()
            active_after = active_budget_minor(post_meta["campaigns"])
            cap_minor = int(preflight["budget"]["cap_minor"])
            if active_after > cap_minor:
                raise DailyBlocked("budget_cap", "live active budget exceeded cap after C20", {"active_after_minor": active_after, "cap_minor": cap_minor})
            drive_after = backend.drive_preflight()["drive"]
            latest_inventory = inventory_rows(paths.inventory)
            stock = stock_counts(latest_inventory, drive_after)
            final = {
                "status": "COMPLETE",
                "request_id": REQUEST_ID,
                "campaign_number": 20,
                "campaign_id": campaign_id,
                "start_time_sp": start_time.isoformat(),
                "budget_usd": 30,
                "bid_strategy": "MAXVOL",
                "structure": "1x1x3",
                "assets_used": 3,
                "selected_assets": selected_public,
                "hierarchy": hierarchy["validation"],
                "creatives": creatives,
                "ad_account_video_association": True,
                "account_budget_active_minor": active_after,
                "account_budget_remaining_minor": cap_minor - active_after,
                "account_budget_cap_minor": cap_minor,
                "stock_remaining": stock,
                "first_delivery_mode": "observe_only_no_auto_pause",
                "audit": str(AUDIT_PATH),
                "completed_at_sp": finished_sp.isoformat(),
            }
            audit.update(stage="COMPLETE", final=final, assignments=assignments, drive_moves=moves, completed_at_sp=finished_sp.isoformat())
            atomic_json(AUDIT_PATH, audit)
            state.update(final, status="COMPLETE", updated_at_utc=utc_now())
            atomic_json(STATE_PATH, state)
            return final
        except Exception as exc:
            audit.update(stage="FAILED_RECONCILIATION_REQUIRED" if campaign_write_started else "FAILED", failure={"type": type(exc).__name__, "message": str(exc)[:700]}, failed_at_utc=utc_now(), manual_reconciliation_required=campaign_write_started)
            atomic_json(AUDIT_PATH, audit)
            if not campaign_write_started:
                release_inventory(paths.inventory, inventory_rows(paths.inventory), selected_ids)
            state = load_json(STATE_PATH) if STATE_PATH.exists() else {"schema_version": 3, "request_id": REQUEST_ID}
            state.update(status=audit["stage"], failure=audit["failure"], manual_reconciliation_required=campaign_write_started, updated_at_utc=utc_now())
            atomic_json(STATE_PATH, state)
            raise
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Authorized C20 ad-account-video canary")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    ap.add_argument("--confirm-execute", action="store_true")
    return ap


def main() -> int:
    args = parser().parse_args()
    if args.execute and not args.confirm_execute:
        raise SystemExit("--execute requires --confirm-execute")
    result = run(dry_run=args.dry_run, execute=args.execute)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"status": "FAILED", "error_type": type(exc).__name__, "message": str(exc)[:700]}, ensure_ascii=False))
        raise SystemExit(2)
