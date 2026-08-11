#!/usr/bin/env python3
from __future__ import annotations

import collections
import datetime as dt
import fcntl
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

BASE = Path('/root/mgs-agent')
MANIFEST = BASE / 'reports/storage-audits/20260811-vps-cleanup-round2-manifest.json'
RESULT = BASE / 'data/vps-cleanup-round2-result.json'
AUDIT = BASE / 'logs/events-audit.jsonl'
EXPECTED_SET = '04a8e7804e43fbff25522e256e1a1a4b2b885a85df8e5689d122aabb543c0f9e'
CONFIRMATION_MESSAGE_ID = '1536779414203932742'
REQUEST_MESSAGE_ID = '1536771147587125328'
THREAD_ID = '1536567182824308839'
DRIVE_PREFLIGHT = Path('/run/mgs-vps-cleanup-round2-prestate/drive-predelete.json')
LOCK = Path('/run/mgs-vps-cleanup-round2.lock')


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def atomic_json(path: Path, obj: dict) -> None:
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')
    os.replace(tmp, path)


def append_audit(obj: dict) -> None:
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT.open('a', encoding='utf-8') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        f.write(json.dumps(obj, ensure_ascii=False, separators=(',', ':')) + '\n')
        f.flush()
        os.fsync(f.fileno())
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def filesystem() -> dict:
    s = os.statvfs('/')
    total = s.f_blocks * s.f_frsize
    free = s.f_bavail * s.f_frsize
    return {'total_bytes': total, 'used_bytes': total - free, 'free_bytes': free}


def iter_entries(root: str):
    st = os.lstat(root)
    yield '.', st, os.readlink(root) if stat.S_ISLNK(st.st_mode) else None
    if stat.S_ISDIR(st.st_mode) and not stat.S_ISLNK(st.st_mode):
        for dp, ds, fs in os.walk(root, followlinks=False):
            for name in list(ds) + list(fs):
                path = os.path.join(dp, name)
                st = os.lstat(path)
                yield os.path.relpath(path, root), st, os.readlink(path) if stat.S_ISLNK(st.st_mode) else None
                if name in ds and stat.S_ISLNK(st.st_mode):
                    ds.remove(name)


def inspect(root: str) -> dict:
    h = hashlib.sha256()
    files = dirs = symlinks = logical = allocated = 0
    devs: set[int] = set()
    for rel, st, link in iter_entries(root):
        mode = st.st_mode
        kind = 'd' if stat.S_ISDIR(mode) else 'l' if stat.S_ISLNK(mode) else 'f' if stat.S_ISREG(mode) else 'o'
        if kind == 'd':
            dirs += 1
        elif kind == 'l':
            symlinks += 1
        elif kind == 'f':
            files += 1
            logical += st.st_size
        allocated += st.st_blocks * 512
        devs.add(st.st_dev)
        h.update((json.dumps([rel, kind, st.st_size, st.st_blocks, st.st_mtime_ns, link], ensure_ascii=False, separators=(',', ':')) + '\n').encode())
    return {
        'files': files,
        'dirs': dirs,
        'symlinks': symlinks,
        'logical_bytes': logical,
        'allocated_bytes': allocated,
        'device_count': len(devs),
        'mount_crossing': len(devs) > 1,
        'metadata_fingerprint_sha256': h.hexdigest(),
    }


def process_refs(targets: list[str]) -> dict[str, list[dict]]:
    found: dict[str, list[dict]] = collections.defaultdict(list)
    for pid in os.listdir('/proc'):
        if not pid.isdigit():
            continue
        refs: list[tuple[str, str]] = []
        for label in ('cwd', 'exe', 'root'):
            try:
                refs.append((label, os.path.realpath(f'/proc/{pid}/{label}')))
            except OSError:
                pass
        try:
            names = os.listdir(f'/proc/{pid}/fd')
        except OSError:
            names = []
        for name in names:
            try:
                refs.append(('fd', os.path.realpath(f'/proc/{pid}/fd/{name}')))
            except OSError:
                pass
        for target in targets:
            root = target.rstrip('/')
            for label, ref in refs:
                if ref == root or ref.startswith(root + '/'):
                    found[target].append({'pid': int(pid), 'ref': f'{label}:{ref}'})
    return found


