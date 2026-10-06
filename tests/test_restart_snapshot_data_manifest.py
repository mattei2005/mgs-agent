"""Restart metadata must not be parsed as shell execution by Hermes' intact guard."""
from pathlib import Path
import re

from cron.lifecycle_guard import scan_gateway_lifecycle

ROOT = Path('/root/mgs-agent')
HELPER = ROOT / 'scripts/mgs-gateway-restart-safe.sh'
OLD = ROOT / 'backups/discord-thread-suffix-20261006-1557017992934727691/mgs-gateway-restart-safe.sh'
MANIFEST = ROOT / 'data/mgs-gateway-restart-ares-snapshot-files.txt'


def scan(text, cwd):
    reads = []

    def backend(path):
        reads.append(path)
        source = Path(path)
        if source.is_file() and source.stat().st_size < 1024 * 1024:
            return source.read_text(errors='replace')
        return None

    return scan_gateway_lifecycle(text, cwd=cwd, read_remote_script=backend), reads


def test_original_helper_reproduces_document_walk_budget_failure():
    result, reads = scan(OLD.read_text(), str(HELPER.parent))
    assert result[0] is True and 'remote reads' in result[1]
    assert len(reads) == 64


def test_live_helper_passes_unchanged_native_guard():
    result, reads = scan(str(HELPER) + ' --agents "ares atena zeus" --reason fixture', '/root')
    assert result == (False, None)
    assert len(reads) <= 8


def test_manifest_preserves_exact_protected_ares_files():
    old_array = re.search(r'SNAPSHOT_FILES\+=\(\n(.*?)\n  \)', OLD.read_text(), re.S).group(1)
    expected = re.findall(r'"(/root/[^"\n]+)"', old_array)
    actual = [line for line in MANIFEST.read_text().splitlines() if line and not line.startswith('#')]
    assert len(expected) == len(actual) == 7
    assert actual == expected
    assert [p for p in actual if Path(p).is_file()] == [p for p in expected if Path(p).is_file()]
    assert 'SNAPSHOT_FILES+=("$ARES_SNAPSHOT_MANIFEST")' in HELPER.read_text()


def test_direct_lifecycle_commands_remain_blocked():
    # Negative safety fixtures: this test never executes a lifecycle command.
    for command in ['hermes gateway restart', 'systemctl restart hermes-gateway',
                    'bash -c "hermes gateway stop"']:
        assert scan_gateway_lifecycle(command, cwd='/root')[0] is True


def test_referenced_unsafe_script_remains_blocked(tmp_path):
    unsafe = tmp_path / 'unsafe-fixture.sh'
    unsafe.write_text('#!/bin/sh\nhermes gateway restart\n')
    assert scan_gateway_lifecycle('bash ' + str(unsafe), cwd=str(tmp_path))[0] is True
