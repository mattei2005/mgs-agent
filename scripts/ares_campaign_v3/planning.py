from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .schema import CampaignSpec, Manifest
from .transport import BatchOperation


@dataclass(frozen=True)
class StagePlan:
    name: str
    operations: tuple[BatchOperation, ...]


@dataclass(frozen=True)
class BundlePlan:
    account_id: str
    app_key: str
    index: int
    campaigns: tuple[CampaignSpec, ...]
    stages: tuple[StagePlan, ...]
    outer_write_calls: int
    outer_readback_calls: int = 1
    intermediate_get_calls: int = 0


@dataclass(frozen=True)
class ExecutionPlan:
    request_id: str
    lanes: dict[str, tuple[BundlePlan, ...]]

    @property
    def global_wave_count(self) -> int:
        return max((len(rows) for rows in self.lanes.values()), default=0)

    @property
    def campaigns_per_global_wave(self) -> list[int]:
        return [sum(len(rows[index].campaigns) for rows in self.lanes.values() if index < len(rows)) for index in range(self.global_wave_count)]

    def summary(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "lane_count": len(self.lanes),
            "global_wave_count": self.global_wave_count,
            "campaigns_per_global_wave": self.campaigns_per_global_wave,
            "lanes": {
                account: [
                    {
                        "bundle": row.index,
                        "campaigns": len(row.campaigns),
                        "modes": sorted({campaign.mode for campaign in row.campaigns}),
                        "outer_write_calls": row.outer_write_calls,
                        "outer_readback_calls": row.outer_readback_calls,
                        "intermediate_get_calls": row.intermediate_get_calls,
                    }
                    for row in bundles
                ]
                for account, bundles in self.lanes.items()
            },
        }


