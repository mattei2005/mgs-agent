import copy
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from ares_campaign_v3.prestaged_reconciliation import resolve_slot, copy_parameters

class PrestagedReconciliationTests(unittest.TestCase):
    def spec(self):
        return SimpleNamespace(name='AD 01 - ASSET', source_ad_id='100', creative_payload={'name':'Creative ASSET','object_story_spec':{'page_id':'1','video_data':{'call_to_action':{'type':'GET_OFFER','value':{'link':'https://example.org/'}}}}})
    def test_confirmed_slot_survives_generated_names_and_repeated_lineage(self):
        ad=self.spec(); rows=[{'id':'501','adset_id':'20','source_ad_id':'100','name':'AD 01','creative':{'name':'Creative ASSET 2026-10-20-abc'}}, {'id':'502','adset_id':'20','source_ad_id':'100','name':'AD 01','creative':{'name':'Creative OTHER 2026-10-20-abc'}}]
        record={'confirmed_objects':{'ad_copy_1_1':{'copied_ad_id':'501'}}}
        chosen,duplicates=resolve_slot(rows,ad,'20',record,1,1,2)
        self.assertEqual(chosen['id'],'501');self.assertEqual(duplicates,[])
    def test_journal_prefers_first_success_and_marks_only_proven_duplicates(self):
        ad=self.spec();rows=[{'id':i,'adset_id':'20','source_ad_id':'100','status':'PAUSED','creative':{'name':'Creative ASSET 2026-10-20-abc'}} for i in ['501','503']]
        record={'write_journal':[{'confirmed':[{'name':'ad_copy_1_1','ids':{'copied_ad_id':'501'}}]},{'confirmed':[{'name':'recovery_ad_copy_1_1','ids':{'copied_ad_id':'503'}}]}]}
        chosen,extras=resolve_slot(rows,ad,'20',record,1,1,2)
        self.assertEqual(chosen['id'],'501');self.assertEqual([x['id'] for x in extras],['503'])
    def test_ambiguous_unjournaled_duplicate_fails_closed(self):
        ad=self.spec();rows=[{'id':i,'adset_id':'20','source_ad_id':'100','name':ad.name,'creative':{'name':'Creative ASSET'}} for i in ['1','2']]
        with self.assertRaises(ValueError):resolve_slot(rows,ad,'20',{},1,1,2)
    def test_parent_and_lineage_not_bypassed_by_persisted_id(self):
        with self.assertRaises(ValueError):resolve_slot([{'id':'501','adset_id':'WRONG','source_ad_id':'100'}],self.spec(),'20',{'confirmed_objects':{'ad_copy_1_1':{'copied_ad_id':'501'}}},1,1,2)
    def test_video_offer_schema_normalization_preserves_immutable_input(self):
        ad=self.spec();old=copy.deepcopy(ad.creative_payload);result=copy_parameters(ad.creative_payload,'SHEIN-US-DIRECT')
        self.assertEqual(result['object_story_spec']['video_data']['call_to_action']['type'],'GET_OFFER_VIEW')
        self.assertEqual(ad.creative_payload,old)
        self.assertEqual(copy_parameters(old,'OTHER'),old)

if __name__=='__main__':unittest.main()
