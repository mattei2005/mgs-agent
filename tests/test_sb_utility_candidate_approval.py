#!/usr/bin/env python3
import importlib.util
import json
import pathlib
import unittest

SCRIPT = pathlib.Path('/root/mgs-agent/scripts/sb-utility-candidate-approval.py')
spec = importlib.util.spec_from_file_location('candidate_approval', SCRIPT)
assert spec and spec.loader
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)
repair = candidate.repair


def message(mid, color='verde', text=None):
    row = {
        'MESSAGE_ID': mid,
        'TEXT': text or f'Existing unique message {mid}',
        'CTA_1': f'CTA {mid}',
        'LINK_1': f'https://example.com/{mid}',
    }
    if color == 'verde':
        row['APPROVED'] = 1
    elif color == 'vermelho':
        row['REJECTED'] = 1
    return row


class CandidateApprovalTests(unittest.TestCase):
    def test_stage_messages_preserves_links_and_replaces_tail(self):
        messages = [message(i) for i in range(1, 21)]
        candidates = [
            {
                'candidate_id': 'a',
                'text': 'New unique candidate A',
                'cta_1': 'OPEN A',
                'text_cta_hash': repair.text_cta_hash({'TEXT': 'New unique candidate A', 'CTA_1': 'OPEN A'}),
            },
            {
                'candidate_id': 'b',
                'text': 'New unique candidate B',
                'cta_1': 'OPEN B',
                'text_cta_hash': repair.text_cta_hash({'TEXT': 'New unique candidate B', 'CTA_1': 'OPEN B'}),
            },
        ]
        staged, placements = candidate.stage_messages(messages, candidates)
        self.assertEqual([item['message_id'] for item in placements], [19, 20])
        self.assertEqual(repair.link_map(staged), repair.link_map(messages))
        self.assertEqual(repair.counts_for(staged)['cinza'], 20)
        texts = [repair.normalized(item['TEXT']) for item in staged]
        self.assertEqual(len(texts), len(set(texts)))

    def test_stage_messages_blocks_visible_duplicate(self):
        messages = [message(i) for i in range(1, 21)]
        duplicate = {
            'candidate_id': 'dup',
            'text': messages[0]['TEXT'],
            'cta_1': 'OTHER CTA',
            'text_cta_hash': repair.text_cta_hash({'TEXT': messages[0]['TEXT'], 'CTA_1': 'OTHER CTA'}),
        }
        with self.assertRaisesRegex(ValueError, 'unique_visible_text'):
            candidate.stage_messages(messages, [duplicate])

    def test_needs_by_vertical_uses_maximum_reusable_deficit(self):
        rows = []
        for template_id, red_count in [('1', 4), ('2', 7)]:
            messages = [message(i, 'vermelho' if i <= red_count else 'verde') for i in range(1, 31)]
            rows.append({
                'ID': template_id,
                'NAME': f'Site {template_id} - GB-CC-EN/EN-SR - g001-d Test',
                'COMPANY': 'digital-trust',
                'PAGES': 1,
                'MESSAGES': json.dumps(messages),
            })
        needs = candidate.needs_by_vertical(rows, {'records': {}})
        self.assertEqual(needs['GB-CC-EN']['deficit'], 7)
        self.assertEqual(len(needs['GB-CC-EN']['templates']), 2)

    def test_spanish_formatting_preserves_visible_text(self):
        raw = {'candidate_id': 'x', 'text': 'REVISIÓN DISPONIBLE\n\nConsulta los detalles ahora.', 'cta_1': 'VER ESTADO'}
        formatted = candidate.formatted_candidate(raw, 'MX-CC-ES')
        self.assertIn('\u200b', formatted['text'])
        self.assertEqual(repair.normalized(formatted['text']), repair.normalized(raw['text']))

    def test_error_embed_is_fail_closed_and_has_no_mentions(self):
        payload = candidate.error_embed(['GB-CC-EN:catalog_deficit:0/5'], 'staged')
        self.assertEqual(payload['content'], '')
        self.assertEqual(payload['allowed_mentions'], {'parse': []})
        self.assertIn('não aprovada', payload['embeds'][0]['fields'][-1]['value'])

    def test_retired_candidate_is_not_selected_again(self):
        raw = {'candidate_id': 'retired-1', 'text': 'A unique retired copy', 'cta_1': 'OPEN'}
        catalog = {'candidates': {'GB-CC-EN': [raw]}}
        state = {'verticals': {}, 'retired_candidate_ids': ['retired-1']}
        selected = candidate.select_catalog_candidates(catalog, 'GB-CC-EN', 1, {'records': {}}, state, set())
        self.assertEqual(selected, [])

    def test_notification_failure_does_not_raise(self):
        original_notify = candidate.notify
        original_log = candidate.append_log
        try:
            candidate.notify = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError('http_503'))
            candidate.append_log = lambda *args, **kwargs: None
            item = {'vertical': 'GB-CC-EN'}
            self.assertIsNone(candidate.safe_notify({}, 'completed', item))
            self.assertIn('http_503', item['notify_error'])
        finally:
            candidate.notify = original_notify
            candidate.append_log = original_log

    def test_stage_promotion_is_idempotent_after_transport_failure(self):
        import tempfile
        original_path = candidate.CONFIG_PATH
        original_log = candidate.append_log
        try:
            with tempfile.TemporaryDirectory() as directory:
                candidate.CONFIG_PATH = pathlib.Path(directory) / 'config.json'
                candidate.append_log = lambda *args, **kwargs: None
                config = {'stage': 'staged', 'auto_promote': True}
                state = {'verticals': {
                    'A': {'stage': 'staged', 'status': 'completed'},
                    'B': {'stage': 'staged', 'status': 'completed'},
                }}
                self.assertTrue(candidate.promote_stage_if_complete(config, state))
                self.assertEqual(config['stage'], 'full')
                self.assertFalse(candidate.promote_stage_if_complete(config, state))
        finally:
            candidate.CONFIG_PATH = original_path
            candidate.append_log = original_log


if __name__ == '__main__':
    unittest.main(verbosity=2)
