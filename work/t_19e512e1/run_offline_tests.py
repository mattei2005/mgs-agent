"""QA-only runner: deny real transport and all writes outside task/scratch."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path('/root/mgs-agent')
WORK = ROOT / 'work/t_19e512e1'
SCRATCH = Path(json.loads((WORK / 'checkpoint-before.json').read_text())['scratch'])
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts'), str(ROOT / 'tests')]
os.environ['HERMES_PROFILE'] = 'ares'  # process-only synthetic guard context
os.environ['TMPDIR'] = str(SCRATCH)
tempfile.tempdir = str(SCRATCH)
original_tempdir = tempfile.TemporaryDirectory
class IsolatedDirectory(original_tempdir):
    def __init__(self, *args, **kwargs):
        kwargs['dir'] = str(SCRATCH)
        super().__init__(*args, **kwargs)
tempfile.TemporaryDirectory = IsolatedDirectory
blocked = []
write_denials = []
forbidden = {'socket.connect', 'socket.connect_ex', 'socket.sendto', 'socket.sendmsg',
             'socket.getaddrinfo', 'socket.gethostbyname',
             'socket.gethostbyaddr', 'subprocess.Popen', 'os.system', 'os.exec',
             'os.posix_spawn', 'os.fork', 'os.forkpty'}
def check_path(path, dir_fd=None):
    if isinstance(path, (str, bytes, os.PathLike)):
        target = Path(os.fsdecode(path))
        if not target.is_absolute() and isinstance(dir_fd, int) and dir_fd >= 0:
            target = Path(os.readlink('/proc/self/fd/' + str(dir_fd))) / target
        target = target.resolve()
        if not (target.is_relative_to(WORK) or target.is_relative_to(SCRATCH)):
            write_denials.append(str(target))
            raise RuntimeError('offline write forbidden outside task/scratch')
def guard(event, args):
    if event in forbidden:
        blocked.append(event)
        raise RuntimeError('offline transport forbidden: ' + event)
    if event == 'open':
        path, mode, flags = args
        writing = (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (
            isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
        if writing:
            check_path(path)
    elif event in {'os.remove', 'os.rmdir'}:
        check_path(args[0], args[1])
    elif event in {'os.mkdir', 'os.chmod'}:
        check_path(args[0], args[2])
    elif event in {'os.truncate', 'os.utime'}:
        check_path(args[0])
    elif event in {'os.rename', 'os.link', 'os.symlink'}:
        check_path(args[0]); check_path(args[1])
sys.addaudithook(guard)
label, *modules = sys.argv[1:]
assert label.replace('-', '').isalnum()
if not modules:
    modules = json.loads((ROOT / 'data/ares/meta-ads/audit/maintenance/t_2559be3f/broad-installed-tests.json').read_text())['modules']
paths = json.loads((WORK / 'checkpoint-before.json').read_text())['sha256']
def hashes():
    return {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() if Path(p).is_file() else None for p in paths}
before = hashes()
import test_eggbev_creation_runner
import test_eggbev_clone_v3
with tempfile.TemporaryDirectory() as state:
    test_eggbev_creation_runner.RUNNER.STATE_ROOT = Path(state) / 'creation-state'
    # Only disk roots differ from installed config; policy/app binding stays exact.
    runner = test_eggbev_creation_runner.RUNNER
    original_load = runner.load_json
    def isolated_load(path):
        value = original_load(path)
        if Path(path) == runner.CONFIG_PATH:
            value = copy.deepcopy(value)
            value['state_root'] = str(Path(state) / 'engine-state')
            value['audit_root'] = str(Path(state) / 'engine-audit')
        return value
    runner.load_json = isolated_load
    original_registry = test_eggbev_clone_v3.MediaRegistry
    def isolated_registry(path):
        if Path(path) == ROOT / 'work/test-empty-media-registry.json':
            path = Path(state) / 'empty-media-registry.json'
        return original_registry(path)
    test_eggbev_clone_v3.MediaRegistry = isolated_registry
    with (WORK / (label + '.log')).open('w') as log:
        result = unittest.TextTestRunner(stream=log, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(modules))
after = hashes()
receipt = {'modules': modules, 'tests_run': result.testsRun,
           'failures': len(result.failures), 'errors': len(result.errors),
           'skipped': len(result.skipped), 'successful': result.wasSuccessful(),
           'failure_test_ids': [t.id() for t, _ in result.failures],
           'error_test_ids': [t.id() for t, _ in result.errors],
           'network_process_guard': True, 'write_guard': True,
           'blocked_transports': blocked, 'write_denials': write_denials,
           'protected_hashes_before': before, 'protected_hashes_after': after,
           'protected_unchanged_during_tests': before == after,
           'log': str(WORK / (label + '.log'))}
(WORK / (label + '.json')).write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({k: v for k, v in receipt.items() if not k.startswith('protected_hashes')}, indent=2))
sys.exit(0 if result.wasSuccessful() and not blocked and not write_denials and before == after else 1)
