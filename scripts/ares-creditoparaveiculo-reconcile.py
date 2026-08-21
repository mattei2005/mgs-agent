#!/usr/bin/env python3
"""Separate read-only Drive↔Meta reconciler for CPV campaign writer."""
from __future__ import annotations

import argparse
import fcntl
import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

MODULE_PATH = Path('/root/.hermes/profiles/ares/scripts/creditoparaveiculo-daily-create.py')
LOCK_PATH = Path('/root/.hermes/profiles/ares/locks/creditoparaveiculo-reconcile.lock')
spec = importlib.util.spec_from_file_location('cpv_daily_reconciler_module', MODULE_PATH)
if not spec or not spec.loader:
    raise RuntimeError('cannot load CPV daily module')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value or '').replace('Z', '+00:00'))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def asset_entry(row: dict[str, Any], conflicts: list[dict[str, Any]]) -> dict[str, Any]:
    own = [item for item in conflicts if str(item.get('asset_id') or '') == str(row.get('asset_id') or '')]
    return {
        'asset_id': row.get('asset_id'),
        'canonical_filename': row.get('canonical_filename'),
        'asset_drive_id': row.get('asset_drive_id'),
        'clean_checksum': row.get('clean_checksum'),
        'perceptual_fingerprint': row.get('perceptual_fingerprint'),
        'approved': not own,
        'meta_conflicts': own,
    }


def manifest_from_audit(path: Path, valid_seconds: int) -> dict[str, Any]:
    audit = json.loads(path.read_text(encoding='utf-8'))
    preflight = audit.get('preflight') or {}
    created = parse_utc(str(audit.get('created_at_utc') or ''))
    if utc_now() - created > timedelta(hours=6):
        raise RuntimeError('source audit is older than six hours')
    selected = preflight.get('selected_assets') or []
    conflicts = preflight.get('meta_conflicts') or []
    if len(selected) < 3:
        raise RuntimeError('source audit lacks selected asset evidence')
    assets = [asset_entry(row, conflicts) for row in selected]
    if not all(row['approved'] for row in assets):
        raise RuntimeError('source audit contains selected Meta conflicts')
    now = utc_now()
    return {
        'schema_version': 1,
        'status': 'valid',
        'account_id': mod.ACCOUNT_ID,
        'generated_at_utc': now.isoformat(),
        'valid_until_utc': (now + timedelta(seconds=max(300, valid_seconds))).isoformat(),
        'source': {'mode': 'validated_existing_audit', 'audit_path': str(path), 'audit_created_at_utc': audit.get('created_at_utc')},
        'meta_counts': {
            'ads_scanned': int(preflight.get('meta_ads_scanned_current_and_archived') or preflight.get('meta_ads_scanned') or 0),
            'video_ids_scanned': int(preflight.get('meta_video_ids_scanned') or 0),
        },
        'assets': assets,
    }


def manifest_from_live(valid_seconds: int) -> dict[str, Any]:
    common = mod.load_common()
    token, _ = common.get_token_from_1password(mod.TOKEN_ITEM, force_refresh=False)
    source = mod.source_preflight(common, token)
    page_token = source.pop('page_token')
    ads_all = mod.account_ads_snapshot(common, token)
    cleaned = mod.known_cleaned_daily_ids()
    ads = [
        row for row in ads_all
        if str(row.get('id') or '') not in cleaned['ads']
        and str((row.get('campaign') or {}).get('id') or '') not in cleaned['campaigns']
        and str((row.get('creative') or {}).get('id') or '') not in cleaned['creatives']
    ]
    video_ids = [item for item in mod.extract_video_ids(ads) if item not in cleaned['videos']]
    videos = mod.video_metadata(common, page_token, video_ids)
    drive_mod = mod.load_drive_module()
    drive_sa = drive_mod.extract_service_account(drive_mod.get_op_item_json())
    if drive_sa.get('client_email') != 'mgsagent@mgs-core-prod.iam.gserviceaccount.com' or drive_sa.get('project_id') != 'mgs-core-prod':
        raise RuntimeError('canonical Drive service account mismatch')
    drive_token = drive_mod.get_access_token(drive_sa)
    drive = mod.drive_inventory(drive_token)
    live_by_id = {str(row['id']): row for row in drive['files']}
    inventory = mod.load_inventory()
    candidates, _ = mod.pool_candidates(inventory, live_by_id, None, False)
    conflicts = mod.selected_meta_conflicts(candidates, ads, videos)
    assets = [asset_entry(row, conflicts) for row in candidates]
    if sum(row['approved'] for row in assets) < 3:
        raise RuntimeError('fewer than three reconciled assets')
    now = utc_now()
    return {
        'schema_version': 1,
        'status': 'valid',
        'account_id': mod.ACCOUNT_ID,
        'generated_at_utc': now.isoformat(),
        'valid_until_utc': (now + timedelta(seconds=max(300, valid_seconds))).isoformat(),
        'source': {'mode': 'live_separate_reconciliation', 'current_and_archived': True},
        'meta_counts': {'ads_scanned': len(ads_all), 'video_ids_scanned': len(video_ids)},
        'assets': assets,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--from-audit', type=Path)
    parser.add_argument('--valid-seconds', type=int, default=21600)
    args = parser.parse_args()
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open('a+') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        manifest = manifest_from_audit(args.from_audit, args.valid_seconds) if args.from_audit else manifest_from_live(args.valid_seconds)
        mod.atomic_json(mod.RECONCILIATION_PATH, manifest)
    approved = sum(bool(row.get('approved')) for row in manifest['assets'])
    print(json.dumps({
        'status': manifest['status'],
        'mode': (manifest.get('source') or {}).get('mode'),
        'assets': len(manifest['assets']),
        'approved': approved,
        'conflicted': len(manifest['assets']) - approved,
        'valid_until_utc': manifest['valid_until_utc'],
        'path': str(mod.RECONCILIATION_PATH),
        'meta_writes': 0,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
