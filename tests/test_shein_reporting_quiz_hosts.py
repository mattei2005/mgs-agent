"""Quiz entry hosts must not replace financial publisher identity."""
import importlib.util
from pathlib import Path
import unittest

HOME = Path('/root/.hermes/profiles/ares')
spec = importlib.util.spec_from_file_location('quiz_host_daily', HOME / 'scripts/shein-daily-report.py')
daily = importlib.util.module_from_spec(spec)
spec.loader.exec_module(daily)


class ReportingQuizHosts(unittest.TestCase):
    aid = '7840111366055613'

    def ads(self, *links):
        return [{'account_id': self.aid, 'creative': {'object_story_spec': {
            'video_data': {'call_to_action': {'value': {'link': link}}}}}}
            for link in links]

    def quiz(self, *links, domain='yolokfx.com'):
        return daily.reporting_quiz(self.ads(*links), self.aid, domain)

    def test_authorized_entry_is_read_from_actual_cta(self):
        self.assertEqual(self.quiz('https://lp-yolo.com/quiz/us/sh2-g002/?utm_campaign=b01fb01c152'), 'v2')

    def test_original_host_unchanged(self):
        self.assertEqual(self.quiz('https://yolokfx.com/quiz/us/sh3-g002/'), 'v3')

    def test_alias_is_not_shared_with_other_revenue_domains(self):
        self.assertEqual(self.quiz('https://lp-yolo.com/quiz/us/sh2-g002/', domain='mavroa.com'), 'n/d')

    def test_unknown_and_lookalike_hosts_remain_unconfirmed(self):
        for host in ('unapproved.example', 'lp-yolo.com.unapproved.example'):
            with self.subTest(host=host):
                self.assertEqual(self.quiz(f'https://{host}/quiz/us/sh2-g002/'), 'n/d')

    def test_missing_and_mixed_destinations_are_not_invented(self):
        self.assertEqual(self.quiz(), 'n/d')
        self.assertEqual(self.quiz('https://lp-yolo.com/quiz/us/sh2-g002/',
                                   'https://yolokfx.com/quiz/us/sh3-g002/'), 'misto')
        self.assertEqual(self.quiz('https://lp-yolo.com/quiz/us/sh2-g002/',
                                   'https://unapproved.example/quiz/us/sh2-g002/'), 'n/d')

    def test_cross_account_rows_fail_closed(self):
        with self.assertRaises(AssertionError):
            daily.reporting_quiz(self.ads('https://lp-yolo.com/quiz/us/sh2-g002/'), 'other', 'yolokfx.com')


if __name__ == '__main__':
    unittest.main()
