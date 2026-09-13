#!/usr/bin/env python3
"""SHEIN-US-DIRECT materializer for the shared Campaign Engine v3.

This runner owns operation-specific request materialization and approval state.
It does not implement reporting, optimization, or an alternate campaign writer.
Every campaign mutation is delegated to ares-campaign-engine-v3.py.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from ares_campaign_v3.engine import CampaignEngine
from ares_campaign_v3.media_registry import MediaRegistry
from ares_campaign_v3.prevalidation import prevalidate_payload, validate_account_policy
from ares_campaign_v3.schema import Manifest
from ares_campaign_v3.shein import (
    SHEIN_ACCOUNT_ID,
    SHEIN_APP_KEY,
    build_clone_prestaged_manifest,
    build_from_zero_manifest,
    build_pure_clone_manifest,
    next_campaign_numbers,
)
from ares_campaign_v3.transport import FakeBatchTransport

BASE = Path("/root/mgs-agent")
CONFIG_PATH = BASE / "data/ares/meta-ads/engine-v3/config.json"
REGISTRY_PATH = BASE / "data/ares/meta-ads/engine-v3/media-registry.json"
STATE_ROOT = BASE / "data/ares/meta-ads/state/shein-campaigns"
AUDIT_ROOT = BASE / "data/ares/meta-ads/audit/shein/campaigns"
ENGINE_CLI = BASE / "scripts/ares-campaign-engine-v3.py"
ET = ZoneInfo("America/New_York")
AUTHORIZED_EXECUTORS = {
    "Rodolfo",
    "Rodolfo Mattei",
    "Geizian",
    "Kelly",
    "Kelly Nice",
}
MODE_ORDER = ["from_zero_prestaged", "pure_clone", "clone_prestaged"]


class SheinRunnerBlocked(RuntimeError):
    def __init__(self, stage: str, detail: Any):
        self.stage = stage
        self.detail = detail
        super().__init__(f"{stage}: {detail}")


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise SheinRunnerBlocked("json", f"cannot load {path.name}") from exc
    if not isinstance(value, dict):
        raise SheinRunnerBlocked("json", f"expected object in {path.name}")
    return value


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(raw)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        temporary.unlink(missing_ok=True)


def safe_request_id(value: str) -> str:
    text = "".join(char if char.isalnum() or char in "_.-" else "-" for char in str(value))
    text = text.strip("-")
    if not text:
        raise SheinRunnerBlocked("request_id", "invalid request id")
    return text[:160]


def state_path(request_id: str) -> Path:
    return STATE_ROOT / f"{safe_request_id(request_id)}.json"


def summary_digest(value: dict[str, Any]) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _register_fake_media(registry: MediaRegistry, assets: list[dict[str, Any]]) -> None:
    for asset in assets:
        registry.register(
            account_id=SHEIN_ACCOUNT_ID,
            asset_id=asset["asset_id"],
            checksum=asset["checksum"],
            vertical_video_id=asset["vertical_video_id"],
            square_video_id=asset["square_video_id"],
            ready=True,
            source="shein-offline-smoke",
            upload_edge="ad_account_advideos",
            association_verified=True,
        )


def _fake_campaign(number: int, budget: str) -> dict[str, Any]:
    return {
        "id": f"campaign-{number}",
        "name": f"{number} - PRODUTOS SHEIN - US-EN (b01fb03c{number:03d}) event_add_to_wishlist",
        "daily_budget": budget,
        "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
        "objective": "OUTCOME_SALES",
        "buying_type": "AUCTION",
        "special_ad_categories": [],
        "special_ad_category_country": [],
    }


def _fake_adset(number: int) -> dict[str, Any]:
    return {
        "id": f"adset-{number}",
        "billing_event": "IMPRESSIONS",
        "optimization_goal": "OFFSITE_CONVERSIONS",
        "targeting": {
            "age_min": 18,
            "age_max": 65,
            "geo_locations": {
                "countries": ["US"],
                "location_types": ["frequently_in", "home", "recent"],
            },
            "targeting_automation": {"advantage_audience": 1},
        },
        "promoted_object": {
            "pixel_id": "1049581090103163",
            "custom_event_type": "ADD_TO_WISHLIST",
            "smart_pse_enabled": False,
        },
        "attribution_spec": [
            {"event_type": "CLICK_THROUGH", "window_days": 7},
            {"event_type": "VIEW_THROUGH", "window_days": 1},
            {"event_type": "ENGAGED_VIDEO_VIEW", "window_days": 1},
        ],
        "regional_regulated_categories": ["VOLUNTARY_VERIFICATION"],
        "regional_regulation_identities": {
            "universal_beneficiary": "1773412024030451",
            "universal_payer": "1773412024030451",
        },
        "is_dynamic_creative": False,
    }


def _fake_ad(campaign_number: int, slot: int, *, upstream: str | None = None) -> dict[str, Any]:
    return {
        "id": f"ad-{campaign_number}-{slot}",
        "name": f"VIDEO - {slot:02d}",
        "source_ad_id": upstream or f"ad-{campaign_number - 1}-{slot}",
        "creative": {
            "id": f"creative-{campaign_number}-{slot}",
            "effective_object_story_id": f"410983488769165_post-{campaign_number}-{slot}",
            "object_story_spec": {
                "page_id": "410983488769165",
                "instagram_user_id": "17841469509077092",
                "video_data": {
                    "video_id": f"source-video-{campaign_number}-{slot}",
                    "title": "CLICK HERE ✅",
                    "message": "😱 SHEIN PRODUCTS FREE\n✔️ NO EXTRA COSTS OR FEES.",
                    "call_to_action": {
                        "type": "GET_OFFER_VIEW",
                        "value": {
                            "link": (
                                "https://yolokfx.com/quiz/us/sh2-g005/"
                                f"?utm_source=facebook&utm_medium=g005-s"
                                f"&utm_campaign=b01fb03c{campaign_number:03d}"
                                f"&utm_adgroup=b01fb03c{campaign_number:03d}g01"
                            )
                        },
                    },
                    "image_url": "https://example.test/source.jpg",
                    "image_hash": "source-image-hash",
                },
            },
            "degrees_of_freedom_spec": {
                "creative_features_spec": {
                    "advantage_plus_creative": {"enroll_status": "OPT_OUT"},
                    "standard_enhancements": {"enroll_status": "OPT_IN"},
                }
            },
        },
    }


def _fake_assets(product: str, count: int) -> list[dict[str, Any]]:
    return [
        {
            "asset_id": f"asset-{product}-{index}",
            "checksum": f"checksum-{product}-{index}",
            "canonical_filename": f"SHEIN_US_EN_VID_FREE_{product}_PV_{index:03d}.mp4",
            "vertical_video_id": f"video-{product}-{index}",
            "square_video_id": f"square-{product}-{index}",
            "thumbnail_url": f"https://example.test/{product}-{index}.jpg",
            "ready": True,
            "upload_edge": "ad_account_advideos",
            "association_verified": True,
        }
        for index in range(1, count + 1)
    ]


def seal_and_plan(
    payload: dict[str, Any],
    *,
    registry: MediaRegistry,
    config: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    parsed = Manifest.from_dict(payload)
    validate_account_policy(parsed, config)
    sealed = prevalidate_payload(payload, registry)
    manifest = Manifest.from_dict(sealed)
    plan = CampaignEngine(
        config,
        transport_factory=lambda account: FakeBatchTransport(account),
    ).dry_run(manifest)
    return sealed, plan


def offline_smoke(output: Path | None = None) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as raw:
        registry = MediaRegistry(Path(raw) / "registry.json")
        blender = _fake_assets("PORTABLE_BLENDER", 3)
        makeup = _fake_assets("MAKEUP_BAG", 3)
        _register_fake_media(registry, [*blender, *makeup])
        start = (datetime.now(ET) + timedelta(days=2)).replace(
            hour=0, minute=10, second=0, microsecond=0
        ).isoformat()
        c34 = _fake_campaign(34, "3000")
        c20 = _fake_campaign(20, "2500")
        a34 = [_fake_ad(34, 1), _fake_ad(34, 2)]
        a20 = [
            _fake_ad(20, 1, upstream="ad-19-1"),
            _fake_ad(20, 2, upstream="ad-19-2"),
        ]
        manifests = [
            build_from_zero_manifest(
                request_id="shein-offline-c038",
                number=38,
                start_time=start,
                reference_campaign=c34,
                reference_adset=_fake_adset(34),
                copy_source_ad=a34[0],
                assets=blender,
                budget_minor=5000,
                product_label="LIQUIDIFICADOR",
            ),
            build_pure_clone_manifest(
                request_id="shein-offline-c039",
                number=39,
                start_time=start,
                source_campaign=c34,
                source_adset=_fake_adset(34),
                source_ads=a34,
            ),
            build_clone_prestaged_manifest(
                request_id="shein-offline-c040",
                number=40,
                start_time=start,
                source_campaign=c20,
                source_adset=_fake_adset(20),
                source_ads=a20,
                assets=makeup,
                budget_minor=5000,
                product_label="MALETA DE MAQUIAGEM",
            ),
        ]
        config = load_json(CONFIG_PATH)
        sealed: list[dict[str, Any]] = []
        plans: list[dict[str, Any]] = []
        for payload in manifests:
            final, plan = seal_and_plan(payload, registry=registry, config=config)
            sealed.append(final)
            plans.append(plan["plan"])
        result = {
            "status": "OFFLINE_SMOKE_OK",
            "engine_version": 3,
            "campaigns": len(sealed),
            "ads": sum(
                len(campaign.get("ads") or [])
                for payload in sealed
                for campaign in payload.get("campaigns") or []
            ),
            "modes": [payload["execution_mode"] for payload in sealed],
            "plans": plans,
            "network_calls": 0,
            "writes": 0,
        }
        if output:
            atomic_json(output, {"manifests": sealed, "result": result})
        return result


def materialize_resolved(
    request: dict[str, Any],
    output_dir: Path,
    *,
    registry_path: Path = REGISTRY_PATH,
    config_path: Path = CONFIG_PATH,
) -> dict[str, Any]:
    request_id = safe_request_id(str(request.get("request_id") or ""))
    start_time = str(request.get("start_time") or "")
    live_campaigns = list(request.get("live_campaigns") or [])
    numbers = next_campaign_numbers(live_campaigns, 3)
    expected_modes = list(request.get("mode_order") or MODE_ORDER)
    if expected_modes != MODE_ORDER:
        raise SheinRunnerBlocked("mode_order", f"expected {MODE_ORDER}")
    zero = request.get("from_zero") or {}
    pure = request.get("pure_clone") or {}
    clone = request.get("clone_prestaged") or {}
    manifests = [
        build_from_zero_manifest(
            request_id=f"{request_id}-c{numbers[0]:03d}",
            number=numbers[0],
            start_time=start_time,
            reference_campaign=zero["reference_campaign"],
            reference_adset=zero["reference_adset"],
            copy_source_ad=zero["copy_source_ad"],
            assets=list(zero["assets"]),
            budget_minor=int(zero["budget_minor"]),
            product_label=str(zero["product_label"]),
        ),
        build_pure_clone_manifest(
            request_id=f"{request_id}-c{numbers[1]:03d}",
            number=numbers[1],
            start_time=start_time,
            source_campaign=pure["source_campaign"],
            source_adset=pure["source_adset"],
            source_ads=list(pure["source_ads"]),
            budget_minor=(
                int(pure["budget_minor"])
                if pure.get("budget_minor") is not None
                else None
            ),
        ),
        build_clone_prestaged_manifest(
            request_id=f"{request_id}-c{numbers[2]:03d}",
            number=numbers[2],
            start_time=start_time,
            source_campaign=clone["source_campaign"],
            source_adset=clone["source_adset"],
            source_ads=list(clone["source_ads"]),
            assets=list(clone["assets"]),
            budget_minor=int(clone["budget_minor"]),
            product_label=str(clone["product_label"]),
        ),
    ]
    registry = MediaRegistry(registry_path)
    config = load_json(config_path)
    sealed: list[dict[str, Any]] = []
    plans: list[dict[str, Any]] = []
    output_dir.mkdir(parents=True, exist_ok=True)
    for payload in manifests:
        final, plan = seal_and_plan(payload, registry=registry, config=config)
        path = output_dir / f"{safe_request_id(final['request_id'])}-sealed.json"
        atomic_json(path, final)
        sealed.append(final)
        plans.append(plan["plan"])
    summary = {
        "request_id": request_id,
        "engine_version": 3,
        "account_id": SHEIN_ACCOUNT_ID,
        "start_time": start_time,
        "numbers": numbers,
        "campaigns": [
            {
                "request_id": payload["request_id"],
                "mode": payload["execution_mode"],
                "name": payload["campaigns"][0]["name"],
                "budget_minor": (
                    payload["campaigns"][0].get("campaign_updates", {}).get("daily_budget")
                    or payload["campaigns"][0].get("campaign_create", {}).get("daily_budget")
                ),
                "ads": len(payload["campaigns"][0]["ads"]),
                "manifest_digest": Manifest.from_dict(payload).digest,
            }
            for payload in sealed
        ],
        "plans": plans,
    }
    digest = summary_digest(summary)
    state = {
        "schema_version": 1,
        "request_id": request_id,
        "phase": "AWAITING_FINAL_APPROVAL",
        "summary": summary,
        "summary_digest": digest,
        "manifest_paths": [
            str(output_dir / f"{safe_request_id(payload['request_id'])}-sealed.json")
            for payload in sealed
        ],
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "campaign_writes": 0,
        "network_calls": 0,
    }
    atomic_json(state_path(request_id), state)
    atomic_json(AUDIT_ROOT / f"{request_id}-materialization.json", state)
    return {
        "status": "AWAITING_FINAL_APPROVAL",
        "request_id": request_id,
        "summary_digest": digest,
        "summary": summary,
        "campaign_writes": 0,
        "network_calls": 0,
    }


def execute_materialized(args: argparse.Namespace) -> dict[str, Any]:
    if not args.confirm_execute:
        raise SheinRunnerBlocked("approval", "--confirm-execute is required")
    if args.authorized_by not in AUTHORIZED_EXECUTORS:
        raise SheinRunnerBlocked("authority", "authorized executor is required")
    path = state_path(args.request_id)
    state = load_json(path)
    if state.get("phase") not in {
        "AWAITING_FINAL_APPROVAL",
        "EXECUTION_DEFERRED",
        "RECOVERY_PENDING",
    }:
        raise SheinRunnerBlocked("state", f"request is not executable: {state.get('phase')}")
    if args.summary_digest != state.get("summary_digest"):
        raise SheinRunnerBlocked("approval", "summary digest mismatch")
    account = load_json(BASE / "data/ares/meta-ads/accounts/2429758060563333.json")
    account_row = (account.get("accounts") or [{}])[0]
    route = ((account_row.get("runtime_routes") or {}).get("campaign_creation") or {})
    if route.get("write_enabled") is not True:
        raise SheinRunnerBlocked("write_gate", "account-scoped write gate is closed")
    results = list(state.get("engine_results") or [])
    completed_requests = {
        str(row.get("request_id"))
        for row in results
        if row.get("status") in {"COMPLETE_FUTURE_ACTIVE", "COMPLETE_PAUSED"}
    }
    for manifest_path in state.get("manifest_paths") or []:
        manifest = load_json(Path(manifest_path))
        request_id = str(manifest["request_id"])
        if request_id in completed_requests:
            continue
        command = [
            "python3",
            str(ENGINE_CLI),
            "execute",
            "--manifest",
            str(manifest_path),
            "--confirm-execute",
        ]
        proc = subprocess.run(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=1800,
            check=False,
        )
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            payload = {"status": "FAILED", "message": "engine returned non-JSON output"}
        results.append(payload)
        state["engine_results"] = results
        if proc.returncode != 0:
            state.update(
                phase="RECOVERY_PENDING",
                automatic_recovery_required=True,
                last_engine_error={
                    "request_id": request_id,
                    "status": payload.get("status"),
                    "message": payload.get("message"),
                },
            )
            atomic_json(path, state)
            raise SheinRunnerBlocked("engine", state["last_engine_error"])
        if payload.get("status") == "PARTIAL_DEFERRED_QUOTA":
            state.update(phase="EXECUTION_DEFERRED", automatic_recovery_required=True)
            atomic_json(path, state)
            return {
                "status": "EXECUTION_DEFERRED",
                "request_id": args.request_id,
                "engine_results": results,
            }
        if payload.get("status") not in {"COMPLETE_FUTURE_ACTIVE", "COMPLETE_PAUSED"}:
            state.update(phase="RECOVERY_PENDING", automatic_recovery_required=True)
            atomic_json(path, state)
            raise SheinRunnerBlocked("engine", payload)
    state.update(
        phase="POSTPROCESS_PENDING",
        automatic_recovery_required=False,
        engine_results=results,
        completed_engine_at_utc=datetime.now(timezone.utc).isoformat(),
    )
    atomic_json(path, state)
    return {
        "status": "POSTPROCESS_PENDING",
        "request_id": args.request_id,
        "campaign_count": len(results),
        "engine_results": results,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    smoke = sub.add_parser("offline-smoke")
    smoke.add_argument("--output", type=Path)
    materialize = sub.add_parser("materialize")
    materialize.add_argument("--input", type=Path, required=True)
    materialize.add_argument("--output-dir", type=Path, required=True)
    materialize.add_argument("--registry", type=Path, default=REGISTRY_PATH)
    materialize.add_argument("--config", type=Path, default=CONFIG_PATH)
    status = sub.add_parser("status")
    status.add_argument("--request-id", required=True)
    execute = sub.add_parser("execute")
    execute.add_argument("--request-id", required=True)
    execute.add_argument("--summary-digest", required=True)
    execute.add_argument("--authorized-by", required=True)
    execute.add_argument("--confirm-execute", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "offline-smoke":
            result = offline_smoke(args.output)
        elif args.command == "materialize":
            result = materialize_resolved(
                load_json(args.input),
                args.output_dir,
                registry_path=args.registry,
                config_path=args.config,
            )
        elif args.command == "status":
            result = load_json(state_path(args.request_id))
        else:
            result = execute_materialized(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (SheinRunnerBlocked, KeyError, ValueError) as exc:
        if isinstance(exc, SheinRunnerBlocked):
            stage, detail = exc.stage, exc.detail
        else:
            stage, detail = "materialization", str(exc)
        print(
            json.dumps(
                {"status": "BLOCKED", "stage": stage, "detail": detail},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
