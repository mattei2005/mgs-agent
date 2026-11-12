"""Offline acceptance: elapsed NOW continuation and per-child recovery safety."""
import copy
import json
import sys
import tempfile
import unittest
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, '/root/mgs-agent/scripts')
import test_eggbev_target_page_clone as harness
from eggbev_target_fake import TargetFakeMeta
from ares_campaign_v3 import target_continuation as tc
from ares_campaign_v3 import target_page_clone as adapter
from ares_campaign_v3.schema import Manifest, ManifestError
from ares_campaign_v3.prevalidation import content_digest
from ares_campaign_v3.transport import BatchTransportError

AID='1034081997659047'
RID='offline-target-clone'
ACTOR='1055570806945620030'
NOW='1570313044771475559'
OK='1570313437379170436'
PROMPT='1570313339748491298'

class PartialMeta(TargetFakeMeta):
    failed=False
    def execute(self, operations, stage):
        if stage=='creative_create' and not self.failed:
            self.failed=True
            rows=super().execute(operations[:1],stage)
            raise BatchTransportError(stage, {'successful_children':[{'name':rows[0].name,'code':200,'ids':rows[0].body}], 'children':[{'name':o.name,'code':400,'error':{'code':100,'error_subcode':1487390,'is_transient':False}} for o in operations[1:]]})
        return super().execute(operations,stage)
    def graph_get_credential_metadata(self, account_id, token, inspect_token=False):
        assert account_id==AID
        return (200,{'data':{'app_id':'1299247318762949','user_id':'1700526774973769','is_valid':True}} if inspect_token else {'id':'1700526774973769','name':'offline'}, {})

class ElapsedClock(datetime):
    @classmethod
    def now(cls,tz=None):return datetime.now(tz)+timedelta(days=2)

class ContinuationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.home=self.root/'request';self.home.mkdir()
        self.fake=PartialMeta();self.engine=harness.TargetEngineTests().engine(self.fake,self.root)
        c=harness.specimen();c['ads']=[copy.deepcopy(c['ads'][0]) for _ in range(3)]
        from ares_campaign_v3.eggbev_create import messenger_welcome_message
        for i,a in enumerate(c['ads'],1):
            a['name']='AD '+str(i);a['media']['asset_id']='asset-'+str(i)
            a['creative_payload']['name']='creative-'+str(i)
            for vi,v in enumerate(a['creative_payload']['asset_feed_spec']['videos']):v['adlabels']=[{'name':f'slot-{i}-{vi}'}]
            a['creative_payload']['asset_feed_spec']['additional_data']={'page_welcome_message':messenger_welcome_message()}
        self.payload={'schema_version':3,'request_id':RID,'operation':tc.OPERATION,'graph_version':'v26.0','created_at':datetime.now(timezone.utc).isoformat(),'campaigns':[c],'prevalidated':True}
        self.payload['prevalidation']={'content_digest':content_digest(self.payload)}
        self.manifest=Manifest.from_dict(self.payload)
        with self.assertRaises(BatchTransportError):self.engine.execute(self.manifest)
        self.cp=Path(self.engine.config['state_root'])/'checkpoints'/f'{RID}-{AID}.json'
        self.checkpoint=tc.load(self.cp);self.initial=copy.deepcopy(self.checkpoint)
        self.config=self.engine.config
        account=self.config['accounts'][AID]
        account.update({'meta_app_id':'1299247318762949','token_item':'offline-existing','token_identity':'offline','campaign_policy':{'immediate_start_request_ids':[RID]}})
        self.q={'request_id':RID,'operation':tc.OPERATION,'account_id':AID,'start_time':c['start_time'],'requested_by_discord_id':ACTOR,'source_thread_id':'1541578556037927053','final_publication_approval':{'message_id':OK,'schedule_change_message_id':NOW,'immediate_requested':True,'technical_seeds_preserved':True}}
        self.path=self.home/'request.json';self.write(self.path,self.q)
        self.write(self.home/'final-approval.json',{'message_id':OK,'approved_digest':self.payload['prevalidation']['content_digest']})
        self.messages={mid:{'id':mid,'channel_id':self.q['source_thread_id'],'content':text,'author':{'id':('1508864261504630925' if mid==PROMPT else ACTOR),'bot':mid==PROMPT}} for mid,text in [(NOW,'NOW explicit'),(PROMPT,'three final ACTIVE / three seed PAUSED'),(OK,'sim')]}
        rec=self.checkpoint['bundles'][0]
        self.receipt={'request_id':RID,'account_id':AID,'request_path':str(self.path),'request_sha256':tc.file_digest(self.path),'manifest_digest':tc.digest(self.payload),'account_identity':{k:account.get(k) for k in ['app_key','meta_app_id','token_item','token_identity']},'authorized_by':ACTOR,'approval_message_id':OK,'now_message_id':NOW,'prompt_message_id':PROMPT,'meta_actor_id':'1700526774973769','messages':[{'id':m['id'],'content_digest':tc.digest(m['content']),'author_id':m['author']['id'],'bot':m['author']['bot']} for m in self.messages.values()],'journal_prefix_count':len(rec['write_journal']),'journal_prefix_digest':tc.digest(rec['write_journal']),'confirmed_objects':copy.deepcopy(rec['confirmed_objects']),'files':{'final-approval.json':tc.file_digest(self.home/'final-approval.json')}}
        self.rpath=Path(self.config['state_root'])/'target-continuations'/f'{RID}-{AID}.json'
        self.pin()
        self.clocks=ExitStack();self.addCleanup(self.clocks.close)
        self.clocks.enter_context(patch('ares_campaign_v3.schema.datetime',ElapsedClock))
        self.clocks.enter_context(patch.object(tc,'datetime',ElapsedClock))
    def write(self,path,data):
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    def pin(self):
        self.write(self.rpath,self.receipt)
        self.config['accounts'][AID]['target_page_replacement']['continuations']={RID:{'receipt_path':str(self.rpath),'sha256':tc.file_digest(self.rpath)}}
    def admission(self):return tc.admission(self.path,self.payload,self.config,meta=self.fake,token='synthetic-only',get_message=lambda p:self.messages[p.split('/')[-1]])
    def test_clock_expired_without_context_denied(self):
        with self.assertRaises(ManifestError):Manifest.from_dict(self.payload)
        with self.assertRaises(ValueError):self.engine.execute(self.manifest)
    def test_partial_success_missing_only_and_idempotent(self):
        original=copy.deepcopy(self.payload);before=len(self.fake.calls)
        with self.admission():
            m=Manifest.from_dict(self.payload);result=self.engine.execute(m)
        self.assertEqual(result['status'],'COMPLETE_FUTURE_ACTIVE')
        calls=self.fake.calls[before:]
        self.assertFalse(any(method=='POST' and name in {'campaign_create_1','adset_create_1','creative_create_1_1'} for _,name,method,_ in calls))
        self.assertFalse(any(stage=='target_uncertain_reconciliation' for stage,_,_,_ in calls))
        final=tc.load(self.cp)['bundles'][0]
        for k,v in self.initial['bundles'][0]['confirmed_objects'].items():self.assertEqual(final['confirmed_objects'][k],v)
        self.assertEqual(len([v for v in self.fake.objects.values() if v.get('_kind')=='campaign']),1)
        self.assertEqual(len([v for v in self.fake.objects.values() if v.get('_kind')=='adset']),1)
        ads=[v for v in self.fake.objects.values() if v.get('_kind')=='ad'];self.assertEqual(len(ads),6)
        self.assertEqual(sum(v['status']=='PAUSED' for v in ads),3)
        self.assertEqual(self.payload,original)
        before=len(self.fake.calls)
        with self.admission():self.assertTrue(self.engine.execute(Manifest.from_dict(self.payload))['idempotent_replay'])
        self.assertEqual(len(self.fake.calls),before)
    def test_manifest_tamper_rejected(self):
        self.payload['campaigns'][0]['campaign_create']['daily_budget']='9999'
        with self.assertRaises(ValueError):tc.validate_local(self.path,self.payload,self.config)
    def test_receipt_tamper_rejected(self):
        self.receipt['meta_actor_id']='99999';self.write(self.rpath,self.receipt)
        with self.assertRaises(ValueError):tc.validate_local(self.path,self.payload,self.config)
    def test_legacy_partial_response_missing_only_no_global_inventory(self):
        cp=copy.deepcopy(self.initial);cp['bundles'][0]['write_journal'][-1].pop('failed_children')
        self.write(self.cp,cp)
        self.receipt['journal_prefix_digest']=tc.digest(cp['bundles'][0]['write_journal']);self.pin()
        before=len(self.fake.calls)
        with self.admission():result=self.engine.execute(Manifest.from_dict(self.payload))
        self.assertEqual(result['status'],'COMPLETE_FUTURE_ACTIVE')
        self.assertFalse(any('/adcreatives' in x[3] and x[2]=='GET' for x in self.fake.calls[before:]))
        final=tc.load(self.cp)['bundles'][0]
        self.assertIn('target_clone_legacy_failure_receipt',final)
        self.assertEqual(final['write_journal'][:3],cp['bundles'][0]['write_journal'])
    def test_other_request_and_account_rejected(self):
        for key,value in [('request_id','another-request'),('account_id','999999999')]:
            with self.subTest(key=key):
                q={**self.q,key:value};self.write(self.path,q)
                with self.assertRaises(ValueError):tc.validate_local(self.path,self.payload,self.config)
        self.write(self.path,self.q)
    def test_missing_checkpoint_rejected(self):
        self.cp.unlink()
        with self.assertRaises(FileNotFoundError):tc.validate_local(self.path,self.payload,self.config)
    def test_not_allowlisted_rejected(self):
        self.config['accounts'][AID]['campaign_policy']['immediate_start_request_ids']=[]
        with self.assertRaises(ValueError):tc.validate_local(self.path,self.payload,self.config)
    def test_changed_approval_or_identity_rejected(self):
        self.messages[OK]['content']='no'
        with self.assertRaises(ValueError):
            with self.admission():pass
        self.messages[OK]['content']='sim'
        with patch.object(self.fake,'graph_get_credential_metadata',return_value=(200,{'id':'999999'},{'unused':True})):
            with self.assertRaises(ValueError):
                with self.admission():pass
    def test_checkpoint_id_and_journal_tamper_rejected(self):
        for mutate in [lambda b:b['confirmed_objects']['campaign_create_1'].update(id='99999'),lambda b:b['write_journal'][0]['operations'][0].update(body_digest='x'*64),lambda b:b['target_clone_ids'].update(campaign_id_1='99999')]:
            cp=copy.deepcopy(self.initial);mutate(cp['bundles'][0]);self.write(self.cp,cp)
            with self.assertRaises(ValueError):
                with self.admission():pass
        self.write(self.cp,self.initial)
    def test_arbitrary_completed_step_cannot_skip(self):
        cp=copy.deepcopy(self.initial);cp['bundles'][0]['target_clone_completed_steps'].append('target_seed_create_1_2');self.write(self.cp,cp)
        with self.assertRaises(ValueError):
            with self.admission():pass
    def test_remote_hierarchy_drift_blocks_before_write(self):
        sid=self.initial['bundles'][0]['confirmed_objects']['adset_create_1']['id']
        self.fake.objects[sid]['campaign_id']='99999';before=len(self.fake.calls)
        with self.admission():
            with self.assertRaises(ValueError):self.engine.execute(Manifest.from_dict(self.payload))
        self.assertFalse(any(x[2]=='POST' for x in self.fake.calls[before:]))
    def test_other_campaign_cannot_use_elapsed_context(self):
        with self.admission():
            value=copy.deepcopy(self.payload);value['campaigns'][0]['account_id']='999999999'
            with self.assertRaises(ManifestError):Manifest.from_dict(value)
            value=copy.deepcopy(self.payload);value['request_id']='another-request'
            with self.assertRaises(ManifestError):Manifest.from_dict(value)
        self.assertIsNone(tc.CURRENT.get())
    def test_rematerialized_known_variant_not_qa_bypass(self):
        ident=self.initial['bundles'][0]['confirmed_objects']['creative_create_1_1']['id']
        self.fake.objects[ident]['asset_feed_spec']['videos'][0]['video_id']='99999999'
        original_execute=self.fake.execute
        def rematerialize(operations,stage):
            rows=original_execute(operations,stage)
            if stage=='target_same_page_copy':
                for obj in self.fake.objects.values():
                    if obj.get('_kind')=='ad' and obj.get('source_ad_id'):obj['creative']['asset_feed_spec']['videos'][0]['video_id']='99999999'
            return rows
        self.fake.execute=rematerialize
        with self.admission():
            with self.assertRaisesRegex(ValueError,'video IDs rematerialized'):self.engine.execute(Manifest.from_dict(self.payload))
        campaigns=[v for v in self.fake.objects.values() if v.get('_kind')=='campaign']
        self.assertEqual(campaigns[0]['status'],'PAUSED')
        record=tc.load(self.cp)['bundles'][0]
        self.assertFalse(record['target_clone_known_media_observed'][ident]['media_equivalence_verified'])

