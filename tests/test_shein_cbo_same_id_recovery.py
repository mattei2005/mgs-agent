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
    def test_same_strategy_cap_uses_adset_not_atomic_mapping(self):
        engine=Engine();engine.campaign['bid_strategy']='COST_CAP'
        shell_recovery.reconcile(engine,SimpleNamespace(account_id='999',campaigns=(self.spec(),)),None,{'campaign_ids':['111'],'adset_ids':['222']})
        writes=[op for _,ops in engine.calls for op in ops if op.method=='POST']
        self.assertTrue(writes);self.assertTrue(all('adset_bid_amounts' not in op.body for op in writes))
        self.assertEqual([op.body['bid_amount'] for op in writes if op.relative_url=='222'],['60'])
        self.assertEqual(engine.adset['bid_amount'],'60')
    def test_cap_recovery_wrong_parent_fails_before_writes(self):
        engine=Engine();engine.adset['campaign_id']='333'
        with self.assertRaises(ValueError):
            shell_recovery.reconcile(engine,SimpleNamespace(account_id='999',campaigns=(self.spec(),)),None,{'campaign_ids':['111'],'adset_ids':['222']})
        self.assertFalse([op for _,ops in engine.calls for op in ops if op.method=='POST'])

class PrestagedShellRecovery(CBORecovery):
    def run_core(self, *, exists=True, campaigns=None, account_operation='SHEIN-US-DIRECT'):
        from unittest.mock import Mock
        from ares_campaign_v3.engine import CampaignEngine
        class RecoveryEngine(Engine):
            def _batch(self, bundle, transport, operations, stage):
                if stage == 'recovery_shell_inventory' and not self.exists:
                    self.calls.append((stage, copy.deepcopy(operations)))
                    return [BatchResult(op.name,200,{'data':[]},[]) for op in operations]
                if stage == 'recovery_shell_adset_copy':
                    self.calls.append((stage,copy.deepcopy(operations)))
                    self.exists=True
                    return [BatchResult(op.name,200,{'copied_adset_id':'222'},[]) for op in operations]
                return super()._batch(bundle,transport,operations,stage)
        engine=RecoveryEngine();engine.exists=exists
        engine.config={'accounts':{'999':{'operation':account_operation}}}
        engine._readback_only_record=lambda bundle,record: True
        engine._timed_start=lambda: ({},0)
        engine._timed_finish=lambda *args: None
        engine._readback_ops=lambda campaign_ids: []
        spec=self.spec();spec.creative_materialization_route='ad_copy';spec.source_adset_id='source-set'
        bundle=SimpleNamespace(account_id='999',campaigns=(spec,))
        record={'campaign_ids':['111'] if campaigns is None else campaigns,'stage':'campaign_copies_created','timings':{}}
        result=CampaignEngine._recover_prestaged_bundle(engine,bundle,None,record)
        return engine,record,result
    def test_missing_adset_recovered_without_campaign_copy(self):
        engine,record,result=self.run_core(exists=False)
        copies=[op for _,ops in engine.calls for op in ops if op.kind=='adset_copy']
        self.assertEqual(len(copies),1);self.assertEqual(copies[0].relative_url,'source-set/copies')
        self.assertEqual(copies[0].body['campaign_id'],'111')
        self.assertEqual(record['adset_ids'],['222']);self.assertEqual(result,['111'])
        self.assertFalse([op for _,ops in engine.calls for op in ops if op.kind=='campaign_copy'])
    def test_existing_adset_adopted_without_copy(self):
        engine,record,result=self.run_core(exists=True)
        self.assertEqual(record['adset_ids'],['222'])
        self.assertFalse([op for _,ops in engine.calls for op in ops if op.kind in {'campaign_copy','adset_copy'}])
    def test_incomplete_campaign_identity_rejected(self):
        from ares_campaign_v3.engine import ExecutionFailed
        with self.assertRaises(ExecutionFailed):self.run_core(campaigns=[])
    def test_other_operation_does_not_gain_shell_recovery(self):
        from ares_campaign_v3.engine import ExecutionFailed
        with self.assertRaises(ExecutionFailed):self.run_core(account_operation='OTHER')

if __name__=='__main__':unittest.main()
