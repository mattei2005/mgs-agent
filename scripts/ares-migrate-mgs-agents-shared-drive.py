#!/usr/bin/env python3
"""Controlled, resumable migration of the full My Drive MGS-AGENTS tree.

- Recreates folder hierarchy in Shared Drive (folders receive new IDs).
- Moves eligible files to preserve IDs/checksums.
- Copies externally-owned files and records old -> new IDs.
- Validates the entire destination.
- Moves the old source tree into a My Drive backup container after PASS.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import importlib.util
import json
import os
import sys
import time
import urllib.error
import urllib.parse
from collections import Counter, deque
from pathlib import Path

REPO = Path('/root/mgs-agent')
MODULE = REPO / 'scripts/ares-execute-creative-copy-clean.py'
INVENTORY = REPO / 'data/ares/creative-ops/shared-drive-migration/20260716T001727Z/mgs-agents-full-inventory.json'
SOURCE_ROOT = '14ica5TVauTrzAxcl4T-ViJorF89vRKIl'
SOURCE_PARENT = '0AEK1IDaqSuDlUk9PVA'
TARGET_DRIVE = '0AEwt4Ye690ocUk9PVA'
TARGET_NAME = 'MGS-AGENTS'
FOLDER_MIME = 'application/vnd.google-apps.folder'
WORK = REPO / 'tmp/ares-shared-drive-migration-live'
CHECKPOINT = WORK / 'checkpoint.json'
LOG = WORK / 'events.jsonl'
LOCK = REPO / 'tmp/ares-intake-locks/mgs-agents-shared-drive-migration.lock'
FINAL_BASE = REPO / 'data/ares/creative-ops/shared-drive-migration'
MIGRATION_TAG = 'mgs-agents-shared-drive-20260716'

spec = importlib.util.spec_from_file_location('drive_mod', MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(mod)
mod.load_env()


def atomic_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(tmp, path)


def event(kind: str, **data) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    payload = {'ts_utc': dt.datetime.now(dt.UTC).isoformat(), 'event': kind, **data}
    with LOG.open('a', encoding='utf-8') as f:
        f.write(json.dumps(payload, ensure_ascii=False) + '\n')


def parse_error(exc: urllib.error.HTTPError) -> dict:
    raw = exc.read().decode(errors='ignore')
    try:
        body = json.loads(raw)
    except Exception:
        body = {'raw': raw[:2000]}
    return {'http_status': exc.code, 'body': body}


class ApiFailure(RuntimeError):
    def __init__(self, action: str, detail: dict):
        super().__init__(f'{action}: {json.dumps(detail, ensure_ascii=False)[:1500]}')
        self.action = action
        self.detail = detail


def api(drive, url: str, *, action: str, method: str = 'GET', data: bytes | None = None, headers: dict | None = None):
    for attempt in range(1, 9):
        try:
            return drive.request(url, method=method, data=data, headers=headers) or {}
        except urllib.error.HTTPError as exc:
            detail = parse_error(exc)
            text = json.dumps(detail, ensure_ascii=False)
            retryable = exc.code in {429, 500, 502, 503, 504} or (exc.code == 403 and any(x in text for x in ('rateLimitExceeded', 'userRateLimitExceeded', 'backendError')))
            if retryable and attempt < 8:
                wait = min(60, 2 ** attempt)
                event('api_retry', action=action, attempt=attempt, wait_seconds=wait, detail=detail)
                time.sleep(wait)
                continue
            raise ApiFailure(action, detail) from exc


def file_get(drive, file_id: str) -> dict:
    fields = 'id,name,mimeType,parents,driveId,size,md5Checksum,headRevisionId,version,trashed,createdTime,modifiedTime,ownedByMe,owners(displayName,emailAddress),appProperties,capabilities(canMoveItemIntoTeamDrive,canMoveItemWithinDrive,canTrash,canDelete)'
    q = urllib.parse.urlencode({'supportsAllDrives': 'true', 'fields': fields})
    return api(drive, f'https://www.googleapis.com/drive/v3/files/{file_id}?{q}', action=f'files.get:{file_id}')


def drive_get(drive) -> dict:
    q = urllib.parse.urlencode({'fields': 'id,name,capabilities(canAddChildren,canManageMembers,canRename,canTrashChildren)'})
    return api(drive, f'https://www.googleapis.com/drive/v3/drives/{TARGET_DRIVE}?{q}', action='drives.get')


def find_migrated_child(drive, parent_id: str, source_id: str) -> list[dict]:
    query = f"'{parent_id}' in parents and trashed=false and appProperties has {{ key='mgs_source_id' and value='{source_id}' }}"
    params = {'q': query, 'fields': 'files(id,name,mimeType,parents,driveId,size,md5Checksum,appProperties,trashed)', 'pageSize': '100', 'supportsAllDrives': 'true', 'includeItemsFromAllDrives': 'true'}
    data = api(drive, 'https://www.googleapis.com/drive/v3/files?' + urllib.parse.urlencode(params), action=f'find_migrated:{source_id}')
    return data.get('files', [])


def create_folder(drive, parent_id: str, row: dict) -> dict:
    found = find_migrated_child(drive, parent_id, row['id'])
    if len(found) == 1:
        return found[0]
    if len(found) > 1:
        raise RuntimeError(f"duplicate migrated folders for {row['id']}: {[x['id'] for x in found]}")
    body = {'name': row['name'], 'mimeType': FOLDER_MIME, 'parents': [parent_id], 'appProperties': {'mgs_source_id': row['id'], 'mgs_migration': MIGRATION_TAG}}
    params = {'supportsAllDrives': 'true', 'fields': 'id,name,mimeType,parents,driveId,appProperties,trashed'}
    return api(drive, 'https://www.googleapis.com/drive/v3/files?' + urllib.parse.urlencode(params), action=f'create_folder:{row["path"]}', method='POST', data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})


def move_file(drive, row: dict, dest_parent: str) -> dict:
    params = {'supportsAllDrives': 'true', 'addParents': dest_parent, 'removeParents': row['parent_id'], 'fields': 'id,name,mimeType,parents,driveId,size,md5Checksum,headRevisionId,version,trashed,appProperties'}
    try:
        return api(drive, f'https://www.googleapis.com/drive/v3/files/{row["id"]}?' + urllib.parse.urlencode(params), action=f'move_file:{row["path"]}', method='PATCH', data=b'{}', headers={'Content-Type': 'application/json'})
    except ApiFailure:
        # A process can die after Drive commits the move but before checkpointing.
        # Re-read before treating a retry failure as fatal.
        current = file_get(drive, row['id'])
        if current.get('driveId') == TARGET_DRIVE and current.get('parents') == [dest_parent]:
            return current
        raise


def copy_file(drive, row: dict, dest_parent: str) -> dict:
    found = find_migrated_child(drive, dest_parent, row['id'])
    if len(found) == 1:
        return file_get(drive, found[0]['id'])
    if len(found) > 1:
        raise RuntimeError(f"duplicate copies for {row['id']}: {[x['id'] for x in found]}")
    body = {'name': row['name'], 'parents': [dest_parent], 'appProperties': {'mgs_source_id': row['id'], 'mgs_migration': MIGRATION_TAG}}
    params = {'supportsAllDrives': 'true', 'fields': 'id,name,mimeType,parents,driveId,size,md5Checksum,headRevisionId,version,trashed,appProperties'}
    return api(drive, f'https://www.googleapis.com/drive/v3/files/{row["id"]}/copy?' + urllib.parse.urlencode(params), action=f'copy_file:{row["path"]}', method='POST', data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})


def list_tree(drive, root_id: str) -> list[dict]:
    rows = []
    queue = deque([(root_id, 'MGS-AGENTS', 0)])
    fields = 'id,name,mimeType,parents,driveId,size,md5Checksum,headRevisionId,version,trashed,appProperties'
    while queue:
        parent, path, depth = queue.popleft()
        page = None
        while True:
            params = {'q': f"'{parent}' in parents and trashed=false", 'fields': f'nextPageToken,files({fields})', 'pageSize': '1000', 'orderBy': 'folder,name_natural', 'supportsAllDrives': 'true', 'includeItemsFromAllDrives': 'true'}
            if page:
                params['pageToken'] = page
            data = api(drive, 'https://www.googleapis.com/drive/v3/files?' + urllib.parse.urlencode(params), action=f'list_tree:{parent}')
            for item in data.get('files', []):
                item = dict(item)
                item['path'] = path + '/' + item['name']
                item['depth'] = depth + 1
                rows.append(item)
                if item['mimeType'] == FOLDER_MIME:
                    queue.append((item['id'], item['path'], depth + 1))
            page = data.get('nextPageToken')
            if not page:
                break
    return rows


def create_backup_container(drive, checkpoint: dict) -> str:
    name = '_MGS-AGENTS_MIGRATION_BACKUP_' + checkpoint['run_id']

    def validated(folder_id: str) -> str:
        meta = file_get(drive, folder_id)
        props = meta.get('appProperties') or {}
        if meta.get('name') != name or meta.get('mimeType') != FOLDER_MIME or meta.get('parents') != [SOURCE_PARENT] or meta.get('driveId') or meta.get('trashed') is True or props.get('mgs_migration') != MIGRATION_TAG or props.get('mgs_backup_for') != SOURCE_ROOT:
            raise RuntimeError(f'backup container validation failed: {meta}')
        return folder_id

    if checkpoint.get('backup_container_id'):
        return validated(checkpoint['backup_container_id'])
    query = f"'{SOURCE_PARENT}' in parents and trashed=false and appProperties has {{ key='mgs_backup_for' and value='{SOURCE_ROOT}' }} and appProperties has {{ key='mgs_migration' and value='{MIGRATION_TAG}' }}"
    params = {'q': query, 'fields': 'files(id,name,mimeType,parents,driveId,trashed,appProperties)', 'pageSize': '100', 'spaces': 'drive'}
    found = api(drive, 'https://www.googleapis.com/drive/v3/files?' + urllib.parse.urlencode(params), action='find_backup_container').get('files', [])
    if len(found) > 1:
        raise RuntimeError(f'ambiguous backup containers: {[x["id"] for x in found]}')
    if found:
        folder_id = found[0]['id']
    else:
        body = {'name': name, 'mimeType': FOLDER_MIME, 'parents': [SOURCE_PARENT], 'appProperties': {'mgs_migration': MIGRATION_TAG, 'mgs_backup_for': SOURCE_ROOT}}
        params = {'fields': 'id,name,mimeType,parents,appProperties'}
        folder_id = api(drive, 'https://www.googleapis.com/drive/v3/files?' + urllib.parse.urlencode(params), action='create_backup_container', method='POST', data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})['id']
    validated(folder_id)
    checkpoint['backup_container_id'] = folder_id
    atomic_json(CHECKPOINT, checkpoint)
    return folder_id


def move_source_to_backup(drive, checkpoint: dict) -> dict:
    backup_id = create_backup_container(drive, checkpoint)
    current = file_get(drive, SOURCE_ROOT)
    if current.get('parents') == [backup_id]:
        return current
    if SOURCE_PARENT not in (current.get('parents') or []):
        raise RuntimeError(f"source root is not under expected My Drive parent; parents={current.get('parents')}")
    params = {'addParents': backup_id, 'removeParents': SOURCE_PARENT, 'fields': 'id,name,mimeType,parents,driveId,trashed,appProperties'}
    return api(drive, f'https://www.googleapis.com/drive/v3/files/{SOURCE_ROOT}?' + urllib.parse.urlencode(params), action='move_source_root_to_backup', method='PATCH', data=b'{}', headers={'Content-Type': 'application/json'})


def validate_metadata(row: dict, target: dict, dest_parent: str, *, copied: bool) -> None:
    if target.get('name') != row['name'] or target.get('mimeType') != row['mimeType']:
        raise RuntimeError(f"metadata mismatch for {row['path']}: target={target}")
    if target.get('parents') != [dest_parent] or target.get('driveId') != TARGET_DRIVE or target.get('trashed') is True:
        raise RuntimeError(f"destination placement mismatch for {row['path']}: target={target}")
    if int(target.get('size') or 0) != int(row.get('size_bytes') or 0):
        raise RuntimeError(f"size mismatch for {row['path']}: {row.get('size_bytes')} != {target.get('size')}")
    if row.get('md5Checksum') and target.get('md5Checksum') != row['md5Checksum']:
        raise RuntimeError(f"MD5 mismatch for {row['path']}: {row['md5Checksum']} != {target.get('md5Checksum')}")
    if copied and target.get('id') == row['id']:
        raise RuntimeError(f"copy unexpectedly reused source ID for {row['path']}")
    if not copied and target.get('id') != row['id']:
        raise RuntimeError(f"move changed file ID for {row['path']}")


def validate_exact_target(rows: list[dict], checkpoint: dict, target_tree: list[dict]) -> None:
    target_by_id = {x['id']: x for x in target_tree}
    folder_rows = {x['id']: x for x in rows if x['kind'] == 'FOLDER'}
    file_rows = {x['id']: x for x in rows if x['kind'] == 'FILE'}
    expected_folder_keys = {SOURCE_ROOT} | set(folder_rows)
    if set(checkpoint['folder_map']) != expected_folder_keys:
        raise RuntimeError('checkpoint folder_map keys do not match inventory')
    if set(checkpoint['file_map']) != set(file_rows):
        raise RuntimeError('checkpoint file_map keys do not match inventory')
    actions = Counter(x['action'] for x in checkpoint['file_map'].values())
    if actions != Counter({'MOVE_PRESERVE_ID': 1035, 'COPY_NEW_ID': 104}):
        raise RuntimeError(f'checkpoint action counts mismatch: {dict(actions)}')
    expected_target_ids = set()
    for row in rows:
        copied = row['migration_action'] == 'COPY_NEW_ID'
        target_id = checkpoint['folder_map'][row['id']] if row['kind'] == 'FOLDER' else checkpoint['file_map'][row['id']]['target_id']
        expected_target_ids.add(target_id)
        target = target_by_id.get(target_id)
        if not target:
            raise RuntimeError(f"target missing for {row['path']}: {target_id}")
        dest_parent = TARGET_DRIVE if row['parent_id'] == SOURCE_ROOT else checkpoint['folder_map'][row['parent_id']]
        validate_metadata(row, target, dest_parent, copied=copied)
        if row['kind'] == 'FOLDER' or copied:
            props = target.get('appProperties') or {}
            if props.get('mgs_source_id') != row['id'] or props.get('mgs_migration') != MIGRATION_TAG:
                raise RuntimeError(f"migration properties mismatch for {row['path']}: {props}")
    if set(target_by_id) != expected_target_ids:
        raise RuntimeError('target contains missing or unrelated IDs')


def validate_residual_source(drive, rows: list[dict], checkpoint: dict, target_tree: list[dict]) -> dict:
    residual = list_tree(drive, SOURCE_ROOT)
    residual_by_id = {x['id']: x for x in residual}
    target_by_id = {x['id']: x for x in target_tree}
    expected = {x['id']: x for x in rows if x['kind'] == 'FOLDER' or x['migration_action'] == 'COPY_NEW_ID'}
    if set(residual_by_id) != set(expected):
        missing = sorted(set(expected) - set(residual_by_id))
        extra = sorted(set(residual_by_id) - set(expected))
        raise RuntimeError(f'residual source mismatch: missing={missing[:20]} extra={extra[:20]}')
    for source_id, row in expected.items():
        item = residual_by_id[source_id]
        expected_parent = SOURCE_ROOT if row['parent_id'] == SOURCE_ROOT else row['parent_id']
        if item.get('name') != row['name'] or item.get('mimeType') != row['mimeType'] or item.get('parents') != [expected_parent] or item.get('driveId') or item.get('trashed') is True:
            raise RuntimeError(f"residual metadata mismatch for {row['path']}: {item}")
        if int(item.get('size') or 0) != int(row.get('size_bytes') or 0) or (row.get('md5Checksum') and item.get('md5Checksum') != row['md5Checksum']):
            raise RuntimeError(f"residual content mismatch for {row['path']}")
        if row['migration_action'] == 'COPY_NEW_ID':
            target_id = checkpoint['file_map'][source_id]['target_id']
            dest = target_by_id.get(target_id) or {}
            if dest.get('md5Checksum') != row.get('md5Checksum') or int(dest.get('size') or 0) != int(row.get('size_bytes') or 0):
                raise RuntimeError(f"copied destination changed for {row['path']}")
    return {'items': len(residual), 'folders': sum(x['mimeType'] == FOLDER_MIME for x in residual), 'files': sum(x['mimeType'] != FOLDER_MIME for x in residual), 'bytes': sum(int(x.get('size') or 0) for x in residual if x['mimeType'] != FOLDER_MIME)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    inv = json.loads(INVENTORY.read_text(encoding='utf-8'))
    rows = inv['items']
    folders = sorted((x for x in rows if x['kind'] == 'FOLDER'), key=lambda x: (x['depth'], x['path'], x['id']))
    files = sorted((x for x in rows if x['kind'] == 'FILE'), key=lambda x: (x['path'], x['id']))
    counts = Counter(x['migration_action'] for x in rows)
    expected = {'items': 1443, 'folders': 304, 'files': 1139, 'RECREATE_NEW_ID': 304, 'MOVE_PRESERVE_ID': 1035, 'COPY_NEW_ID': 104}
    actual = {'items': len(rows), 'folders': len(folders), 'files': len(files), **dict(counts)}
    if actual != expected:
        raise RuntimeError(f'inventory count mismatch: expected={expected} actual={actual}')
    summary = inv.get('summary') or {}
    scope = summary.get('scope') or {}
    if scope.get('root_id') != SOURCE_ROOT or scope.get('target_drive_id') != TARGET_DRIVE or scope.get('root_name') != 'MGS-AGENTS':
        raise RuntimeError(f'inventory scope mismatch: {scope}')
    ids = [x['id'] for x in rows]
    if len(ids) != len(set(ids)):
        raise RuntimeError('inventory contains duplicate IDs')
    folder_ids = {x['id'] for x in folders}
    for row in rows:
        if row['parent_id'] != SOURCE_ROOT and row['parent_id'] not in folder_ids:
            raise RuntimeError(f"inventory parent graph broken for {row['path']}: {row['parent_id']}")
        if row['kind'] == 'FOLDER' and (row['mimeType'] != FOLDER_MIME or row['migration_action'] != 'RECREATE_NEW_ID'):
            raise RuntimeError(f"invalid folder action for {row['path']}")
        if row['kind'] == 'FILE' and row['migration_action'] not in {'MOVE_PRESERVE_ID', 'COPY_NEW_ID'}:
            raise RuntimeError(f"invalid file action for {row['path']}")
    if sum(int(x.get('size_bytes') or 0) for x in files) != 4882460554 or sum(bool(x.get('md5Checksum')) for x in files) != 1134:
        raise RuntimeError('inventory byte/MD5 totals mismatch')
    inventory_sha256 = hashlib.sha256(INVENTORY.read_bytes()).hexdigest()
    if not args.apply:
        print(json.dumps({'status': 'DRY_RUN_PASS', 'inventory': str(INVENTORY), 'actual': actual, 'source_root': SOURCE_ROOT, 'target_drive': TARGET_DRIVE, 'target_name': TARGET_NAME, 'backup_policy': 'move old source root into My Drive backup container after full validation'}, ensure_ascii=False, indent=2))
        return 0

    LOCK.parent.mkdir(parents=True, exist_ok=True)
    lock_fd = LOCK.open('w')
    try:
        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise RuntimeError(f'migration lock already held: {LOCK}')
    lock_fd.write(json.dumps({'pid': os.getpid(), 'started_at_utc': dt.datetime.now(dt.UTC).isoformat()}))
    lock_fd.flush()

    WORK.mkdir(parents=True, exist_ok=True)
    if CHECKPOINT.exists():
        checkpoint = json.loads(CHECKPOINT.read_text(encoding='utf-8'))
    else:
        checkpoint = {'schema_version': 1, 'inventory_sha256': inventory_sha256, 'source_root_id': SOURCE_ROOT, 'target_drive_id': TARGET_DRIVE, 'migration_tag': MIGRATION_TAG, 'run_id': dt.datetime.now(dt.UTC).strftime('%Y%m%dT%H%M%SZ'), 'started_at_utc': dt.datetime.now(dt.UTC).isoformat(), 'phase': 'preflight', 'folder_map': {SOURCE_ROOT: TARGET_DRIVE}, 'file_map': {}, 'completed_folders': [], 'completed_files': [], 'errors': []}
        atomic_json(CHECKPOINT, checkpoint)
    binding = {'schema_version': 1, 'inventory_sha256': inventory_sha256, 'source_root_id': SOURCE_ROOT, 'target_drive_id': TARGET_DRIVE, 'migration_tag': MIGRATION_TAG}
    mismatch = {k: {'expected': v, 'actual': checkpoint.get(k)} for k, v in binding.items() if checkpoint.get(k) != v}
    if mismatch:
        raise RuntimeError(f'checkpoint binding mismatch: {mismatch}')
    token = mod.refresh_oauth_access_token(mod.oauth_credentials())
    drive = mod.Drive(token)
    try:
        dg = drive_get(drive)
        if dg.get('name') != TARGET_NAME or not (dg.get('capabilities') or {}).get('canAddChildren'):
            raise RuntimeError(f'target drive preflight failed: {dg}')
        source = file_get(drive, SOURCE_ROOT)
        fresh_run = not checkpoint.get('completed_folders') and not checkpoint.get('completed_files')
        if source.get('name') != 'MGS-AGENTS' or source.get('mimeType') != FOLDER_MIME or source.get('driveId') or source.get('trashed') is True:
            raise RuntimeError(f'source preflight failed: {source}')
        if fresh_run:
            caps = source.get('capabilities') or {}
            if source.get('parents') != [SOURCE_PARENT] or not source.get('ownedByMe') or not caps.get('canMoveItemWithinDrive'):
                raise RuntimeError(f'source destructive prerequisites failed: {source}')
        elif checkpoint.get('phase') == 'complete' and source.get('parents') != [checkpoint.get('backup_container_id')]:
            raise RuntimeError(f'completed checkpoint/source placement mismatch: {source}')
        if fresh_run:
            target_before = list_tree(drive, TARGET_DRIVE)
            if target_before:
                raise RuntimeError(f'target Shared Drive is not empty before migration: {len(target_before)} items')
            source_live = list_tree(drive, SOURCE_ROOT)
            expected_by_id = {x['id']: x for x in rows}
            live_by_id = {x['id']: x for x in source_live}
            if set(live_by_id) != set(expected_by_id):
                missing = sorted(set(expected_by_id) - set(live_by_id))
                added = sorted(set(live_by_id) - set(expected_by_id))
                raise RuntimeError(f'source snapshot drift: missing={missing[:20]} added={added[:20]}')
            drift = []
            for source_id, expected_row in expected_by_id.items():
                live = live_by_id[source_id]
                checks = {
                    'name': (expected_row['name'], live.get('name')),
                    'mimeType': (expected_row['mimeType'], live.get('mimeType')),
                    'parent_id': (expected_row['parent_id'], (live.get('parents') or [None])[0]),
                    'size': (int(expected_row.get('size_bytes') or 0), int(live.get('size') or 0)),
                    'md5': (expected_row.get('md5Checksum'), live.get('md5Checksum')),
                }
                bad = {k: v for k, v in checks.items() if v[0] != v[1]}
                if bad:
                    drift.append({'id': source_id, 'path': expected_row['path'], 'mismatch': bad})
            if drift:
                raise RuntimeError(f'source metadata drift detected: {json.dumps(drift[:20], ensure_ascii=False)}')
            checkpoint['preflight_snapshot'] = {'status': 'PASS', 'source_items': len(source_live), 'target_items_before': 0, 'metadata_drift': 0}
            atomic_json(CHECKPOINT, checkpoint)
        event('preflight_pass', source=source, target_drive=dg, counts=actual, snapshot=checkpoint.get('preflight_snapshot'))

        checkpoint['phase'] = 'folders'
        atomic_json(CHECKPOINT, checkpoint)
        completed_folders = set(checkpoint.get('completed_folders', []))
        for idx, row in enumerate(folders, 1):
            parent_dest = checkpoint['folder_map'].get(row['parent_id'])
            if not parent_dest:
                raise RuntimeError(f"missing destination parent mapping for folder {row['path']} ({row['parent_id']})")
            if row['id'] in completed_folders:
                if idx % 25 == 0:
                    print(json.dumps({'phase': 'folders', 'completed': len(completed_folders), 'total': len(folders), 'resume_skip_through_index': idx}, ensure_ascii=False), flush=True)
                continue
            target = create_folder(drive, parent_dest, row)
            target_id = target['id']
            checkpoint['folder_map'][row['id']] = target_id
            checkpoint['completed_folders'].append(row['id'])
            completed_folders.add(row['id'])
            atomic_json(CHECKPOINT, checkpoint)
            if idx % 25 == 0 or idx == len(folders):
                print(json.dumps({'phase': 'folders', 'completed': idx, 'total': len(folders)}, ensure_ascii=False), flush=True)

        checkpoint['phase'] = 'files'
        atomic_json(CHECKPOINT, checkpoint)
        completed_files = set(checkpoint.get('completed_files', []))
        for idx, row in enumerate(files, 1):
            dest_parent = checkpoint['folder_map'].get(row['parent_id'])
            if not dest_parent:
                raise RuntimeError(f"missing destination parent mapping for file {row['path']} ({row['parent_id']})")
            copied = row['migration_action'] == 'COPY_NEW_ID'
            if row['id'] in completed_files:
                if idx % 25 == 0:
                    print(json.dumps({'phase': 'files', 'completed': len(completed_files), 'total': len(files), 'resume_skip_through_index': idx}, ensure_ascii=False), flush=True)
                continue
            target = copy_file(drive, row, dest_parent) if copied else move_file(drive, row, dest_parent)
            validate_metadata(row, target, dest_parent, copied=copied)
            checkpoint['file_map'][row['id']] = {'target_id': target['id'], 'action': row['migration_action'], 'source_path': row['path'], 'target_parent_id': dest_parent, 'md5Checksum': row.get('md5Checksum'), 'size_bytes': row.get('size_bytes'), 'mimeType': row['mimeType']}
            checkpoint['completed_files'].append(row['id'])
            completed_files.add(row['id'])
            atomic_json(CHECKPOINT, checkpoint)
            if idx % 25 == 0 or idx == len(files):
                print(json.dumps({'phase': 'files', 'completed': idx, 'total': len(files), 'moves': sum(1 for x in checkpoint['file_map'].values() if x['action']=='MOVE_PRESERVE_ID'), 'copies': sum(1 for x in checkpoint['file_map'].values() if x['action']=='COPY_NEW_ID')}, ensure_ascii=False), flush=True)

        checkpoint['phase'] = 'validate'
        atomic_json(CHECKPOINT, checkpoint)
        target_tree = []
        target_folders = []
        target_files = []
        for consistency_attempt in range(1, 7):
            target_tree = list_tree(drive, TARGET_DRIVE)
            target_folders = [x for x in target_tree if x['mimeType'] == FOLDER_MIME]
            target_files = [x for x in target_tree if x['mimeType'] != FOLDER_MIME]
            if len(target_tree) == 1443 and len(target_folders) == 304 and len(target_files) == 1139:
                break
            if consistency_attempt < 6:
                wait = 5 * consistency_attempt
                event('validation_consistency_retry', attempt=consistency_attempt, wait_seconds=wait, items=len(target_tree), folders=len(target_folders), files=len(target_files))
                time.sleep(wait)
        if len(target_tree) != 1443 or len(target_folders) != 304 or len(target_files) != 1139:
            raise RuntimeError(f'target count mismatch after consistency retries: items={len(target_tree)} folders={len(target_folders)} files={len(target_files)}')
        if sum(int(x.get('size') or 0) for x in target_files) != 4882460554:
            raise RuntimeError('target total byte count mismatch')
        mapped_targets = set(checkpoint['folder_map'].values()) - {TARGET_DRIVE}
        if mapped_targets != {x['id'] for x in target_folders}:
            raise RuntimeError('target folder mapping does not match target tree')
        file_targets = {x['target_id'] for x in checkpoint['file_map'].values()}
        if file_targets != {x['id'] for x in target_files}:
            raise RuntimeError('target file mapping does not match target tree')
        validate_exact_target(rows, checkpoint, target_tree)
        md5_by_id = {x['id']: x.get('md5Checksum') for x in target_files}
        md5_mismatches = []
        for source_id, mapped in checkpoint['file_map'].items():
            if mapped.get('md5Checksum') and md5_by_id.get(mapped['target_id']) != mapped['md5Checksum']:
                md5_mismatches.append(source_id)
        if md5_mismatches:
            raise RuntimeError(f'MD5 mismatches: {md5_mismatches[:20]}')
        residual_validation = validate_residual_source(drive, rows, checkpoint, target_tree)
        checkpoint['validation'] = {'status': 'PASS', 'target_items': len(target_tree), 'target_folders': len(target_folders), 'target_files': len(target_files), 'target_bytes': sum(int(x.get('size') or 0) for x in target_files), 'md5_checked': sum(bool(x.get('md5Checksum')) for x in target_files), 'md5_mismatches': 0, 'exact_hierarchy_metadata': 'PASS', 'residual_source': residual_validation}
        atomic_json(CHECKPOINT, checkpoint)
        event('destination_validation_pass', validation=checkpoint['validation'])

        checkpoint['phase'] = 'backup_source'
        atomic_json(CHECKPOINT, checkpoint)
        move_source_to_backup(drive, checkpoint)
        backup_readback = file_get(drive, SOURCE_ROOT)
        if backup_readback.get('name') != 'MGS-AGENTS' or backup_readback.get('mimeType') != FOLDER_MIME or backup_readback.get('parents') != [checkpoint['backup_container_id']] or backup_readback.get('driveId') or backup_readback.get('trashed') is True:
            raise RuntimeError(f'source backup readback mismatch: {backup_readback}')
        checkpoint['source_backup'] = {'status': 'PASS', 'container_id': checkpoint['backup_container_id'], 'source_root_id': SOURCE_ROOT, 'source_root_name': backup_readback.get('name'), 'source_root_parents': backup_readback.get('parents'), 'residual_source': residual_validation}
        checkpoint['phase'] = 'complete'
        checkpoint['completed_at_utc'] = dt.datetime.now(dt.UTC).isoformat()
        atomic_json(CHECKPOINT, checkpoint)
        event('migration_complete', validation=checkpoint['validation'], source_backup=checkpoint['source_backup'])

        final_dir = FINAL_BASE / checkpoint['run_id']
        final_dir.mkdir(parents=True, exist_ok=True)
        final_report = {
            'generated_at_utc': dt.datetime.now(dt.UTC).isoformat(),
            'status': 'PASS',
            'run_id': checkpoint['run_id'],
            'source_root_id': SOURCE_ROOT,
            'destination_shared_drive_id': TARGET_DRIVE,
            'destination_shared_drive_name': TARGET_NAME,
            'counts': actual,
            'validation': checkpoint['validation'],
            'source_backup': checkpoint['source_backup'],
            'folder_map_count': len(checkpoint['folder_map']),
            'file_map_count': len(checkpoint['file_map']),
            'moved_file_count': sum(1 for x in checkpoint['file_map'].values() if x['action'] == 'MOVE_PRESERVE_ID'),
            'copied_file_count': sum(1 for x in checkpoint['file_map'].values() if x['action'] == 'COPY_NEW_ID'),
            'copy_policy': 'The residual source tree contains the 304 original folder shells and 104 externally owned originals, validated and moved into a My Drive backup container after destination PASS.',
            'artifacts': {'folder_map': 'folder-map.json', 'file_map': 'file-map.json', 'target_tree': 'target-tree.json'}
        }
        atomic_json(final_dir / 'migration-report.json', final_report)
        atomic_json(final_dir / 'folder-map.json', checkpoint['folder_map'])
        atomic_json(final_dir / 'file-map.json', checkpoint['file_map'])
        atomic_json(final_dir / 'target-tree.json', {'items': target_tree})
        print(json.dumps({'status': 'PASS', 'final_dir': str(final_dir), 'report': final_report}, ensure_ascii=False, indent=2), flush=True)
        return 0
    except Exception as exc:
        checkpoint['errors'].append({'at_utc': dt.datetime.now(dt.UTC).isoformat(), 'phase': checkpoint.get('phase'), 'type': type(exc).__name__, 'detail': str(exc)[:4000]})
        atomic_json(CHECKPOINT, checkpoint)
        event('migration_failed', phase=checkpoint.get('phase'), error_type=type(exc).__name__, detail=str(exc)[:4000])
        print(json.dumps({'status': 'FAIL', 'phase': checkpoint.get('phase'), 'error_type': type(exc).__name__, 'detail': str(exc), 'checkpoint': str(CHECKPOINT)}, ensure_ascii=False, indent=2), file=sys.stderr, flush=True)
        return 1
    finally:
        try:
            LOCK.unlink(missing_ok=True)
        except Exception:
            pass


if __name__ == '__main__':
    raise SystemExit(main())