class RejectionTests(unittest.TestCase):
    def test_success_without_id_or_conflicting_id_stays_uncertain(self):
        r={'write_journal':[{'state':'CONFIRMED','operations':[{'name':'creative_create_1_2'}],'confirmed':[]}]}
        self.assertTrue(adapter._uncertain(r,'creative_create_1_2'))
        for ids in [{'id':'0'},{'id':'123','copied_ad_id':'124'},{'id':'not-id'}]:
            r['write_journal'][0]['confirmed']=[{'name':'creative_create_1_2','ids':ids}]
            self.assertTrue(adapter._uncertain(r,'creative_create_1_2'))
    def record(self,code=400,error=None):
        name='creative_create_1_2'
        return {'write_journal':[{'state':'PARTIAL_OR_UNCERTAIN','stage':'creative_create','operations':[{'name':name}],'failed_children':[{'name':name,'code':code,'error':error or {'code':100,'error_subcode':1487390,'is_transient':False}}]}]}
    def test_definitive_response_known_missing(self):self.assertFalse(adapter._uncertain(self.record(),'creative_create_1_2'))
    def test_timeout_5xx_transient_unknown_id_fail_closed(self):
        records=[self.record(code=500),self.record(error={'code':2,'is_transient':True}),self.record(error={'code':100}),self.record(error={'code':100,'is_transient':False,'error_data':{'id':'123'}})]
        r=self.record();r['write_journal'][0].pop('failed_children');records.append(r)
        r=self.record();r['write_journal'][0]['state']='IN_FLIGHT';r['write_journal'][0]['failed_children']=[];records.append(r)
        for record in records:
            with self.subTest(record=record):self.assertTrue(adapter._uncertain(record,'creative_create_1_2'))
    def test_older_uncertainty_not_cleared_by_later_rejection(self):
        r=self.record();old=copy.deepcopy(r['write_journal'][0]);old.pop('failed_children');r['write_journal'].insert(0,old)
        self.assertTrue(adapter._uncertain(r,'creative_create_1_2'))
    def test_legacy_error_only_binds_last_matching_intent(self):
        r=self.record();r['error']={'stage':'creative_create','detail':{'children':r['write_journal'][0].pop('failed_children')}}
        self.assertFalse(adapter._uncertain(r,'creative_create_1_2'))
        r['write_journal'].append({'state':'CONFIRMED','stage':'other','operations':[]})
        self.assertTrue(adapter._uncertain(r,'creative_create_1_2'))

