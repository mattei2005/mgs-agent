"""D-1 preparation and publication preserve gates without duplicate refresh."""
import importlib.util
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

spec = importlib.util.spec_from_file_location('daily_single_refresh', Path('/root/.hermes/profiles/ares/scripts/shein-daily-report.py'))
assert spec is not None and spec.loader is not None
daily = importlib.util.module_from_spec(spec)
spec.loader.exec_module(daily)


class SingleRefresh(unittest.TestCase):
    def exercise(self, *, prepare=False, frozen=False, hour=9, completed=False):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td)
            root = state / '2026-11-10'
            root.mkdir()
            if frozen:
                (root / 'a').mkdir()
                (root / 'a/delivery-intent-0.json').write_text('{}')
            if completed:
                daily.save(root / 'completion.json', {'status': 'COMPLETE_GET_VERIFIED'})
            bindings = [{'account_id': str(i), 'thread_id': str(i + 100), 'manager_code': f'g00{i // 4 + 1}'} for i in range(24)]
            runner = Mock()
            discord = Mock()
            discord.verify.return_value = {}
            policy = {'policy_id': 'test', 'source_thread_id': 'test'}
            before = datetime(2026, 11, 11, hour, tzinfo=ZoneInfo('America/New_York'))
            after = before.replace(hour=max(8, hour))
            clock = Mock()
            instants = iter([before, before, before, before, after] if hour < 8 else [before] * 4)
            clock.now.side_effect = lambda *a: next(instants, after)
            delivery = lambda r, b, d: {'account_id': b['account_id'], 'thread_id': b['thread_id'], 'manager': b['manager_code'], 'parts': [{'id': b['account_id']}], 'campaigns': 1}
            with patch.object(daily, 'STATE', state), patch.object(daily, 'load', wraps=daily.load) as load, patch.object(daily, 'resolve', return_value=bindings), patch.object(daily, 'Runner', return_value=runner), patch.object(daily, 'Discord', return_value=discord), patch.object(daily, 'datetime', clock), patch.object(daily, 'now', return_value=before.isoformat()), patch.object(daily.time, 'sleep') as sleep, patch.object(daily, 'deliver_account', side_effect=delivery) as send:
                load.side_effect = lambda p: policy if p == daily.POLICY else __import__('json').loads(Path(p).read_text())
                result = daily.main(SimpleNamespace(run_date='2026-11-10', prepare_only=prepare, verify_only=False))
            return runner, send, sleep, result

    def test_publish_refreshes_and_materializes_once(self):
        runner, send, _, result = self.exercise()
        runner.refresh.assert_called_once_with()
        runner.materialize.assert_called_once_with()
        self.assertEqual(send.call_count, 24)
        self.assertEqual(result['status'], 'COMPLETE_GET_VERIFIED')

    def test_prepare_still_renders_without_delivery(self):
        runner, send, _, result = self.exercise(prepare=True)
        runner.refresh.assert_called_once_with()
        runner.materialize.assert_called_once_with()
        send.assert_not_called()
        self.assertEqual(result['status'], '24_D1_REPORTS_PREPARED')

    def test_frozen_resume_never_refreshes_or_recollects(self):
        runner, send, _, _ = self.exercise(frozen=True)
        runner.refresh.assert_not_called()
        runner.materialize.assert_not_called()
        runner.collect.assert_not_called()
        self.assertEqual(send.call_count, 24)

    def test_early_publication_waits_then_refreshes_once(self):
        runner, _, sleep, _ = self.exercise(hour=7)
        sleep.assert_called_once_with(3600.0)
        runner.refresh.assert_called_once_with()

    def test_completed_journal_never_replays(self):
        runner, send, _, _ = self.exercise(completed=True)
        runner.refresh.assert_not_called()
        send.assert_not_called()


if __name__ == '__main__':
    unittest.main()
