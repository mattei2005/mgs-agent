from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
from typing import Any

from .adapters import build_cpv_manifest
from .engine import CampaignEngine, EngineDisabled, ExecutionFailed
from .media_registry import MediaNotReady, MediaRegistry
from .prestage import AdAccountVideoUploader, MediaUploadError, PrestageService
from .prevalidation import prevalidate_payload
from .quota import QuotaBlocked
from .schema import Manifest, ManifestError
from .source_selection import expand_source_selections
from .transport import BatchTransportError, FakeBatchTransport, GraphBatchTransport

BASE = Path("/root/mgs-agent")
DEFAULT_CONFIG = BASE / "data/ares/meta-ads/engine-v3/config.json"
DEFAULT_MEDIA = BASE / "data/ares/meta-ads/engine-v3/media-registry.json"
COMMON_PATH = BASE / "scripts/ares-meta-common.py"


def load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected object in {path}")
    return value


def load_common():
    spec = importlib.util.spec_from_file_location("ares_meta_common_v3_credentials", COMMON_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load credential provider")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def real_transport_factory(config: dict[str, Any], manifest: Manifest):
    common = load_common()
    accounts = config.get("accounts") or {}
    tokens: dict[str, str] = {}
    for account in sorted({campaign.account_id for campaign in manifest.campaigns}):
        account_cfg = accounts.get(account) or {}
        token_item = account_cfg.get("token_item")
        if not token_item:
            raise RuntimeError(f"missing token_item for account {account}")
        token, _ = common.get_token_from_1password(item_name=token_item)
        tokens[account] = token
    require_proof = config.get("require_appsecret_proof") is True
    app_secret = os.environ.get("ARES_META_APP_SECRET")
    if require_proof and not app_secret:
        raise RuntimeError("ARES_META_APP_SECRET is required while appsecret_proof is enabled")
    return lambda account: GraphBatchTransport(account, manifest.graph_version, tokens[account], app_secret=app_secret)


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Ares Campaign Engine v3")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    sub = ap.add_subparsers(dest="command", required=True)
    for name in ("validate", "plan"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--manifest", required=True)
    prevalidate = sub.add_parser("prevalidate")
    prevalidate.add_argument("--manifest", required=True)
    prevalidate.add_argument("--registry", default=str(DEFAULT_MEDIA))
    prevalidate.add_argument("--output", required=True)
    execute = sub.add_parser("execute")
    execute.add_argument("--manifest", required=True)
    execute.add_argument("--confirm-execute", action="store_true")
    execute.add_argument("--offline-fake", action="store_true", help="test transport; never contacts Meta")
    media = sub.add_parser("media-register")
    media.add_argument("--registry", default=str(DEFAULT_MEDIA))
    media.add_argument("--account-id", required=True)
    media.add_argument("--asset-id", required=True)
    media.add_argument("--checksum", required=True)
    media.add_argument("--vertical-video-id", required=True)
    media.add_argument("--square-video-id", required=True)
    media.add_argument("--ready", action="store_true")
    media.add_argument("--confirm-readback", action="store_true")
    summary = sub.add_parser("media-summary")
    summary.add_argument("--registry", default=str(DEFAULT_MEDIA))
    prestage = sub.add_parser("prestage-upload")
    prestage.add_argument("--registry", default=str(DEFAULT_MEDIA))
    prestage.add_argument("--account-id", required=True)
    prestage.add_argument("--page-id", required=True)
    prestage.add_argument("--asset-id", required=True)
    prestage.add_argument("--checksum", required=True)
    prestage.add_argument("--vertical-file", required=True)
    prestage.add_argument("--square-file", required=True)
    prestage.add_argument("--confirm-upload", action="store_true")
    cpv = sub.add_parser("build-cpv")
    cpv.add_argument("--registry", default=str(DEFAULT_MEDIA))
    cpv.add_argument("--assets-json", required=True)
    cpv.add_argument("--source-snapshot-json", required=True)
    cpv.add_argument("--mode", choices=["clone_prestaged", "from_zero_prestaged"], default="clone_prestaged")
    cpv.add_argument("--from-zero-specs-json")
    cpv.add_argument("--campaign-numbers", required=True)
    cpv.add_argument("--operational-date", required=True)
    cpv.add_argument("--request-id", required=True)
    cpv.add_argument("--status", choices=["PAUSED", "ACTIVE"], default="PAUSED")
    cpv.add_argument("--output", required=True)
    return ap


def _main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "media-register":
        if not args.confirm_readback:
            raise SystemExit("media-register requires --confirm-readback")
        record = MediaRegistry(args.registry).register(
            account_id=args.account_id, asset_id=args.asset_id, checksum=args.checksum,
            vertical_video_id=args.vertical_video_id, square_video_id=args.square_video_id,
            ready=args.ready, source="v3-cli-readback",
        )
        print(json.dumps({"status": "REGISTERED", "account_id": record["account_id"], "asset_id": record["asset_id"], "ready": record["ready"]}))
        return 0
    if args.command == "media-summary":
        print(json.dumps(MediaRegistry(args.registry).summary(), ensure_ascii=False))
        return 0
    if args.command == "prestage-upload":
        if not args.confirm_upload:
            raise SystemExit("prestage-upload requires --confirm-upload")
        config = load_json(args.config)
        if config.get("media_upload_enabled") is not True:
            raise SystemExit("v3 media upload is disabled in config")
        account = str(args.account_id).removeprefix("act_")
        account_cfg = (config.get("accounts") or {}).get(account) or {}
        token_item = account_cfg.get("token_item")
        if not token_item:
            raise SystemExit(f"missing token_item for account {account}")
        os.environ["ARES_META_GRAPH_VERSION"] = str(config.get("graph_version") or "v26.0")
        common = load_common()
        user_token, _ = common.get_token_from_1password(item_name=token_item)
        status, pages, _ = common.graph_get("me/accounts", user_token, {"fields": "id,name,tasks,access_token", "limit": 200})
        if status != 200:
            raise SystemExit(f"Page inventory failed http={status}")
        page = next((row for row in (pages.get("data") or []) if str(row.get("id")) == str(args.page_id)), None)
        if not page or "ADVERTISE" not in (page.get("tasks") or []):
            raise SystemExit("Page missing ADVERTISE task")
        uploader = AdAccountVideoUploader(
            common=common,
            user_token=user_token,
            account_id=account,
            graph_version=str(config.get("graph_version") or "v26.0"),
        )
        record = PrestageService(MediaRegistry(args.registry), uploader).prestage(
            account_id=account, asset_id=args.asset_id, checksum=args.checksum,
            vertical_path=args.vertical_file, square_path=args.square_file,
        )
        print(json.dumps({"status": "PRESTAGED_READY", "account_id": record["account_id"], "asset_id": record["asset_id"], "ready": record["ready"]}))
        return 0
    if args.command == "build-cpv":
        assets = load_json(args.assets_json).get("assets") or []
        source_selections = expand_source_selections(load_json(args.source_snapshot_json))
        from_zero_specs = None
        if args.from_zero_specs_json:
            from_zero_specs = load_json(args.from_zero_specs_json).get("from_zero_specs") or []
        if args.mode == "from_zero_prestaged" and from_zero_specs is None:
            raise SystemExit("from-zero build-cpv requires --from-zero-specs-json")
        numbers = [int(item.strip()) for item in args.campaign_numbers.split(",") if item.strip()]
        payload = build_cpv_manifest(
            registry=MediaRegistry(args.registry), asset_refs=assets, campaign_numbers=numbers,
            operational_date=args.operational_date, request_id=args.request_id, source_selections=source_selections,
            mode=args.mode, from_zero_specs=from_zero_specs, status=args.status,
        )
        Manifest.from_dict(payload)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({"status": "MANIFEST_BUILT_NOT_PREVALIDATED", "output": str(output), "campaigns": len(payload["campaigns"])}))
        return 0
    if args.command == "prevalidate":
        payload = prevalidate_payload(load_json(args.manifest), MediaRegistry(args.registry))
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({"status": "PREVALIDATED", "output": str(output), "content_digest": payload["prevalidation"]["content_digest"]}))
        return 0

    config = load_json(args.config)
    manifest = Manifest.from_dict(load_json(args.manifest))
    if args.command == "validate":
        print(json.dumps({"status": "VALID", "request_id": manifest.request_id, "campaigns": len(manifest.campaigns), "digest": manifest.digest}))
        return 0
    if args.command == "plan":
        engine = CampaignEngine(config, transport_factory=lambda account: FakeBatchTransport(account))
        print(json.dumps(engine.dry_run(manifest), ensure_ascii=False, indent=2))
        return 0
    if not args.confirm_execute:
        raise SystemExit("execute requires --confirm-execute")
    factory = (lambda account: FakeBatchTransport(account)) if args.offline_fake else real_transport_factory(config, manifest)
    result = CampaignEngine(config, transport_factory=factory).execute(manifest)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return _main(argv)
    except (EngineDisabled, ExecutionFailed, ManifestError, MediaNotReady, MediaUploadError, QuotaBlocked, BatchTransportError) as exc:
        status = "BLOCKED" if isinstance(exc, (EngineDisabled, ManifestError, MediaNotReady, QuotaBlocked)) else "FAILED"
        print(json.dumps({"status": status, "error_type": type(exc).__name__, "message": str(exc)[:500]}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
