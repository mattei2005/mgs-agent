from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path


RUNNER = Path('/root/mgs-agent/scripts/ares-meta-library-heavy-run.sh')
ROOT = Path('/root/mgs-agent')


def make_mock_systemd_run(tmp_path: Path) -> Path:
    mock = tmp_path / 'systemd-run-mock'
    mock.write_text(
        '#!/usr/bin/env bash\n'
        'set -euo pipefail\n'
        ': "${MOCK_ARGV_LOG:?}"\n'
        'printf "%s\\n" "$@" >> "$MOCK_ARGV_LOG"\n'
        'while (($#)); do\n'
        '  if [[ "$1" == "--" ]]; then shift; break; fi\n'
        '  shift\n'
        'done\n'
        'exec "$@"\n'
    )
    mock.chmod(0o700)
    return mock


def runner_env(tmp_path: Path, mock: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.update({
        'ARES_META_LIBRARY_HEAVY_LOCK_FILE': str(tmp_path / 'queue.lock'),
        'ARES_META_LIBRARY_HEAVY_LOCK_TIMEOUT': '10',
        'ARES_META_LIBRARY_HEAVY_SYSTEMD_RUN': str(mock),
        'MOCK_ARGV_LOG': str(tmp_path / 'argv.log'),
    })
    return env


def test_runner_propagates_exit_and_resource_contract(tmp_path: Path):
    mock = make_mock_systemd_run(tmp_path)
    env = runner_env(tmp_path, mock)
    ok = subprocess.run([str(RUNNER), '--label', 'fixture', '--', '/bin/sh', '-c', 'exit 0'], env=env)
    failed = subprocess.run([str(RUNNER), '--label', 'fixture', '--', '/bin/sh', '-c', 'exit 23'], env=env)
    assert ok.returncode == 0
    assert failed.returncode == 23
    argv = (tmp_path / 'argv.log').read_text()
    assert '--property=CPUQuota=180%' in argv
    assert '--property=MemoryHigh=5G' in argv
    assert '--property=Nice=10' in argv
    assert '--expand-environment=no' in argv


def test_runner_serializes_meta_library_jobs(tmp_path: Path):
    mock = make_mock_systemd_run(tmp_path)
    env = runner_env(tmp_path, mock)
    started = tmp_path / 'first-started'
    ended = tmp_path / 'first-ended'
    second = tmp_path / 'second-started'
    first_cmd = f'date +%s%N > {started}; sleep 0.35; date +%s%N > {ended}'
    second_cmd = f'date +%s%N > {second}'
    first = subprocess.Popen([str(RUNNER), '--label', 'first', '--', '/bin/sh', '-c', first_cmd], env=env)
    deadline = time.monotonic() + 3
    while not started.exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert started.exists()
    other = subprocess.Popen([str(RUNNER), '--label', 'second', '--', '/bin/sh', '-c', second_cmd], env=env)
    assert first.wait(timeout=5) == 0
    assert other.wait(timeout=5) == 0
    assert int(second.read_text()) >= int(ended.read_text())


def test_campaign_engine_is_not_wrapped():
    guarded = []
    for path in (ROOT / 'scripts' / 'ares_campaign_v3').rglob('*.py'):
        if RUNNER.name in path.read_text(errors='replace'):
            guarded.append(path)
    assert guarded == []
