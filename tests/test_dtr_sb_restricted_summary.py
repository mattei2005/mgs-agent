#!/usr/bin/env python3
import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path('/root/mgs-agent/scripts/dtr-sb-restricted-summary.py')
spec = importlib.util.spec_from_file_location('dtr_sb_restricted_summary', SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError(f'cannot load {SCRIPT}')
summary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(summary)


class FakeDaily:
    @staticmethod
    def norm(value):
        return '' if value is None else str(value).strip()

    @classmethod
    def low(cls, value):
        return cls.norm(value).lower()

    @staticmethod
    def load_ignore_keys():
        return set(), set()

    @staticmethod
    def ignored_page(_row, _fb_ignore, _bot_pg_ignore):
        return False

    @classmethod
    def sb_public_from_raw(cls, raw):
        return {
            'status': cls.norm(raw.get('STATUS')),
            'restricted_until': cls.norm(raw.get('RESTRICTED_UNTIL')),
        }


class FakeSync:
    def __init__(self):
        self.active_checks = []

    def active_restricted(self, row, tday):
        self.active_checks.append((row.get('PAGE_NAME'), tday))
        restricted_until = FakeDaily.norm(row.get('RESTRICTED_UNTIL'))[:10]
        return bool(restricted_until and restricted_until >= tday)

    @staticmethod
    def derive_sites(row):
        return row.get('SITE', '?')


class RestrictedSummaryActiveDateTest(unittest.TestCase):
    def test_past_dates_are_excluded_but_today_is_inclusive(self):
        rows = [
            {'USER_LOGIN': 'bot@example.com', 'PAGE_NAME': 'past-broadcast', 'STATUS': 'Broadcast', 'RESTRICTED_UNTIL': '2026-07-14', 'SITE': 'past'},
            {'USER_LOGIN': 'bot@example.com', 'PAGE_NAME': 'today-broadcast', 'STATUS': 'Broadcast', 'RESTRICTED_UNTIL': '2026-07-15', 'SITE': 'today'},
            {'USER_LOGIN': 'bot@example.com', 'PAGE_NAME': 'future-broadcast', 'STATUS': 'Broadcast', 'RESTRICTED_UNTIL': '2026-07-16', 'SITE': 'future'},
            {'USER_LOGIN': 'bot@example.com', 'PAGE_NAME': 'past-onhold', 'STATUS': 'On-hold', 'RESTRICTED_UNTIL': '2026-07-14', 'SITE': 'past'},
            {'USER_LOGIN': 'bot@example.com', 'PAGE_NAME': 'today-onhold', 'STATUS': 'On-hold', 'RESTRICTED_UNTIL': '2026-07-15', 'SITE': 'today'},
            {'USER_LOGIN': 'bot@example.com', 'PAGE_NAME': 'future-ready', 'STATUS': 'Ready', 'RESTRICTED_UNTIL': '2026-07-16', 'SITE': 'future'},
            {'USER_LOGIN': 'inactive@example.com', 'PAGE_NAME': 'inactive-user', 'STATUS': 'Broadcast', 'RESTRICTED_UNTIL': '2026-07-16', 'SITE': 'inactive'},
        ]
        sync = FakeSync()

        snapshot = summary.build_snapshot(
            rows,
            {'bot@example.com'},
            FakeDaily,
            sync,
            tday='2026-07-15',
        )

        self.assertEqual(snapshot['restricted_total'], 4)
        self.assertEqual(snapshot['broadcast_restricted'], 2)
        self.assertEqual(snapshot['on_hold_ignored'], 1)
        self.assertEqual(snapshot['other_status_restricted'], 1)
        self.assertEqual(snapshot['dates'], {
            '2026-07-15': {'pages': 1, 'sites': ['today']},
            '2026-07-16': {'pages': 1, 'sites': ['future']},
        })
        self.assertEqual(len(sync.active_checks), 6)
        self.assertTrue(all(tday == '2026-07-15' for _, tday in sync.active_checks))
        blocks = summary.render_blocks(snapshot)
        self.assertTrue(all('📊 PÁGINAS RESTRITAS — RESUMO OPERACIONAL' in block for block in blocks))


if __name__ == '__main__':
    unittest.main()
