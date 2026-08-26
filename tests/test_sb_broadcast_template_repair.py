#!/usr/bin/env python3
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import threading
import unittest
import datetime as dt
from unittest import mock
from http.server import BaseHTTPRequestHandler, HTTPServer

SCRIPT = pathlib.Path('/root/mgs-agent/scripts/sb-broadcast-template-repair.py')
spec = importlib.util.spec_from_file_location('repair', SCRIPT)
assert spec and spec.loader
repair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)


def message(mid, color, text=None, link=None):
    row = {'MESSAGE_ID': mid, 'TEXT': text or f'Unique message {mid}', 'CTA_1': f'CTA {mid}', 'LINK_1': link or f'https://example.com/{mid}'}
    if color == 'verde': row['APPROVED'] = 1
    elif color == 'vermelho': row['REJECTED'] = 1
    elif color == 'roxo': row['INVALID_FORMAT'] = 1
    return row


def template(colors, name='Site - US-CC-EN - g001-d Ciro', template_id='10', pages=5):
    messages = [message(i + 1, color) for i, color in enumerate(colors)]
    return {'ID': template_id, 'NAME': name, 'COMPANY': 'digital-trust', 'PAGES': pages, 'MESSAGES': json.dumps(messages)}


def bank_for(rows):
    bank = {'version': 1, 'records': {}}
    for i in range(1, 20):
        msg = {'TEXT': f'Approved replacement {i}', 'CTA_1': f'OPEN {i}'}
        key = repair.text_cta_hash(msg)
        bank['records'][key] = {'text_cta_hash': key, 'vertical': 'US-CC-EN', 'text': msg['TEXT'], 'cta_1': msg['CTA_1'], 'approved_count': 5, 'rejected_count': 0, 'last_approved_at': f'2026-07-{i:02d}T00:00:00-04:00'}
    return bank


