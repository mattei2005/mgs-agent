import os
import json
import subprocess
import tempfile
import time
import unittest
from pathlib import Path


SCRIPT = Path('/root/mgs-agent/scripts/monitor-cron-stale-logs.sh')


class CronStaleLogMonitorTests(unittest.TestCase):
    def test_new_per_minute_job_without_log_warms_up_then_becomes_stale(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            missing_log = tmp_path / 'not-created-yet.log'
            state = tmp_path / 'state.json'
            fake_bin = tmp_path / 'bin'
            fake_bin.mkdir()
            fake_crontab = fake_bin / 'crontab'
            fake_crontab.write_text(
                '#!/usr/bin/env python3\n'
                'print("* * * * * /root/mgs-agent/scripts/new-minute-monitor.py '
                f'>> {missing_log} 2>&1")\n',
                encoding='utf-8',
            )
            fake_crontab.chmod(0o755)

            env = dict(os.environ)
            env['PATH'] = f'{fake_bin}:{env["PATH"]}'
            env['CRON_STALE_STATE'] = str(state)

            first = subprocess.run(
                [str(SCRIPT)],
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
                check=False,
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertIn('problems=0 resolved=0 alerts_sent=0', first.stdout)
            self.assertIn('new-minute-monitor.py', state.read_text(encoding='utf-8'))

            second = subprocess.run(
                [str(SCRIPT), '--dry-run'],
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
                check=False,
            )
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertIn('new-minute-monitor.py', second.stdout)
            self.assertIn('WARMUP', second.stdout)
            self.assertIn('problems=0 resolved=0 dry_run=1', second.stdout)
            saved = json.loads(state.read_text())
            saved['missing_log_first_seen'][str(missing_log)] = int(time.time()) - 6 * 60
            state.write_text(json.dumps(saved))
            expired = subprocess.run(
                [str(SCRIPT), '--dry-run'], env=env, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=False,
            )
            self.assertEqual(expired.returncode, 0, expired.stderr)
            self.assertIn('STALE', expired.stdout)
            self.assertIn('problems=1 resolved=0 dry_run=1', expired.stdout)

    def test_daily_missing_log_grace_expires_without_hiding_legacy_failure(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            missing_log = tmp_path / 'daily.log'
            state = tmp_path / 'state.json'
            fake_bin = tmp_path / 'bin'
            fake_bin.mkdir()
            fake_crontab = fake_bin / 'crontab'
            fake_crontab.write_text(
                '#!/usr/bin/env python3\n'
                'print("4 23 * * * /root/mgs-agent/scripts/finance-month-rollover.py '
                f'--scheduled >> {missing_log} 2>&1")\n', encoding='utf-8',
            )
            fake_crontab.chmod(0o755)
            env = dict(os.environ)
            env['PATH'] = f'{fake_bin}:{env["PATH"]}'
            env['CRON_STALE_STATE'] = str(state)
            first = subprocess.run(
                [str(SCRIPT)], env=env, capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            saved = json.loads(state.read_text())
            for hours, expected in ((12, 'WARMUP'), (37, 'STALE')):
                saved['missing_log_first_seen'][str(missing_log)] = int(time.time()) - hours * 3600
                state.write_text(json.dumps(saved))
                result = subprocess.run(
                    [str(SCRIPT), '--dry-run'], env=env, capture_output=True, text=True, timeout=30,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(expected, result.stdout)
            saved.pop('missing_log_first_seen')
            state.write_text(json.dumps(saved))
            legacy = subprocess.run(
                [str(SCRIPT), '--dry-run'], env=env, capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(legacy.returncode, 0, legacy.stderr)
            self.assertIn('STALE', legacy.stdout)
            missing_log.write_text('{"pass": true, "status": "not_last_day", "writes": 0}\n')
            recovered = subprocess.run(
                [str(SCRIPT), '--dry-run'], env=env, capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(recovered.returncode, 0, recovered.stderr)
            self.assertIn('problems=0 ', recovered.stdout)

    def test_per_minute_job_uses_five_minute_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            fake_log = tmp_path / 'minute.log'
            fake_log.write_text('{"ok":true}\n', encoding='utf-8')
            stale_time = time.time() - (6 * 60)
            os.utime(fake_log, (stale_time, stale_time))
            fake_bin = tmp_path / 'bin'
            fake_bin.mkdir()
            fake_crontab = fake_bin / 'crontab'
            fake_crontab.write_text(
                '#!/usr/bin/env python3\n'
                'print("* * * * * /root/mgs-agent/scripts/minute-monitor.py '
                f'>> {fake_log} 2>&1")\n',
                encoding='utf-8',
            )
            fake_crontab.chmod(0o755)

            env = dict(os.environ)
            env['PATH'] = f'{fake_bin}:{env["PATH"]}'
            result = subprocess.run(
                [str(SCRIPT), '--dry-run'],
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('minute-monitor.py', result.stdout)
            self.assertIn('STALE', result.stdout)
            self.assertIn('threshold=5min', result.stdout)

    def test_daily_retention_log_does_not_inherit_quarter_hour_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            monitor_log = tmp_path / 'monitor.log'
            retention_log = tmp_path / 'retention.log'
            monitor_log.write_text('{"ok": true}\n', encoding='utf-8')
            retention_log.write_text('{"ok": true}\n', encoding='utf-8')
            stale_for_quarter_hour = time.time() - (66 * 60)
            os.utime(retention_log, (stale_for_quarter_hour, stale_for_quarter_hour))

            cron_rows = [
                '12,27,42,57 * * * * python3 '
                '/root/mgs-agent/scripts/monitor-sb-messenger-token-invalid.py --apply '
                f'>> {monitor_log} 2>&1',
                '5 0 * * * python3 '
                '/root/mgs-agent/scripts/monitor-sb-messenger-token-invalid.py '
                f'--cleanup-old-messages --apply >> {retention_log} 2>&1',
            ]
            fake_bin = tmp_path / 'bin'
            fake_bin.mkdir()
            fake_crontab = fake_bin / 'crontab'
            fake_crontab.write_text(
                '#!/usr/bin/env python3\n'
                f'print({os.linesep.join(cron_rows)!r})\n',
                encoding='utf-8',
            )
            fake_crontab.chmod(0o755)

            env = dict(os.environ)
            env['PATH'] = f'{fake_bin}:{env["PATH"]}'
            result = subprocess.run(
                [str(SCRIPT), '--dry-run'],
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.count('monitor-sb-messenger-token-invalid.py'), 2)
            self.assertNotIn('STALE', result.stdout)
            self.assertIn('problems=0 ', result.stdout)

    def test_duplicate_schedules_emit_one_problem_in_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            fake_log = tmp_path / 'shared.log'
            fake_log.write_text(
                '{"status": "FAIL", "error_type": "RuntimeError", '
                '"error": "No such file or directory while collecting transient cron output"}\n',
                encoding='utf-8',
            )
            cron_rows = [
                f'{schedule} python3 /root/mgs-agent/scripts/mgs-offsite-backup.py status '
                f'>> {fake_log} 2>&1'
                for schedule in (
                    '25 * * * *',
                    '15 3 * * *',
                    '40 5 * * 0',
                    '12 * * * *',
                )
            ]
            fake_bin = tmp_path / 'bin'
            fake_bin.mkdir()
            fake_crontab = fake_bin / 'crontab'
            fake_crontab.write_text(
                '#!/usr/bin/env python3\n'
                f'print({os.linesep.join(cron_rows)!r})\n',
                encoding='utf-8',
            )
            fake_crontab.chmod(0o755)

            env = dict(os.environ)
            env['PATH'] = f'{fake_bin}:{env["PATH"]}'
            result = subprocess.run(
                [str(SCRIPT), '--dry-run'],
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.count('mgs-offsite-backup.py'), 4)
            self.assertIn('problems=1 resolved=0 dry_run=1', result.stdout)

    def test_json_ok_boundary_supersedes_older_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            fake_log = tmp_path / 'activity-monitor.log'
            fake_log.write_text(
                'Traceback (most recent call last):\n'
                'RuntimeError: Meta activities failed: HTTP 429\n'
                '{"ok":true,"mode":"apply","events_fetched":0}\n',
                encoding='utf-8',
            )
            fake_bin = tmp_path / 'bin'
            fake_bin.mkdir()
            fake_crontab = fake_bin / 'crontab'
            fake_crontab.write_text(
                '#!/usr/bin/env python3\n'
                'print("2-57/5 * * * * /root/mgs-agent/scripts/'
                f'ares-meta-account-activity-monitor.py --apply >> {fake_log} 2>&1")\n',
                encoding='utf-8',
            )
            fake_crontab.chmod(0o755)

            env = dict(os.environ)
            env['PATH'] = f'{fake_bin}:{env["PATH"]}'
            result = subprocess.run(
                [str(SCRIPT), '--dry-run'],
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('ares-meta-account-activity-monitor.py | OK', result.stdout)
            self.assertIn('problems=0 ', result.stdout)

    def test_offset_five_minute_schedule_uses_twenty_minute_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            fake_log = tmp_path / 'offset-five.log'
            fake_log.write_text('{"ok":true}\n', encoding='utf-8')
            stale_time = time.time() - (25 * 60)
            os.utime(fake_log, (stale_time, stale_time))
            fake_bin = tmp_path / 'bin'
            fake_bin.mkdir()
            fake_crontab = fake_bin / 'crontab'
            fake_crontab.write_text(
                '#!/usr/bin/env python3\n'
                'print("2-57/5 * * * * /root/mgs-agent/scripts/'
                f'offset-five.py >> {fake_log} 2>&1")\n',
                encoding='utf-8',
            )
            fake_crontab.chmod(0o755)

            env = dict(os.environ)
            env['PATH'] = f'{fake_bin}:{env["PATH"]}'
            result = subprocess.run(
                [str(SCRIPT), '--dry-run'],
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('offset-five.py', result.stdout)
            self.assertIn('STALE', result.stdout)
            self.assertIn('threshold=20min', result.stdout)

    def test_honcho_minute_watcher_uses_five_minute_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            fake_log = tmp_path / 'billing-watch.log'
            fake_log.write_text('{"status":"ok"}\n', encoding='utf-8')
            stale_time = time.time() - (6 * 60)
            os.utime(fake_log, (stale_time, stale_time))
            fake_bin = tmp_path / 'bin'
            fake_bin.mkdir()
            fake_crontab = fake_bin / 'crontab'
            fake_crontab.write_text(
                '#!/usr/bin/env python3\n'
                'print("* * * * * /root/mgs-agent/scripts/'
                f'monitor_honcho_billing_watch.py >> {fake_log} 2>&1")\n',
                encoding='utf-8',
            )
            fake_crontab.chmod(0o755)
            env = dict(os.environ)
            env['PATH'] = f'{fake_bin}:{env["PATH"]}'
            result = subprocess.run(
                [str(SCRIPT), '--dry-run'], env=env, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('STALE', result.stdout)
            self.assertIn('threshold=5min', result.stdout)

    def test_honcho_six_hour_probe_uses_nine_hour_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            fake_log = tmp_path / 'health.log'
            fake_log.write_text('SKIP healthy\n', encoding='utf-8')
            stale_time = time.time() - (10 * 3600)
            os.utime(fake_log, (stale_time, stale_time))
            fake_bin = tmp_path / 'bin'
            fake_bin.mkdir()
            fake_crontab = fake_bin / 'crontab'
            fake_crontab.write_text(
                '#!/usr/bin/env python3\n'
                'print("54 2,8,14,20 * * * /root/mgs-agent/scripts/'
                f'monitor-honcho-health.sh >> {fake_log} 2>&1")\n',
                encoding='utf-8',
            )
            fake_crontab.chmod(0o755)
            env = dict(os.environ)
            env['PATH'] = f'{fake_bin}:{env["PATH"]}'
            result = subprocess.run(
                [str(SCRIPT), '--dry-run'], env=env, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('STALE', result.stdout)
            self.assertIn('threshold=540min', result.stdout)


class FinanceJsonBoundaryTests(unittest.TestCase):
    def test_applied_boundary_preserves_later_and_incomplete_failures(self) -> None:
        failure = json.dumps({'pass': False, 'status': 'failed', 'detail': 'Traceback: remote preflight failed'})
        cases = (
            ([failure, json.dumps({'pass': True, 'status': 'applied'})], 'OK'),
            ([failure, json.dumps({'pass': True, 'status': 'already_applied'})], 'OK'),
            ([json.dumps({'pass': True, 'status': 'applied'}), failure], 'ERROR'),
            ([failure, json.dumps({'pass': False, 'status': 'applied'})], 'ERROR'),
            ([failure, json.dumps({'pass': True, 'status': 'partial_applied'})], 'ERROR'),
        )
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            log = root / 'gam.log'
            fake_bin = root / 'bin'
            fake_bin.mkdir()
            crontab = fake_bin / 'crontab'
            crontab.write_text(
                '#!/usr/bin/env python3\n'
                'print("3,8,18,28 8 * * * /usr/bin/python3 '
                '/root/mgs-agent/apps/finance-system/finance_gam_revenue_sync.py '
                f'--scheduled-intake >> {log} 2>&1")\n'
            )
            crontab.chmod(0o755)
            env = dict(os.environ, PATH=f'{fake_bin}:{os.environ["PATH"]}',
                       CRON_STALE_STATE=str(root / 'state.json'))
            for lines, expected in cases:
                with self.subTest(lines=lines):
                    log.write_text('\n'.join(lines) + '\n')
                    # Keep the real producer heartbeat older than this isolated log.
                    stamp = time.time() + 60
                    os.utime(log, (stamp, stamp))
                    result = subprocess.run([str(SCRIPT), '--dry-run'], env=env,
                                            capture_output=True, text=True, timeout=30)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn(f'| {expected:6} |', result.stdout)


if __name__ == '__main__':
    unittest.main()