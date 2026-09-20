from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path('/root/mgs-agent/scripts/monitor-vps-health.py')
spec = importlib.util.spec_from_file_location('monitor_vps_health', SCRIPT)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_cpu_usage_from_five_minute_samples():
    previous = {'idle': 1_000, 'total': 2_000, 'observed_at': 100.0}
    current = {'idle': 1_600, 'total': 3_000, 'observed_at': 400.0}
    used, elapsed = m.cpu_usage_from_samples(previous, current)
    assert used == 40.0
    assert elapsed == 300.0


def test_cpu_usage_rejects_short_or_stale_windows():
    previous = {'idle': 100, 'total': 200, 'observed_at': 100.0}
    assert m.cpu_usage_from_samples(previous, {'idle': 101, 'total': 210, 'observed_at': 101.0}) is None
    assert m.cpu_usage_from_samples(previous, {'idle': 900, 'total': 1_200, 'observed_at': 1_100.0}) is None


def test_cpu_metric_never_uses_instant_spike_and_preserves_short_window(monkeypatch):
    previous = {'idle': 100, 'total': 200, 'observed_at': 100.0}
    current = {'idle': 101, 'total': 210, 'observed_at': 105.0}
    monkeypatch.setattr(m, 'read_cpu_sample', lambda: current)
    metric, persisted = m.cpu_usage_metric(previous)
    assert metric == {'used_pct': None, 'source': 'window_pending', 'window_seconds': 5}
    assert persisted is previous


def test_recent_authorized_restart_is_service_specific(tmp_path: Path):
    audit = tmp_path / 'audit.jsonl'
    now = 2_000_000_000.0
    rows = [
        {
            'ts': '2033-05-18T03:31:40Z',
            'event': 'gateway_restart_finalizer_started',
            'reason': 'authorized-cutover',
            'detail': 'agents=ares atena zeus',
        },
    ]
    audit.write_text('\n'.join(json.dumps(row) for row in rows) + '\n')
    assert m.recent_authorized_restart('ares-gateway', now, audit_path=audit) == 'authorized-cutover'
    assert m.recent_authorized_restart('mgs-autocommit', now, audit_path=audit) is None


def test_embed_labels_rolling_cpu_and_sanitized_consumers():
    metrics = {
        'cpu': {'used_pct': 41.2, 'source': 'rolling_proc_stat', 'window_seconds': 300},
        'memory': {'used_pct': 25.0, 'available_mb': 12000},
        'disk_root': {'used_pct': 60.0, 'free_gb': 75.0},
        'load': {'load1': 1.0, 'load5': 1.5, 'load15': 2.0},
        'inode_root': {'used_pct': 4.0},
        'updates': {'available': False, 'index_refreshed': False},
        'mgs_backups': {'gb': 2.0},
        'uptime': {'days': 4.0},
        'services': {'ares-gateway': {'active': 'active'}},
        'top_consumers': [
            {'class': 'Ares Meta Library', 'process': 'chrome-headless', 'cpu_pct': 98.0, 'rss_mb': 512, 'pid': 123},
        ],
    }
    embeds = m.build_status_embeds('test', 1, metrics, [])
    rendered = json.dumps(embeds, ensure_ascii=False)
    assert 'média 300s' in rendered
    assert 'Ares Meta Library' in rendered
    assert 'chrome-headless' in rendered
    assert 'http' not in rendered
