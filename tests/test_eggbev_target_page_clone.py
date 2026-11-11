"""Isolated target-Page clone architecture; no provider calls."""
import copy
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
sys.path.insert(0, '/root/mgs-agent/scripts')
from ares_campaign_v3.schema import CampaignSpec, ManifestError


def specimen():
    media = {'asset_id':'asset-a','checksum':'a'*64,'vertical_video_id':'91001','square_video_id':'91002','ready':True,'upload_edge':'ad_account_advideos','association_verified':True}
    return {'idempotency_key':'test-target-1','app_key':'test-app','account_id':'1034081997659047','mode':'clone_target_prestaged','source_campaign_id':'81001','source_adset_id':'81002','name':'301 - Target Page - ENG - US - (pg_23186) - C01','adset_name':'ADGROUP 01','start_time':(datetime.now(timezone.utc)+timedelta(days=1)).isoformat(),'status':'ACTIVE','campaign_create':{'objective':'OUTCOME_SALES','buying_type':'AUCTION','daily_budget':'3500','bid_strategy':'LOWEST_COST_WITHOUT_CAP','special_ad_categories':['FINANCIAL_PRODUCTS_SERVICES'],'special_ad_category_country':['US']},'adset_create':{'billing_event':'IMPRESSIONS','optimization_goal':'OFFSITE_CONVERSIONS','destination_type':'MESSENGER','targeting':{'geo_locations':{'countries':['US']}},'promoted_object':{'page_id':'82001','pixel_id':'935354115143283','custom_event_type':'OTHER','custom_event_str':'eggbev-pv-u'},'attribution_spec':[],'regional_regulated_categories':[],'regional_regulation_identities':{},'is_dynamic_creative':False},'ads':[{'name':'AD 01 - CC_US_EN_VID_AVAILABLE_LIMIT_PV_160','source_ad_id':'81003','media':media,'creative_payload':{'name':'target creative unique','object_story_spec':{'page_id':'82001','instagram_user_id':'82002'},'url_tags':'utm_campaign=pg_23186','asset_feed_spec':{'videos':[{'video_id':'91001'},{'video_id':'91002'}]}}}]}


class TargetSchemaTests(unittest.TestCase):
    def test_explicit_new_mode(self):
        c=CampaignSpec.from_dict(specimen())
        self.assertEqual(c.mode,'clone_target_prestaged')
        self.assertEqual(c.source_campaign_id,'81001')
        self.assertTrue(c.ads[0].media)
    def test_missing_source_is_rejected(self):
        d=specimen();d.pop('source_campaign_id')
        with self.assertRaises(ManifestError):CampaignSpec.from_dict(d)
    def test_mismatched_page_is_rejected(self):
        d=specimen();d['adset_create']['promoted_object']['page_id']='82003'
        with self.assertRaises(ManifestError):CampaignSpec.from_dict(d)
    def test_no_adset_copy_updates(self):
        d=specimen();d['adset_updates']={'promoted_object':{'page_id':'82001'}}
        with self.assertRaises(ManifestError):CampaignSpec.from_dict(d)
    def test_preserves_input(self):
        d=specimen();old=copy.deepcopy(d);CampaignSpec.from_dict(d);self.assertEqual(d,old)

class PageDependencyTests(unittest.TestCase):
    def test_live_mapping_metadata_only_and_context_removed(self):
        import importlib.util
        from ares_campaign_v3 import eggbev_page_identity as p
        spec=importlib.util.spec_from_file_location('exact_dependency_guard','/root/mgs-agent/scripts/mgs-ares-asset-scope.py');guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
        class SB:
            def api_request(self,method,path,**kwargs):
                return 200,[{'UTM_CAMPAIGN':'pg_23186','FB_PAGE_ID':'82001','PAGE_NAME':'Target Page'}],{}
        class Meta:
            def graph_get(self,path,token,params):
                guard.enforce_meta_path(path,params,'GET')
                if '/' in path:return 200,{'data':[{'id':'82002','username':'test'}]},{}
                return 200,{'id':'82001','name':'Target Page','access_token':'synthetic-only'},{}
        self.assertIsNone(p.dependency('82001'))
        result=p.resolve(Meta(),SB(),'synthetic-only','1034081997659047','pg_23186')
        self.assertEqual(result['instagram_user_id'],'82002');self.assertNotIn('access_token',result)
        self.assertIsNone(p.dependency('82001'))
        with self.assertRaises(guard.ScopeError):guard.enforce_meta_path('82001',{'fields':'id,name'},'GET')
    def test_other_account_rejected_before_sb(self):
        from ares_campaign_v3.eggbev_page_identity import resolve
        with self.assertRaises(ValueError):resolve(None,None,'synthetic-only','999999999','pg_23186')

if __name__=='__main__':unittest.main()
