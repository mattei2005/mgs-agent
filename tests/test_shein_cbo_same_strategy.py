"""Offline payload regression for Meta 2446030: unchanged CBO strategy."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from ares_campaign_v3.cbo_bid import shell_payloads
class CboBidTests(unittest.TestCase):
    def spec(self):return SimpleNamespace(name='target',status='PAUSED',start_time='2030-10-14T00:45:00-04:00',adset_name='group',campaign_updates={'daily_budget':'4500','bid_strategy':'COST_CAP'},adset_updates={'bid_amount':'90','bid_constraints':{}},bid_override=True)
    def test_same_strategy_updates_cap_on_adset(self):
        c,a=shell_payloads(self.spec(),'123',source_strategy='COST_CAP')
        self.assertNotIn('adset_bid_amounts',c);self.assertEqual(a['bid_amount'],'90');self.assertEqual(a['bid_constraints'],{})
    def test_changed_strategy_remains_campaign_atomic(self):
        c,a=shell_payloads(self.spec(),'123',source_strategy='LOWEST_COST_WITHOUT_CAP')
        self.assertEqual(c['adset_bid_amounts'],{'123':90});self.assertNotIn('bid_amount',a)
if __name__=='__main__':unittest.main()
