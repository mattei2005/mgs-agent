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
    def test_pbia_initialization_is_exact_and_read_back(self):
        import importlib.util,json,tempfile
        from ares_campaign_v3 import eggbev_page_identity as p
        spec=importlib.util.spec_from_file_location('init_dependency_guard','/root/mgs-agent/scripts/mgs-ares-asset-scope.py');guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
        class SB:
            def api_request(self,*args,**kwargs):return 200,[{'UTM_CAMPAIGN':'pg_23186','FB_PAGE_ID':'82001','PAGE_NAME':'Target Page'}],{}
        class Meta:
            made=False;writes=0
            def graph_get(self,path,token,params):
                guard.enforce_meta_path(path,params,'GET')
                if '/' in path:return 200,{'data':[{'id':'82002'}] if self.made else []},{}
                return 200,{'id':'82001','name':'Target Page','access_token':'synthetic-only'},{}
            def graph_post_once(self,path,token,body):
                guard.enforce_meta_path(path,body,'POST');self.made=True;self.writes+=1
                with selftest.assertRaises(guard.ScopeError):guard.enforce_meta_path('82001',{'name':'wrong'},'POST')
                return 200,{'id':'82002'},{}
        selftest=self
        with tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch') as tmp:
            request=Path(tmp)/'request.json';request.write_text(json.dumps({'request_id':'offline-only','account_id':'1034081997659047','target_page_token':'pg_23186','commercial_ok_message_id':'1569925441127579672'}))
            meta=Meta();out=p.resolve(meta,SB(),'synthetic-only','1034081997659047','pg_23186',ensure_pbia=True,request_path=request)
            self.assertTrue(out['pbia_initialized']);self.assertEqual(meta.writes,1)
            self.assertEqual(json.loads((Path(tmp)/'pbia-initialization.json').read_text())['state'],'VERIFIED')
            p.resolve(meta,SB(),'synthetic-only','1034081997659047','pg_23186',ensure_pbia=True,request_path=request);self.assertEqual(meta.writes,1)
    def test_other_account_rejected_before_sb(self):
        from ares_campaign_v3.eggbev_page_identity import resolve
        with self.assertRaises(ValueError):resolve(None,None,'synthetic-only','999999999','pg_23186')

class TargetEngineTests(unittest.TestCase):
    def engine(self,fake,root):
        from ares_campaign_v3.engine import CampaignEngine
        config={'enabled':True,'write_enabled':True,'state_root':str(root/'state'),'audit_root':str(root/'audit'),'require_account_registration':True,'accounts':{'1034081997659047':{'app_key':'test-app','operation':'Eggbev-US-CC-EN-BOT','supported_modes':['clone_target_prestaged'],'ad_serving_route':'direct_and_lineage_verified','target_page_replacement':{'enabled':True,'authorized_by':'344196393512075265','authority_message_id':'1569927267633602693','account_id':'1034081997659047'}}}}
        return CampaignEngine(config,transport_factory=lambda account:fake)
    def manifest(self):
        from ares_campaign_v3.schema import Manifest
        from ares_campaign_v3.eggbev_create import messenger_welcome_message
        d=specimen();d['ads'][0]['creative_payload']['asset_feed_spec']['additional_data']={'page_welcome_message':messenger_welcome_message()}
        return Manifest.from_dict({'schema_version':3,'request_id':'offline-target-clone','operation':'Eggbev-US-CC-EN-BOT','graph_version':'v26.0','created_at':datetime.now(timezone.utc).isoformat(),'campaigns':[d]})
    def test_real_engine_and_replay(self):
        import tempfile
        from eggbev_target_fake import TargetFakeMeta
        with tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch') as temp:
            fake=TargetFakeMeta();engine=self.engine(fake,Path(temp));m=self.manifest();result=engine.execute(m)
            self.assertEqual(result['status'],'COMPLETE_FUTURE_ACTIVE')
            self.assertEqual(len([x for x in fake.objects.values() if x.get('_kind')=='campaign']),1)
            self.assertEqual(len([x for x in fake.objects.values() if x.get('_kind')=='adset']),1)
            ads=[x for x in fake.objects.values() if x.get('_kind')=='ad'];self.assertEqual(len(ads),2)
            self.assertEqual(len([x for x in ads if x['status']=='PAUSED']),1)
            before=len(fake.calls);self.assertTrue(engine.execute(m)['idempotent_replay']);self.assertEqual(before,len(fake.calls))
    def test_crash_after_unknown_seed_never_duplicates(self):
        import tempfile
        from eggbev_target_fake import TargetFakeMeta
        with tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch') as temp:
            fake=TargetFakeMeta(crash_seed=True);engine=self.engine(fake,Path(temp));m=self.manifest()
            with self.assertRaises(KeyboardInterrupt):engine.execute(m)
            result=engine.execute(m);self.assertEqual(result['status'],'COMPLETE_FUTURE_ACTIVE')
            self.assertEqual(len([x for x in fake.objects.values() if x.get('_kind')=='ad']),2)
            self.assertEqual(len([x for x in fake.calls if x[1].startswith('target_seed_create')]),1)
    def test_bad_page_readback_contains_parent_paused(self):
        import tempfile
        from eggbev_target_fake import TargetFakeMeta
        with tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch') as temp:
            fake=TargetFakeMeta(wrong_final=True);engine=self.engine(fake,Path(temp))
            with self.assertRaises(ValueError):engine.execute(self.manifest())
            campaigns=[x for x in fake.objects.values() if x.get('_kind')=='campaign']
            self.assertEqual(len(campaigns),1);self.assertEqual(campaigns[0]['status'],'PAUSED')

class TargetUploaderTests(unittest.TestCase):
    def test_association_proves_ids_before_ready_and_is_not_repeated(self):
        import importlib.util
        from unittest.mock import patch
        from ares_campaign_v3.prestage import AdAccountVideoUploader
        spec=importlib.util.spec_from_file_location('target_uploader_test','/root/mgs-agent/scripts/ares-eggbev-target-clone.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        uploader=m.TargetAccountUploader(common=object(),user_token='synthetic-only',account_id='1034081997659047');events=[];proof={'91001':{'associated':True}}
        with patch.object(AdAccountVideoUploader,'verify_association',side_effect=lambda ids:(events.append('association') or proof)) as check,patch.object(AdAccountVideoUploader,'wait_ready',side_effect=lambda ids:(events.append('ready') or {'91001':{'ready':True}})):
            uploader.wait_ready(['91001']);self.assertEqual(uploader.verify_association(['91001']),proof)
            self.assertEqual(events,['association','ready']);self.assertEqual(check.call_count,1)

if __name__=='__main__':unittest.main()
