#!/usr/bin/env python3
import importlib.util
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from typing import Any

SCRIPT = Path('/root/mgs-agent/scripts/sb-restricted-transition-monitor.py')
spec = importlib.util.spec_from_file_location('sb_restricted_transition_monitor', SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError(f'cannot load {SCRIPT}')
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)


def row(page_id, date, status='Broadcast', name=None):
    return {
        'page_name': name or f'Page {page_id}',
        'profile_name': 'Segurador Teste',
        'bot_user': 'bot@example.com',
        'page_id': str(page_id),
        'fb_page_id': f'90000000000{int(page_id):03d}',
        'status': status,
        'restricted_until': date,
        'utm_campaign': f'pg_{page_id}',
        'sites': 'openzed',
    }


class TransitionComparisonTest(unittest.TestCase):
    def test_new_renewed_status_change_and_resolved(self):
        previous = {
            monitor.stable_key(row(1, '2026-07-14')): row(1, '2026-07-14'),
            monitor.stable_key(row(2, '2026-08-11', 'Campaign')): row(2, '2026-08-11', 'Campaign'),
            monitor.stable_key(row(3, '2026-08-11')): row(3, '2026-08-11'),
        }
        current = {
            monitor.stable_key(row(1, '2026-08-11')): row(1, '2026-08-11'),
            monitor.stable_key(row(2, '2026-08-11', 'Broadcast')): row(2, '2026-08-11', 'Broadcast'),
            monitor.stable_key(row(4, '2026-08-12', 'Campaign')): row(4, '2026-08-12', 'Campaign'),
        }

        transitions, resolved = monitor.compare_snapshots(previous, current)

        by_page = {item['after']['page_id']: item for item in transitions}
        self.assertEqual(set(by_page), {'1', '2', '4'})
        self.assertEqual(by_page['1']['kind'], 'renovada')
        self.assertEqual(by_page['1']['changed'], ['data'])
        self.assertEqual(by_page['2']['kind'], 'status alterado')
        self.assertEqual(by_page['2']['changed'], ['status'])
        self.assertEqual(by_page['4']['kind'], 'nova')
        self.assertEqual([item['page_id'] for item in resolved], ['3'])

        lines = monitor.transition_lines(transitions)
        rendered = '\n'.join(lines)
        self.assertIn('renovada', rendered)
        self.assertIn('status alterado', rendered)
        self.assertNotIn('renovada/…', rendered)

    def test_renderer_chunks_without_omission_or_duplicate_link(self):
        transitions = []
        for page_id in range(1, 36):
            transitions.append({
                'kind': 'nova',
                'key': monitor.stable_key(row(page_id, '2026-08-12')),
                'before': None,
                'after': row(page_id, '2026-08-12'),
            })
        counts = {
            'active_status_broadcast': 439,
            'active_status_campaign': 1,
            'excluded_status_on-hold': 50,
        }

        blocks = monitor.render_blocks(transitions, counts, 'fixture')

        self.assertGreater(len(blocks), 1)
        self.assertTrue(all(len(block) <= monitor.DISCORD_LIMIT for block in blocks))
        self.assertTrue(all('🔴 PÁGINAS RESTRITAS — TRANSIÇÕES DETECTADAS NA SB' in block for block in blocks))
        joined = '\n'.join(blocks)
        for page_id in range(1, 36):
            fb_page_id = row(page_id, '2026-08-12')['fb_page_id']
            self.assertEqual(joined.count(fb_page_id), 1)
        self.assertEqual(joined.count(monitor.SHEET_URL), 1)

    def test_revenue_7d_is_aggregated_and_rendered_in_brl(self):
        daily = monitor.load_module('dtr_sb_daily_match_audit_revenue_test', monitor.DAILY_PATH)
        sync = daily.load_audit_mod().sync
        current = row(7, '2026-08-12')
        report_rows = [
            {'USER_LOGIN': 'bot@example.com', 'UTM_CAMPAIGN': 'pg_7', 'PAGE_ID': current['fb_page_id'], 'REVENUE': '1.25'},
            {'USER_LOGIN': 'bot@example.com', 'UTM_CAMPAIGN': 'pg_7', 'PAGE_ID': current['fb_page_id'], 'REVENUE': '2.75'},
        ]
        stats = sync.enrich_revenue_7d([current], report_rows)
        transition = {'kind': 'nova', 'key': monitor.stable_key(current), 'before': None, 'after': current}

        rendered = '\n'.join(monitor.transition_lines([transition]))

        self.assertEqual(stats, {'rows': 1, 'matched': 1, 'unmatched': 0})
        self.assertEqual(current['revenue_7d_brl'], 'R$ 4,00')
        self.assertIn('Receita 7d', rendered)
        self.assertIn('R$ 4,00', rendered)

    def test_state_serializes_decimal_revenue_without_corruption(self):
        current: dict[str, Any] = row(7, '2026-08-12')
        current['revenue_7d'] = Decimal('4.00')
        transition = {'kind': 'nova', 'key': monitor.stable_key(current), 'before': None, 'after': current}
        original_state_path = monitor.STATE_PATH
        with tempfile.TemporaryDirectory() as tmp_dir:
            setattr(monitor, 'STATE_PATH', Path(tmp_dir) / 'state.json')
            try:
                monitor.save_state(
                    {monitor.stable_key(current): current},
                    {'monitored_active': 1},
                    [transition],
                    [],
                    'fixture',
                )
                saved = json.loads(monitor.STATE_PATH.read_text(encoding='utf-8'))
            finally:
                setattr(monitor, 'STATE_PATH', original_state_path)

        self.assertEqual(saved['active'][monitor.stable_key(current)]['revenue_7d'], '4.00')
        self.assertEqual(saved['last_transitions'][0]['after']['revenue_7d'], '4.00')

    def test_exit_requires_live_inactive_readback_and_ignores_onhold(self):
        class Daily:
            @staticmethod
            def norm(value):
                return '' if value is None else str(value).strip()

            @classmethod
            def low(cls, value):
                return cls.norm(value).lower()

            @classmethod
            def sb_public_from_raw(cls, raw):
                return {
                    'page_id': cls.norm(raw.get('PAGE_ID')),
                    'fb_page_id': cls.norm(raw.get('FB_PAGE_ID')),
                    'bot_user': cls.low(raw.get('USER_LOGIN')),
                }

        class Sync:
            @staticmethod
            def derive_sites(raw):
                return raw.get('SITE', 'openzed')

            @staticmethod
            def active_restricted(raw, tday):
                date = str(raw.get('RESTRICTED_UNTIL') or '')[:10]
                return bool(date and date >= tday)

        previous = [
            row(1, '2026-08-01'),
            row(2, '2026-08-01'),
            row(3, '2026-08-01'),
        ]
        live = [
            {'PAGE_ID': '1', 'FB_PAGE_ID': row(1, '')['fb_page_id'], 'USER_LOGIN': 'bot@example.com', 'STATUS': 'Broadcast', 'RESTRICTED_UNTIL': ''},
            {'PAGE_ID': '2', 'FB_PAGE_ID': row(2, '')['fb_page_id'], 'USER_LOGIN': 'bot@example.com', 'STATUS': 'On-hold', 'RESTRICTED_UNTIL': ''},
        ]

        confirmed = monitor.confirmed_resolutions(previous, live, Daily, Sync, '2026-07-16')

        self.assertEqual([item['page id'] for item in confirmed], ['1'])
        self.assertEqual(confirmed[0]['nome da pagina'], 'Page 1')


if __name__ == '__main__':
    unittest.main()
