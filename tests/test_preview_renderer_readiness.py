"""Deterministic startup races plus isolated real Chromium cleanup/reap."""
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from ares_campaign_v3 import preview_renderer as renderer

PORT = 43123
BROWSER_PATH = '/devtools/browser/12345678-1234-1234-1234-123456789abc'
VALID = f'{PORT}\n{BROWSER_PATH}'
VERSION = {'webSocketDebuggerUrl': f'ws://127.0.0.1:{PORT}{BROWSER_PATH}'}


class Clock:
    def __init__(self, on_sleep=lambda _: None):
        self.now = 0.0
        self.sleeps = 0
        self.on_sleep = on_sleep

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds
        self.sleeps += 1
        self.on_sleep(self.sleeps)


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ['TMPDIR'])
        self.addCleanup(self.tmp.cleanup)
        self.portfile = Path(self.tmp.name) / 'DevToolsActivePort'
        self.proc = Mock()
        self.proc.poll.return_value = None

    def wait(self, clock, opener=None, timeout=1):
        if opener is None:
            opener = Mock(side_effect=lambda *a, **k: io.StringIO(json.dumps(VERSION)))
        with patch.object(renderer.time, 'monotonic', clock.monotonic), \
             patch.object(renderer.time, 'sleep', clock.sleep), \
             patch.object(renderer, 'urlopen', opener):
            result = renderer._wait_for_browser(self.proc, self.portfile, timeout)
        return result, opener

    def test_missing_file_then_complete(self):
        clock = Clock(lambda _: self.portfile.write_text(VALID))
        result, opener = self.wait(clock)
        self.assertEqual(result, VERSION)
        self.assertEqual(clock.sleeps, 1)
        self.assertEqual(opener.call_count, 1)

    def test_empty_file_then_complete(self):
        self.portfile.write_text('')
        clock = Clock(lambda _: self.portfile.write_text(VALID))
        self.assertEqual(self.wait(clock)[0], VERSION)
        self.assertEqual(clock.sleeps, 1)

    def test_partial_writes_do_not_trigger_attach_or_probe(self):
        contents = ['', '431', '43123\n', f'43123\n{BROWSER_PATH[:30]}', VALID]
        self.portfile.write_text(contents[0])
        clock = Clock(lambda n: self.portfile.write_text(contents[min(n, 4)]))
        result, opener = self.wait(clock)
        self.assertEqual(result, VERSION)
        self.assertEqual(clock.sleeps, 4)
        self.assertEqual(opener.call_count, 1)

    def test_invalid_ports_never_probe(self):
        for value in ['0', '-1', '65536', '9999999999999999999999', 'abc', '43.2', '+43123', ' 43123', '\u0664\u0663\u0661\u0662\u0663', '']:
            with self.subTest(value=value):
                self.portfile.write_text(f'{value}\n{BROWSER_PATH}')
                opener = Mock()
                with self.assertRaisesRegex(ValueError, 'startup timed out'):
                    self.wait(Clock(), opener, timeout=.25)
                opener.assert_not_called()

    def test_port_boundaries_are_accepted(self):
        for port in [1, 65535]:
            with self.subTest(port=port):
                self.portfile.write_text(f'{port}\n{BROWSER_PATH}')
                value = {'webSocketDebuggerUrl': f'ws://127.0.0.1:{port}{BROWSER_PATH}'}
                result, _ = self.wait(Clock(), Mock(return_value=io.StringIO(json.dumps(value))))
                self.assertEqual(result, value)

    def test_invalid_or_partial_browser_paths_never_probe(self):
        for path in ['', '/devtools/browser/', BROWSER_PATH[:-1], '/devtools/page/123', 'https://outside.invalid', BROWSER_PATH + '\nextra']:
            with self.subTest(path=path):
                self.portfile.write_text(f'{PORT}\n{path}')
                opener = Mock()
                with self.assertRaisesRegex(ValueError, 'startup timed out'):
                    self.wait(Clock(), opener, timeout=.25)
                opener.assert_not_called()

    def test_invalid_encoding_retries_then_accepts(self):
        self.portfile.write_bytes(b'\xff')
        self.assertEqual(self.wait(Clock(lambda _: self.portfile.write_text(VALID)))[0], VERSION)

    def test_disappearing_file_is_retryable(self):
        with patch.object(Path, 'read_text', side_effect=[FileNotFoundError(), VALID]):
            self.assertEqual(self.wait(Clock())[0], VERSION)

    def test_transient_endpoint_unavailable_then_ready(self):
        self.portfile.write_text(VALID)
        opener = Mock(side_effect=[OSError('not listening yet'), io.StringIO(json.dumps(VERSION))])
        clock = Clock()
        self.assertEqual(self.wait(clock, opener)[0], VERSION)
        self.assertEqual(clock.sleeps, 1)

    def test_version_malformed_or_wrong_endpoint_does_not_attach(self):
        variants = ['not json', '[]', '{}', json.dumps({'webSocketDebuggerUrl': 5})]
        for url in [f'ws://outside.invalid:{PORT}{BROWSER_PATH}', f'ws://127.0.0.1:1{BROWSER_PATH}', f'wss://127.0.0.1:{PORT}{BROWSER_PATH}', f'ws://127.0.0.1:{PORT}/devtools/browser/wrong', f'ws://user@127.0.0.1:{PORT}{BROWSER_PATH}', f'ws://127.0.0.1:{PORT}{BROWSER_PATH}?x=1', f'ws://127.0.0.1:{PORT}{BROWSER_PATH}#x']:
            variants.append(json.dumps({'webSocketDebuggerUrl': url}))
        self.portfile.write_text(VALID)
        for value in variants:
            with self.subTest(value=value):
                opener = Mock(side_effect=lambda *a, **k: io.StringIO(value))
                with self.assertRaisesRegex(ValueError, 'startup timed out'):
                    self.wait(Clock(), opener, timeout=.25)

    def test_dead_process_fails_immediately_even_with_valid_file(self):
        self.portfile.write_text(VALID)
        self.proc.poll.return_value = 1
        opener = Mock()
        clock = Clock()
        with self.assertRaisesRegex(ValueError, 'exited before readiness'):
            self.wait(clock, opener)
        opener.assert_not_called()
        self.assertEqual(clock.sleeps, 0)

    def test_process_death_during_probe_is_rejected(self):
        self.portfile.write_text(VALID)
        self.proc.poll.side_effect = [None, 1]
        with self.assertRaisesRegex(ValueError, 'exited before readiness'):
            self.wait(Clock())

    def test_timeout_is_bounded_for_empty_file(self):
        self.portfile.write_text('')
        clock = Clock()
        with self.assertRaisesRegex(ValueError, 'startup timed out'):
            self.wait(clock, timeout=.25)
        self.assertLessEqual(clock.now, .25)

    def test_http_timeout_is_capped_by_remaining_deadline(self):
        self.portfile.write_text(VALID)
        opener = Mock(side_effect=OSError('not ready'))
        with self.assertRaisesRegex(ValueError, 'startup timed out'):
            self.wait(Clock(), opener, timeout=.25)
        self.assertTrue(opener.call_args_list)
        self.assertTrue(all(0 < c.kwargs['timeout'] <= .25 for c in opener.call_args_list))

    def test_probe_completing_after_deadline_is_rejected(self):
        self.portfile.write_text(VALID)
        clock = Clock()
        def late(*a, **k):
            clock.now = 2
            return io.StringIO(json.dumps(VERSION))
        with self.assertRaisesRegex(ValueError, 'startup timed out'):
            self.wait(clock, Mock(side_effect=late), timeout=1)


