import os
import subprocess
from pathlib import Path


SCRIPT = Path('/root/mgs-agent/scripts/monitor-cron-stale-logs.sh')


def test_duplicate_schedules_emit_one_problem_in_dry_run(tmp_path: Path) -> None:
    fake_log = tmp_path / 'shared.log'
    fake_log.write_text(
        '{"status": "FAIL", "error_type": "RuntimeError", '
        '"error": "another MGS off-site backup or restore is already running"}\n',
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

    assert result.returncode == 0, result.stderr
    assert result.stdout.count('mgs-offsite-backup.py') == 4
    assert 'problems=1 resolved=0 dry_run=1' in result.stdout