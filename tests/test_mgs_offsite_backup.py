from __future__ import annotations

import datetime as dt
import fcntl
import importlib.util
import io
import json
import os
import tarfile
import tempfile
import threading
import time
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path('/root/mgs-agent/scripts/mgs-offsite-backup.py')
spec = importlib.util.spec_from_file_location('mgs_offsite_backup', SCRIPT)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class OffsiteBackupTests(unittest.TestCase):
    def test_lock_waits_for_real_holder_without_truncating(self) -> None:
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as raw:
            lock_path = Path(raw) / 'backup.lock'
            lock_path.write_text('holder marker')
            holder = lock_path.open('a')
            fcntl.flock(holder, fcntl.LOCK_EX | fcntl.LOCK_NB)
            release = threading.Timer(0.05, holder.close)
            release.start()
            try:
                started = time.monotonic()
                acquired = mod.acquire_lock({'lock_path': str(lock_path)}, timeout_seconds=0.3)
                try:
                    self.assertGreaterEqual(time.monotonic() - started, 0.05)
                    self.assertEqual(lock_path.read_text(), 'holder marker')
                    with lock_path.open('a') as contender:
                        with self.assertRaises(BlockingIOError):
                            fcntl.flock(contender, fcntl.LOCK_EX | fcntl.LOCK_NB)
                finally:
                    acquired.close()
            finally:
                release.join()
                holder.close()

    def test_lock_timeout_preserves_holder_and_can_retry(self) -> None:
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as raw:
            lock_path = Path(raw) / 'backup.lock'
            config = {'lock_path': str(lock_path)}
            with lock_path.open('a') as holder:
                fcntl.flock(holder, fcntl.LOCK_EX | fcntl.LOCK_NB)
                started = time.monotonic()
                with self.assertRaisesRegex(RuntimeError, 'lock wait exceeded 0.03s'):
                    mod.acquire_lock(config, timeout_seconds=0.03)
                self.assertLess(time.monotonic() - started, 1.0)
                with lock_path.open('a') as contender:
                    with self.assertRaises(BlockingIOError):
                        fcntl.flock(contender, fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = mod.acquire_lock(config, timeout_seconds=0)
            acquired.close()

    def test_lock_io_error_closes_handle_without_retry(self) -> None:
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as raw:
            lock_path = Path(raw) / 'backup.lock'
            handle = lock_path.open('a')
            with patch.object(mod.Path, 'open', return_value=handle), \
                 patch.object(mod.fcntl, 'flock', side_effect=OSError('fixture I/O failure')), \
                 patch.object(mod.time, 'sleep') as sleep:
                with self.assertRaisesRegex(OSError, 'fixture I/O failure'):
                    mod.acquire_lock({'lock_path': str(lock_path)})
                self.assertTrue(handle.closed)
                sleep.assert_not_called()

    def test_full_tier_classification(self) -> None:
        self.assertEqual(mod.classify_full_tier(dt.datetime(2026, 8, 1, tzinfo=dt.timezone.utc)), 'monthly')
        self.assertEqual(mod.classify_full_tier(dt.datetime(2026, 7, 19, tzinfo=dt.timezone.utc)), 'weekly')
        self.assertEqual(mod.classify_full_tier(dt.datetime(2026, 7, 20, tzinfo=dt.timezone.utc)), 'daily')

    def test_skip_large_and_transient_data(self) -> None:
        self.assertTrue(mod.is_skipped_rel(Path('data/generated/asset.png')))
        self.assertTrue(mod.is_skipped_rel(Path('data/ares/creative-inventory/frames/a.jpg')))
        self.assertTrue(mod.is_skipped_rel(Path('data/ares/creative-ops/ready/a.mp4')))
        self.assertTrue(mod.is_skipped_rel(Path('tmp/test.json')))
        self.assertFalse(mod.is_skipped_rel(Path('data/knowledge-registry.json')))

    def test_quick_inventory_has_continuity_sources(self) -> None:
        names = {arc.as_posix() for _, arc in mod.iter_mgs_files('quick')}
        self.assertIn('mgs-agent/context/knowledge-governance.md', names)
        self.assertIn('mgs-agent/data/agent-checkpoints.json', names)
        self.assertIn('mgs-agent/data/knowledge-registry.json', names)
        self.assertIn('mgs-agent/config/backup/mgs-dr-backup-public.asc', names)

    def test_full_inventory_excludes_binary_assets_and_secret_backups(self) -> None:
        rows = list(mod.iter_mgs_files('full'))
        rels = {src.relative_to(mod.REPO).as_posix() for src, _ in rows}
        self.assertIn('context/mgs-os-map.md', rels)
        self.assertIn('scripts/mgs-knowledge-control.py', rels)
        self.assertIn('.env', rels)
        self.assertIn('apps/finance-system/server.mjs', rels)
        self.assertNotIn('apps/finance-system/private/source.json', rels)
        self.assertNotIn('apps/finance-system/node_modules/express/package.json', rels)
        self.assertIn('reports/finance-full-audit-1548812376290234451.md', rels)
        self.assertTrue(all(not rel.startswith('data/generated/') for rel in rels))
        self.assertTrue(all(not rel.startswith('data/ares/creative-inventory/') for rel in rels))
        self.assertTrue(all(not Path(rel).name.startswith('.env.bak') for rel in rels))
        self.assertTrue(all(not (rel.startswith('data/') and Path(rel).suffix.lower() not in mod.MGS_DATA_SUFFIXES) for rel in rels))

    def test_safe_zip_rejects_path_traversal(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            good = tmp_path / 'good.zip'
            with zipfile.ZipFile(good, 'w') as archive:
                archive.writestr('safe/file.txt', 'ok')
            mod.safe_zip(good)

            bad = tmp_path / 'bad.zip'
            with zipfile.ZipFile(bad, 'w') as archive:
                archive.writestr('../escape.txt', 'bad')
            with self.assertRaisesRegex(RuntimeError, 'unsafe zip member'):
                mod.safe_zip(bad)

    def test_registered_reports_survive_nested_and_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as raw:
            repo = Path(raw) / 'repo'
            nested = repo / 'data/ares/meta-ads/reports/example/report.md'
            absolute = repo / 'reports/absolute.md'
            unrelated = repo / 'reports/unregistered.md'
            outside = Path(raw) / 'reports/outside.md'
            linked = repo / 'reports/linked.md'
            oversized = repo / 'reports/oversized.txt'
            binary = repo / 'reports/image.png'
            for path in (nested, absolute, unrelated, outside, oversized, binary):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('fixture')
            with oversized.open('wb') as handle:
                handle.truncate(10 * 1024 * 1024 + 1)
            linked.symlink_to(absolute)
            registry = repo / 'data/knowledge-registry.json'
            registry.parent.mkdir(parents=True, exist_ok=True)
            registry.write_text(json.dumps({'entries': [
                {'canonical_source': nested.relative_to(repo).as_posix()},
                {'canonical_source': str(absolute)},
                {'canonical_source': str(outside)},
                {'canonical_source': linked.relative_to(repo).as_posix()},
                {'canonical_source': oversized.relative_to(repo).as_posix()},
                {'canonical_source': binary.relative_to(repo).as_posix()},
            ]}))
            with patch.object(mod, 'REPO', repo):
                rows = list(mod.iter_mgs_files('full'))
            rels = {src.relative_to(repo).as_posix() for src, _ in rows}
            self.assertIn(nested.relative_to(repo).as_posix(), rels)
            self.assertIn(absolute.relative_to(repo).as_posix(), rels)
            self.assertNotIn(unrelated.relative_to(repo).as_posix(), rels)
            self.assertNotIn(linked.relative_to(repo).as_posix(), rels)
            self.assertNotIn(oversized.relative_to(repo).as_posix(), rels)
            self.assertNotIn(binary.relative_to(repo).as_posix(), rels)

    def test_live_registered_local_reports_are_in_full_inventory(self) -> None:
        selected = {src.resolve() for src, _ in mod.iter_mgs_files('full')}
        registry = json.loads((mod.REPO / 'data/knowledge-registry.json').read_text())
        for entry in registry['entries']:
            source = Path(entry['canonical_source'])
            path = source if source.is_absolute() else mod.REPO / source
            resolved = path.resolve()
            if resolved.is_relative_to(mod.REPO) and 'reports' in resolved.relative_to(mod.REPO).parts[:-1]:
                with self.subTest(source=str(source)):
                    self.assertIn(resolved, selected)

    def test_archive_skips_file_deleted_after_inventory(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            vanished = tmp_path / 'vanished.md'
            output = tmp_path / 'output.zip'
            vanished.write_text('transient cron output')
            vanished.unlink()
            with zipfile.ZipFile(output, 'w') as archive:
                self.assertFalse(mod.archive_write_if_present(archive, vanished, 'cron/output/vanished.md'))
            with zipfile.ZipFile(output) as archive:
                self.assertEqual(archive.namelist(), [])

    def test_monitor_fails_on_newer_restore_failure(self) -> None:
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as raw:
            state = Path(raw) / 'state.json'
            now = mod.iso_now()
            state.write_text(json.dumps({
                'last_success': {'quick': {'created_at_utc': now}, 'full': {'created_at_utc': now}},
                'last_restore_test': {'tested_at_utc': '2026-09-06T09:47:34+00:00'},
                'last_restore_attempt': {'status': 'FAIL', 'tested_at_utc': '2026-09-13T09:48:27+00:00'},
            }))
            with patch.object(mod, 'load_config', return_value={'state_path': str(state), 'monitor': {'max_quick_age_hours': 2, 'max_full_age_hours': 36, 'max_restore_age_days': 8}}):
                healthy, issues = mod.monitor()
            self.assertFalse(healthy)
            self.assertIn('restore test mais recente falhou', issues)

    def test_materialized_restore_database_name_is_fail_closed(self) -> None:
        self.assertEqual(mod.validate_restore_database_name('mgs_finance_dr_1548835136693600328'), 'mgs_finance_dr_1548835136693600328')
        for value in ('mgs_finance', 'postgres', 'mgs_finance_dr_bad-name', 'mgs_finance_dr_x', 'MGS_FINANCE_DR_1548835136693600328'):
            with self.assertRaises(ValueError):
                mod.validate_restore_database_name(value)

    def test_finance_infrastructure_tar_is_path_safe(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as raw:
            payload=b'unit'
            good=Path(raw)/'good.tar.gz'
            with tarfile.open(good,'w:gz') as archive:
                info=tarfile.TarInfo('etc/systemd/system/mgs-finance-dash.service');info.size=len(payload);archive.addfile(info,io.BytesIO(payload))
            self.assertEqual(mod.safe_tar(good),['etc/systemd/system/mgs-finance-dash.service'])
            bad=Path(raw)/'bad.tar.gz'
            with tarfile.open(bad,'w:gz') as archive:
                info=tarfile.TarInfo('../escape');info.size=len(payload);archive.addfile(info,io.BytesIO(payload))
            with self.assertRaises(RuntimeError):
                mod.safe_tar(bad)


if __name__ == '__main__':
    unittest.main()