class LauncherCleanupTests(unittest.TestCase):
    chrome = '/root/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome'

    def test_startup_failure_terminates_only_owned_group_and_reaps_before_cleanup(self):
        proc = Mock(pid=987654321)
        proc.wait.side_effect = [subprocess.TimeoutExpired('owned-browser', 5), 0]
        created = []
        def launched(args, **kwargs):
            self.assertTrue(kwargs['start_new_session'])
            directory = next(a.split('=', 1)[1] for a in args if a.startswith('--user-data-dir='))
            created.append(Path(directory))
            (created[0] / 'own-file').write_text('owned temporary profile')
            return proc
        with patch.object(renderer.subprocess, 'Popen', side_effect=launched), \
             patch.object(renderer, '_wait_for_browser', side_effect=ValueError('not ready')), \
             patch.object(renderer.os, 'killpg') as kill, \
             patch('websockets.sync.client.connect') as connect:
            with self.assertRaisesRegex(ValueError, 'activation remains PAUSED'):
                renderer.render_previews([], chrome_path=self.chrome)
        connect.assert_not_called()
        self.assertEqual(kill.call_args_list, [unittest.mock.call(proc.pid, renderer.signal.SIGTERM), unittest.mock.call(proc.pid, renderer.signal.SIGKILL)])
        self.assertEqual(proc.wait.call_count, 2)
        self.assertFalse(created[0].exists())
        self.assertTrue(Path(self.chrome).is_file())

    def test_real_dead_child_is_reaped_and_only_temporary_profile_is_removed(self):
        self._real_cleanup('/bin/false', expect_failure=True)

    def test_real_chromium_success_is_reaped_and_temporary_profile_removed(self):
        for _ in range(3):
            self._real_cleanup(self.chrome, expect_failure=False)

    def _real_cleanup(self, executable, *, expect_failure):
        original = subprocess.Popen
        children = []
        directories = []
        def launch(args, **kwargs):
            child = original(args, **kwargs)
            children.append(child)
            directories.append(Path(next(a.split('=', 1)[1] for a in args if a.startswith('--user-data-dir='))))
            return child
        with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']) as scratch:
            sentinel = Path(scratch) / 'protected-sentinel'
            sentinel.write_text('preserve')
            with patch.dict(os.environ, {'TMPDIR': scratch}), patch.object(renderer.subprocess, 'Popen', side_effect=launch):
                if expect_failure:
                    with self.assertRaisesRegex(ValueError, 'activation remains PAUSED'):
                        renderer.render_previews([], chrome_path=executable, timeout=3)
                else:
                    self.assertEqual(renderer.render_previews([], chrome_path=executable, timeout=8), [])
            self.assertEqual(sentinel.read_text(), 'preserve')
            self.assertEqual(len(children), 1)
            self.assertIsNotNone(children[0].returncode)
            with self.assertRaises(ChildProcessError):
                os.waitpid(children[0].pid, os.WNOHANG)
            self.assertFalse(directories[0].exists())
            self.assertTrue(Path(executable).exists())


if __name__ == '__main__':
    unittest.main()
