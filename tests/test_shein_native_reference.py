"""Offline safety contract for manual-equivalent creative references."""
import copy
import unittest
from ares_campaign_v3.shein_native_reference import attach_plan

class NativeReferenceTests(unittest.TestCase):
    def setUp(self):
        self.source=[{'id':str(i),'creative':{'id':str(i+100),'degrees_of_freedom_spec':{'creative_features_spec':{'image_background_gen':{'enroll_status':'OPT_IN'},'standard_enhancements':{'enroll_status':'OPT_IN'}}}}} for i in [1,2]]
        self.manual=[{'id':str(i+10),'source_ad_id':str(i),'status':'PAUSED','creative':copy.deepcopy(self.source[i-1]['creative'])} for i in [1,2]]
        self.target=[{'id':str(i+20),'source_ad_id':str(i),'adset_id':'500','status':'PAUSED','creative':{'id':str(i+200)}} for i in [1,2]]
    def test_only_canary_reference_changes_no_creative_parameters(self):
        before=copy.deepcopy([self.source,self.manual,self.target]);plan=attach_plan(self.source,self.manual,self.target,'500')
        self.assertEqual(len(plan),2)
        for p in plan:
            self.assertIn(p['ad_id'],['21','22'])
            self.assertEqual(set(p['body']),{'creative','status'})
            self.assertEqual(set(p['body']['creative']),{'creative_id'})
            self.assertEqual(p['body']['status'],'PAUSED')
        self.assertEqual(before,[self.source,self.manual,self.target])
    def test_already_correct_reference_is_not_written_twice(self):
        for i,t in enumerate(self.target):t['creative']=copy.deepcopy(self.source[i]['creative'])
        self.assertEqual(attach_plan(self.source,self.manual,self.target,'500'),[])
    def test_partial_attachment_updates_only_missing_reference(self):
        self.target[0]['creative']=copy.deepcopy(self.source[0]['creative'])
        self.assertEqual([p['ad_id'] for p in attach_plan(self.source,self.manual,self.target,'500')],['22'])
    def test_manual_active_children_require_explicit_paused_parent_proof(self):
        for a in self.manual:a['status']='ACTIVE'
        with self.assertRaises(ValueError):attach_plan(self.source,self.manual,self.target,'500')
        self.assertEqual(len(attach_plan(self.source,self.manual,self.target,'500',manual_campaign_paused=True)),2)
        self.target[0]['status']='ACTIVE'
        with self.assertRaises(ValueError):attach_plan(self.source,self.manual,self.target,'500',manual_campaign_paused=True)
    def test_active_wrong_parent_foreign_lineage_and_manual_drift_block_all_writes(self):
        for kind in ['active','parent','lineage','manual_id','manual_feature','missing','duplicate']:
            source,manual,target=copy.deepcopy([self.source,self.manual,self.target])
            if kind=='active':target[1]['status']='ACTIVE'
            if kind=='parent':target[1]['adset_id']='900'
            if kind=='lineage':target[1]['source_ad_id']='9'
            if kind=='manual_id':manual[1]['creative']['id']='999'
            if kind=='manual_feature':manual[1]['creative']['degrees_of_freedom_spec']={}
            if kind=='missing':target.pop()
            if kind=='duplicate':manual[1]['source_ad_id']='1'
            with self.subTest(kind=kind),self.assertRaises(ValueError):attach_plan(source,manual,target,'500')

if __name__=='__main__':unittest.main()
