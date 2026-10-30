"""Task-local regression receipt; never permits non-loopback sockets."""
import argparse
import json
import socket
import sys
from pathlib import Path

ROOT = Path('/root/mgs-agent')
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts'), str(ROOT / 'tests')]
import pytest

parser = argparse.ArgumentParser()
parser.add_argument('--output', required=True, type=Path)
selection = parser.add_mutually_exclusive_group()
selection.add_argument('--suite', action='store_true')
selection.add_argument('--related', action='store_true')
args = parser.parse_args()
targets = [
    'tests/test_shein_media_qa.py::DriveCacheTests::test_same_ready_folder_queried_once_without_skipping_asset_checks',
    'tests/test_ares_campaign_v3_daily_cpv.py::test_meta_preflight_uses_cache_first_token_lookup_without_force_refresh',
    'tests/test_ares_campaign_v3_daily_cpv.py::test_cpv_action_readers_keep_writer_gate_but_reports_use_bounded_shared_lane',
]
if args.related:
    targets = ['tests/test_shein_media_qa.py', 'tests/test_ares_campaign_v3_daily_cpv.py',
               'tests/test_creditoparaveiculo_report_isolation.py', 'tests/test_archive_stock_locations.py']
if args.suite:
    patterns = ['test_shein*.py', 'test_ares_campaign_engine_v3.py', 'test_ares_shein_campaigns_v3.py',
                'test_eggbev_clone_v3.py', 'test_eggbev_from_zero_v3.py', 'test_ares_campaign_v3_daily_cpv.py',
                'test_prestage*.py', 'test_prestaged*.py', 'test_ares_asset_scope*.py',
                'test_creditoparaveiculo_report_isolation.py', 'test_archive_stock_locations.py']
    targets = sorted({str(p.relative_to(ROOT)) for pattern in patterns for p in (ROOT / 'tests').glob(pattern)})

blocked = []
def audit(event, event_args):
    if event == 'socket.connect':
        address = event_args[1]
        if isinstance(address, tuple) and address[0] not in {'127.0.0.1', 'localhost', '::1'}:
            blocked.append('non-loopback socket')
            raise AssertionError('offline regression forbids external network')
    if event == 'socket.getaddrinfo' and event_args[0] not in {'127.0.0.1', 'localhost', '::1', None}:
        blocked.append('external DNS')
        raise AssertionError('offline regression forbids external DNS')
sys.addaudithook(audit)

class Receipt:
    def __init__(self):
        self.items = []
        self.reports = []
        self.subtests = []
    def pytest_collection_finish(self, session):
        self.items = [item.nodeid for item in session.items]
    def pytest_runtest_logreport(self, report):
        if report.when == 'call' or report.failed:
            row = {'id': report.nodeid, 'when': report.when, 'outcome': report.outcome}
            if hasattr(report, 'context'):
                self.subtests.append(row)
            else:
                self.reports.append(row)

receipt = Receipt()
code = pytest.main(['-q', '--tb=short', '-p', 'no:cacheprovider', *targets], plugins=[receipt])
loaded = {n: str(getattr(m, '__file__', '')) for n, m in sys.modules.items() if n.startswith('ares_campaign_v3.')}
wrong = {n: p for n, p in loaded.items() if p and not Path(p).is_relative_to(ROOT / 'scripts')}
summary = {
    'exit_code': int(code), 'collected': len(receipt.items),
    'passed': sum(row['outcome'] == 'passed' for row in receipt.reports),
    'failed': [row for row in receipt.reports if row['outcome'] == 'failed'],
    'skipped': [row for row in receipt.reports if row['outcome'] == 'skipped'],
    'subtests_passed': sum(row['outcome'] == 'passed' for row in receipt.subtests),
    'module_origin_mismatch': wrong, 'external_network_attempts_blocked': len(blocked),
    'network_policy': 'audit hook rejects external DNS and non-loopback sockets; local renderer integration allowed',
    'exclusions': [], 'targets': targets,
}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary))
sys.exit(int(code) or bool(wrong) or bool(blocked))
