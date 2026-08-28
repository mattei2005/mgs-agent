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
from .quota import LaneQuotaStore, QuotaBlocked
from .schema import Manifest
from .transport import BatchOperation, BatchResult, BatchTransportError


ENGINE_RELEASE_VERSION = "3.1.5"


class EngineDisabled(RuntimeError):
    pass


class ExecutionFailed(RuntimeError):
    pass


class ReadbackCooldownDeferred(RuntimeError):
    def __init__(self, retry_after_seconds: int):
        self.retry_after_seconds = int(retry_after_seconds)
        super().__init__("bundle writes completed; consolidated readback deferred to the next quota window")


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

    @staticmethod
    def _readback_only_record(bundle: BundlePlan, record: dict[str, Any]) -> bool:
        expected_ads = sum(len(campaign.ads) for campaign in bundle.campaigns)
        return (
            str(record.get("stage") or "") == "children_created_readback_pending"
            and len(record.get("campaign_ids") or []) == len(bundle.campaigns)
            and len(record.get("adset_ids") or []) == len(bundle.campaigns)
            and len(record.get("ad_ids") or []) == expected_ads
            and int(record.get("created_children") or 0) == expected_ads
        )

    def _recovery_points(self, bundle: BundlePlan, record: dict[str, Any]) -> int:
        if self._readback_only_record(bundle, record):
            per_campaign = int(self.config.get("readback_recovery_points_per_campaign", 3))
            return max(1, per_campaign * len(bundle.campaigns))
        return self._points(bundle)

    def _readback_retry_seconds(self, bundle: BundlePlan) -> int:
        safety = max(0, int(self.config.get("quota_retry_safety_seconds", 5)))
        default = max(
            int(self.config.get("score_window_seconds", 300)) + safety,
            int(self.config.get("development_access_readback_cooldown_seconds", 0)),
        )
        snapshot = self.quota.snapshot((bundle.app_key, bundle.account_id))
        live = snapshot.get("live_usage") or {}
        candidates = [default]
        try:
            reset_seconds = int(float(live.get("reset_time_duration") or 0))
        except (TypeError, ValueError):
            reset_seconds = 0
        if reset_seconds > 0:
            candidates.append(reset_seconds + safety)

        def collect_estimates(value: Any) -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    if str(key) == "estimated_time_to_regain_access":
                        try:
                            minutes = float(child)
                        except (TypeError, ValueError):
                            minutes = 0.0
                        if minutes > 0:
                            candidates.append(int(minutes * 60) + safety)
                    else:
                        collect_estimates(child)
            elif isinstance(value, list):
                for child in value:
                    collect_estimates(child)

        collect_estimates(live.get("business_usage"))
        return max(candidates)

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
                BatchOperation(f"readback_ads_{index}", "GET", f"{campaign_id}/ads?fields=id,name,status,effective_status,configured_status,adset_id,source_ad_id,issues_info,failed_delivery_checks,creative{{id,name,status,effective_object_story_id}}&limit=50", kind="readback"),
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

        adset_copy_ops: list[BatchOperation] = []
        for index, (campaign, campaign_id) in enumerate(zip(bundle.campaigns, campaign_ids), 1):
            adset_copy_ops.append(BatchOperation(
                f"adset_copy_{index}", "POST", f"{campaign.source_adset_id}/copies",
                body={
                    "campaign_id": campaign_id,
                    "deep_copy": "false",
                    "status_option": campaign.status,
                    "start_time": campaign.start_time,
                    "rename_options": {"rename_strategy": "NO_RENAME"},
                },
                kind="adset_copy",
            ))
        timing, started = self._timed_start()
        record["timings"]["adset_copy"] = timing
        adset_results = self._batch(bundle, transport, adset_copy_ops, "adset_copy")
        self._timed_finish(timing, started)
        adset_ids: list[str] = []
        for index in range(len(bundle.campaigns)):
            result = next(row for row in adset_results if row.name == f"adset_copy_{index + 1}")
            adset_ids.append(_copied_id(result, "copied_adset_id", "copied_adsets"))
        record["adset_ids"] = adset_ids
        record["stage"] = "adsets_created"

        shell_update_ops: list[BatchOperation] = []
        for index, (campaign, campaign_id, adset_id) in enumerate(zip(bundle.campaigns, campaign_ids, adset_ids), 1):
            shell_update_ops.extend([
                BatchOperation(
                    f"campaign_update_{index}", "POST", campaign_id,
                    body={"name": campaign.name, "status": campaign.status, "start_time": campaign.start_time, **campaign.campaign_updates},
                    kind="campaign_update",
                ),
                BatchOperation(
                    f"adset_update_{index}", "POST", adset_id,
                    body={"name": campaign.adset_name or campaign.name, "status": campaign.status},
                    kind="adset_update",
                ),
            ])
        timing, started = self._timed_start()
        record["timings"]["shell_normalize"] = timing
        self._batch(bundle, transport, shell_update_ops, "campaign_adset_update")
        self._timed_finish(timing, started)
        record["stage"] = "shells_normalized"

        ad_copy_ops: list[BatchOperation] = []
        for ci, (campaign, adset_id) in enumerate(zip(bundle.campaigns, adset_ids), 1):
            for ai, ad in enumerate(campaign.ads, 1):
                ad_copy_ops.append(BatchOperation(
                    f"ad_copy_{ci}_{ai}", "POST", f"{ad.source_ad_id}/copies",
                    body={
                        "adset_id": adset_id,
                        "creative_parameters": ad.creative_payload,
                        "status_option": campaign.status,
                        "rename_options": {"rename_strategy": "NO_RENAME"},
                    },
                    kind="ad_copy_with_creative",
                ))
        timing, started = self._timed_start()
        record["timings"]["ad_copies"] = timing
        ad_copy_results = self._batch(bundle, transport, ad_copy_ops, "ad_copy_with_creative")
        self._timed_finish(timing, started)
        copied_ad_ids: list[str] = []
        for ci, campaign in enumerate(bundle.campaigns, 1):
            for ai in range(1, len(campaign.ads) + 1):
                result = next(row for row in ad_copy_results if row.name == f"ad_copy_{ci}_{ai}")
                copied_ad_ids.append(_copied_id(result, "copied_ad_id"))
        record["ad_ids"] = copied_ad_ids
        record["created_children"] = len(copied_ad_ids)
        record["stage"] = "ads_copied_with_lineage"

        ad_name_ops: list[BatchOperation] = []
        offset = 0
        for campaign in bundle.campaigns:
            for ad in campaign.ads:
                ad_name_ops.append(BatchOperation(
                    f"ad_name_update_{offset + 1}", "POST", copied_ad_ids[offset],
                    body={"name": ad.name, "status": campaign.status},
                    kind="ad_name_update",
                ))
                offset += 1
        timing, started = self._timed_start()
        record["timings"]["ad_name_normalize"] = timing
        self._batch(bundle, transport, ad_name_ops, "ad_name_update")
        self._timed_finish(timing, started)
        record["stage"] = "children_created_readback_pending"

        if len(bundle.campaigns) >= 2 and int(self.config.get("development_access_readback_cooldown_seconds", 0)) > 0:
            retry_after = self._readback_retry_seconds(bundle)
            record["readback_cooldown"] = {
                "reason": "development_access_score_decay",
                "retry_after_seconds": retry_after,
                "write_replay_blocked": True,
                "deferred_at": _utc(),
            }
            raise ReadbackCooldownDeferred(retry_after)

        timing, started = self._timed_start()
        record["timings"]["readback"] = timing
        readbacks = self._batch(bundle, transport, self._readback_ops(campaign_ids), "consolidated_readback")
        self._timed_finish(timing, started)
        record["readback_children"] = len(readbacks)
        return campaign_ids

    def _run_from_zero_bundle(self, bundle: BundlePlan, transport: Any, record: dict[str, Any]) -> list[str]:
        timing, started = self._timed_start()
        record["timings"]["campaign_create"] = timing
        campaign_ops = [
            BatchOperation(
                f"campaign_create_{index}", "POST", f"act_{bundle.account_id}/campaigns",
                body={**campaign.campaign_create, "name": campaign.name, "status": "PAUSED"},
                kind="campaign_create",
            )
            for index, campaign in enumerate(bundle.campaigns, 1)
        ]
        campaign_results = self._batch(bundle, transport, campaign_ops, "campaign_create")
        self._timed_finish(timing, started)
        campaign_ids = [_copied_id(row, "id") for row in campaign_results]
        record["campaign_ids"] = campaign_ids
        record["stage"] = "campaigns_created_from_zero"

        adset_ops = [
            BatchOperation(
                f"adset_create_{index}", "POST", f"act_{bundle.account_id}/adsets",
                body={
                    **campaign.adset_create,
                    "name": campaign.adset_name,
                    "campaign_id": campaign_id,
                    "status": "ACTIVE",
                    "start_time": campaign.start_time,
                },
                kind="adset_create",
            )
            for index, (campaign, campaign_id) in enumerate(zip(bundle.campaigns, campaign_ids), 1)
        ]
        timing, started = self._timed_start()
        record["timings"]["adset_create"] = timing
        adset_results = self._batch(bundle, transport, adset_ops, "adset_create")
        self._timed_finish(timing, started)
        adset_ids = [_copied_id(row, "id") for row in adset_results]
        record["adset_ids"] = adset_ids
        record["stage"] = "adsets_created_from_zero"

        creative_ops = []
        for ci, campaign in enumerate(bundle.campaigns, 1):
            for ai, ad in enumerate(campaign.ads, 1):
                creative_ops.append(BatchOperation(
                    f"creative_create_{ci}_{ai}", "POST", f"act_{bundle.account_id}/adcreatives",
                    body=ad.creative_payload, kind="creative_create",
                ))
        timing, started = self._timed_start()
        record["timings"]["creative_create"] = timing
        creative_results = self._batch(bundle, transport, creative_ops, "creative_create")
        self._timed_finish(timing, started)
        creative_ids = [_copied_id(row, "id") for row in creative_results]
        record["creative_ids"] = creative_ids
        record["stage"] = "creatives_created_from_zero"

        ad_ops = []
        offset = 0
        for ci, (campaign, adset_id) in enumerate(zip(bundle.campaigns, adset_ids), 1):
            for ai, ad in enumerate(campaign.ads, 1):
                ad_ops.append(BatchOperation(
                    f"ad_create_{ci}_{ai}", "POST", f"act_{bundle.account_id}/ads",
                    body={
                        "name": ad.name,
                        "adset_id": adset_id,
                        "creative": {"creative_id": creative_ids[offset]},
                        "status": "ACTIVE",
                    },
                    kind="ad_create",
                ))
                offset += 1
        timing, started = self._timed_start()
        record["timings"]["ad_create"] = timing
        ad_results = self._batch(bundle, transport, ad_ops, "ad_create")
        self._timed_finish(timing, started)
        ad_ids = [_copied_id(row, "id") for row in ad_results]
        record["ad_ids"] = ad_ids
        record["created_children"] = len(ad_ids)
        record["stage"] = "ads_created_from_zero"

        finalize_ops = [
            BatchOperation(
                f"campaign_finalize_{index}", "POST", campaign_id,
                body={"status": campaign.status}, kind="campaign_finalize",
            )
            for index, (campaign, campaign_id) in enumerate(zip(bundle.campaigns, campaign_ids), 1)
        ]
        timing, started = self._timed_start()
        record["timings"]["campaign_finalize"] = timing
        self._batch(bundle, transport, finalize_ops, "campaign_finalize")
        self._timed_finish(timing, started)
        record["stage"] = "children_created_readback_pending"

        if len(bundle.campaigns) >= 2 and int(self.config.get("development_access_readback_cooldown_seconds", 0)) > 0:
            retry_after = self._readback_retry_seconds(bundle)
            record["readback_cooldown"] = {
                "reason": "development_access_score_decay",
                "retry_after_seconds": retry_after,
                "write_replay_blocked": True,
                "deferred_at": _utc(),
            }
            raise ReadbackCooldownDeferred(retry_after)

        timing, started = self._timed_start()
        record["timings"]["readback"] = timing
        readbacks = self._batch(bundle, transport, self._readback_ops(campaign_ids), "consolidated_readback")
        self._timed_finish(timing, started)
        record["readback_children"] = len(readbacks)
        return campaign_ids

    def _recover_prestaged_bundle(self, bundle: BundlePlan, transport: Any, record: dict[str, Any]) -> list[str]:
        """Reconcile a partial prestaged bundle and create only missing ads."""
        campaign_ids = [str(value) for value in record.get("campaign_ids") or []]
        adset_ids = [str(value) for value in record.get("adset_ids") or []]
        if len(campaign_ids) != len(bundle.campaigns) or len(adset_ids) != len(bundle.campaigns):
            raise ExecutionFailed("partial prestaged bundle is missing campaign/adset identities")

        if self._readback_only_record(bundle, record):
            previous_recovery = record.get("recovery")
            if isinstance(previous_recovery, dict) and previous_recovery:
                record.setdefault("recovery_history", []).append(previous_recovery)
            record["recovery"] = {
                "mode": "consolidated_readback_only",
                "blind_replay_blocked": True,
                "write_replay_blocked": True,
                "started_at": _utc(),
                "existing_ads": len(record.get("ad_ids") or []),
                "missing_ads_created": 0,
                "mutation_calls": 0,
            }
            timing, started = self._timed_start()
            record["timings"]["recovery_consolidated_readback"] = timing
            readbacks = self._batch(bundle, transport, self._readback_ops(campaign_ids), "recovery_consolidated_readback")
            self._timed_finish(timing, started)
            record["readback_children"] = len(readbacks)
            record["recovery"]["finished_at"] = _utc()
            record["stage"] = "readback_complete_recovered"
            return campaign_ids

        record["recovery"] = {
            "mode": "readback_then_missing_only",
            "blind_replay_blocked": True,
            "started_at": _utc(),
        }
        recovery_reads = [
            BatchOperation(
                f"recovery_ads_{index}",
                "GET",
                f"{campaign_id}/ads?fields=id,name,status,effective_status,configured_status,adset_id,source_ad_id,issues_info,creative{{id,name,status,effective_object_story_id}}&limit=50",
                kind="readback",
            )
            for index, campaign_id in enumerate(campaign_ids, 1)
        ]
        timing, started = self._timed_start()
        record["timings"]["recovery_readback"] = timing
        read_results = self._batch(bundle, transport, recovery_reads, "recovery_existing_ads_readback")
        self._timed_finish(timing, started)

        live_by_campaign: dict[int, list[dict[str, Any]]] = {}
        for index in range(1, len(bundle.campaigns) + 1):
            result = next(row for row in read_results if row.name == f"recovery_ads_{index}")
            live_by_campaign[index] = list(result.body.get("data") or [])

        resolved: dict[tuple[int, int], str] = {}
        resolved_rows: dict[tuple[int, int], dict[str, Any]] = {}
        missing_ops: list[BatchOperation] = []
        for ci, (campaign, adset_id) in enumerate(zip(bundle.campaigns, adset_ids), 1):
            live_rows = live_by_campaign[ci]
            for ai, ad in enumerate(campaign.ads, 1):
                matches = [
                    row
                    for row in live_rows
                    if str(row.get("adset_id") or "") == adset_id
                    and str(row.get("source_ad_id") or "") == str(ad.source_ad_id)
                ]
                if len(matches) > 1:
                    raise ExecutionFailed(
                        f"partial prestaged bundle has duplicate lineage for campaign {ci} ad {ai}"
                    )
                if matches:
                    resolved[(ci, ai)] = str(matches[0].get("id") or "")
                    if not resolved[(ci, ai)]:
                        raise ExecutionFailed("recovery readback returned an ad without id")
                    resolved_rows[(ci, ai)] = matches[0]
                    continue
                missing_ops.append(BatchOperation(
                    f"recovery_ad_copy_{ci}_{ai}",
                    "POST",
                    f"{ad.source_ad_id}/copies",
                    body={
                        "adset_id": adset_id,
                        "creative_parameters": ad.creative_payload,
                        "status_option": campaign.status,
                        "rename_options": {"rename_strategy": "NO_RENAME"},
                    },
                    kind="ad_copy_with_creative",
                ))

        if missing_ops:
            timing, started = self._timed_start()
            record["timings"]["recovery_missing_ad_copies"] = timing
            missing_results = self._batch(bundle, transport, missing_ops, "recovery_missing_ad_copies")
            self._timed_finish(timing, started)
            for result in missing_results:
                match = re.fullmatch(r"recovery_ad_copy_(\d+)_(\d+)", result.name)
                if not match:
                    raise ExecutionFailed("unexpected recovery ad-copy result name")
                resolved[(int(match.group(1)), int(match.group(2)))] = _copied_id(result, "copied_ad_id")

        expected_count = sum(len(campaign.ads) for campaign in bundle.campaigns)
        if len(resolved) != expected_count:
            raise ExecutionFailed("recovery did not resolve every expected ad")
        copied_ad_ids = [
            resolved[(ci, ai)]
            for ci, campaign in enumerate(bundle.campaigns, 1)
            for ai in range(1, len(campaign.ads) + 1)
        ]
        record["ad_ids"] = copied_ad_ids
        record["created_children"] = len(copied_ad_ids)
        record["recovery"]["existing_ads"] = expected_count - len(missing_ops)
        record["recovery"]["missing_ads_created"] = len(missing_ops)

        ad_name_ops: list[BatchOperation] = []
        offset = 0
        for ci, campaign in enumerate(bundle.campaigns, 1):
            for ai, ad in enumerate(campaign.ads, 1):
                live = resolved_rows.get((ci, ai))
                configured_status = str((live or {}).get("configured_status") or (live or {}).get("status") or "")
                if live is not None and str(live.get("name") or "") == ad.name and configured_status == campaign.status:
                    offset += 1
                    continue
                ad_name_ops.append(BatchOperation(
                    f"recovery_ad_name_update_{offset + 1}",
                    "POST",
                    copied_ad_ids[offset],
                    body={"name": ad.name, "status": campaign.status},
                    kind="ad_name_update",
                ))
                offset += 1
        if ad_name_ops:
            timing, started = self._timed_start()
            record["timings"]["recovery_ad_name_normalize"] = timing
            self._batch(bundle, transport, ad_name_ops, "recovery_ad_name_update")
            self._timed_finish(timing, started)
        record["recovery"]["ads_normalized"] = len(ad_name_ops)
        record["recovery"]["unchanged_ads_skipped"] = expected_count - len(ad_name_ops)

        recovery_mutations = len(missing_ops) + len(ad_name_ops)
        record["recovery"]["mutation_calls"] = recovery_mutations
        if recovery_mutations and int(self.config.get("development_access_readback_cooldown_seconds", 0)) > 0:
            retry_after = self._readback_retry_seconds(bundle)
            record["stage"] = "children_created_readback_pending"
            record["readback_cooldown"] = {
                "reason": "recovery_write_requires_fresh_score_decay",
                "retry_after_seconds": retry_after,
                "write_replay_blocked": True,
                "deferred_at": _utc(),
            }
            record["recovery"]["readback_deferred_after_mutation"] = True
            raise ReadbackCooldownDeferred(retry_after)

        timing, started = self._timed_start()
        record["timings"]["recovery_consolidated_readback"] = timing
        readbacks = self._batch(bundle, transport, self._readback_ops(campaign_ids), "recovery_consolidated_readback")
        self._timed_finish(timing, started)
        record["readback_children"] = len(readbacks)
        record["recovery"]["finished_at"] = _utc()
        record["stage"] = "readback_complete_recovered"
        return campaign_ids

    def _recover_from_zero_bundle(self, bundle: BundlePlan, transport: Any, record: dict[str, Any]) -> list[str]:
        """Read back every layer and create only missing from-zero objects."""
        if self._readback_only_record(bundle, record):
            readback_campaign_ids = [str(value) for value in record.get("campaign_ids") or []]
            previous_recovery = record.get("recovery")
            if isinstance(previous_recovery, dict) and previous_recovery:
                record.setdefault("recovery_history", []).append(previous_recovery)
            record["recovery"] = {
                "mode": "consolidated_readback_only",
                "blind_replay_blocked": True,
                "write_replay_blocked": True,
                "started_at": _utc(),
                "mutation_calls": 0,
            }
            timing, started = self._timed_start()
            record["timings"]["recovery_consolidated_readback"] = timing
            readbacks = self._batch(bundle, transport, self._readback_ops(readback_campaign_ids), "recovery_consolidated_readback")
            self._timed_finish(timing, started)
            record["readback_children"] = len(readbacks)
            record["recovery"]["finished_at"] = _utc()
            record["stage"] = "readback_complete_recovered"
            return readback_campaign_ids

        record["recovery"] = {
            "mode": "readback_then_missing_only_from_zero",
            "blind_replay_blocked": True,
            "write_replay_blocked": True,
            "started_at": _utc(),
        }

        campaign_list = self._batch(bundle, transport, [BatchOperation(
            "recovery_campaign_inventory", "GET",
            f"act_{bundle.account_id}/campaigns?fields=id,name,status,effective_status,configured_status&limit=500",
            kind="readback",
        )], "recovery_campaign_inventory")[0].body.get("data") or []
        campaign_ids: list[str | None] = [None] * len(bundle.campaigns)
        recorded_campaigns = [str(value) for value in record.get("campaign_ids") or []]
        if len(recorded_campaigns) == len(bundle.campaigns):
            campaign_ids = list(recorded_campaigns)
        missing_campaign_ops = []
        for ci, campaign in enumerate(bundle.campaigns, 1):
            if campaign_ids[ci - 1]:
                continue
            matches = [
                row for row in campaign_list
                if str(row.get("name") or "") == campaign.name
                and str(row.get("configured_status") or row.get("status") or "").upper() not in {"DELETED", "ARCHIVED"}
            ]
            if len(matches) > 1:
                raise ExecutionFailed(f"from-zero recovery found duplicate campaign name at index {ci}")
            if matches:
                campaign_ids[ci - 1] = str(matches[0]["id"])
            else:
                missing_campaign_ops.append(BatchOperation(
                    f"recovery_campaign_create_{ci}", "POST", f"act_{bundle.account_id}/campaigns",
                    body={**campaign.campaign_create, "name": campaign.name, "status": "PAUSED"},
                    kind="campaign_create",
                ))
        if missing_campaign_ops:
            results = self._batch(bundle, transport, missing_campaign_ops, "recovery_missing_campaign_create")
            for result in results:
                ci = int(result.name.rsplit("_", 1)[1])
                campaign_ids[ci - 1] = _copied_id(result, "id")
        if any(not value for value in campaign_ids):
            raise ExecutionFailed("from-zero recovery could not resolve every campaign")
        resolved_campaign_ids = [str(value) for value in campaign_ids]
        record["campaign_ids"] = resolved_campaign_ids

        adset_reads = self._batch(bundle, transport, [
            BatchOperation(
                f"recovery_adsets_{ci}", "GET",
                f"{campaign_id}/adsets?fields=id,name,status,effective_status,configured_status,start_time&limit=50",
                kind="readback",
            )
            for ci, campaign_id in enumerate(resolved_campaign_ids, 1)
        ], "recovery_adset_inventory")
        recorded_adsets = [str(value) for value in record.get("adset_ids") or []]
        adset_ids: list[str | None] = list(recorded_adsets) if len(recorded_adsets) == len(bundle.campaigns) else [None] * len(bundle.campaigns)
        missing_adset_ops = []
        for ci, (campaign, campaign_id) in enumerate(zip(bundle.campaigns, resolved_campaign_ids), 1):
            if adset_ids[ci - 1]:
                continue
            rows = next(row for row in adset_reads if row.name == f"recovery_adsets_{ci}").body.get("data") or []
            matches = [row for row in rows if str(row.get("name") or "") == str(campaign.adset_name)]
            if len(matches) > 1:
                raise ExecutionFailed(f"from-zero recovery found duplicate adset name at index {ci}")
            if matches:
                adset_ids[ci - 1] = str(matches[0]["id"])
            else:
                missing_adset_ops.append(BatchOperation(
                    f"recovery_adset_create_{ci}", "POST", f"act_{bundle.account_id}/adsets",
                    body={
                        **campaign.adset_create,
                        "name": campaign.adset_name,
                        "campaign_id": campaign_id,
                        "status": "ACTIVE",
                        "start_time": campaign.start_time,
                    },
                    kind="adset_create",
                ))
        if missing_adset_ops:
            results = self._batch(bundle, transport, missing_adset_ops, "recovery_missing_adset_create")
            for result in results:
                ci = int(result.name.rsplit("_", 1)[1])
                adset_ids[ci - 1] = _copied_id(result, "id")
        if any(not value for value in adset_ids):
            raise ExecutionFailed("from-zero recovery could not resolve every adset")
        resolved_adset_ids = [str(value) for value in adset_ids]
        record["adset_ids"] = resolved_adset_ids

        ad_reads = self._batch(bundle, transport, [
            BatchOperation(
                f"recovery_ads_{ci}", "GET",
                f"{campaign_id}/ads?fields=id,name,adset_id,status,configured_status,creative{{id,name}}&limit=100",
                kind="readback",
            )
            for ci, campaign_id in enumerate(resolved_campaign_ids, 1)
        ], "recovery_ad_inventory")
        creative_inventory = self._batch(bundle, transport, [BatchOperation(
            "recovery_creative_inventory", "GET",
            f"act_{bundle.account_id}/adcreatives?fields=id,name,status&limit=500",
            kind="readback",
        )], "recovery_creative_inventory")[0].body.get("data") or []

        resolved_ads: dict[tuple[int, int], str] = {}
        resolved_creatives: dict[tuple[int, int], str] = {}
        missing_creative_ops = []
        for ci, (campaign, adset_id) in enumerate(zip(bundle.campaigns, resolved_adset_ids), 1):
            rows = next(row for row in ad_reads if row.name == f"recovery_ads_{ci}").body.get("data") or []
            for ai, ad in enumerate(campaign.ads, 1):
                matches = [row for row in rows if str(row.get("name") or "") == ad.name and str(row.get("adset_id") or "") == adset_id]
                if len(matches) > 1:
                    raise ExecutionFailed(f"from-zero recovery found duplicate ad name at {ci}.{ai}")
                if matches:
                    resolved_ads[(ci, ai)] = str(matches[0]["id"])
                    creative = matches[0].get("creative") or {}
                    if creative.get("id"):
                        resolved_creatives[(ci, ai)] = str(creative["id"])
                    continue
                creative_name = str(ad.creative_payload.get("name") or "")
                creative_matches = [row for row in creative_inventory if str(row.get("name") or "") == creative_name]
                if len(creative_matches) > 1:
                    raise ExecutionFailed(f"from-zero recovery found duplicate creative name at {ci}.{ai}")
                if creative_matches:
                    resolved_creatives[(ci, ai)] = str(creative_matches[0]["id"])
                else:
                    missing_creative_ops.append(BatchOperation(
                        f"recovery_creative_create_{ci}_{ai}", "POST", f"act_{bundle.account_id}/adcreatives",
                        body=ad.creative_payload, kind="creative_create",
                    ))
        if missing_creative_ops:
            results = self._batch(bundle, transport, missing_creative_ops, "recovery_missing_creative_create")
            for result in results:
                match = re.fullmatch(r"recovery_creative_create_(\d+)_(\d+)", result.name)
                if not match:
                    raise ExecutionFailed("unexpected from-zero recovery creative result")
                resolved_creatives[(int(match.group(1)), int(match.group(2)))] = _copied_id(result, "id")

        missing_ad_ops = []
        for ci, (campaign, adset_id) in enumerate(zip(bundle.campaigns, resolved_adset_ids), 1):
            for ai, ad in enumerate(campaign.ads, 1):
                if (ci, ai) in resolved_ads:
                    continue
                creative_id = resolved_creatives.get((ci, ai))
                if not creative_id:
                    raise ExecutionFailed(f"from-zero recovery missing creative identity at {ci}.{ai}")
                missing_ad_ops.append(BatchOperation(
                    f"recovery_ad_create_{ci}_{ai}", "POST", f"act_{bundle.account_id}/ads",
                    body={"name": ad.name, "adset_id": adset_id, "creative": {"creative_id": creative_id}, "status": "ACTIVE"},
                    kind="ad_create",
                ))
        if missing_ad_ops:
            results = self._batch(bundle, transport, missing_ad_ops, "recovery_missing_ad_create")
            for result in results:
                match = re.fullmatch(r"recovery_ad_create_(\d+)_(\d+)", result.name)
                if not match:
                    raise ExecutionFailed("unexpected from-zero recovery ad result")
                resolved_ads[(int(match.group(1)), int(match.group(2)))] = _copied_id(result, "id")

        expected_count = sum(len(campaign.ads) for campaign in bundle.campaigns)
        if len(resolved_ads) != expected_count:
            raise ExecutionFailed("from-zero recovery did not resolve every expected ad")
        record["creative_ids"] = [
            resolved_creatives[(ci, ai)]
            for ci, campaign in enumerate(bundle.campaigns, 1)
            for ai in range(1, len(campaign.ads) + 1)
        ]
        record["ad_ids"] = [
            resolved_ads[(ci, ai)]
            for ci, campaign in enumerate(bundle.campaigns, 1)
            for ai in range(1, len(campaign.ads) + 1)
        ]
        record["created_children"] = expected_count

        direct_campaign_reads = self._batch(bundle, transport, [
            BatchOperation(f"recovery_campaign_status_{ci}", "GET", f"{campaign_id}?fields=id,status,configured_status", kind="readback")
            for ci, campaign_id in enumerate(resolved_campaign_ids, 1)
        ], "recovery_campaign_status_readback")
        finalize_ops = []
        for ci, (campaign, campaign_id) in enumerate(zip(bundle.campaigns, resolved_campaign_ids), 1):
            live = next(row for row in direct_campaign_reads if row.name == f"recovery_campaign_status_{ci}").body
            if str(live.get("configured_status") or live.get("status") or "") != campaign.status:
                finalize_ops.append(BatchOperation(
                    f"recovery_campaign_finalize_{ci}", "POST", campaign_id,
                    body={"status": campaign.status}, kind="campaign_finalize",
                ))
        if finalize_ops:
            self._batch(bundle, transport, finalize_ops, "recovery_campaign_finalize")

        record["recovery"].update({
            "missing_campaigns_created": len(missing_campaign_ops),
            "missing_adsets_created": len(missing_adset_ops),
            "missing_creatives_created": len(missing_creative_ops),
            "missing_ads_created": len(missing_ad_ops),
            "campaigns_finalized": len(finalize_ops),
        })
        recovery_mutations = sum(map(len, (
            missing_campaign_ops,
            missing_adset_ops,
            missing_creative_ops,
            missing_ad_ops,
            finalize_ops,
        )))
        record["recovery"]["mutation_calls"] = recovery_mutations
        if recovery_mutations and int(self.config.get("development_access_readback_cooldown_seconds", 0)) > 0:
            retry_after = self._readback_retry_seconds(bundle)
            record["stage"] = "children_created_readback_pending"
            record["readback_cooldown"] = {
                "reason": "recovery_write_requires_fresh_score_decay",
                "retry_after_seconds": retry_after,
                "write_replay_blocked": True,
                "deferred_at": _utc(),
            }
            record["recovery"]["readback_deferred_after_mutation"] = True
            raise ReadbackCooldownDeferred(retry_after)
        timing, started = self._timed_start()
        record["timings"]["recovery_consolidated_readback"] = timing
        readbacks = self._batch(bundle, transport, self._readback_ops(resolved_campaign_ids), "recovery_consolidated_readback")
        self._timed_finish(timing, started)
        record["readback_children"] = len(readbacks)
        record["recovery"]["finished_at"] = _utc()
        record["stage"] = "readback_complete_recovered"
        return resolved_campaign_ids

    def _run_lane(self, account: str, bundles: tuple[BundlePlan, ...], request_id: str) -> dict[str, Any]:
        transport = self.transport_factory(account)
        checkpoint_path = Path(self.config["state_root"]) / "checkpoints" / f"{_safe_name(request_id)}-{_safe_name(account)}.json"
        if checkpoint_path.exists():
            lane_result = json.loads(checkpoint_path.read_text())
            if str(lane_result.get("account_id")) != account:
                raise ExecutionFailed("lane checkpoint account mismatch")
        else:
            lane_result = {"account_id": account, "status": "IN_PROGRESS", "bundles": [], "campaign_ids": [], "checkpoint_path": str(checkpoint_path)}
        lane_result["status"] = "IN_PROGRESS"
        lane_result.pop("deferred", None)
        completed_indices = {int(row["index"]) for row in (lane_result.get("bundles") or []) if row.get("status") == "COMPLETE"}
        failed_by_index = {
            int(row["index"]): row
            for row in (lane_result.get("bundles") or [])
            if row.get("status") in {"FAILED", "READBACK_DEFERRED"}
        }
        _atomic_json(checkpoint_path, lane_result)
        for bundle in bundles:
            if bundle.index in completed_indices:
                continue
            bundle_request_id = f"{request_id}:{account}:{bundle.index}"
            previous_failed = failed_by_index.get(bundle.index)
            points = self._recovery_points(bundle, previous_failed) if previous_failed is not None else self._points(bundle)
            try:
                quota = self.quota.reserve((bundle.app_key, account), points, request_id=bundle_request_id)
            except QuotaBlocked as exc:
                lane_result["status"] = "DEFERRED_QUOTA"
                lane_result["deferred"] = {"next_bundle_index": bundle.index, **exc.detail}
                _atomic_json(checkpoint_path, lane_result)
                return lane_result
            if previous_failed is not None:
                record = previous_failed
                record["status"] = "RECOVERING"
                record["quota_recovery"] = quota
                record.setdefault("timings", {})
            else:
                record = {
                    "index": bundle.index,
                    "status": "IN_PROGRESS",
                    "idempotency_keys": [campaign.idempotency_key for campaign in bundle.campaigns],
                    "projected_points": points,
                    "quota": quota,
                    "timings": {},
                    "intermediate_get_calls": 0,
                    "outer_readback_calls": 1,
                }
                lane_result.setdefault("bundles", []).append(record)
            _atomic_json(checkpoint_path, lane_result)
            try:
                mode = bundle.campaigns[0].mode
                if previous_failed is not None:
                    if mode == "clone_prestaged":
                        ids = self._recover_prestaged_bundle(bundle, transport, record)
                    elif mode == "from_zero_prestaged":
                        ids = self._recover_from_zero_bundle(bundle, transport, record)
                    else:
                        raise ExecutionFailed("automatic recovery requires a prestaged execution mode")
                elif mode == "pure_clone":
                    ids = self._run_pure_bundle(bundle, transport, record)
                elif mode == "clone_prestaged":
                    ids = self._run_prestaged_bundle(bundle, transport, record)
                else:
                    ids = self._run_from_zero_bundle(bundle, transport, record)
                record["campaign_ids"] = ids
                record["quota_completion"] = self.quota.complete((bundle.app_key, account), bundle_request_id)
                record["status"] = "COMPLETE"
                record.pop("error", None)
                record["stage"] = "readback_complete_recovered" if previous_failed is not None else "readback_complete"
                lane_result["campaign_ids"].extend(ids)
                lane_result["manual_reconciliation_required"] = False
                _atomic_json(checkpoint_path, lane_result)
            except ReadbackCooldownDeferred as exc:
                record["status"] = "READBACK_DEFERRED"
                lane_result["status"] = "DEFERRED_QUOTA"
                lane_result["manual_reconciliation_required"] = False
                lane_result["automatic_recovery_required"] = True
                lane_result["deferred"] = {
                    "next_bundle_index": bundle.index,
                    "reason": "development_access_score_decay",
                    "retry_after_seconds": exc.retry_after_seconds,
                    "readback_only": True,
                    "write_replay_blocked": True,
                }
                _atomic_json(checkpoint_path, lane_result)
                return lane_result
            except Exception as exc:
                record["status"] = "FAILED"
                error_row: dict[str, Any] = {"type": type(exc).__name__, "message": str(exc)[:500]}
                if isinstance(exc, BatchTransportError):
                    error_row["stage"] = exc.stage
                    error_row["detail"] = exc.detail
                record["error"] = error_row
                lane_result["status"] = "FAILED"
                lane_result["manual_reconciliation_required"] = False
                lane_result["automatic_recovery_required"] = True
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
                checkpoint_dir = Path(self.config["state_root"]) / "checkpoints"
                checkpoints = list(checkpoint_dir.glob(f"{_safe_name(manifest.request_id)}-*.json")) if checkpoint_dir.exists() else []
                if not checkpoints:
                    raise ExecutionFailed("failed request has no checkpoint for recovery")
        audit: dict[str, Any] = {
            "engine_version": 3,
            "engine_release_version": ENGINE_RELEASE_VERSION,
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
            deferred_accounts = sorted(account for account, value in lane_results.items() if value.get("status") == "DEFERRED_QUOTA")
            if deferred_accounts:
                status = "PARTIAL_DEFERRED_QUOTA"
            else:
                status = "COMPLETE_PAUSED" if all(campaign.status == "PAUSED" for campaign in manifest.campaigns) else "COMPLETE_FUTURE_ACTIVE"
            metrics = {
                "lane_count": len(lane_results),
                "campaign_count": len(campaign_ids),
                "global_wave_count": plan.global_wave_count,
                "intermediate_get_calls": 0,
                "outer_readback_calls": sum(sum(row.get("status") == "COMPLETE" for row in result["bundles"]) for result in lane_results.values()),
            }
            retry_after = max((int((lane_results[account].get("deferred") or {}).get("retry_after_seconds") or 0) for account in deferred_accounts), default=0)
            result = {
                "status": status,
                "request_id": manifest.request_id,
                "campaign_ids": campaign_ids,
                "metrics": metrics,
                "audit_path": str(audit_path),
                "idempotent_replay": False,
                "deferred_accounts": deferred_accounts,
                "retry_after_seconds": retry_after,
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
                "manual_reconciliation_required": False,
                "automatic_recovery_required": True,
                "blind_replay_blocked": True,
                "lane_checkpoints": checkpoint_paths,
            })
            _atomic_json(audit_path, audit)
            raise