class CachedPageDependencyTests(unittest.TestCase):
    def test_fresh_scoped_context_precedes_compatible_cache_only(self):
        import importlib.util
        from ares_campaign_v3 import eggbev_page_identity as page
        spec=importlib.util.spec_from_file_location('target_cache_guard','/root/mgs-agent/scripts/mgs-ares-asset-scope.py');guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
        data=guard.load_scope();cached={'82001':{'source':'scoped_graph_dependency','kind':'page','account_ids':[AID]}}
        with patch.object(guard,'_objects',return_value=cached):
            marker=page.CURRENT.set({'account_id':AID,'page_id':'82001','ensure_pbia':False})
            try:
                dependency=guard._dependency_for_node('82001',data)
                guard._enforce_dependency('82001/page_backed_instagram_accounts',{'fields':'id,username','limit':10},'GET',dependency,data)
                with self.assertRaises(guard.ScopeError):guard._enforce_dependency('82001/page_backed_instagram_accounts',{},'POST',dependency,data)
                with patch.object(guard,'_objects',return_value={'82001':{**cached['82001'],'account_ids':['999999999']}}):
                    with self.assertRaises(guard.ScopeError):guard._dependency_for_node('82001',data)
            finally:page.CURRENT.reset(marker)
            dependency=guard._dependency_for_node('82001',data)
            with self.assertRaises(guard.ScopeError):guard._enforce_dependency('82001/page_backed_instagram_accounts',{'fields':'id,username','limit':10},'GET',dependency,data)

if __name__=='__main__':unittest.main()