class RepairTests(unittest.TestCase):
    def test_filter_requires_company_pages_production_and_30(self):
        good = template(['verde'] * 30)
        self.assertTrue(repair.active_production(good))
        bad_company = dict(good, COMPANY='other')
        self.assertFalse(repair.active_production(bad_company))
        test_row = dict(good, NAME='Teste-US-CC-EN-X')
        self.assertFalse(repair.active_production(test_row))
        no_pages = dict(good, PAGES=0)
        self.assertFalse(repair.active_production(no_pages))

    def test_explicit_test_template_exclusion_blocks_id_and_exact_name(self):
        red = template(['vermelho'] + ['verde'] * 29, template_id='protected-id')
        config = repair.default_config()
        config['excluded_templates'] = [{
            'id': 'protected-id',
            'name': 'Protected test template',
            'reason': 'manual_test',
        }]
        self.assertIsNotNone(repair.excluded_template(red, config))
        self.assertEqual(repair.classify_rows([red], bank_for([red]), config, repair.default_state()), [])

        recreated = dict(red, ID='new-id', NAME='Protected test template')
        self.assertIsNotNone(repair.excluded_template(recreated, config))
        self.assertEqual(repair.classify_rows([recreated], bank_for([recreated]), config, repair.default_state()), [])

        ordinary = dict(red, ID='ordinary-id', NAME='Ordinary - US-CC-EN - g001-d Ciro')
        self.assertIsNone(repair.excluded_template(ordinary, config))
        self.assertEqual(len(repair.classify_rows([ordinary], bank_for([ordinary]), config, repair.default_state())), 1)

    def test_invalid_exclusion_config_fails_closed(self):
        row = template(['vermelho'] + ['verde'] * 29)
        config = repair.default_config()
        config['excluded_templates'] = 'not-a-list'
        with self.assertRaisesRegex(RuntimeError, 'excluded_templates_config_not_list'):
            repair.classify_rows([row], bank_for([row]), config, repair.default_state())

    def test_green_only_is_untouched(self):
        row = template(['verde'] * 30)
        plan = repair.build_repair(row, bank_for([row]))
        self.assertEqual(plan['action'], 'skip_green')
        self.assertEqual(repair.content_hash(plan['messages']), repair.content_hash(repair.parse_messages(row)))

    def test_first_name_placeholder_is_removed_and_forces_reset(self):
        row = template(['verde'] * 30)
        messages = repair.parse_messages(row)
        messages[0]['TEXT'] = 'Congratulations, {{first_name}}! Your card is ready.'
        messages[1]['TEXT'] = '— {{first_name}}, your request is ready.'
        row['MESSAGES'] = json.dumps(messages)
        links = repair.link_map(messages)
        plan = repair.build_repair(row, bank_for([row]))
        self.assertEqual(plan['action'], 'sanitize_first_name_reset')
        self.assertEqual(plan['sanitized_slots'], [1, 2])
        self.assertEqual(plan['messages'][0]['TEXT'], 'Congratulations! Your card is ready.')
        self.assertEqual(plan['messages'][1]['TEXT'], '— your request is ready.')
        self.assertNotIn('{{first_name}}', json.dumps(plan['messages']))
        self.assertEqual(repair.link_map(plan['messages']), links)
        self.assertEqual(repair.counts_for(plan['messages'])['cinza'], 30)

    def test_red_batch_replaced_links_preserved_and_all_statuses_removed(self):
        colors = ['verde'] * 20 + ['vermelho'] * 4 + ['roxo'] * 6
        row = template(colors)
        before = repair.parse_messages(row)
        plan = repair.build_repair(row, bank_for([row]))
        self.assertEqual(plan['action'], 'replace_red_reset')
        self.assertEqual(len(plan['replaced_slots']), 4)
        self.assertEqual(repair.link_map(plan['messages']), repair.link_map(before))
        self.assertEqual(repair.counts_for(plan['messages']), {'verde': 0, 'cinza': 30, 'vermelho': 0, 'roxo': 0})
        texts = [repair.normalized(m['TEXT']) for m in plan['messages']]
        self.assertEqual(len(texts), len(set(texts)))

    def test_purple_reset_preserves_content_and_links(self):
        row = template(['verde'] * 25 + ['roxo'] * 5)
        before = repair.parse_messages(row)
        plan = repair.build_repair(row, bank_for([row]))
        self.assertEqual(plan['action'], 'reset_purple')
        self.assertEqual(repair.content_hash(plan['messages']), repair.content_hash(before))
        self.assertEqual(repair.counts_for(plan['messages'])['cinza'], 30)

    def test_insufficient_bank_requests_generation(self):
        row = template(['vermelho'] * 30)
        plan = repair.build_repair(row, {'records': {}})
        self.assertEqual(plan['action'], 'needs_generation')
        self.assertEqual(plan['deficit'], 30)
        self.assertEqual(plan['approved_available'], 0)
        self.assertEqual(plan['approved_required'], 30)

    def test_duplicate_visible_text_replaces_only_extra_slot(self):
        row = template(['verde'] * 30)
        messages = repair.parse_messages(row)
        messages[10]['TEXT'] = messages[0]['TEXT']
        row['MESSAGES'] = json.dumps(messages)
        before_links = repair.link_map(repair.parse_messages(row))
        plan = repair.build_repair(row, bank_for([row]))
        self.assertEqual(plan['action'], 'replace_duplicates_reset')
        self.assertEqual(plan['duplicate_slots'], [11])
        self.assertEqual([slot['message_id'] for slot in plan['replaced_slots']], [11])
        texts = [repair.normalized(item['TEXT']) for item in plan['messages']]
        self.assertEqual(len(texts), len(set(texts)))
        self.assertEqual(repair.link_map(plan['messages']), before_links)

    def test_duplicate_and_red_share_single_replacement_slot(self):
        row = template(['verde'] * 29 + ['vermelho'])
        messages = repair.parse_messages(row)
        messages[-1]['TEXT'] = messages[0]['TEXT']
        row['MESSAGES'] = json.dumps(messages)
        plan = repair.build_repair(row, bank_for([row]))
        self.assertEqual(plan['action'], 'replace_red_duplicates_reset')
        self.assertEqual(len(plan['replaced_slots']), 1)
        self.assertEqual(plan['replaced_slots'][0]['reason'], 'red_and_duplicate')

    def test_approved_candidates_are_unique_by_visible_text(self):
        bank = bank_for([])
        first = next(iter(bank['records'].values()))
        duplicate = dict(first)
        duplicate['cta_1'] = first['cta_1'] + ' ALT'
        duplicate['text_cta_hash'] = repair.text_cta_hash({'TEXT': duplicate['text'], 'CTA_1': duplicate['cta_1']})
        bank['records'][duplicate['text_cta_hash']] = duplicate
        candidates = repair.approved_candidates(bank, 'US-CC-EN', set(), set())
        texts = [repair.normalized(item['text']) for item in candidates]
        self.assertEqual(len(texts), len(set(texts)))

    def test_approved_candidates_reject_first_name_placeholder(self):
        bank = bank_for([])
        msg = {'TEXT': 'Hello {{first_name}}', 'CTA_1': 'OPEN'}
        key = repair.text_cta_hash(msg)
        bank['records'][key] = {
            'text_cta_hash': key, 'vertical': 'US-CC-EN', 'text': msg['TEXT'],
            'cta_1': msg['CTA_1'], 'approved_count': 10, 'rejected_count': 0,
            'last_approved_at': '2026-08-08T00:00:00-04:00',
        }
        candidates = repair.approved_candidates(bank, 'US-CC-EN', set(), set())
        self.assertTrue(all('{{first_name}}' not in item['text'] for item in candidates))

    def test_bank_preserves_ever_green_on_purple(self):
        bank = {'records': {}}
        msg = message(1, 'verde')
        key, record = repair.upsert_bank_observation(bank, 'T', msg, 'verde', 'US-CC-EN', '2026-08-03T08:00:00-03:00')
        purple = message(1, 'roxo', text=msg['TEXT'], link=msg['LINK_1'])
        purple['CTA_1'] = msg['CTA_1']
        key2, record2 = repair.upsert_bank_observation(bank, 'T', purple, 'roxo', 'US-CC-EN', '2026-08-04T08:00:00-03:00')
        self.assertEqual(key, key2)
        self.assertGreater(record2['approved_count'], 0)
        self.assertEqual(record2['status'], 'approved_diagnostic')

    def test_embed_is_compact_and_has_no_mentions(self):
        item = {'template_id': '10', 'template': 'Site - US-CC-EN - g001-d Ciro', 'vertical': 'US-CC-EN', 'pages': 5, 'cycle': 1, 'before': {'verde': 20, 'cinza': 0, 'vermelho': 4, 'roxo': 6}, 'action_label': '4 vermelhas substituídas', 'approval_started_at_sp': '2026-08-03T08:00:00-03:00', 'due_at_sp': '2026-08-03T08:30:00-03:00', 'next_step': 'Aguardar.'}
        payload = repair.discord_embed('started', item)
        raw = json.dumps(payload, ensure_ascii=False)
        self.assertLess(len(raw), 6000)
        self.assertEqual(payload['content'], '')
        self.assertEqual(payload['allowed_mentions']['parse'], [])
        self.assertLessEqual(len(payload['embeds'][0]['fields']), 25)

    def test_notification_failure_does_not_abort_repair_state(self):
        item = {'template_id': '10', 'template': 'Site'}
        with mock.patch.object(repair, 'post_event', side_effect=RuntimeError('http_503')):
            with mock.patch.object(repair, 'append_log'):
                self.assertIsNone(repair.safe_post_event({}, {}, 'started', item))
                self.assertIn('http_503', item['notify_error'])

    def test_daily_fingerprint_allows_changed_result_but_dedupes_repeat(self):
        state = {}
        empty = {
            'template_id': 'daily', 'cycle': '2026-08-24',
            'processed': 0, 'positive': 0, 'blocked': 0,
            'summary': 'Nenhum template processado hoje.',
        }
        actual = {
            'template_id': 'daily', 'cycle': '2026-08-24',
            'processed': 6, 'positive': 3, 'blocked': 3,
            'summary': 'resultado real',
        }
        with mock.patch.object(repair, 'post_discord', side_effect=['1', '2']) as post:
            self.assertEqual(repair.post_event(state, {}, 'daily', empty), '1')
            self.assertEqual(repair.post_event(state, {}, 'daily', actual), '2')
            self.assertEqual(repair.post_event(state, {}, 'daily', actual), '2')
        self.assertEqual(post.call_count, 2)

    def test_daily_capacity_counts_already_started_templates(self):
        state = {'templates': {
            'a': {'last_started_date': '2026-08-07'},
            'b': {'last_started_date': '2026-08-07'},
            'c': {'last_started_date': '2026-08-06'},
        }}
        self.assertEqual(repair.remaining_daily_capacity(state, 6, '2026-08-07'), 4)
        self.assertEqual(repair.remaining_daily_capacity(state, 1, '2026-08-07'), 0)

    def test_scheduled_digest_skips_outside_sao_paulo_hour(self):
        current = dt.datetime(2026, 8, 25, 0, 10, tzinfo=repair.SP)
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = pathlib.Path(tmpdir) / 'state.json'
            config_path = pathlib.Path(tmpdir) / 'config.json'
            state_path.write_text(json.dumps(repair.default_state()))
            config_path.write_text(json.dumps(repair.default_config()))
            with mock.patch.object(repair, 'STATE_PATH', state_path), \
                 mock.patch.object(repair, 'CONFIG_PATH', config_path), \
                 mock.patch.object(repair, 'now_sp', return_value=current), \
                 mock.patch.object(repair, 'safe_post_event') as post:
                result = repair.daily_digest(notify=True, scheduled=True)
        self.assertEqual(result['status'], 'skip')
        self.assertEqual(result['reason'], 'outside_digest_hour_sp')
        post.assert_not_called()

    def test_digest_can_backfill_explicit_sao_paulo_date(self):
        current = dt.datetime(2026, 8, 25, 0, 10, tzinfo=repair.SP)
        state = repair.default_state()
        state['templates'] = {
            'a': {
                'template_id': 'a', 'template': 'A',
                'approval_started_at_sp': '2026-08-24T09:00:00-03:00',
                'before': {'verde': 20, 'vermelho': 1, 'roxo': 9},
                'after': {'verde': 29, 'vermelho': 1, 'roxo': 0},
                'status': 'eligible_next_day', 'no_progress_cycles': 0,
            },
            'b': {
                'template_id': 'b', 'template': 'B',
                'approval_started_at_sp': '2026-08-25T09:00:00-03:00',
                'status': 'blocked', 'no_progress_cycles': 2,
            },
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = pathlib.Path(tmpdir) / 'state.json'
            config_path = pathlib.Path(tmpdir) / 'config.json'
            state_path.write_text(json.dumps(state))
            config_path.write_text(json.dumps(repair.default_config()))
            with mock.patch.object(repair, 'STATE_PATH', state_path), \
                 mock.patch.object(repair, 'CONFIG_PATH', config_path), \
                 mock.patch.object(repair, 'now_sp', return_value=current), \
                 mock.patch.object(repair, 'safe_post_event', return_value='123') as post:
                result = repair.daily_digest(notify=True, report_date='2026-08-24')
        self.assertEqual(result['processed'], 1)
        self.assertEqual(result['positive'], 1)
        self.assertEqual(result['blocked'], 0)
        self.assertEqual(result['message_id'], '123')
        self.assertEqual(post.call_args.args[3]['cycle'], '2026-08-24')


class CaptureHandler(BaseHTTPRequestHandler):
    received = None
    def do_POST(self):
        length = int(self.headers.get('Content-Length', '0'))
        CaptureHandler.received = json.loads(self.rfile.read(length))
        body = json.dumps({'id': '999', 'channel_id': '1522487422510694450'}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, format, *args):
        pass


class DiscordTransportTest(unittest.TestCase):
    def test_poster_mock_roundtrip(self):
        server = HTTPServer(('127.0.0.1', 0), CaptureHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        payload = {'content': '', 'embeds': [{'title': 'Mock'}], 'allowed_mentions': {'parse': []}}
        env = dict(**__import__('os').environ)
        env['MGS_DISCORD_API_URL_OVERRIDE'] = f'http://127.0.0.1:{server.server_port}/messages'
        env['MGS_DISCORD_BOT_TOKEN_OVERRIDE'] = 'fixture-token'
        result = subprocess.run([sys.executable, '/root/mgs-agent/scripts/discord-bot-post.py', '--channel-id', '1522487422510694450'], input=json.dumps(payload), text=True, capture_output=True, env=env, timeout=10)
        server.shutdown(); thread.join(timeout=2); server.server_close()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(CaptureHandler.received, payload)
        self.assertIn('http=200', result.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
