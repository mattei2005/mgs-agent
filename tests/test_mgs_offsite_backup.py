from __future__ import annotations

import datetime as dt
import importlib.util
import unittest
import zipfile
from pathlib import Path

SCRIPT = Path('/root/mgs-agent/scripts/mgs-offsite-backup.py')
spec = importlib.util.spec_from_file_location('mgs_offsite_backup', SCRIPT)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class OffsiteBackupTests(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
