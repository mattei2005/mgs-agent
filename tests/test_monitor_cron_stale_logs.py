import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path


SCRIPT = Path('/root/mgs-agent/scripts/monitor-cron-stale-logs.sh')


class CronStaleLogMonitorTests(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()