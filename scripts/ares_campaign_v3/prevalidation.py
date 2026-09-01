from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from .eggbev_page_eligibility import PageEligibilityError, require_page_eligible
from .media_registry import MediaRegistry
from .schema import Manifest, ManifestError


def _require_subset(actual: Any, expected: Any, path: str) -> None:
    """Require an operation policy subset without rejecting extra API fields."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            raise ManifestError(f"account campaign policy requires object at {path}")
        for key, value in expected.items():
            if key not in actual:
                raise ManifestError(f"account campaign policy missing {path}.{key}")
            _require_subset(actual[key], value, f"{path}.{key}")
        return
    if actual != expected:
        raise ManifestError(
            f"account campaign policy requires {path}={json.dumps(expected, ensure_ascii=False, sort_keys=True)}"
        )


def content_digest(payload: dict[str, Any]) -> str:
    clean = copy.deepcopy(payload)
    clean.pop("prevalidated", None)
    clean.pop("prevalidation", None)
    encoded = json.dumps(clean, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def verify_prevalidation(payload: dict[str, Any]) -> bool:
    prevalidation = payload.get("prevalidation") or {}
    expected = str(prevalidation.get("content_digest") or "")
    return payload.get("prevalidated") is True and bool(expected) and expected == content_digest(payload)


def validate_account_policy(manifest: Manifest, config: dict[str, Any]) -> None:
    accounts = config.get("accounts") or {}
    require_registration = config.get("require_account_registration") is True
    for campaign in manifest.campaigns:
        account = accounts.get(campaign.account_id)
        if account is None:
            if require_registration:
                raise ManifestError(f"account {campaign.account_id} is not registered in engine v3")
            continue
        if str(account.get("app_key") or "") != campaign.app_key:
            raise ManifestError(f"account {campaign.account_id} app_key mismatch")

        supported_modes = set(account.get("supported_modes") or [])
        if config.get("require_explicit_account_modes") is True and not supported_modes:
            raise ManifestError(
                f"account {campaign.account_id} must explicitly declare supported_modes"
            )
        if supported_modes and campaign.mode not in supported_modes:
            raise ManifestError(
                f"account {campaign.account_id} does not support mode {campaign.mode}"
            )

        serving_route = str(account.get("ad_serving_route") or "").strip()
        allowed_serving_routes = {
            "lineage_required_for_new_media",
            "direct_and_lineage_verified",
        }
        if config.get("require_explicit_ad_serving_route") is True and not serving_route:
            raise ManifestError(
                f"account {campaign.account_id} must explicitly declare ad_serving_route"
            )
        if serving_route and serving_route not in allowed_serving_routes:
            raise ManifestError(
                f"account {campaign.account_id} has unsupported ad_serving_route {serving_route}"
            )
        if serving_route == "lineage_required_for_new_media" and campaign.mode == "from_zero_prestaged":
            raise ManifestError(
                f"account {campaign.account_id} requires ad copy lineage for new media; from_zero_prestaged is forbidden"
            )
        if account.get("pure_clone_tracking_required") is True and campaign.mode == "pure_clone":
            if not campaign.source_adset_id or not campaign.adset_name or not campaign.ads:
                raise ManifestError(
                    f"account {campaign.account_id} requires tracking-aware pure_clone with source adset, ad names and creative payloads"
                )

        base_policy = dict(account.get("campaign_policy") or {})
        mode_policies = base_policy.pop("by_mode", {}) or {}
        policy = {**base_policy, **dict(mode_policies.get(campaign.mode) or {})}
        required_operation = str(account.get("operation") or "").strip()
        if required_operation and manifest.operation != required_operation:
            raise ManifestError(
                f"account {campaign.account_id} requires operation {required_operation}"
            )
        if manifest.operation == "Eggbev-US-CC-EN-BOT":
            page_ids: set[str] = set()
            promoted = (campaign.adset_create or {}).get("promoted_object") or {}
            if promoted.get("page_id"):
                page_ids.add(str(promoted["page_id"]))
            for ad in campaign.ads:
                story = (ad.creative_payload or {}).get("object_story_spec") or {}
                if story.get("page_id"):
                    page_ids.add(str(story["page_id"]))
            if len(page_ids) > 1:
                raise ManifestError("Eggbev Page identity is ambiguous in manifest")
            try:
                require_page_eligible(campaign.name, meta_page_id=next(iter(page_ids), None))
            except PageEligibilityError as exc:
                raise ManifestError(str(exc)) from exc
        name_regex = policy.get("name_regex")
        if name_regex and re.fullmatch(str(name_regex), campaign.name) is None:
            raise ManifestError(f"campaign name violates account naming policy: {campaign.name}")

        if policy.get("budget_update_required"):
            budget_source = str(policy.get("budget_source") or "campaign_updates")
            if budget_source == "campaign_create":
                raw_budget = campaign.campaign_create.get("daily_budget")
            elif budget_source == "campaign_updates":
                raw_budget = campaign.campaign_updates.get("daily_budget")
            else:
                raise ManifestError(f"unsupported campaign policy budget_source: {budget_source}")
            try:
                budget_minor = int(str(raw_budget))
            except (TypeError, ValueError) as exc:
                raise ManifestError("account campaign policy requires explicit daily_budget") from exc
            if budget_minor <= 0:
                raise ManifestError("daily_budget must be a positive minor-unit integer")

        allowed_ad_counts = {int(item) for item in (policy.get("allowed_ad_counts") or [])}
        if allowed_ad_counts and len(campaign.ads) not in allowed_ad_counts:
            raise ManifestError(
                f"account campaign policy allows ad counts {sorted(allowed_ad_counts)}; got {len(campaign.ads)}"
            )

        if policy.get("required_campaign_create"):
            _require_subset(
                campaign.campaign_create,
                policy["required_campaign_create"],
                "campaign_create",
            )
        if policy.get("required_adset_create"):
            _require_subset(
                campaign.adset_create,
                policy["required_adset_create"],
                "adset_create",
            )

        required_status = str(policy.get("configured_status") or "").upper()
        if required_status and campaign.status != required_status:
            raise ManifestError(f"account campaign policy requires status {required_status}")

        required_local_time = policy.get("start_local_time")
        immediate_override_ids = {str(value) for value in (policy.get("immediate_start_request_ids") or [])}
        if required_local_time and manifest.request_id not in immediate_override_ids:
            start = datetime.fromisoformat(campaign.start_time.replace("Z", "+00:00"))
            local = start.astimezone(ZoneInfo(str(account.get("timezone") or "UTC")))
            if local.strftime("%H:%M") != str(required_local_time):
                raise ManifestError(
                    f"account campaign policy requires start_time {required_local_time} {account.get('timezone') or 'UTC'}"
                )

        if campaign.mode == "pure_clone":
            allowed = set(policy.get("pure_clone_allowed_update_keys") or [])
            unexpected = set(campaign.campaign_updates) - allowed
            if unexpected:
                raise ManifestError(
                    f"pure_clone account policy forbids campaign_updates: {sorted(unexpected)}"
                )


def prevalidate_payload(payload: dict[str, Any], registry: MediaRegistry) -> dict[str, Any]:
    manifest = Manifest.from_dict(payload)
    checks = ["schema_v3", "unique_idempotency", "timezone_start", "safe_creative_payload"]
    media_keys: list[str] = []
    source_ad_ids: list[str] = []
    for campaign in manifest.campaigns:
        for ad in campaign.ads:
            if ad.source_ad_id:
                source_ad_ids.append(ad.source_ad_id)
            if ad.media is None:
                continue
            record = registry.require_ready(campaign.account_id, ad.media.asset_id, ad.media.checksum)
            if str(record["vertical_video_id"]) != ad.media.vertical_video_id or str(record["square_video_id"]) != ad.media.square_video_id:
                raise ManifestError(f"manifest media IDs drifted for asset={ad.media.asset_id}")
            if record.get("upload_edge") != "ad_account_advideos" or record.get("association_verified") is not True:
                raise ManifestError(f"manifest media is not associated with the ad account for asset={ad.media.asset_id}")
            media_keys.append(f"{campaign.account_id}|{ad.media.asset_id}|{ad.media.checksum}")
    if len(media_keys) != len(set(media_keys)):
        raise ManifestError("duplicate media lineage in manifest")
    if media_keys:
        checks.extend(["media_registry_exact", "media_lineage_unique", "ad_account_video_association"])
    if source_ad_ids:
        checks.append("source_ad_lineage")
    result = copy.deepcopy(payload)
    result.pop("prevalidation", None)
    result["prevalidated"] = True
    result["prevalidation"] = {
        "engine_version": 3,
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "content_digest": content_digest(result),
    }
    if not verify_prevalidation(result):
        raise RuntimeError("prevalidation digest self-check failed")
    return result
