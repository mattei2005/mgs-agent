#!/usr/bin/env python3
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import threading
import unittest
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

    def test_green_only_is_untouched(self):
        row = template(['verde'] * 30)
        plan = repair.build_repair(row, bank_for([row]))
        self.assertEqual(plan['action'], 'skip_green')
        self.assertEqual(repair.content_hash(plan['messages']), repair.content_hash(repair.parse_messages(row)))

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
