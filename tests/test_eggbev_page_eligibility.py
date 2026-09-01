import json
import tempfile
import unittest
from pathlib import Path

from scripts.ares_campaign_v3.eggbev_page_eligibility import (
    PageEligibilityError,
    build_denylist,
    load_denylist,
    page_eligibility,
    require_page_eligible,
)


class EggbevPageEligibilityTests(unittest.TestCase):
    def transition(self):
        return {
            'last_check': '2026-08-31T20:00:00-04:00',
            'history': {
                'pages': {
                    'bot-page:disparoseggbev@gmail.com|5071': {
                        'bot_user': 'disparoseggbev@gmail.com',
                        'sites': 'eggbev',
                        'page_id': '5071',
                        'page_name': 'Tina Walter',
                        'fb_page_id': '632774769923890',
                        'currently_restricted': False,
                        'last_entry_at': '2026-08-31T11:14:21-04:00',
                        'last_exit_at': '2026-09-29T00:00:00-04:00',
                        'last_known_restricted_until': '2026-09-28',
                    }
                }
            },
            'active': {},
        }

    def test_historical_restriction_is_permanently_ineligible_even_after_exit(self):
        denylist = build_denylist(self.transition())
        result = page_eligibility('pg_5071', meta_page_id='632774769923890', denylist=denylist)
        self.assertFalse(result['eligible'])
        self.assertEqual(result['reason'], 'restricted_page_history')
        with self.assertRaisesRegex(PageEligibilityError, 'solicite outra página'):
            require_page_eligible('165 - Tina Walter - (pg_5071)', denylist=denylist)

    def test_page_without_restriction_history_is_eligible(self):
        denylist = build_denylist(self.transition())
        result = page_eligibility('pg_5024', denylist=denylist)
        self.assertTrue(result['eligible'])

    def test_existing_denylist_entries_are_never_auto_removed(self):
        first = build_denylist(self.transition())
        second = build_denylist({'last_check': '2026-09-30T00:00:00-04:00', 'history': {'pages': {}}, 'active': {}}, first)
        self.assertIn('pg_5071', second['pages'])

    def test_missing_or_invalid_denylist_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / 'missing.json'
            with self.assertRaisesRegex(PageEligibilityError, 'indisponível'):
                load_denylist(missing)
            invalid = Path(directory) / 'invalid.json'
            invalid.write_text(json.dumps({'operation_id': 'wrong'}))
            with self.assertRaisesRegex(PageEligibilityError, 'inválida'):
                load_denylist(invalid)


if __name__ == '__main__':
    unittest.main()
