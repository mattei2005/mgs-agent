#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path('/root/mgs-agent/scripts/ares-meta-account-activity-monitor.py')
spec = importlib.util.spec_from_file_location('activity_monitor', SCRIPT)
assert spec is not None and spec.loader is not None
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)

CONFIG = {
    'trusted_api_sources': [
        {'actor_id': '10229590004590742', 'application_id': '163163106580854'}
    ],
    'account_alias': 'Creditoparaveiculo-BR-CAR-BR-13-G006',
}


def event(**changes):
    base = {
        'event_time': '2026-08-30T15:00:00+0000',
        'event_type': 'update_campaign_budget',
        'object_id': '123',
        'object_name': 'C99 test',
        'actor_id': '2983592665336693',
        'actor_name': 'External User',
        'application_id': '119211728144504',
        'application_name': 'Power Editor',
        'extra_data': json.dumps({
            'old_value': {'type': 'payment_amount', 'currency': 'USD', 'old_value': 2500},
            'new_value': {'type': 'payment_amount', 'currency': 'USD', 'new_value': 3000},
        }),
    }
    base.update(changes)
    return base


class ActivityMonitorTests(unittest.TestCase):
    def test_external_budget_change_alerts(self):
        result = monitor.classify_event(event(), CONFIG, audit_lookup=False)
        self.assertTrue(result['alert'])
        self.assertEqual(result['classification'], 'external_or_manual_change')

    def test_trusted_app_without_audit_alerts(self):
        row = event(actor_id='10229590004590742', application_id='163163106580854')
        result = monitor.classify_event(row, CONFIG, audit_lookup=False)
        self.assertTrue(result['alert'])
        self.assertEqual(result['classification'], 'trusted_app_without_local_audit')

    def test_meta_review_lifecycle_is_ignored(self):
        row = event(
            event_type='update_ad_run_status',
            actor_id='0',
            actor_name='Meta',
            application_id=None,
            extra_data=json.dumps({'old_value': 'Pending Review', 'new_value': 'Active'}),
        )
        result = monitor.classify_event(row, CONFIG, audit_lookup=False)
        self.assertFalse(result['alert'])
        self.assertEqual(result['classification'], 'ignored_meta_lifecycle')

    def test_meta_campaign_status_change_is_alerted(self):
        row = event(
            event_type='update_campaign_run_status',
            actor_id='0',
            actor_name='Meta',
            application_id=None,
            extra_data=json.dumps({'old_value': 'Active', 'new_value': 'Inactive', 'rule_info': {'id': 'r1'}}),
        )
        result = monitor.classify_event(row, CONFIG, audit_lookup=False)
        self.assertTrue(result['alert'])
        self.assertEqual(result['classification'], 'meta_or_native_rule_material_change')

    def test_event_key_is_stable(self):
        first = monitor.event_key(event())
        second = monitor.event_key(dict(reversed(list(event().items()))))
        self.assertEqual(first, second)

    def test_alert_renders_minor_currency(self):
        item = {'event': event(), 'classification': 'external_or_manual_change'}
        text = monitor.build_alert([item], CONFIG, 'America/Sao_Paulo')
        self.assertIn('USD 25.00', text)
        self.assertIn('USD 30.00', text)
        self.assertIn('Power Editor', text)
        self.assertIn('Eventos agrupados: 1 em 1 objeto(s).', text)

    def test_alert_groups_events_for_same_object_without_raw_targeting(self):
        targeting = event(
            event_type='update_ad_set_target_spec',
            object_id='adset-1',
            object_name='AdGroup C04',
            extra_data=json.dumps({'old_value': [], 'new_value': [{'content': 'Brasil'}]}),
        )
        created = event(
            event_type='create_ad_set',
            object_id='adset-1',
            object_name='AdGroup C04',
            extra_data=json.dumps({'old_value': None, 'new_value': None}),
        )
        items = [
            {'event': targeting, 'classification': 'external_or_manual_change'},
            {'event': created, 'classification': 'external_or_manual_change'},
        ]
        text = monitor.build_alert(items, CONFIG, 'America/Sao_Paulo')
        self.assertIn('Eventos agrupados: 2 em 1 objeto(s).', text)
        self.assertIn('segmentação atualizada; detalhes preservados no audit', text)
        self.assertNotIn("{'content': 'Brasil'}", text)

    def test_account05_alias_falls_back_to_exact_meta_alias(self):
        operation = {'account': {'exact_meta_alias': 'Creditoparaveiculo-BR-CAR-BR-05-G006'}, 'account_activity_monitor': {}}
        account = {'meta_detected': {'name': 'fallback'}}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            operation_path = root / 'operation.json'
            account_path = root / 'account.json'
            operation_path.write_text(json.dumps(operation))
            account_path.write_text(json.dumps({'accounts': [account]}))
            _, _, config = monitor.load_inputs(operation_path, account_path)
        self.assertEqual(config['account_alias'], 'Creditoparaveiculo-BR-CAR-BR-05-G006')

    def test_engine_checkpoint_reconciles_trusted_ares_write(self):
        row = event(
            event_time='2026-08-31T05:32:53+0000',
            object_id='120248500821400046',
            actor_id='122171910794667280',
            application_id='860397696767230',
        )
        config = {
            'trusted_api_sources': [
                {'actor_id': '122171910794667280', 'application_id': '860397696767230'}
            ],
            'audit_match_window_seconds': 1800,
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit = root / 'audit'
            engine_audit = root / 'engine-audit'
            checkpoints = root / 'checkpoints'
            audit.mkdir()
            engine_audit.mkdir()
            checkpoints.mkdir()
            checkpoint = checkpoints / 'request.json'
            checkpoint.write_text(json.dumps({
                'campaign_ids': ['120248500821400046'],
                'started_at': '2026-08-31T05:32:53+00:00',
            }))
            timestamp = 1788154373
            os.utime(checkpoint, (timestamp, timestamp))
            root_names = ('AUDIT_ROOT', 'ENGINE_AUDIT_ROOT', 'ENGINE_CHECKPOINT_ROOT')
            old_roots = tuple(getattr(monitor, name) for name in root_names)
            for name, value in zip(root_names, (audit, engine_audit, checkpoints), strict=True):
                setattr(monitor, name, value)
            try:
                result = monitor.classify_event(row, config)
            finally:
                for name, value in zip(root_names, old_roots, strict=True):
                    setattr(monitor, name, value)
        self.assertFalse(result['alert'])
        self.assertEqual(result['classification'], 'trusted_ares_audited')

    def test_fixture_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture.json'
            path.write_text(json.dumps({'data': [event(), 'bad']}))
            rows = monitor.fixture_events(path)
            self.assertEqual(len(rows), 1)


if __name__ == '__main__':
    unittest.main()
