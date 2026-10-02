import datetime
import fcntl
import hashlib
import json
import os
import pathlib
import shutil
import stat
import subprocess
import sys

REPO = pathlib.Path('/root/mgs-agent')
APP = REPO / 'apps/finance-system'
PRIVATE = APP / 'private'
WORK = pathlib.Path(__file__).parent
MANIFEST = WORK / 'deletion-manifest.json'
RESULT = WORK / 'deletion-result.json'
JOURNAL = WORK / 'deletion-journal.jsonl'
AUDIT = REPO / 'logs/events-audit.jsonl'
CONFIRMATION = '1555579701227946015'
MANIFEST_SHA256 = 'c9056f83c9571ad5e9f741093e8588d9cd501881fac56c24fe5ef1f86bf19993'
REMOTE_HELPER = APP / 'finance_gam_revenue_sync.py'
REMOTE_HELPER_SHA256 = '66398b3cb4bee4053215cb37d6b83327077457b8b644b39b4e14e43d371c5bd9'


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    with path.open('w') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())


def audit(action, **fields):
    event = {
        'timestamp': now(),
        'agent': 'zeus',
        'action': action,
        'confirmation_message_id': CONFIRMATION,
        'manifest_sha256': MANIFEST_SHA256,
        **fields,
    }
    with AUDIT.open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        handle.write(json.dumps(event, ensure_ascii=False) + '\n')
        handle.flush()
        os.fsync(handle.fileno())


def disk():
    fs = os.statvfs('/')
    used = (fs.f_blocks - fs.f_bfree) * fs.f_frsize
    available = fs.f_bavail * fs.f_frsize
    return {'used': used, 'available': available, 'percent': used / (used + available) * 100}


def tree(path):
    assert path.exists() and path.is_dir() and not path.is_symlink()
    assert path.parent.parent == PRIVATE and path.name in {'candidate', 'stage'}
    digest = hashlib.sha256()
    files = directories = logical = allocated = 0
    oldest = 2**63 - 1
    newest = 0
    for base, dirs, names in os.walk(path, followlinks=False):
        for entry in [pathlib.Path(base)] + [pathlib.Path(base, name) for name in sorted(names)]:
            metadata = entry.lstat()
            assert metadata.st_dev == PRIVATE.stat().st_dev
            assert not stat.S_ISLNK(metadata.st_mode)
            assert stat.S_ISDIR(metadata.st_mode) or stat.S_ISREG(metadata.st_mode)
            relative = str(entry.relative_to(path))
            digest.update(json.dumps([
                relative,
                metadata.st_mode,
                metadata.st_dev,
                metadata.st_ino,
                metadata.st_nlink,
                metadata.st_size,
                metadata.st_blocks,
                metadata.st_mtime_ns,
            ], separators=(',', ':')).encode())
            logical += metadata.st_size
            allocated += metadata.st_blocks * 512
            oldest = min(oldest, metadata.st_mtime_ns)
            newest = max(newest, metadata.st_mtime_ns)
            if stat.S_ISDIR(metadata.st_mode):
                directories += 1
            else:
                files += 1
    return {
        'file_count': files,
        'directory_count': directories,
        'logical_bytes': logical,
        'allocated_bytes': allocated,
        'oldest_mtime_ns': oldest,
        'newest_mtime_ns': newest,
        'metadata_sha256': digest.hexdigest(),
    }


def process_references(targets):
    roots = [entry['path'] for entry in targets]
    hit = lambda value: any(value == root or value.startswith(root + '/') for root in roots)
    references = []
    for line in pathlib.Path('/proc/self/mountinfo').read_text().splitlines():
        mount = line.split()[4]
        assert not hit(mount), ('mount crossing', mount)
    for proc in pathlib.Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            command = (proc / 'cmdline').read_bytes().decode(errors='replace')
            for root in roots:
                if root in command:
                    references.append((proc.name, 'cmdline', root))
            links = [proc / 'cwd', proc / 'exe']
            try:
                links += list((proc / 'fd').iterdir())
            except OSError:
                pass
            for link_path in links:
                try:
                    value = os.readlink(link_path)
                    if hit(value):
                        references.append((proc.name, 'link', value))
                except OSError:
                    pass
            try:
                for line in (proc / 'maps').read_text(errors='replace').splitlines():
                    value = line.split(maxsplit=5)[-1]
                    if hit(value):
                        references.append((proc.name, 'mmap', value))
            except OSError:
                pass
        except OSError:
            pass
    assert not references, references


def remote_status():
    assert sha256(REMOTE_HELPER) == REMOTE_HELPER_SHA256
    sys.path.insert(0, str(APP))
    import finance_gam_revenue_sync as remote
    command = (
        "systemctl is-active mgs-finance-dash mgs-finance-dash.socket mgs-postgresql18; "
        "systemctl show mgs-finance-dash mgs-postgresql18 -p Id -p MainPID -p ActiveState -p WorkingDirectory; "
        + remote.PG
        + "psql -h "
        + remote.SOCKET
        + " -U mgs_pg -d mgs_finance -At -c \"SELECT count(*), max(revision), count(*) FILTER (WHERE state='locked') FROM scenarios; SELECT count(*) FROM finance_history; SELECT count(*) FROM finance_ledger;\""
    )
    output = remote.ssh(command, timeout=120)
    lines = output.splitlines()
    assert lines[:3] == ['active', 'active', 'active'], lines[:3]
    return {'lines': lines, 'helper_sha256': REMOTE_HELPER_SHA256}


