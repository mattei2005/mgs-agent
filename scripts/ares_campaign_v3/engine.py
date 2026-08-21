from __future__ import annotations

import json
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

from .planning import BundlePlan, Planner
from .prevalidation import verify_prevalidation
from .quota import LaneQuotaStore
from .schema import Manifest
from .transport import BatchOperation, BatchResult


class EngineDisabled(RuntimeError):
    pass


class ExecutionFailed(RuntimeError):
    pass


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")[:120] or "request"


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    os.replace(tmp, path)


def _copied_id(result: BatchResult, *keys: str) -> str:
    for key in keys:
        value = result.body.get(key)
        if isinstance(value, (str, int)) and str(value):
            return str(value)
        if isinstance(value, list) and value:
            item = value[0]
            if isinstance(item, dict) and item.get("id"):
                return str(item["id"])
            if isinstance(item, (str, int)):
                return str(item)
    if result.body.get("id"):
        return str(result.body["id"])
    raise ExecutionFailed(f"copy response missing ID for {result.name}")


class CampaignEngine:
    def __init__(self, config: dict[str, Any], *, transport_factory: Callable[[str], Any]):
        self.config = config
        self.transport_factory = transport_factory
        self.planner = Planner(bundle_size=int(config.get("bundle_size", 2)), max_ads_per_batch=int(config.get("max_ads_per_batch", 10)))
        self.quota = LaneQuotaStore(
            config["state_root"],
            soft_score=int(config.get("soft_score", 100)),
            hard_score=int(config.get("hard_score", 120)),
            window_seconds=int(config.get("score_window_seconds", 300)),
        )
        self.audit_root = Path(config["audit_root"])
        self._audit_lock = threading.Lock()

    def dry_run(self, manifest: Manifest) -> dict[str, Any]:
        plan = self.planner.build(manifest)
        summary = plan.summary()
        return {
            "status": "DRY_RUN_OK",
            "request_id": manifest.request_id,
            "manifest_digest": manifest.digest,
            "campaign_count": len(manifest.campaigns),
            "plan": summary,
            "network_calls": 0,
            "writes": 0,
        }

    def _points(self, bundle: BundlePlan) -> int:
        points_by_mode = self.config.get("points_per_mode") or {}
        return sum(int(points_by_mode.get(campaign.mode, 45)) for campaign in bundle.campaigns)

    def _batch(self, bundle: BundlePlan, transport: Any, operations: list[BatchOperation], stage: str) -> list[BatchResult]:
        results = transport.execute(operations, stage)
        headers = getattr(transport, "last_outer_headers", None)
        if isinstance(headers, dict) and headers:
            self.quota.observe_headers((bundle.app_key, bundle.account_id), headers)
        return results

    @staticmethod
    def _timed_start() -> tuple[dict[str, Any], float]:
        return {"started_at": _utc()}, perf_counter()

    @staticmethod
    def _timed_finish(row: dict[str, Any], started: float) -> None:
        row["finished_at"] = _utc()
        row["duration_ms"] = round((perf_counter() - started) * 1000, 3)

    @staticmethod
    def _readback_ops(campaign_ids: list[str]) -> list[BatchOperation]:
        operations: list[BatchOperation] = []
        for index, campaign_id in enumerate(campaign_ids, 1):
            operations.extend([
                BatchOperation(f"readback_campaign_{index}", "GET", f"{campaign_id}?fields=id,name,status,effective_status,configured_status,daily_budget,bid_strategy,start_time", kind="readback"),
                BatchOperation(f"readback_adsets_{index}", "GET", f"{campaign_id}/adsets?fields=id,name,status,effective_status,configured_status,start_time,bid_amount,bid_strategy&limit=20", kind="readback"),
                BatchOperation(f"readback_ads_{index}", "GET", f"{campaign_id}/ads?fields=id,name,status,effective_status,configured_status,adset_id,creative{{id,name}}&limit=50", kind="readback"),
            ])
        return operations

    def _run_pure_bundle(self, bundle: BundlePlan, transport: Any, record: dict[str, Any]) -> list[str]:
        timing, started = self._timed_start()
        record["timings"]["copy_submit"] = timing
        copy_results = self._batch(bundle, transport, list(bundle.stages[0].operations), "pure_clone_copy")
        self._timed_finish(timing, started)
        campaign_ids = [_copied_id(row, "copied_campaign_id", "copied_campaigns") for row in copy_results]
        record["campaign_ids"] = campaign_ids
        record["stage"] = "copies_created_readback_pending"
        timing, started = self._timed_start()
        record["timings"]["readback"] = timing
        readbacks = self._batch(bundle, transport, self._readback_ops(campaign_ids), "consolidated_readback")
        self._timed_finish(timing, started)
        record["readback_children"] = len(readbacks)
        return campaign_ids

    def _run_prestaged_bundle(self, bundle: BundlePlan, transport: Any, record: dict[str, Any]) -> list[str]:
        timing, started = self._timed_start()
        record["timings"]["copy_submit"] = timing
        copy_results = self._batch(bundle, transport, list(bundle.stages[0].operations), "campaign_copy")
        self._timed_finish(timing, started)
        campaign_ids = [_copied_id(row, "copied_campaign_id", "copied_campaigns") for row in copy_results]
        record["campaign_ids"] = campaign_ids
        record["stage"] = "campaign_copies_created"

        shell_ops: list[BatchOperation] = []
        for index, (campaign, campaign_id) in enumerate(zip(bundle.campaigns, campaign_ids), 1):
            shell_ops.extend([
                BatchOperation(
                    f"campaign_update_{index}", "POST", campaign_id,
                    body={"name": campaign.name, "status": campaign.status, "start_time": campaign.start_time, **campaign.campaign_updates},
                    kind="campaign_update",
                ),
                BatchOperation(
                    f"adset_copy_{index}", "POST", f"{campaign.source_adset_id}/copies",
                    body={
                        "campaign_id": campaign_id,
                        "deep_copy": "false",
                        "status_option": "ACTIVE",
                        "start_time": campaign.start_time,
                        "rename_options": {"rename_strategy": "ONLY_TOP_LEVEL_RENAME", "rename_suffix": f" - {campaign.adset_name or campaign.name}"},
                    },
                    kind="adset_copy",
                ),
            ])
        timing, started = self._timed_start()
        record["timings"]["shells"] = timing
        shell_results = self._batch(bundle, transport, shell_ops, "campaign_update_adset_copy")
        self._timed_finish(timing, started)
        adset_ids: list[str] = []
        for index in range(len(bundle.campaigns)):
            result = next(row for row in shell_results if row.name == f"adset_copy_{index + 1}")
            adset_ids.append(_copied_id(result, "copied_adset_id", "copied_adsets"))
        record["adset_ids"] = adset_ids
        record["stage"] = "shells_created"

        create_ops: list[BatchOperation] = []
        for ci, (campaign, adset_id) in enumerate(zip(bundle.campaigns, adset_ids), 1):
            for ai, ad in enumerate(campaign.ads, 1):
                creative_name = f"creative_{ci}_{ai}"
                create_ops.append(BatchOperation(
                    creative_name, "POST", f"act_{campaign.account_id}/adcreatives",
                    body=ad.creative_payload, kind="creative_create",
                ))
                create_ops.append(BatchOperation(
                    f"ad_{ci}_{ai}", "POST", f"act_{campaign.account_id}/ads",
                    body={
                        "name": ad.name,
                        "adset_id": adset_id,
                        "status": "ACTIVE",
                        "creative": {"creative_id": f"{{result={creative_name}:$.id}}"},
                    },
                    depends_on=creative_name,
                    kind="ad_create",
                ))
        timing, started = self._timed_start()
        record["timings"]["creative_ads"] = timing
        create_results = self._batch(bundle, transport, create_ops, "creative_ad_create")
        self._timed_finish(timing, started)
        record["created_children"] = len(create_results)
        record["stage"] = "children_created_readback_pending"

        timing, started = self._timed_start()
        record["timings"]["readback"] = timing
        readbacks = self._batch(bundle, transport, self._readback_ops(campaign_ids), "consolidated_readback")
        self._timed_finish(timing, started)
        record["readback_children"] = len(readbacks)
        return campaign_ids

    def _run_lane(self, account: str, bundles: tuple[BundlePlan, ...], request_id: str) -> dict[str, Any]:
        transport = self.transport_factory(account)
        checkpoint_path = Path(self.config["state_root"]) / "checkpoints" / f"{_safe_name(request_id)}-{_safe_name(account)}.json"
        lane_result: dict[str, Any] = {"account_id": account, "status": "IN_PROGRESS", "bundles": [], "campaign_ids": [], "checkpoint_path": str(checkpoint_path)}
        _atomic_json(checkpoint_path, lane_result)
        for bundle in bundles:
            bundle_request_id = f"{request_id}:{account}:{bundle.index}"
            points = self._points(bundle)
            quota = self.quota.reserve((bundle.app_key, account), points, request_id=bundle_request_id)
            record: dict[str, Any] = {
                "index": bundle.index,
                "status": "IN_PROGRESS",
                "idempotency_keys": [campaign.idempotency_key for campaign in bundle.campaigns],
                "projected_points": points,
                "quota": quota,
                "timings": {},
                "intermediate_get_calls": 0,
                "outer_readback_calls": 1,
            }
            lane_result["bundles"].append(record)
            _atomic_json(checkpoint_path, lane_result)
            try:
                if bundle.campaigns[0].mode == "pure_clone":
                    ids = self._run_pure_bundle(bundle, transport, record)
                else:
                    ids = self._run_prestaged_bundle(bundle, transport, record)
                record["campaign_ids"] = ids
                record["quota_completion"] = self.quota.complete((bundle.app_key, account), bundle_request_id)
                record["status"] = "COMPLETE"
                record["stage"] = "readback_complete"
                lane_result["campaign_ids"].extend(ids)
                _atomic_json(checkpoint_path, lane_result)
            except Exception as exc:
                record["status"] = "FAILED"
                record["error"] = {"type": type(exc).__name__, "message": str(exc)[:500]}
                lane_result["status"] = "FAILED"
                lane_result["manual_reconciliation_required"] = True
                _atomic_json(checkpoint_path, lane_result)
                raise
        lane_result["status"] = "COMPLETE"
        _atomic_json(checkpoint_path, lane_result)
        return lane_result

    def execute(self, manifest: Manifest) -> dict[str, Any]:
        if self.config.get("enabled") is not True or self.config.get("write_enabled") is not True:
            raise EngineDisabled("v3 execute is disabled; use dry_run until the canary gate is approved")
        if self.config.get("require_prevalidated_manifest") is True and not verify_prevalidation(manifest.raw):
            raise ExecutionFailed("manifest prevalidation is missing or digest does not match")
        plan = self.planner.build(manifest)
        audit_path = self.audit_root / f"{_safe_name(manifest.request_id)}.json"
        if audit_path.exists():
            previous = json.loads(audit_path.read_text())
            if previous.get("manifest_digest") != manifest.digest:
                raise ExecutionFailed("request_id already exists with a different manifest")
            if previous.get("status") in {"COMPLETE_PAUSED", "COMPLETE_FUTURE_ACTIVE"}:
                result = dict(previous["result"])
                result["idempotent_replay"] = True
                return result
            if previous.get("status") == "FAILED":
                raise ExecutionFailed("failed request requires reconciliation before replay")
        audit: dict[str, Any] = {
            "engine_version": 3,
            "request_id": manifest.request_id,
            "manifest_digest": manifest.digest,
            "operation": manifest.operation,
            "started_at": _utc(),
            "status": "IN_PROGRESS",
            "plan": plan.summary(),
            "lanes": {},
        }
        _atomic_json(audit_path, audit)
        lane_results: dict[str, Any] = {}
        try:
            workers = max(1, min(len(plan.lanes), int(self.config.get("max_account_workers", 8))))
            with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="ares-v3-lane") as pool:
                futures = {pool.submit(self._run_lane, account, bundles, manifest.request_id): account for account, bundles in plan.lanes.items()}
                for future in as_completed(futures):
                    account = futures[future]
                    lane_results[account] = future.result()
            campaign_ids = [campaign_id for account in sorted(lane_results) for campaign_id in lane_results[account]["campaign_ids"]]
            status = "COMPLETE_PAUSED" if all(campaign.status == "PAUSED" for campaign in manifest.campaigns) else "COMPLETE_FUTURE_ACTIVE"
            metrics = {
                "lane_count": len(lane_results),
                "campaign_count": len(campaign_ids),
                "global_wave_count": plan.global_wave_count,
                "intermediate_get_calls": 0,
                "outer_readback_calls": sum(len(result["bundles"]) for result in lane_results.values()),
            }
            result = {
                "status": status,
                "request_id": manifest.request_id,
                "campaign_ids": campaign_ids,
                "metrics": metrics,
                "audit_path": str(audit_path),
                "idempotent_replay": False,
            }
            audit.update({"status": status, "finished_at": _utc(), "lanes": lane_results, "result": result})
            _atomic_json(audit_path, audit)
            return result
        except Exception as exc:
            checkpoint_dir = Path(self.config["state_root"]) / "checkpoints"
            checkpoint_paths = sorted(str(path) for path in checkpoint_dir.glob(f"{_safe_name(manifest.request_id)}-*.json")) if checkpoint_dir.exists() else []
            audit.update({
                "status": "FAILED",
                "finished_at": _utc(),
                "lanes": lane_results,
                "error": {"type": type(exc).__name__, "message": str(exc)[:500]},
                "manual_reconciliation_required": True,
                "blind_replay_blocked": True,
                "lane_checkpoints": checkpoint_paths,
            })
            _atomic_json(audit_path, audit)
            raise