def service_state() -> dict:
    services = ['ares-gateway.service', 'atena-gateway.service', 'zeus-gateway.service']
    active = {}
    for service in services:
        proc = subprocess.run(['systemctl', 'is-active', service], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        active[service] = proc.stdout.strip()
    failed = subprocess.run(['systemctl', '--failed', '--no-legend', '--plain'], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    failed_rows = [row for row in failed.stdout.splitlines() if row.strip()]
    return {'services': active, 'failed_units': failed_rows}


def canonical_hash(manifest: dict) -> str:
    selected = []
    keys = {'path', 'action', 'group', 'metadata_fingerprint_sha256', 'files', 'dirs', 'symlinks', 'allocated_bytes'}
    for row in sorted(manifest['deletion_targets'], key=lambda item: item['path']):
        selected.append(dict(sorted({key: value for key, value in row.items() if key in keys}.items())))
    payload = {'deletion_targets': selected, 'policy_changes': manifest['policy_changes_pending_confirmation']}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def main() -> int:
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open('w') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        manifest = json.loads(MANIFEST.read_text())
        actual_set = canonical_hash(manifest)
        if actual_set != EXPECTED_SET or manifest.get('operation_set_sha256') != EXPECTED_SET:
            raise RuntimeError(f'target_set_hash_drift actual={actual_set}')
        drive = json.loads(DRIVE_PREFLIGHT.read_text())
        if drive.get('status') != 'PASS' or drive.get('ready_exact_match') != 210 or drive.get('execution_completed_pass') != 5:
            raise RuntimeError('drive_preflight_drift')
        targets = manifest['deletion_targets']
        target_paths = [row['path'] for row in targets]
        refs = process_refs(target_paths)
        if refs:
            raise RuntimeError('process_reference_drift=' + json.dumps(refs, ensure_ascii=False)[:1000])
        services = service_state()
        if any(value != 'active' for value in services['services'].values()) or services['failed_units']:
            raise RuntimeError('service_health_drift=' + json.dumps(services))
        for protected in manifest['protected_paths']:
            if not os.path.lexists(protected):
                raise RuntimeError(f'protected_path_missing={protected}')
        for row in targets:
            path = row['path']
            if not os.path.lexists(path):
                raise RuntimeError(f'target_missing={path}')
            root_st = os.lstat(path)
            if row['action'] == 'delete_tree' and (not stat.S_ISDIR(root_st.st_mode) or stat.S_ISLNK(root_st.st_mode)):
                raise RuntimeError(f'target_type_drift={path}')
            if row['action'] == 'delete_file' and not stat.S_ISREG(root_st.st_mode):
                raise RuntimeError(f'target_type_drift={path}')
            live = inspect(path)
            for key in ('files', 'dirs', 'symlinks', 'allocated_bytes', 'metadata_fingerprint_sha256'):
                if live[key] != row[key]:
                    raise RuntimeError(f'target_fingerprint_drift={path} key={key} expected={row[key]} actual={live[key]}')
            if live['mount_crossing']:
                raise RuntimeError(f'mount_crossing={path}')
        before = filesystem()
        event_id = 'vps-cleanup-round2-' + dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        append_audit({
            'timestamp': now(),
            'event': 'vps_cleanup_round2_started',
            'event_id': event_id,
            'actor': 'zeus',
            'authorized_by': 'rodolfo',
            'request_message_id': REQUEST_MESSAGE_ID,
            'confirmation_message_id': CONFIRMATION_MESSAGE_ID,
            'thread_id': THREAD_ID,
            'target_set_sha256': EXPECTED_SET,
            'targets': len(targets),
            'files': manifest['summary']['files'],
            'dirs': manifest['summary']['dirs'],
            'inode_aware_reclaimable_bytes': manifest['summary']['inode_aware_reclaimable_bytes'],
            'disk_before': before,
            'drive_preflight': drive,
            'services': services,
            'status': 'started',
        })
        removed: list[dict] = []
        try:
            for row in targets:
                path = row['path']
                if row['action'] == 'delete_tree':
                    shutil.rmtree(path)
                elif row['action'] == 'delete_file':
                    os.unlink(path)
                else:
                    raise RuntimeError(f'unsupported_action={row["action"]}')
                if os.path.lexists(path):
                    raise RuntimeError(f'target_remained={path}')
                removed.append({'path': path, 'action': row['action'], 'group': row['group'], 'allocated_bytes': row['allocated_bytes']})
        except Exception as exc:
            after = filesystem()
            result = {
                'status': 'PARTIAL_FAILURE',
                'event_id': event_id,
                'target_set_sha256': EXPECTED_SET,
                'confirmation_message_id': CONFIRMATION_MESSAGE_ID,
                'removed': removed,
                'remaining': [row['path'] for row in targets if os.path.lexists(row['path'])],
                'error_type': type(exc).__name__,
                'error': str(exc)[:1000],
                'disk_before': before,
                'disk_after': after,
                'finished_at_utc': now(),
            }
            atomic_json(RESULT, result)
            append_audit({'timestamp': now(), 'event': 'vps_cleanup_round2_partial_failure', **result})
            raise
        after = filesystem()
        result = {
            'status': 'DELETION_COMPLETED_POLICY_CHANGES_PENDING',
            'event_id': event_id,
            'target_set_sha256': EXPECTED_SET,
            'confirmation_message_id': CONFIRMATION_MESSAGE_ID,
            'targets_removed': len(removed),
            'files_removed_manifest': manifest['summary']['files'],
            'dirs_removed_manifest': manifest['summary']['dirs'],
            'manifest_inode_aware_bytes': manifest['summary']['inode_aware_reclaimable_bytes'],
            'removed_allocated_bytes_manifest': sum(row['allocated_bytes'] for row in removed),
            'disk_before': before,
            'disk_after': after,
            'observed_free_delta_bytes': after['free_bytes'] - before['free_bytes'],
            'protected_paths_present': all(os.path.lexists(path) for path in manifest['protected_paths']),
            'finished_at_utc': now(),
        }
        atomic_json(RESULT, result)
        append_audit({'timestamp': now(), 'event': 'vps_cleanup_round2_deletion_completed', 'event_id': event_id, 'actor': 'zeus', 'authorized_by': 'rodolfo', 'thread_id': THREAD_ID, **result})
        print(json.dumps({key: result[key] for key in ('status', 'event_id', 'targets_removed', 'manifest_inode_aware_bytes', 'observed_free_delta_bytes', 'protected_paths_present')}, ensure_ascii=False))
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