def local_units():
    failed = subprocess.run(
        ['systemctl', '--failed', '--no-legend', '--plain'],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert not failed.strip(), failed
    return {'failed_units': 0}


assert sys.argv[1:] == ['--execute', MANIFEST_SHA256]
assert not RESULT.exists(), 'Existing result requires reconciliation; blind retry forbidden'
assert sha256(MANIFEST) == MANIFEST_SHA256
manifest = json.loads(MANIFEST.read_text())
targets = manifest['targets']
assert len(targets) == len({entry['path'] for entry in targets}) == 28
assert manifest['totals']['inode_aware_reclaim_bytes'] == 52963414016
assert shutil.rmtree.avoids_symlink_attacks

# Validate the complete set before the first destructive side effect. Some files
# are hardlinked across target trees, so fingerprints are not re-evaluated after
# deletion starts because removing one legitimate link changes st_nlink elsewhere.
for entry in targets:
    path = pathlib.Path(entry['path'])
    assert path.resolve() == path
    assert tree(path) == {key: entry[key] for key in [
        'file_count',
        'directory_count',
        'logical_bytes',
        'allocated_bytes',
        'oldest_mtime_ns',
        'newest_mtime_ns',
        'metadata_sha256',
    ]}
    assert all(pathlib.Path(report).is_file() for report in entry['report_evidence'])
process_references(targets)
assert (PRIVATE / 'persistent-session-1555570216912560151/candidate').is_dir()
assert (PRIVATE / 'releases').is_dir()
assert sha256(REMOTE_HELPER) == REMOTE_HELPER_SHA256

before = {
    'observed_at': now(),
    'disk': disk(),
    'remote': remote_status(),
    'local': local_units(),
    'active_candidate_retained': True,
    'targets_preflight_pass': True,
}
save(WORK / 'deletion-before.json', before)
executor_hash = sha256(pathlib.Path(__file__))
audit(
    'finance_cleanup_delete_started',
    target_count=len(targets),
    files=manifest['totals']['files'],
    inode_aware_reclaim_bytes=manifest['totals']['inode_aware_reclaim_bytes'],
    executor_sha256=executor_hash,
    remote_helper_sha256=REMOTE_HELPER_SHA256,
)

result = {
    'status': 'started',
    'confirmation_message_id': CONFIRMATION,
    'manifest_sha256': MANIFEST_SHA256,
    'executor_sha256': executor_hash,
    'deleted': [],
}
try:
    for entry in targets:
        path = pathlib.Path(entry['path'])
        assert path.exists() and path.is_dir() and not path.is_symlink()
        assert path.parent.parent == PRIVATE and path.name in {'candidate', 'stage'}
        shutil.rmtree(path)
        assert not os.path.lexists(path)
        result['deleted'].append(str(path))
        with JOURNAL.open('a') as handle:
            handle.write(json.dumps({'path': str(path), 'removed_at': now()}) + '\n')
            handle.flush()
            os.fsync(handle.fileno())

    assert len(result['deleted']) == 28
    assert all(not os.path.lexists(entry['path']) for entry in targets)
    assert (PRIVATE / 'persistent-session-1555570216912560151/candidate').is_dir()
    assert (PRIVATE / 'releases').is_dir()
    assert all(pathlib.Path(report).is_file() for entry in targets for report in entry['report_evidence'])
    assert sha256(MANIFEST) == MANIFEST_SHA256
    assert sha256(REMOTE_HELPER) == REMOTE_HELPER_SHA256
    os.sync()
    after = {
        'observed_at': now(),
        'disk': disk(),
        'remote': remote_status(),
        'local': local_units(),
        'active_candidate_retained': True,
        'targets_absent': True,
    }
    result.update(
        status='filesystem_completed_validated',
        completed_at=now(),
        deleted_count=28,
        files_removed=manifest['totals']['files'],
        inode_aware_reclaim_estimate_bytes=manifest['totals']['inode_aware_reclaim_bytes'],
        observed_reclaimed_bytes=after['disk']['available'] - before['disk']['available'],
        before=before,
        after=after,
        reports_retained=True,
        release_rollbacks_retained=True,
        production_services_active=True,
        financial_writes=0,
    )
    save(RESULT, result)
    audit(
        'finance_cleanup_delete_completed',
        deleted_count=28,
        observed_reclaimed_bytes=result['observed_reclaimed_bytes'],
        active_candidate_retained=True,
        production_services_active=True,
    )
    print(json.dumps({key: value for key, value in result.items() if key not in {'deleted', 'before', 'after'}}, indent=2))
except BaseException as exc:
    result.update(
        status='partial_failure',
        error_type=type(exc).__name__,
        error=str(exc)[:1000],
        remaining=[entry['path'] for entry in targets if os.path.lexists(entry['path'])],
        failed_at=now(),
    )
    save(RESULT, result)
    audit(
        'finance_cleanup_delete_partial_failure',
        deleted=result['deleted'],
        remaining=result['remaining'],
        error_type=type(exc).__name__,
        error=result['error'],
    )
    raise
