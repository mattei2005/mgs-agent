"""Offline regression: CBO cap recovery must not copy existing shells."""
import copy
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from ares_campaign_v3 import shell_recovery
from ares_campaign_v3.transport import BatchResult


class Engine:
    def __init__(self):
        self.calls = []
        self.campaign = {'id': '111', 'account_id': '999', 'name': 'old', 'status': 'PAUSED', 'daily_budget': '5000', 'bid_strategy': 'LOWEST_COST_WITHOUT_CAP', 'start_time': '2026-10-09T11:30:00-04:00'}
        self.adset = {'id': '222', 'campaign_id': '111', 'name': 'old', 'status': 'PAUSED', 'start_time': self.campaign['start_time'], 'bid_amount': '0', 'bid_constraints': {}}
    def _batch(self, bundle, transport, operations, stage):
        self.calls.append((stage, copy.deepcopy(operations)))
        result = []
        for op in operations:
            if op.method == 'GET':
                body = {'data': [copy.deepcopy(self.adset)]} if '/adsets?' in op.relative_url else copy.deepcopy(self.campaign if op.relative_url.startswith('111?') else self.adset)
            else:
                target = self.campaign if op.relative_url == '111' else self.adset
                target.update({k:v for k,v in op.body.items() if k != 'adset_bid_amounts'})
                if 'adset_bid_amounts' in op.body:
                    self.adset['bid_amount'] = str(op.body['adset_bid_amounts']['222'])
                body = {'success': True}
            result.append(BatchResult(op.name, 200, body, []))
        return result


class CBORecovery(unittest.TestCase):
    def spec(self):
        return SimpleNamespace(name='106 - COCAP', adset_name='106 - COCAP', status='PAUSED', start_time='2026-10-09T11:30:00-04:00',
            campaign_updates={'daily_budget':'7500','bid_strategy':'COST_CAP'}, adset_updates={'bid_amount':'60','bid_constraints':{}},
            bid_override=True, account_id='999', operation='SHEIN-US-DIRECT')
    def test_existing_ids_get_one_atomic_campaign_mapping_and_no_adset_bid_write(self):
        engine=Engine(); bundle=SimpleNamespace(account_id='999', campaigns=(self.spec(),)); record={'campaign_ids':['111'],'adset_ids':['222']}
        shell_recovery.reconcile(engine,bundle,None,record)
        writes=[op for _,ops in engine.calls for op in ops if op.method=='POST']
        self.assertTrue(all(op.relative_url in {'111','222'} for op in writes))
        cap=[op for op in writes if op.relative_url=='111'][0]
        self.assertEqual(cap.body.get('adset_bid_amounts'),{'222':60})
        self.assertEqual(cap.body['bid_strategy'],'COST_CAP')
        self.assertTrue(all('bid_amount' not in op.body and 'bid_strategy' not in op.body for op in writes if op.relative_url=='222'))
        self.assertEqual(engine.adset['bid_amount'],'60')
        self.assertEqual(record['campaign_ids'],['111']);self.assertEqual(record['adset_ids'],['222'])
    def test_converged_recovery_does_not_repeat_bid_update(self):
        engine=Engine(); spec=self.spec();engine.campaign.update(name=spec.name,daily_budget='7500',bid_strategy='COST_CAP');engine.adset.update(name=spec.adset_name,bid_amount='60')
        shell_recovery.reconcile(engine,SimpleNamespace(account_id='999',campaigns=(spec,)),None,{'campaign_ids':['111'],'adset_ids':['222']})
        self.assertFalse([op for _,ops in engine.calls for op in ops if op.method=='POST'])
    def test_cap_recovery_wrong_parent_fails_before_writes(self):
        engine=Engine();engine.adset['campaign_id']='333'
        with self.assertRaises(ValueError):
            shell_recovery.reconcile(engine,SimpleNamespace(account_id='999',campaigns=(self.spec(),)),None,{'campaign_ids':['111'],'adset_ids':['222']})
        self.assertFalse([op for _,ops in engine.calls for op in ops if op.method=='POST'])

if __name__=='__main__':unittest.main()
