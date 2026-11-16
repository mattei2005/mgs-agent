"""Isolated same-account regressions. No HTTP, credentials or campaign writes."""
import copy, importlib.util, json, socket, sys, tempfile, unittest
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

S=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(S/'scripts'))
from ares_campaign_v3 import eggbev_same_account_replacement as same
from ares_campaign_v3 import eggbev_page_identity as page_identity
from ares_campaign_v3.schema import CampaignSpec, ManifestError

class SameAccountTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path('/root/mgs-agent')
        cls.q=json.loads((root/'data/ares/meta-ads/requests/eggbev03-c212-replacement-1571894746719330377.json').read_text())
        snap=json.loads((root/'data/ares/meta-ads/audit/eggbev/same-account'/cls.q['request_id']/'source-live.json').read_text())
        byid={a['id']:a for a in snap['ads']}
        cls.mapping=['120250364730460507','120250364730470507','120250364730460507']
        cls.source={'campaign':snap['campaign'],'adset':snap['adsets'][0],
                    'ads':[copy.deepcopy(byid[i]) for i in cls.mapping],
                    'all_ads':copy.deepcopy(snap['ads']),'technical_seed_ads':[]}
        spec=importlib.util.spec_from_file_location('same_stage_runner',S/'scripts/ares-eggbev-target-clone.py')
        cls.runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.runner)
        cls.page={'id':'1272524399287905','name':'Moorcroft Finances','page_token':'pg_23187','instagram_user_id':'99111'}
        filenames=[f for g in cls.q['campaigns'] for f in g['media_filenames']]
        cls.assets=[{'asset_id':'offline-asset-'+str(i),'clean_checksum':'a'*64,'canonical_filename':f} for i,f in enumerate(filenames)]
        cls.allocation={'names':[f'{i+400} - Moorcroft Finances - ENG - US - (pg_23187) - C{i+10:02d}' for i in range(5)]}
        class Registry:
            def require_ready(self,account,asset,checksum):
                return {'asset_id':asset,'checksum':checksum,'vertical_video_id':'91001','square_video_id':'91002','ready':True,'upload_edge':'ad_account_advideos','association_verified':True}
        cls.registry=Registry()
        cls.policy={'status':'active','implementation_verified':True,'authorized_by_discord_id':same.CEO,
                    'mode':same.MODE,'authority_message_id':'1571911721063546892',
                    'requests':{cls.q['request_id']:{'spec_sha256':same.digest(same.spec(cls.q)),
                       'template_ad_ids':cls.mapping,'target_page_id':cls.page['id']}}}
        cls.account={'supported_modes':[same.MODE],'target_page_replacement':{
                    'enabled':True,'account_id':same.TARGET,'authorized_by':same.CEO,
                    'authority_message_id':'1571911721063546892',
                    'policy_source':'data/ares/meta-ads/policies/eggbev03-same-account-replacement.json',
                    'allowed_request_ids':[cls.q['request_id']]}}
        cls.config={'accounts':{same.TARGET:cls.account}}
    def setUp(self):
        self.net=patch('socket.create_connection',side_effect=AssertionError('network forbidden'));self.net.start();self.addCleanup(self.net.stop)
    def policy_file(self,tmp):
        p=Path(tmp)/'policy.json';p.write_text(json.dumps(self.policy));return p
    def test_admission_and_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=self.policy_file(tmp)
            same.admit(self.q,self.config,p)
            for field,value in [('source_account_id','1034081997659047'),('budget_usd_per_campaign','36'),('request_dependencies',['old']),('cross_account_execution',True)]:
                q=copy.deepcopy(self.q);q[field]=value
                with self.subTest(field=field),self.assertRaises(ValueError):same.admit(q,self.config,p)
    def test_compiles_all_fifteen_slots_without_source_mutation(self):
        before=copy.deepcopy(self.source)
        start=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()
        built=same.build(self.q,self.source,self.page,self.assets,self.registry,self.allocation,self.runner,start)
        self.assertEqual(len(built['campaigns']),5)
        self.assertEqual([len(c['ads']) for c in built['campaigns']],[3]*5)
        self.assertEqual(before,self.source)
        for c in built['campaigns']:
            self.assertEqual(c['account_id'],same.TARGET);self.assertNotIn('cross_account_source',c)
            self.assertEqual(c['campaign_create']['bid_strategy'],before['campaign']['bid_strategy'])
            self.assertEqual(c['campaign_create']['daily_budget'],'3500')
            self.assertEqual(c['adset_create']['promoted_object']['page_id'],self.page['id'])
            self.assertEqual([a['source_ad_id'] for a in c['ads']],self.mapping)
            for ad in c['ads']:
                payload=ad['creative_payload'];self.assertEqual(payload['url_tags'],'utm_campaign=pg_23187')
                afs=payload['asset_feed_spec'];self.assertEqual([t['text'] for t in afs['titles']],self.q['copy']['headlines'])
                self.assertEqual(afs['bodies'][0]['text'],'')
                self.assertNotIn('standard_enhancements',payload.get('degrees_of_freedom_spec',{}).get('creative_features_spec',{}))
                self.assertIn('JSON-AGT',afs['additional_data']['page_welcome_message'])
    def test_page_independent_context(self):
        class SB:
            def api_request(self,*a,**k):return 200,[{'UTM_CAMPAIGN':'pg_23187','FB_PAGE_ID':'1272524399287905','PAGE_NAME':'Moorcroft Finances'}],{}
        test=self
        class Meta:
            def graph_get(self,path,token,params):
                dep=page_identity.dependency('1272524399287905')
                test.assertEqual(dep['account_ids'],[same.TARGET]);test.assertNotIn('authorized_cached_dependency_source_account',dep)
                if '/' in path:return 200,{'data':[{'id':'99111'}]},{}
                return 200,{'id':'1272524399287905','name':'Moorcroft Finances','access_token':'synthetic-only'},{}
        with tempfile.TemporaryDirectory() as tmp:
            p=self.policy_file(tmp);q=Path(tmp)/'request.json';q.write_text(json.dumps(self.q))
            with patch.object(same,'admit',return_value=(self.policy,self.policy['requests'][self.q['request_id']])):
                out=page_identity.resolve(Meta(),SB(),'synthetic-only',same.TARGET,'pg_23187',authority_path=p,request_path=q)
            self.assertEqual(out['id'],'1272524399287905');self.assertIsNone(page_identity.dependency('1272524399287905'))
    def test_real_engine_multi_campaign_and_replay(self):
        import time
        from ares_campaign_v3.engine import CampaignEngine
        from ares_campaign_v3.schema import Manifest
        from eggbev_target_fake import TargetFakeMeta
        start=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()
        built=same.build(self.q,self.source,self.page,self.assets,self.registry,self.allocation,self.runner,start)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);policy=self.policy_file(tmp)
            qp=root/'data/ares/meta-ads/requests'/(self.q['request_id']+'.json');qp.parent.mkdir(parents=True);qp.write_text(json.dumps(self.q))
            cfg=copy.deepcopy(self.config);a=cfg['accounts'][same.TARGET]
            a.update(app_key='mgs-meta-app-953171080682697',operation=same.OP,ad_serving_route='lineage_required_for_new_media')
            cfg.update(enabled=True,write_enabled=True,state_root=str(root/'state'),audit_root=str(root/'audit'),soft_score=10000,hard_score=10000,require_account_registration=True)
            class SameAccountFake(TargetFakeMeta):
                def new(self,value):
                    if value.get('_kind')=='campaign':value={**value,'account_id':same.TARGET}
                    return super().new(value)
            fake=SameAccountFake();engine=CampaignEngine(cfg,transport_factory=lambda account:fake)
            manifest=Manifest.from_dict(built)
            proof={'request_id':manifest.request_id,'digest':manifest.digest,'verified_at_monotonic':time.monotonic()}
            with patch.object(same,'ROOT',root),patch.object(same,'POLICY',policy):
                marker=same.CURRENT.set(proof)
                try:
                    result=engine.execute(manifest)
                    self.assertEqual(result['status'],'COMPLETE_FUTURE_ACTIVE')
                    self.assertEqual(len([v for v in fake.objects.values() if v.get('_kind')=='campaign']),5)
                    self.assertEqual(len([v for v in fake.objects.values() if v.get('_kind')=='ad']),30)
                    count=len(fake.calls);again=engine.execute(manifest)
                    self.assertTrue(again['idempotent_replay']);self.assertEqual(count,len(fake.calls))
                finally:same.CURRENT.reset(marker)
    def test_tracking_override_does_not_expand_other_accounts(self):
        q={'request_id':'offline-only','operation':same.OP,'daily_budget_usd':'35','start_time':(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat(),'copy':self.q['copy']}
        with self.assertRaisesRegex(ValueError,'scoped to independent account03'):
            self.runner.build(q,self.source,self.page,self.assets[:3],self.registry,{'names':['offline-only']},standard_tracking=True)
    def test_missing_source_tracking_remains_rejected_by_default(self):
        with self.assertRaisesRegex(ValueError,'tracking missing'):
            self.runner.source_rematerialization(self.source)
    def test_elapsed_guard_is_exact_and_ephemeral(self):
        import time
        value={'account_id':same.TARGET,'mode':same.MODE,'start_time':'2020-01-01T00:00:00+00:00'}
        self.assertFalse(same.allows_elapsed_campaign(value))
        marker=same.CURRENT.set({'verified_at_monotonic':time.monotonic(),'elapsed_campaign_digests':[same.digest(value)]})
        try:
            self.assertTrue(same.allows_elapsed_campaign(value))
            self.assertFalse(same.allows_elapsed_campaign({**value,'account_id':'1034081997659047'}))
            self.assertFalse(same.allows_elapsed_campaign({**value,'start_time':'2019-01-01T00:00:00+00:00'}))
        finally:same.CURRENT.reset(marker)
        self.assertFalse(same.allows_elapsed_campaign(value))
    def test_partial_media_reconciliation_resumes_cursor(self):
        calls=[]
        class Meta:
            fail=True
            def graph_get(self,path,token,params):
                calls.append(params.get('after'))
                if not params.get('after'):return 200,{'data':[{'id':'1'}],'paging':{'next':'not-followed','cursors':{'after':'cursor-2'}}},{}
                if self.fail:self.fail=False;return 429,{'error':{'code':80004}},{}
                return 200,{'data':[{'id':'2'}]},{}
        with tempfile.TemporaryDirectory() as tmp:
            m=Meta();home=Path(tmp)
            with self.assertRaisesRegex(ValueError,'saved cursor'):same.reconcile_target_media(self.q,home,self.assets,m,'synthetic-only')
            rows=same.reconcile_target_media(self.q,home,self.assets,m,'synthetic-only')
            self.assertEqual([r['id'] for r in rows],['1','2']);self.assertEqual(calls,[None,'cursor-2','cursor-2'])
    def test_engine_direct_execution_denied_without_fresh_approval(self):
        class M:
            campaigns=[type('C',(),{'account_id':same.TARGET,'mode':same.MODE})()]
            request_id=SameAccountTests.q['request_id'];digest='not-approved'
        with patch.object(same,'admit',return_value=(self.policy,{})),patch.object(same,'load',return_value=self.q):
            with self.assertRaisesRegex(ValueError,'fresh exact final-approval'):same.require_execution(M(),self.config)

if __name__=='__main__':unittest.main()
