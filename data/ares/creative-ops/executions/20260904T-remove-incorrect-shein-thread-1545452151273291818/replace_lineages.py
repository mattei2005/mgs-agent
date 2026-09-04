#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import importlib.util
import json
import mimetypes
import os
import shutil
import urllib.parse
from pathlib import Path
from typing import Any

BASE = Path('/root/mgs-agent/data/ares/creative-ops/executions/20260904T-remove-incorrect-shein-thread-1545452151273291818')
HELPER_PATH = Path('/root/mgs-agent/data/ares/creative-ops/executions/20260904T142558Z-kelly-shein-us-en-thread-1545439313246818334/process_batch.py')
INVENTORY = Path('/root/mgs-agent/data/ares/creative-ops/inventory/assets.jsonl')
BACKUPS = Path('/root/mgs-agent/backups/ares-creative-ops')
ROOT_ID = '0AEwt4Ye690ocUk9PVA'
EXPECTED_DRIVE = 'MGS-AGENTS'
EXPECTED_EMAIL = 'mgsagent@mgs-core-prod.iam.gserviceaccount.com'
EXPECTED_PROJECT = 'mgs-core-prod'
THREAD_ID = '1545452151273291818'
OPERATION = 'SHEIN_US_EN'
ANGLE = 'FREE_HAIRBRUSH'
CLAIM = 'FREE FOR YOU; HAIRBRUSH'
PRODUCT_TYPE = 'HAIR_STYLER'

NEW_ITEMS = [
    {
        'label': '14',
        'source_id': '1PU7aHTNl9x4f8n398zDBqRoAQ6v99oAf',
        'source_name': '2_14 US_SHEIN_EN_03-09  - CARREGADOR - Story (INGLES) .mp4',
        'destination_name': 'SHEIN_US_EN_VID_FREE_HAIRBRUSH_PV_001.mp4',
        'variant': '001',
        'old_asset_id': 'asset_6ff7666ea5b5accd6f84',
    },
    {
        'label': '15',
        'source_id': '1xC9wy5EEAC003RslKuwyd6rs92NXQTpn',
        'source_name': '3_15 US_SHEIN_EN_03-09  - CARREGADOR - Story (INGLES) .mp4',
        'destination_name': 'SHEIN_US_EN_VID_FREE_HAIRBRUSH_PV_002.mp4',
        'variant': '002',
        'old_asset_id': 'asset_1ce6dba99cec5bee0873',
    },
    {
        'label': '16',
        'source_id': '1dlQuRVxNcd2iZKOIdd3IgP-TF4VKFJI6',
        'source_name': '1_16 US_SHEIN_EN_03-09  - CARREGADOR - Story (INGLES) .mp4',
        'destination_name': 'SHEIN_US_EN_VID_FREE_HAIRBRUSH_PV_003.mp4',
        'variant': '003',
        'old_asset_id': 'asset_6369d0b16fa61bc001e4',
    },
]

OLD_ITEMS = [
    {
        'label': '14',
        'asset_id': 'asset_6ff7666ea5b5accd6f84',
        'source_id': '1HsTEpRnC9XndovoMk6BmtVoFilSDejUm',
        'source_name': '20_14 US_SHEIN_EN_03-09  - CARREGADOR - Story (INGLES) .mp4',
        'destination_id': '1jMQlMmrZvoxRnzMKiEmQABu7iFgyy5je',
        'destination_name': 'SHEIN_US_EN_VID_FREE_CLOTHES_PRESSER_PV_009.mp4',
    },
    {
        'label': '15',
        'asset_id': 'asset_1ce6dba99cec5bee0873',
        'source_id': '1Yf-4TDB4fN8NdlJvYHATItv1e2tCEBMJ',
        'source_name': '6_15 US_SHEIN_EN_03-09  - CARREGADOR - Story (INGLES) .mp4',
        'destination_id': '1WF2lnab2O3SGIvAxhfyy7Vg7KMvpLGaS',
        'destination_name': 'SHEIN_US_EN_VID_FREE_CLOTHES_PRESSER_PV_003.mp4',
    },
    {
        'label': '16',
        'asset_id': 'asset_6369d0b16fa61bc001e4',
        'source_id': '1lxmMrCUJq5pfMB61XG3lqD_4wzGWD8EZ',
        'source_name': '5_16 US_SHEIN_EN_03-09  - CARREGADOR - Story (INGLES) .mp4',
        'destination_id': '1GvEu2Qz9XCGVkec6WHl1shjin4TcnnHU',
        'destination_name': 'SHEIN_US_EN_VID_FREE_CLOTHES_PRESSER_PV_002.mp4',
    },
]


