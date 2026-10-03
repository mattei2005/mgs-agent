#!/usr/bin/env python3
"""One deterministic, secret-free performance readback for the three MGS agents.

No package/config/process mutations and no model/API calls. Use the JSON summary
before opening full logs, databases, or unrelated infrastructure inventories.
"""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time

try:
    import yaml
except ModuleNotFoundError as exc:
    # Hermes install-store Python can omit PyYAML. The verified distro Python
    # owns this diagnostic dependency; do not install packages or mix ABIs.
    system_python = Path('/usr/bin/python3')
    if exc.name != 'yaml' or __name__ != '__main__' or Path(sys.executable).resolve() == system_python.resolve():
        raise
    os.execv(str(system_python), [str(system_python), str(Path(__file__).resolve()), *sys.argv[1:]])

PROFILES = ('zeus', 'atena', 'ares')


def cpu_counters():
    values = [int(x) for x in Path('/proc/stat').read_text().splitlines()[0].split()[1:9]]
    return sum(values), values[3] + values[4], values[4], values[7]


def store_bytes(path):
    total = 0
    errors = 0
    for root, _, files in os.walk(path):
        for name in files:
            try: total += (Path(root) / name).stat().st_size
            except OSError: errors += 1
    return total, errors


def collect(sample_seconds=1):
    first = cpu_counters(); time.sleep(sample_seconds); last = cpu_counters()
    elapsed = last[0] - first[0]
    memory = dict((key.rstrip(':'), int(value.split()[0])) for key, value in
        (line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines()))
    disk = os.statvfs('/')
    result = {'observed_at': datetime.now().astimezone().isoformat(), 'cpu_count': os.cpu_count(),
        'load_average': list(os.getloadavg()),
        'cpu_busy_pct': round(100 * (1 - (last[1] - first[1]) / elapsed), 2) if elapsed else None,
        'iowait_pct': round(100 * (last[2] - first[2]) / elapsed, 2) if elapsed else None,
        'steal_pct': round(100 * (last[3] - first[3]) / elapsed, 2) if elapsed else None,
        'memory_available_mib': round(memory['MemAvailable'] / 1024, 1),
        'memory_total_mib': round(memory['MemTotal'] / 1024, 1),
        'disk_available_gib': round(disk.f_bavail * disk.f_frsize / 1024**3, 2), 'profiles': {}}
    budget_path = Path('/root/mgs-agent/data/browser-resource-budget.json')
    if budget_path.exists():
        budget = json.loads(budget_path.read_text())
        result['browser_budget'] = {key: budget.get(key) for key in ('slots', 'batch_slots', 'local_workers', 'wait_timeout_seconds')}
    for profile in PROFILES:
        home = Path('/root/.hermes/profiles') / profile
        config = yaml.safe_load((home / 'config.yaml').read_text())
        service = subprocess.run(['systemctl', 'show', profile + '-gateway', '-p', 'ActiveState', '-p', 'MainPID'], capture_output=True, text=True, timeout=10)
        values = dict(line.split('=', 1) for line in service.stdout.splitlines() if '=' in line)
        size, errors = store_bytes(home / 'checkpoints/store')
        result['profiles'][profile] = {'service': values, 'compression_threshold': config.get('compression', {}).get('threshold'),
            'browser_budget_configured': bool(config.get('browser', {}).get('resource_budget_module')),
            'checkpoint_store_mib': round(size / 1024**2, 2), 'checkpoint_scan_errors': errors,
            'checkpoint_cap_mib': config.get('checkpoints', {}).get('max_total_size_mb')}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sample-seconds', type=float, default=1)
    args = parser.parse_args()
    if not 0.1 <= args.sample_seconds <= 30: parser.error('sample must be 0.1–30 seconds')
    print(json.dumps(collect(args.sample_seconds), indent=2))


if __name__ == '__main__': main()