class Planner:
    def __init__(self, *, bundle_size: int = 2, max_ads_per_batch: int = 10):
        self.bundle_size = int(bundle_size)
        self.max_ads_per_batch = int(max_ads_per_batch)
        if self.bundle_size != 2:
            raise ValueError("v3 bundle_size is fixed at two")
        if self.max_ads_per_batch > 10 or self.max_ads_per_batch < 1:
            raise ValueError("max_ads_per_batch must be 1..10")

    @staticmethod
    def _pure_stage(campaigns: tuple[CampaignSpec, ...]) -> StagePlan:
        ops = []
        for index, campaign in enumerate(campaigns, 1):
            ops.append(BatchOperation(
                name=f"campaign_copy_{index}", method="POST", relative_url=f"{campaign.source_campaign_id}/copies",
                body={
                    "deep_copy": "true",
                    "status_option": campaign.status,
                    "start_time": campaign.start_time,
                    "rename_options": json.dumps({"rename_strategy": "NO_RENAME"}, separators=(",", ":")),
                },
                kind="pure_clone",
            ))
        return StagePlan("pure_clone_copy", tuple(ops))

    @staticmethod
    def _pure_update_stage(campaigns: tuple[CampaignSpec, ...]) -> StagePlan:
        ops = []
        for index, campaign in enumerate(campaigns, 1):
            ops.append(BatchOperation(
                name=f"pure_clone_update_{index}",
                method="POST",
                relative_url=f"{{campaign_id_{index}}}",
                body={"name": campaign.name, **campaign.campaign_updates, "status": campaign.status},
                kind="campaign_update",
            ))
        return StagePlan("pure_clone_update", tuple(ops))

    @staticmethod
    def _prestaged_stages(campaigns: tuple[CampaignSpec, ...]) -> tuple[StagePlan, ...]:
        copies = []
        shell_updates = []
        adset_copies = []
        ad_copies = []
        ad_name_updates = []
        for ci, campaign in enumerate(campaigns, 1):
            copies.append(BatchOperation(
                name=f"campaign_copy_{ci}", method="POST", relative_url=f"{campaign.source_campaign_id}/copies",
                body={"deep_copy": "false", "status_option": "PAUSED", "start_time": campaign.start_time}, kind="campaign_copy",
            ))
            shell_updates.extend([
                BatchOperation(name=f"campaign_update_{ci}", method="POST", relative_url=f"{{campaign_id_{ci}}}", body={"name": campaign.name, "status": campaign.status, "start_time": campaign.start_time, **campaign.campaign_updates}, kind="campaign_update"),
                BatchOperation(name=f"adset_update_{ci}", method="POST", relative_url=f"{{adset_id_{ci}}}", body={"name": campaign.adset_name or campaign.name, "status": campaign.status}, kind="adset_update"),
            ])
            adset_copies.append(BatchOperation(name=f"adset_copy_{ci}", method="POST", relative_url=f"{campaign.source_adset_id}/copies", body={"campaign_id": f"{{campaign_id_{ci}}}", "deep_copy": "false", "status_option": campaign.status, "start_time": campaign.start_time}, kind="adset_copy"))
            for ai, ad in enumerate(campaign.ads, 1):
                ad_copies.append(BatchOperation(
                    name=f"ad_copy_{ci}_{ai}", method="POST", relative_url=f"{ad.source_ad_id}/copies",
                    body={"adset_id": f"{{adset_id_{ci}}}", "creative_parameters": ad.creative_payload, "status_option": campaign.status, "rename_options": {"rename_strategy": "NO_RENAME"}},
                    kind="ad_copy_with_creative",
                ))
                ad_name_updates.append(BatchOperation(name=f"ad_name_update_{ci}_{ai}", method="POST", relative_url=f"{{copied_ad_id_{ci}_{ai}}}", body={"name": ad.name, "status": campaign.status}, kind="ad_name_update"))
        return (
            StagePlan("campaign_copy", tuple(copies)),
            StagePlan("adset_copy", tuple(adset_copies)),
            StagePlan("campaign_adset_update", tuple(shell_updates)),
            StagePlan("ad_copy_with_creative", tuple(ad_copies)),
            StagePlan("ad_name_update", tuple(ad_name_updates)),
        )

    @staticmethod
    def _from_zero_stages(campaigns: tuple[CampaignSpec, ...]) -> tuple[StagePlan, ...]:
        account_id = campaigns[0].account_id
        campaign_ops = []
        adset_ops = []
        creative_ops = []
        ad_ops = []
        finalize_ops = []
        for ci, campaign in enumerate(campaigns, 1):
            campaign_ops.append(BatchOperation(
                name=f"campaign_create_{ci}", method="POST", relative_url=f"act_{account_id}/campaigns",
                body={**campaign.campaign_create, "name": campaign.name, "status": "PAUSED"},
                kind="campaign_create",
            ))
            adset_ops.append(BatchOperation(
                name=f"adset_create_{ci}", method="POST", relative_url=f"act_{account_id}/adsets",
                body={
                    **campaign.adset_create,
                    "name": campaign.adset_name,
                    "campaign_id": f"{{campaign_id_{ci}}}",
                    "status": "ACTIVE",
                    "start_time": campaign.start_time,
                },
                kind="adset_create",
            ))
            for ai, ad in enumerate(campaign.ads, 1):
                creative_ops.append(BatchOperation(
                    name=f"creative_create_{ci}_{ai}", method="POST", relative_url=f"act_{account_id}/adcreatives",
                    body=ad.creative_payload, kind="creative_create",
                ))
                ad_ops.append(BatchOperation(
                    name=f"ad_create_{ci}_{ai}", method="POST", relative_url=f"act_{account_id}/ads",
                    body={
                        "name": ad.name,
                        "adset_id": f"{{adset_id_{ci}}}",
                        "creative": {"creative_id": f"{{creative_id_{ci}_{ai}}}"},
                        "status": "ACTIVE",
                    },
                    kind="ad_create",
                ))
            finalize_ops.append(BatchOperation(
                name=f"campaign_finalize_{ci}", method="POST", relative_url=f"{{campaign_id_{ci}}}",
                body={"status": campaign.status}, kind="campaign_finalize",
            ))
        return (
            StagePlan("campaign_create", tuple(campaign_ops)),
            StagePlan("adset_create", tuple(adset_ops)),
            StagePlan("creative_create", tuple(creative_ops)),
            StagePlan("ad_create", tuple(ad_ops)),
            StagePlan("campaign_finalize", tuple(finalize_ops)),
        )

    @staticmethod
    def _readback_placeholders(campaigns: tuple[CampaignSpec, ...]) -> StagePlan:
        ops = []
        for ci, _ in enumerate(campaigns, 1):
            for suffix in ("", "/adsets", "/ads"):
                ops.append(BatchOperation(name=f"readback_{ci}_{suffix or 'campaign'}", method="GET", relative_url=f"{{campaign_id_{ci}}}{suffix}", kind="readback"))
        return StagePlan("consolidated_readback", tuple(ops))

    def build(self, manifest: Manifest) -> ExecutionPlan:
        grouped: dict[str, list[CampaignSpec]] = {}
        for campaign in manifest.campaigns:
            grouped.setdefault(campaign.account_id, []).append(campaign)
        lanes: dict[str, tuple[BundlePlan, ...]] = {}
        for account, campaigns in grouped.items():
            bundles = []
            for offset in range(0, len(campaigns), self.bundle_size):
                chunk = tuple(campaigns[offset:offset + self.bundle_size])
                modes = {campaign.mode for campaign in chunk}
                if len(modes) != 1:
                    raise ValueError("a bundle cannot mix execution modes")
                mode = next(iter(modes))
                if mode == "pure_clone":
                    stages = (self._pure_stage(chunk), self._pure_update_stage(chunk), self._readback_placeholders(chunk))
                    outer_write_calls = 2
                elif mode in {"clone_prestaged", "clone_page_switch"}:
                    stages = (*self._prestaged_stages(chunk), self._readback_placeholders(chunk))
                    outer_write_calls = 5
                    ad_count = sum(len(campaign.ads) for campaign in chunk)
                    if ad_count > self.max_ads_per_batch:
                        raise ValueError("ad batch exceeds max_ads_per_batch")
                else:
                    stages = (*self._from_zero_stages(chunk), self._readback_placeholders(chunk))
                    outer_write_calls = 5
                    ad_count = sum(len(campaign.ads) for campaign in chunk)
                    if ad_count > self.max_ads_per_batch:
                        raise ValueError("ad batch exceeds max_ads_per_batch")
                bundles.append(BundlePlan(account, chunk[0].app_key, len(bundles) + 1, chunk, stages, outer_write_calls))
            lanes[account] = tuple(bundles)
        return ExecutionPlan(manifest.request_id, lanes)