def utcnow() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def dump(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(tmp, path)


def load_helper():
    spec = importlib.util.spec_from_file_location('shein_helper', HELPER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError('cannot load canonical Drive helper')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def patch_trashed(drive, mod, file_id: str) -> dict[str, Any]:
    current = mod.api_get(drive, file_id)
    if not current.get('trashed'):
        params = urllib.parse.urlencode({
            'supportsAllDrives': 'true',
            'fields': 'id,name,parents,driveId,trashed,size,md5Checksum,webViewLink',
        })
        drive.request(
            f'https://www.googleapis.com/drive/v3/files/{file_id}?{params}',
            method='PATCH',
            data=json.dumps({'trashed': True}).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
        )
    return mod.api_get(drive, file_id)


def load_inventory() -> list[dict[str, Any]]:
    return [json.loads(line) for line in INVENTORY.read_text(encoding='utf-8').splitlines() if line.strip()]


def rewrite_inventory(rows: list[dict[str, Any]]) -> None:
    lock_path = INVENTORY.with_suffix(INVENTORY.suffix + '.lock')
    with lock_path.open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        tmp = INVENTORY.with_suffix(INVENTORY.suffix + '.tmp')
        tmp.write_text(''.join(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n' for row in rows), encoding='utf-8')
        os.replace(tmp, INVENTORY)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()

    mod = load_helper()
    executor = mod.load_executor()
    executor.load_env()
    sa = executor.service_account()
    if sa.get('client_email') != EXPECTED_EMAIL or sa.get('project_id') != EXPECTED_PROJECT:
        raise RuntimeError('canonical service-account identity mismatch')
    token, auth_mode = executor.build_access_token()
    if auth_mode != 'service_account':
        raise RuntimeError('non-service-account auth refused')
    drive = executor.Drive(token)
    root = drive.preflight_destination(auth_mode)
    shared = drive.request(f'https://www.googleapis.com/drive/v3/drives/{ROOT_ID}?fields=id,name') or {}
    if root.get('driveId') != ROOT_ID or shared.get('id') != ROOT_ID or shared.get('name') != EXPECTED_DRIVE:
        raise RuntimeError('canonical Shared Drive identity mismatch')

    upload_id = mod.resolve_existing_path(drive, ['CRIATIVOS', 'UPLOAD MANUAL'])
    ready_id = mod.resolve_existing_path(drive, ['CRIATIVOS', OPERATION, 'VID', '01_READY'])
    legacy_id = mod.resolve_existing_path(drive, ['CRIATIVOS', OPERATION, 'VID', '99_LEGACY'])
    lock_key = hashlib.sha256('|'.join(sorted(x['source_id'] for x in NEW_ITEMS)).encode()).hexdigest()[:20]
    lock_path = Path('/root/mgs-agent/tmp/ares-intake-locks') / f'shein-corrected-14-15-16-{lock_key}.lock'
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    with lock_path.open('a+') as batch_lock:
        fcntl.flock(batch_lock, fcntl.LOCK_EX)
        inventory_rows = load_inventory()
        by_asset = {row.get('asset_id'): row for row in inventory_rows if row.get('asset_id')}
        by_source = {row.get('source_drive_id'): row for row in inventory_rows if row.get('source_drive_id')}

        for old in OLD_ITEMS:
            row = by_asset.get(old['asset_id'])
            if not row or row.get('source_drive_id') != old['source_id'] or row.get('asset_drive_id') != old['destination_id']:
                raise RuntimeError(f'old lineage inventory identity mismatch: {old["label"]}')
            for role, fid, name, parent in (
                ('RAW_LEGACY', old['source_id'], old['source_name'], legacy_id),
                ('CLEAN_READY', old['destination_id'], old['destination_name'], ready_id),
            ):
                meta = mod.api_get(drive, fid)
                if meta.get('driveId') != ROOT_ID or meta.get('name') != name:
                    raise RuntimeError(f'old {role} identity mismatch: {old["label"]}')
                if not meta.get('trashed') and meta.get('parents') != [parent]:
                    raise RuntimeError(f'old {role} parent mismatch: {old["label"]}')
                if not meta.get('trashed') and not (meta.get('capabilities') or {}).get('canTrash'):
                    raise RuntimeError(f'old {role} lacks canTrash: {old["label"]}')

        raw_dir = BASE / 'work/raw'
        clean_dir = BASE / 'work/clean'
        frame_dir = BASE / 'work/frames'
        readback_dir = BASE / 'work/readback'
        for path in (raw_dir, clean_dir, frame_dir, readback_dir):
            path.mkdir(parents=True, exist_ok=True)

        live_ready = mod.list_children(drive, ready_id)
        plan = []
        for item in NEW_ITEMS:
            source_meta = mod.api_get(drive, item['source_id'])
            if source_meta.get('driveId') != ROOT_ID or source_meta.get('name') != item['source_name']:
                raise RuntimeError(f'new source identity mismatch: {item["label"]}')
            if source_meta.get('parents') not in ([upload_id], [legacy_id]) or source_meta.get('trashed'):
                raise RuntimeError(f'new source outside upload/legacy: {item["label"]}')
            caps = source_meta.get('capabilities') or {}
            if source_meta.get('parents') == [upload_id] and (not caps.get('canDownload') or not caps.get('canMoveItemWithinDrive')):
                raise RuntimeError(f'new source lacks required capabilities: {item["label"]}')

            raw = raw_dir / f'{item["label"]}.mp4'
            if not raw.exists() or raw.stat().st_size != int(source_meta.get('size') or 0):
                drive.download(item['source_id'], raw)
            tech = mod.ffprobe(raw)
            raw_sha = mod.sha256_file(raw)
            fingerprint = mod.fingerprint_video(raw, tech['duration'], frame_dir, item['label'])
            clean = clean_dir / f'{item["label"]}.mp4'
            if not clean.exists():
                clean_sha = mod.clean_and_verify(raw, clean)
            else:
                mod.verify_clean(clean)
                clean_sha = mod.sha256_file(clean)

            existing_row = by_source.get(item['source_id'])
            if existing_row:
                if existing_row.get('canonical_filename') != item['destination_name'] or existing_row.get('clean_checksum') != clean_sha:
                    raise RuntimeError(f'new source inventoried with conflicting identity: {item["label"]}')
            exact_names = [x for x in live_ready if x.get('name') == item['destination_name']]
            if len(exact_names) > 1:
                raise RuntimeError(f'multiple READY matches: {item["destination_name"]}')
            if exact_names:
                rb = readback_dir / f'preflight-{item["label"]}.mp4'
                drive.download(exact_names[0]['id'], rb)
                if mod.sha256_file(rb) != clean_sha:
                    raise RuntimeError(f'READY name occupied by different content: {item["destination_name"]}')
                mod.verify_clean(rb)

            if any(row.get('clean_checksum') == clean_sha and row.get('source_drive_id') != item['source_id'] for row in inventory_rows):
                raise RuntimeError(f'corrected source is exact duplicate of another lineage: {item["label"]}')
            plan.append({
                **item,
                'source_sha256': raw_sha,
                'clean_sha256': clean_sha,
                'fingerprint': fingerprint,
                'width': tech['width'],
                'height': tech['height'],
                'duration_seconds': tech['duration'],
                'source_created_time': source_meta.get('createdTime'),
                'clean_path': str(clean),
                'existing_destination_id': exact_names[0]['id'] if exact_names else None,
            })

        dry = {
            'generated_at_utc': utcnow(),
            'mode': 'apply' if args.apply else 'dry-run',
            'auth_mode': auth_mode,
            'shared_drive': shared.get('name'),
            'operation': OPERATION,
            'old_lineages_to_trash': OLD_ITEMS,
            'replacement_plan': [{k: v for k, v in x.items() if k != 'clean_path'} for x in plan],
            'visual_classification': {
                'product_type': PRODUCT_TYPE,
                'claim': CLAIM,
                'angle': ANGLE,
                'person': 'PERSON',
                'p_orient': 'PV',
                'placement': 'STORY',
            },
        }
        dump(BASE / 'dry-run.json', dry)
        if not args.apply:
            print(json.dumps({'all_pass': True, 'mode': 'dry-run', 'replacements': len(plan), 'old_lineages': len(OLD_ITEMS), 'dry_run': str(BASE / 'dry-run.json')}, ensure_ascii=False, indent=2))
            return 0

        BACKUPS.mkdir(parents=True, exist_ok=True)
        backup_stamp = dt.datetime.now(dt.UTC).strftime('%Y%m%dT%H%M%SZ')
        backup = BACKUPS / f'assets-before-kelly-shein-corrected-14-15-16-{backup_stamp}.jsonl'
        shutil.copy2(INVENTORY, backup)
        state_path = BASE / 'state.json'
        state = json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else {'created_at_utc': utcnow(), 'items': {}}
        results = []

        for item in plan:
            state_item = state['items'].setdefault(item['source_id'], {})
            destination_id = state_item.get('destination_id') or item['existing_destination_id']
            clean = Path(item['clean_path'])
            mod.verify_clean(clean)
            if mod.sha256_file(clean) != item['clean_sha256']:
                raise RuntimeError(f'clean SHA drift: {item["label"]}')
            if not destination_id:
                destination_id = drive.upload_resumable(
                    ready_id,
                    item['destination_name'],
                    clean,
                    mimetypes.guess_type(item['destination_name'])[0] or 'video/mp4',
                )
                state_item['destination_id'] = destination_id
                state_item['uploaded_at_utc'] = utcnow()
                dump(state_path, state)

            destination_meta = mod.api_get(drive, destination_id)
            if destination_meta.get('name') != item['destination_name'] or destination_meta.get('parents') != [ready_id] or destination_meta.get('driveId') != ROOT_ID or destination_meta.get('trashed'):
                raise RuntimeError(f'new destination readback failed: {item["label"]}')
            rb = readback_dir / f'{item["label"]}-{item["destination_name"]}'
            drive.download(destination_id, rb)
            if mod.sha256_file(rb) != item['clean_sha256']:
                raise RuntimeError(f'new destination SHA readback failed: {item["label"]}')
            mod.verify_clean(rb)
            state_item['destination_verified'] = True
            dump(state_path, state)

            source_meta = mod.api_get(drive, item['source_id'])
            if source_meta.get('parents') == [upload_id]:
                mod.move_file(drive, item['source_id'], upload_id, legacy_id)
            source_after = mod.api_get(drive, item['source_id'])
            if source_after.get('parents') != [legacy_id] or source_after.get('driveId') != ROOT_ID or source_after.get('trashed'):
                raise RuntimeError(f'new source LEGACY readback failed: {item["label"]}')
            state_item['legacy_verified'] = True
            dump(state_path, state)

            asset_id = 'asset_' + hashlib.sha256((item['source_id'] + ':' + destination_id).encode()).hexdigest()[:20]
            inventory_row = {
                'asset_id': asset_id,
                'original_filename': item['source_name'],
                'canonical_filename': item['destination_name'],
                'source_manager': 'KELLY',
                'requested_by': 'Kelly Nice',
                'created_by': 'KELLY',
                'vertical': 'SHEIN',
                'product_type': PRODUCT_TYPE,
                'country': 'US',
                'language': 'EN',
                'strategy': 'TRAFEGO_DIRETO',
                'ad_account_id': None,
                'source_drive_id': item['source_id'],
                'asset_drive_id': destination_id,
                'original_checksum': item['source_sha256'],
                'clean_checksum': item['clean_sha256'],
                'perceptual_fingerprint': item['fingerprint'],
                'format': 'VID',
                'angle': ANGLE,
                'person': 'PERSON',
                'orientation': 'VERTICAL',
                'p_orient': 'PV',
                'variant': item['variant'],
                'status': '01_READY',
                'reservation_status': 'RESERVADO_PELO_GESTOR',
                'ares_eligible': False,
                'used_by': None,
                'campaign_owner': 'Kelly',
                'meta_ad_id': None,
                'meta_creative_id': None,
                'meta_image_hash': None,
                'meta_video_id': None,
                'effective_object_story_id': None,
                'width': item['width'],
                'height': item['height'],
                'aspect_ratio': '9:16',
                'placement_fit': 'STORY',
                'metadata_clean': True,
                'first_seen_at': item['source_created_time'] or utcnow(),
                'last_reconciled_at': utcnow(),
                'performance_label': 'UNKNOWN',
                'notes': f'Upload corrigido por Kelly e tratado por Ares. Produto visual: {PRODUCT_TYPE}. Claim visual dominante: {CLAIM}. Substitui a linhagem errada {item["old_asset_id"]}. Original preservado em 99_LEGACY. Fail-closed até liberação/conciliação Meta × Drive.',
                'source_path': 'MGS-AGENTS/CRIATIVOS/SHEIN_US_EN/VID/99_LEGACY',
                'asset_path': 'MGS-AGENTS/CRIATIVOS/SHEIN_US_EN/VID/01_READY',
                'webViewLink': destination_meta.get('webViewLink'),
                'local_clean_path': None,
                'thread_id': THREAD_ID,
                'supersedes_asset_id': item['old_asset_id'],
            }
            mod.append_inventory(inventory_row)
            state_item['inventory_verified'] = True
            state_item['asset_id'] = asset_id
            dump(state_path, state)
            results.append({
                'label': item['label'],
                'source_id': item['source_id'],
                'source_name': item['source_name'],
                'destination_id': destination_id,
                'destination_name': item['destination_name'],
                'asset_id': asset_id,
                'old_asset_id': item['old_asset_id'],
                'source_sha256': item['source_sha256'],
                'clean_sha256': item['clean_sha256'],
                'metadata_clean': True,
                'drive_readback_verified': True,
                'sha256_readback_verified': True,
            })

        new_by_old = {result['old_asset_id']: result for result in results}
        old_readback = []
        for old in OLD_ITEMS:
            raw_after = patch_trashed(drive, mod, old['source_id'])
            clean_after = patch_trashed(drive, mod, old['destination_id'])
            if not raw_after.get('trashed') or not clean_after.get('trashed'):
                raise RuntimeError(f'old lineage trash readback failed: {old["label"]}')
            old_readback.append({
                'label': old['label'],
                'asset_id': old['asset_id'],
                'source_trashed': True,
                'destination_trashed': True,
            })

        inventory_rows = load_inventory()
        removed_at = utcnow()
        matches = 0
        for row in inventory_rows:
            replacement = new_by_old.get(row.get('asset_id'))
            if not replacement:
                continue
            matches += 1
            row.setdefault('status_before_removal', row.get('status'))
            row['status'] = 'TRASHED_BY_MANAGER_REQUEST'
            row['reservation_status'] = 'REMOVIDO_PELO_GESTOR'
            row['ares_eligible'] = False
            row['removed_by'] = 'Kelly Nice'
            row['removed_at'] = removed_at
            row['removal_mode'] = 'TRASH_REVERSIBLE'
            row['removal_request_thread_id'] = THREAD_ID
            row['source_trashed'] = True
            row['asset_trashed'] = True
            row['last_reconciled_at'] = removed_at
            row['superseded_by_asset_id'] = replacement['asset_id']
            note = ' Linhagem errada removida por pedido da Kelly e substituída pelo upload corrigido; versão limpa e original enviados à lixeira reversível do Shared Drive.'
            if note.strip() not in str(row.get('notes') or ''):
                row['notes'] = str(row.get('notes') or '').rstrip() + note
        if matches != len(OLD_ITEMS):
            raise RuntimeError(f'old inventory update match count={matches}')
        rewrite_inventory(inventory_rows)

        final_rows = load_inventory()
        by_asset_final = {row.get('asset_id'): row for row in final_rows}
        final_new = []
        for result in results:
            src = mod.api_get(drive, result['source_id'])
            dst = mod.api_get(drive, result['destination_id'])
            inv = by_asset_final.get(result['asset_id'])
            if src.get('parents') != [legacy_id] or src.get('trashed'):
                raise RuntimeError(f'final replacement source readback failed: {result["label"]}')
            if dst.get('parents') != [ready_id] or dst.get('trashed') or dst.get('name') != result['destination_name']:
                raise RuntimeError(f'final replacement destination readback failed: {result["label"]}')
            if not inv or inv.get('status') != '01_READY' or inv.get('reservation_status') != 'RESERVADO_PELO_GESTOR' or inv.get('ares_eligible') is not False:
                raise RuntimeError(f'final replacement inventory readback failed: {result["label"]}')
            final_new.append({'label': result['label'], 'source_in_legacy': True, 'destination_in_ready': True, 'inventory_ok': True})
        for old in OLD_ITEMS:
            inv = by_asset_final.get(old['asset_id'])
            if not inv or inv.get('status') != 'TRASHED_BY_MANAGER_REQUEST' or inv.get('reservation_status') != 'REMOVIDO_PELO_GESTOR' or inv.get('ares_eligible') is not False:
                raise RuntimeError(f'final old inventory readback failed: {old["label"]}')
            if not mod.api_get(drive, old['source_id']).get('trashed') or not mod.api_get(drive, old['destination_id']).get('trashed'):
                raise RuntimeError(f'final old Drive readback failed: {old["label"]}')

        direct_remaining = [x for x in mod.list_children(drive, upload_id) if x.get('mimeType') != mod.FOLDER_MIME]
        expected_pending = [x for x in direct_remaining if x.get('id') in {item['source_id'] for item in NEW_ITEMS}]
        if expected_pending:
            raise RuntimeError('replacement sources still pending in UPLOAD MANUAL')

        report = {
            'completed_at_utc': utcnow(),
            'all_pass': True,
            'auth_mode': auth_mode,
            'shared_drive': shared.get('name'),
            'operation': OPERATION,
            'thread_id': THREAD_ID,
            'old_lineages_removed': len(OLD_ITEMS),
            'replacement_lineages_ready': len(results),
            'metadata_clean_verified': len(results),
            'reservation_status': 'RESERVADO_PELO_GESTOR',
            'ares_eligible': False,
            'upload_manual_expected_remaining': len(expected_pending),
            'upload_manual_other_remaining': len(direct_remaining),
            'inventory_backup': str(backup),
            'replacements': results,
            'old_readback': old_readback,
            'final_new_readback': final_new,
        }
        dump(BASE / 'replacement-result.json', report)
        print(json.dumps({
            'all_pass': True,
            'old_lineages_removed': len(OLD_ITEMS),
            'replacement_lineages_ready': len(results),
            'metadata_clean_verified': len(results),
            'upload_manual_expected_remaining': len(expected_pending),
            'upload_manual_other_remaining': len(direct_remaining),
            'result': str(BASE / 'replacement-result.json'),
        }, ensure_ascii=False, indent=2))
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
