"""Regression: exact approved follower accepted by both News consumers only."""
import importlib.util
import os
from pathlib import Path
import unittest

SCRIPTS = Path(os.environ.get('MGS_NEWS_TEST_SCRIPTS', '/root/mgs-agent/scripts'))


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PRIMARY = load('follower_primary', 'hermes-news-explainer.py')
WATCHDOG = load('follower_watchdog', 'hermes-news-explainer-watchdog.py')
BOUNDARY = load('follower_boundary', 'mgs_security_boundaries.py')
trusted_message = BOUNDARY.trusted_message
trusted_hermes_news_message = BOUNDARY.trusted_hermes_news_message


def follower():
    return {
        'id': '1558202777761620120',
        'channel_id': '1505609056771899644',
        'webhook_id': '1505609238976794685',
        'author': {'id': '1505609238976794685', 'bot': True},
        'type': 0,
        'flags': 2,
        'content': 'Step 5 Preview is free on Nous Portal for a limited time!',
        'message_reference': {
            'channel_id': '1490858802726043759',
            'guild_id': '1053877538025386074',
            'message_id': '1558201985889472633',
        },
    }


class OfficialFollowerTests(unittest.TestCase):
    def assert_consumers(self, message, accepted):
        self.assertEqual(trusted_hermes_news_message(message), accepted)
        self.assertEqual(bool(PRIMARY.select_candidates([message], {'last_seen_id': '1'})), accepted)
        self.assertEqual(WATCHDOG.is_source_announcement(message), accepted)

    def test_exact_follower_accepted_without_relaxing_generic_boundary(self):
        self.assert_consumers(follower(), True)
        self.assertFalse(trusted_message(follower()))

    def test_unknown_webhook_rejected(self):
        message = follower()
        message['webhook_id'] = '999999999999999999'
        self.assert_consumers(message, False)

    def test_same_webhook_wrong_destination_rejected(self):
        message = follower()
        message['channel_id'] = '1498132022634483894'
        self.assert_consumers(message, False)

    def test_wrong_author_rejected(self):
        message = follower()
        message['author']['id'] = '344196393512075265'
        self.assert_consumers(message, False)

    def test_wrong_source_channel_rejected(self):
        message = follower()
        message['message_reference']['channel_id'] = '999999999999999999'
        self.assert_consumers(message, False)

    def test_wrong_source_guild_rejected(self):
        message = follower()
        message['message_reference']['guild_id'] = '1185714635991679006'
        self.assert_consumers(message, False)

    def test_missing_destination_rejected(self):
        message = follower()
        message.pop('channel_id')
        self.assert_consumers(message, False)

    def test_missing_reference_rejected(self):
        message = follower()
        message.pop('message_reference')
        self.assert_consumers(message, False)

    def test_uncrossposted_or_malformed_flags_rejected(self):
        for flags in (0, None, '2', 'invalid'):
            with self.subTest(flags=flags):
                message = follower()
                message['flags'] = flags
                self.assert_consumers(message, False)

    def test_malformed_source_id_rejected(self):
        for source_id in ('', '0', '123x', ' 123'):
            with self.subTest(source_id=source_id):
                message = follower()
                message['message_reference']['message_id'] = source_id
                self.assert_consumers(message, False)

    def test_external_regular_bot_rejected(self):
        message = follower()
        message.pop('webhook_id')
        self.assert_consumers(message, False)

    def test_mgs_monitor_preserved(self):
        message = {
            'id': '1558202777761620120', 'type': 0,
            'author': {'id': '1496296175014252634'},
            'embeds': [{'title': 'Hermes Agent — nova versão oficial'}],
        }
        self.assert_consumers(message, True)
        self.assertTrue(trusted_message(message))

    def test_failed_follower_retry_preserved(self):
        message = follower()
        state = {'last_seen_id': message['id'], 'processed': {
            message['id']: {'error': 'transient', 'attempts': 1},
        }}
        self.assertEqual(PRIMARY.select_candidates([message], state), [message])

    def test_completed_follower_not_selected_again(self):
        message = follower()
        state = {'last_seen_id': message['id'], 'processed': {
            message['id']: {'reply_id': '1558202777761620121'},
        }}
        self.assertEqual(PRIMARY.select_candidates([message], state), [])


if __name__ == '__main__':
    unittest.main()
