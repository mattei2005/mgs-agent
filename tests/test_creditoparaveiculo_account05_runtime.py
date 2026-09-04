from __future__ import annotations

import importlib.util
import inspect
import json
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

WATCHER = Path('/root/.hermes/profiles/ares/scripts/creditoparaveiculo-account05-first-delivery.py')
REPORTS = Path('/root/.hermes/profiles/ares/scripts/creditoparaveiculo-account05-reports.py')
WATCH_WRAPPER = Path('/root/.hermes/profiles/ares/scripts/creditoparaveiculo-account05-first-delivery.sh')
ACTIVITY_WRAPPER = Path('/root/.hermes/profiles/ares/scripts/creditoparaveiculo-account05-activity-monitor.sh')
DAILY_WRAPPER = Path('/root/.hermes/profiles/ares/scripts/creditoparaveiculo-account05-daily.sh')
INTRADAY_WRAPPER = Path('/root/.hermes/profiles/ares/scripts/creditoparaveiculo-account05-intraday.sh')
OPERATION = Path('/root/mgs-agent/data/ares/meta-ads/operations/Creditoparaveiculo-BR-CAR-BR-05-CREATIVE-CUT-24H.json')


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Account05RuntimeTest(unittest.TestCase):
    def test_runtime_contract_is_explicit_and_read_only_for_reports(self):
        op = json.loads(OPERATION.read_text())
        self.assertEqual(op['account']['account_id'], '2039876850230678')
        self.assertEqual(op['strategy']['campaign_structure'], 'CBO_1x1x3')
        self.assertEqual(op['strategy']['intermediate_write_level'], 'ad')
        self.assertEqual(op['strategy']['terminal_write_level'], 'campaign')
        self.assertIs(op['first_delivery_guardrail']['enabled'], True)
        self.assertEqual(op['first_delivery_guardrail']['watch_interval_minutes'], 15)
        self.assertIs(op['reporting']['enabled'], True)
        self.assertEqual(op['reporting']['mode'], 'read_only_strategy_reporting')
        self.assertEqual(op['reporting']['daily_thread_id'], '1542892955315081246')
        self.assertEqual(op['reporting']['intraday_thread_id'], '1542892943352799242')
        self.assertEqual(op['reporting']['layout'], 'desktop_aligned_tables_only')
        highlights = op['reporting']['intraday_operational_highlights']
        self.assertIs(highlights['enabled'], True)
        self.assertEqual(highlights['smart_bidding_delay']['endpoint'], '/estimated/delay')
        self.assertEqual(highlights['rewarded_coverage']['filter'], 'rewarded')
        self.assertEqual(highlights['rewarded_coverage']['scope'], 'operation/page level; never a per-campaign metric')
        self.assertEqual(op['reporting']['daily_columns'][3], 'Dia')
        self.assertEqual(op['reporting']['intraday_columns'][3], 'Dia')
        self.assertEqual(op['reporting']['cycle_day_column']['applies_to'], ['daily', 'intraday'])
        cut_cfg = op['management_scope']['autonomous_action_scope']['creative_cut_writes']
        self.assertIsInstance(cut_cfg, dict)
        self.assertEqual(cut_cfg['status'], 'ACTIVE_AUTOMATED_CUTS_ACCOUNT05')
        self.assertIs(cut_cfg['enabled'], True)

    def test_first_delivery_safe_window_and_date_only_rename(self):
        module = load(WATCHER, 'cpv05_watcher_test')
        sp = ZoneInfo('America/Sao_Paulo')
        target = {'cycle_start_date': '2026-08-29'}
        self.assertFalse(module.safe_window(target, datetime(2026, 8, 29, 0, 29, tzinfo=sp)))
        self.assertTrue(module.safe_window(target, datetime(2026, 8, 29, 0, 30, tzinfo=sp)))
        self.assertTrue(module.safe_window(target, datetime(2026, 8, 29, 2, 0, 59, tzinfo=sp)))
        self.assertFalse(module.safe_window(target, datetime(2026, 8, 29, 2, 1, tzinfo=sp)))
        before = '01 - 29-08 - Garagem Brasil - (b01fb05c51) event_Subscribe - MAXVOL'
        after = module.update_date_only(before, '2026-08-31')
        self.assertEqual(after, '01 - 31-08 - Garagem Brasil - (b01fb05c51) event_Subscribe - MAXVOL')
        self.assertTrue(module.name_matches_assignment(after, '51'))

    def test_wrappers_are_script_only_and_account_lane_scoped(self):
        watcher = WATCH_WRAPPER.read_text()
        self.assertIn('--watch --quiet', watcher)
        self.assertIn('ares-cpv-meta-lane-2039876850230678.lock', watcher)
        for path, mode in ((DAILY_WRAPPER, 'daily'), (INTRADAY_WRAPPER, 'intraday')):
            text = path.read_text()
            self.assertIn(f'--mode {mode} --gate', text)
            self.assertIn('ares-cpv-meta-lane-2039876850230678.lock', text)
            self.assertIn('source /root/mgs-agent/.env', text)

    def test_meta_token_cache_is_isolated_for_account05_new_app(self):
        expected = '/root/.cache/mgs/ares-meta-token-creditoparaveiculo-account05-rafael-minibot-1299247318762949.json'
        watcher = load(WATCHER, 'cpv05_watcher_cache_test')
        reports = load(REPORTS, 'cpv05_reports_cache_test')
        self.assertEqual(watcher.META_TOKEN_CACHE_PATH, expected)
        self.assertEqual(reports.META_TOKEN_CACHE_PATH, expected)
        activity = ACTIVITY_WRAPPER.read_text()
        self.assertIn(f'ARES_META_TOKEN_CACHE_PATH={expected}', activity)

    def test_report_labels_follow_live_name_without_global_rule_change(self):
        module = load(REPORTS, 'cpv05_reports_test')
        campaign = {'name': '01 - 29-08 - Garagem Brasil - (b01fb05c51) event_Subscribe - MAXVOL'}
        self.assertEqual(module.visible_campaign_label(campaign, 51), 'C01-29/08')
        legacy = {'name': '51 - 29-08 - Garagem Brasil - (b01fb05c51) event_Subscribe - MAXVOL'}
        self.assertEqual(module.visible_campaign_label(legacy, 51), 'C51-29/08')

    def test_daily_and_intraday_include_cycle_day_column(self):
        module = load(REPORTS, 'cpv05_reports_day_column_test')
        self.assertEqual(module.cycle_day_value('2026-08-29', '2026-09-01'), 4)
        self.assertEqual(module.cycle_day_label(4), 'D4')
        self.assertEqual(module.cycle_day_label(0), 'PREP')
        daily_source = inspect.getsource(module.render_daily)
        intraday_source = inspect.getsource(module.render_intraday)
        self.assertIn("'Dia'", daily_source)
        self.assertIn("'Dia'", intraday_source)
        self.assertIn("cycle_day_label(row['cycle_day'])", daily_source)
        self.assertIn("cycle_day_label(row['cycle_day'])", intraday_source)

    def test_intraday_action_is_read_only_and_waits_for_state(self):
        module = load(REPORTS, 'cpv05_reports_action_test')
        sp = ZoneInfo('America/Sao_Paulo')
        now = datetime(2026, 8, 30, 22, 0, tzinfo=sp)
        self.assertEqual(module.action_label({'current_stage': 'AWAITING_FIRST_SPEND'}, 'ACTIVE', now), '⏳ AGUARDAR 1º GASTO')
        self.assertEqual(module.action_label({'current_stage': 'THREE_ADS_ACTIVE', 'window_started_at_sp': '2026-08-29T01:45:00-03:00', 'next_checkpoint_at_sp': '2026-08-30T01:45:00-03:00'}, 'ACTIVE', now), '👁️ REVISAR JANELA 24H')
        self.assertEqual(module.next_checkpoint_label({'current_stage': 'MANUAL_REVIEW'}, now), 'revisão manual pendente')
        self.assertEqual(module.action_label({'current_stage': 'MANUAL_REVIEW'}, 'ACTIVE', now), '⚠️ REVISÃO MANUAL')
        self.assertEqual(
            module.action_label({
                'current_stage': 'THREE_ADS_ACTIVE',
                'window_started_at_sp': '2026-08-30T01:45:00-03:00',
                'next_checkpoint_at_sp': '2026-08-31T01:45:00-03:00',
                'last_action': {'action': 'MANUAL_REVIEW_RECHECK_SCHEDULED'},
            }, 'ACTIVE', datetime(2026, 8, 30, 22, 0, tzinfo=sp)),
            '⚠️ RECHECK 24H',
        )
        self.assertEqual(module.action_label({}, 'PAUSED', now), '🛑 PAUSADA')

    def test_intraday_reuses_canonical_delay_and_rewarded_highlights(self):
        module = load(REPORTS, 'cpv05_reports_highlights_test')
        fixed = module.fixed_runtime()
        self.assertEqual(fixed.intraday_operational_highlights(
            183,
            {'coverage_pct': 89.37, 'matched': 8390, 'requests': 9388},
            {'coverage_pct': 77.08, 'matched': 26130, 'requests': 33898},
        ), [
            '**⏱️ ATRASO SMART BIDDING: 3h 03min**',
            '**🎯 COBERTURA REWARDED: 89,37%** · atual 8.390/9.388',
            '⚪ Referência anterior/cinza: 77,08% · 26.130/33.898',
        ])
        source = inspect.getsource(module.render_intraday)
        self.assertIn("build_rows(target_date, now_sp, include_delay=True)", source)
        self.assertIn('fixed.fetch_rewarded_pricing()', source)
        self.assertIn('fixed.intraday_operational_highlights(', source)
        self.assertIn("'delay': delay, 'rewarded_coverage': rewarded_pricing", source)


if __name__ == '__main__':
    unittest.main()
