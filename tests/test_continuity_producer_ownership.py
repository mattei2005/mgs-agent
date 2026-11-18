import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, '/root/mgs-agent/scripts')


class ProducerOwnershipTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('supervisor_ownership', '/root/mgs-agent/scripts/mgs_automation_supervisor.py')
        assert spec and spec.loader
        self.m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.m)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.proc = Path(self.tmp.name)
        self.script = '/root/mgs-agent/scripts/alerts-infra-failed-alert-resolver.py'
        self.source = {'kind': 'producer', 'script': Path(self.script).name}
        self.process(100, 90, ['python3', self.script])
        self.process(90, 80, ['flock', '-n', '/var/lock/resolver.lock', self.script])
        self.process(80, 1, ['/bin/sh', '-c', 'flock -n /var/lock/resolver.lock ' + self.script + ' >> /root/mgs-agent/logs/resolver.log 2>&1'])
        self.process(1, 0, ['/sbin/init'])

    def process(self, pid, ppid, args):
        directory = self.proc / str(pid)
        directory.mkdir(exist_ok=True)
        (directory / 'cmdline').write_bytes(b'\0'.join(a.encode() for a in args) + b'\0')
        (directory / 'stat').write_text(f'{pid} (fixture process) S {ppid} ' + '0 ' * 20)

    def mapped_path(self, *args):
        path = Path(*args)
        if str(path) == '/proc' or str(path).startswith('/proc/'):
            return self.proc / path.relative_to('/proc')
        return path

    def active(self, source=None):
        with patch.object(self.m, 'Path', side_effect=self.mapped_path), patch.object(self.m.os, 'getpid', return_value=100):
            return self.m.original_active(source or self.source)

    def test_own_flock_ancestor_is_not_a_parallel_writer(self):
        self.assertFalse(self.active())

    def test_foreign_flock_is_still_a_parallel_writer(self):
        self.process(200, 1, ['/usr/bin/flock', '-n', '/var/lock/other.lock', self.script])
        self.assertTrue(self.active())

    def test_foreign_interpreter_is_still_a_parallel_writer(self):
        self.process(201, 1, ['python3', self.script])
        self.assertTrue(self.active())

    def test_non_flock_ancestor_is_not_ignored(self):
        self.process(90, 80, ['python3', self.script])
        self.assertTrue(self.active())

    def test_ancestor_is_not_ignored_for_another_producer(self):
        self.process(100, 90, ['python3', '/root/mgs-agent/scripts/different.py'])
        self.assertTrue(self.active())

    def test_unreadable_ancestry_keeps_writer_gate(self):
        (self.proc / '100' / 'stat').write_text('unreadable fixture')
        self.assertTrue(self.active())

    def test_active_worker_receipt_still_wins(self):
        with patch.object(self.m, 'worker_active', return_value=True):
            self.assertTrue(self.active({**self.source, 'continuity_key': 'same-request'}))


if __name__ == '__main__':
    unittest.main()
