#!/usr/bin/env python3
"""Execute one frozen Hermes cleanup manifest after Critical confirmation."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile

AUDIT = Path('/root/mgs-agent/logs/events-audit.jsonl')
FINANCE_ROOTS = (
    Path('/root/mgs-agent/apps/finance-system'),
    Path('/root/mgs-agent/work/finance-dashboard-august-20260904'),
)


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def run(args: list[str], *, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(args, text=True, capture_output=True, check=check)


def atomic_json(path: Path, data: dict, mode: int = 0o600) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + '.', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write('\n'); f.flush(); os.fsync(f.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def audit(event: str, detail: dict) -> None:
    row = {'ts': now(), 'event': event, 'actor': 'hermes-cleanup-executor', **detail}
    with AUDIT.open('a', encoding='utf-8') as f:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')


def metadata_rows(root: Path) -> tuple[list[dict], dict]:
    rows: list[dict] = []
    errors: list[str] = []
    if not os.path.lexists(root):
        return rows, {'exists': False, 'errors': []}
    todo: list[Path]
    if root.is_dir() and not root.is_symlink():
        todo = []
        for base, _dirs, files in os.walk(root, topdown=True, followlinks=False):
            todo.append(Path(base))
            todo.extend(Path(base) / name for name in files)
    else:
        todo = [root]
    files = dirs = symlinks = logical = allocated = 0
    root_text = str(root)
    for path in todo:
        try:
            st = os.lstat(path)
        except OSError as exc:
            errors.append(f'{path}:{type(exc).__name__}')
            continue
        rel = '.' if str(path) == root_text else os.path.relpath(path, root)
        kind = 'symlink' if stat.S_ISLNK(st.st_mode) else ('directory' if stat.S_ISDIR(st.st_mode) else 'file')
        target = os.readlink(path) if kind == 'symlink' else ''
        rows.append({'rel': rel, 'type': kind, 'size': st.st_size, 'blocks': st.st_blocks,
                     'mtime_ns': st.st_mtime_ns, 'nlink': st.st_nlink, 'link_target': target})
        files += kind == 'file'; dirs += kind == 'directory'; symlinks += kind == 'symlink'
        logical += st.st_size if kind == 'file' else 0
        allocated += st.st_blocks * 512
    rows.sort(key=lambda x: (x['rel'], x['type']))
    canonical = json.dumps(rows, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    summary = {'exists': True, 'files': files, 'dirs': dirs, 'symlinks': symlinks,
               'logical_bytes': logical, 'allocated_bytes': allocated,
               'fingerprint_sha256': hashlib.sha256(canonical).hexdigest(), 'errors': errors}
    return rows, summary


def inside(value: str, root: Path) -> bool:
    try:
        value_real = os.path.realpath(value)
        root_real = os.path.realpath(root)
        return value_real == root_real or value_real.startswith(root_real + os.sep)
    except OSError:
        return False


def process_refs(targets: list[Path]) -> dict[str, list[int]]:
    refs = {str(p): set() for p in targets}
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        values: list[str] = []
        try:
            values += [x.decode(errors='ignore') for x in (proc / 'cmdline').read_bytes().split(b'\0') if x]
        except OSError:
            pass
        for leaf in ('cwd', 'exe'):
            try:
                values.append(os.readlink(proc / leaf))
            except OSError:
                pass
        try:
            for fd in (proc / 'fd').iterdir():
                try:
                    values.append(os.readlink(fd))
                except OSError:
                    pass
        except OSError:
            pass
        for target in targets:
            if any(inside(value, target) for value in values):
                refs[str(target)].add(int(proc.name))
    return {k: sorted(v) for k, v in refs.items()}


def canonical_target_set(targets: list[dict]) -> bytes:
    payload = [{k: item[k] for k in ('path', 'action', 'type', 'files', 'dirs', 'symlinks',
                                     'logical_bytes', 'allocated_bytes', 'fingerprint_sha256')}
               for item in targets]
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--authorization-message-id', required=True)
    args = ap.parse_args()
    manifest_path = Path(args.manifest)
    manifest = json.loads(manifest_path.read_text())
    targets = manifest['targets']
    expected_hash = manifest['target_set_sha256']
    actual_hash = hashlib.sha256(canonical_target_set(targets)).hexdigest()
    if actual_hash != expected_hash:
        raise SystemExit('target_set_hash_mismatch')
    if args.authorization_message_id == manifest.get('request_message_id'):
        raise SystemExit('critical_confirmation_must_be_a_later_message')

    target_paths = [Path(item['path']) for item in targets]
    retained = [Path(p) for p in manifest['retained_paths']]
    active_launcher = Path('/root/.local/bin/hermes')
    if os.path.realpath(active_launcher) != manifest['expected_active_launcher_realpath']:
        raise SystemExit('active_launcher_drift')
    for path in retained:
        if not os.path.lexists(path):
            raise SystemExit(f'retained_path_missing:{path}')
    for finance in FINANCE_ROOTS:
        if not finance.exists():
            raise SystemExit(f'finance_root_missing:{finance}')
        for target in target_paths:
            if os.path.commonpath([str(finance), str(target)]) in (str(finance), str(target)):
                raise SystemExit(f'finance_path_intersection:{target}:{finance}')

    refs = process_refs(target_paths)
    drifts: list[str] = []
    for expected in targets:
        path = Path(expected['path'])
        if refs[str(path)]:
            drifts.append(f'process_refs:{path}:{refs[str(path)]}')
        if os.path.ismount(path):
            drifts.append(f'mount_target:{path}')
        _rows, current = metadata_rows(path)
        for key in ('files', 'dirs', 'symlinks', 'logical_bytes', 'allocated_bytes', 'fingerprint_sha256'):
            if current.get(key) != expected.get(key):
                drifts.append(f'{key}:{path}:{expected.get(key)}->{current.get(key)}')
        if current.get('errors'):
            drifts.append(f'stat_errors:{path}')
        actual_type = 'symlink' if path.is_symlink() else ('directory' if path.is_dir() else 'file')
        if actual_type != expected['type']:
            drifts.append(f'type:{path}:{expected["type"]}->{actual_type}')
        if expected['type'] == 'directory' and (path / '.git').is_file():
            drifts.append(f'registered_worktree_or_gitfile:{path}')
    for protected_repo in (Path('/root/.hermes/hermes-agent-stage-main-14efb460-mgs'),
                           Path('/root/.hermes/hermes-agent-stage-v2026-9-14-345cd2b0-mgs')):
        alt = protected_repo / '.git/objects/info/alternates'
        if alt.is_file():
            for line in alt.read_text(errors='replace').splitlines():
                if any(inside(line.strip(), target) for target in target_paths):
                    drifts.append(f'protected_alternate_dependency:{protected_repo}:{line.strip()}')
    if drifts:
        audit('hermes_cleanup_aborted', {'manifest': str(manifest_path), 'target_set_sha256': expected_hash,
                                         'authorization_message_id': args.authorization_message_id,
                                         'drifts': drifts})
        raise SystemExit('predelete_drift:' + ';'.join(drifts[:10]))

    for sums in manifest['retained_checksum_manifests']:
        check = run(['sha256sum', '-c', sums])
        if check.returncode:
            raise SystemExit(f'retained_checksum_failed:{sums}')
    if run(['systemctl', '--failed', '--no-legend', '--plain']).stdout.strip():
        raise SystemExit('failed_units_present')
    for service in ('ares-gateway.service', 'atena-gateway.service', 'zeus-gateway.service'):
        if run(['systemctl', 'is-active', service]).stdout.strip() != 'active':
            raise SystemExit(f'service_not_active:{service}')

    audit('hermes_cleanup_started', {'manifest': str(manifest_path), 'target_set_sha256': expected_hash,
                                     'authorization_message_id': args.authorization_message_id,
                                     'target_count': len(targets),
                                     'inode_aware_reclaim_bytes': manifest['inode_aware_reclaim_bytes']})
    deleted: list[str] = []
    try:
        for item in targets:
            path = Path(item['path'])
            if item['action'] == 'delete_tree':
                shutil.rmtree(path)
            elif item['action'] in ('delete_file', 'delete_symlink'):
                path.unlink()
            else:
                raise RuntimeError(f'unknown_action:{item["action"]}')
            deleted.append(str(path))
    except Exception as exc:
        remaining = [item['path'] for item in targets if os.path.lexists(item['path'])]
        audit('hermes_cleanup_partial_failure', {'manifest': str(manifest_path),
                                                  'target_set_sha256': expected_hash,
                                                  'authorization_message_id': args.authorization_message_id,
                                                  'deleted': deleted, 'remaining': remaining,
                                                  'error': f'{type(exc).__name__}:{exc}'})
        raise

    remaining = [item['path'] for item in targets if os.path.lexists(item['path'])]
    if remaining:
        raise SystemExit('targets_still_present:' + ','.join(remaining))
    for path in retained:
        if not os.path.lexists(path):
            raise SystemExit(f'retained_path_lost:{path}')
    result = {
        'status': 'filesystem_cleanup_pass', 'closed_at': now(),
        'manifest': str(manifest_path), 'target_set_sha256': expected_hash,
        'authorization_message_id': args.authorization_message_id,
        'deleted_count': len(deleted), 'deleted': deleted,
        'remaining_targets': [], 'inode_aware_reclaim_estimate_bytes': manifest['inode_aware_reclaim_bytes'],
        'active_launcher_realpath': os.path.realpath(active_launcher),
    }
    result_path = manifest_path.with_name(manifest_path.stem + '-result.json')
    atomic_json(result_path, result)
    audit('hermes_cleanup_filesystem_pass', {'manifest': str(manifest_path), 'result': str(result_path),
                                              'target_set_sha256': expected_hash,
                                              'authorization_message_id': args.authorization_message_id,
                                              'deleted_count': len(deleted)})
    print(json.dumps({'status': 'pass', 'result': str(result_path), 'deleted_count': len(deleted)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
