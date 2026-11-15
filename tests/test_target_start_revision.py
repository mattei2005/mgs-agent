"""Offline temporal gate tests. All files/Meta/Discord are synthetic."""
import copy
import importlib.util
import json
import socket
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from ares_campaign_v3 import target_start_revision as rev
from ares_campaign_v3.prevalidation import prevalidate_payload, verify_prevalidation
from ares_campaign_v3.schema import Manifest
from ares_campaign_v3.engine import CampaignEngine
from test_eggbev_target_page_clone import specimen

AID='1034081997659047'; ACTOR='1055570806945620030'; RID='offline-asap-target'
class Registry:
    def require_ready(self,*args,**kwargs):
        return {'vertical_video_id':'91001','square_video_id':'91002','upload_edge':'ad_account_advideos','association_verified':True}
class RevisionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/zeus/cache/scratch');self.addCleanup(self.temp.cleanup)
        self.home=Path(self.temp.name);self.path=self.home/'request.json'
        self.net=patch.object(socket.socket,'connect',side_effect=AssertionError('external network forbidden'));self.net.start();self.addCleanup(self.net.stop)
        self.old=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
        self.q={'request_id':RID,'account_id':AID,'operation':rev.OPERATION,'requested_by_discord_id':ACTOR,'source_thread_id':'1541578556037927053','start_time':self.old}
        self.raw={'schema_version':3,'request_id':RID,'operation':rev.OPERATION,'graph_version':'v26.0','created_at':'2026-01-01T00:00:00+00:00','campaigns':[specimen()]}
        self.raw['campaigns'][0]['start_time']=self.old
        from ares_campaign_v3.eggbev_create import messenger_welcome_message
        self.raw['campaigns'][0]['ads'][0]['creative_payload']['asset_feed_spec']['additional_data']={'page_welcome_message':messenger_welcome_message()}
        self.payload=prevalidate_payload(self.raw,Registry());self.approved=self.payload['prevalidation']['content_digest']
        self.cfg={'enabled':True,'write_enabled':True,'state_root':str(self.home/'state'),'audit_root':str(self.home/'audit'),'accounts':{AID:{'app_key':'test-app','meta_app_id':'953171080682697','token_item':'synthetic','token_identity':'Ana','operation':rev.OPERATION,'supported_modes':[rev.MODE],'target_page_replacement':{'enabled':True,'authorized_by':'344196393512075265','authority_message_id':'1569927267633602693','account_id':AID},'campaign_policy':{'immediate_start_request_ids':[RID]}}}}
        self.messages=[{'id':'1571371155317850153','author_id':'1508864261504630925','bot':True,'content':'summary'}, {'id':'1571376388437577861','author_id':ACTOR,'bot':False,'content':'approve'}, {'id':'1571382777742626848','author_id':ACTOR,'bot':False,'content':'ASAP'}]
        self.approval='1571376388437577861'
        self.policy={'discord':{'campaign_ops_channel_id':'1539422731727147079','fixed_threads':{'campaign_creation':self.q['source_thread_id']},'route_contracts':{'campaign_cloning':{'immediate_start_exception':rev.POLICY}}}}
        self.users={'agents':{'ares':{'authorized_user_discord_ids':[ACTOR],'_authorized_users_detail':[{'discord_id':ACTOR,'access_level':'full','scope':{'operations':['campaign_management']}}]}},'blocklist':[]}
        self.policy_path=self.home/'operation.json';rev.atomic_json(self.policy_path,self.policy)
        self.users_path=self.home/'users.json';rev.atomic_json(self.users_path,self.users)
        self.patch_root=patch.multiple(rev,OPERATION_PATH=self.policy_path,USERS_PATH=self.users_path);self.patch_root.start();self.addCleanup(self.patch_root.stop)
        for name,value in {'request.json':self.q,'manifest.json':self.payload,'summary.json':{'start_time':self.old,'digest':self.approved,'name':self.payload['campaigns'][0]['name']},'plan.json':{'original':'plan'},'operator-start-override.json':{'intent':'synthetic'},'operator-execution-approval.json':{'approval':'synthetic'}}.items():rev.atomic_json(self.home/name,value)
        self.grant={'schema_version':1,'request_path':str(self.path),'request_id':RID,'account_id':AID,'operation':rev.OPERATION,'approved_digest':self.approved,'approval_message_id':self.approval,'instruction_message_id':'1571382777742626848','authorized_by':ACTOR,'source_thread_id':self.q['source_thread_id'],'meta_actor_id':'122147293515218951','account_identity':{k:self.cfg['accounts'][AID].get(k) for k in rev.IDENTITY_KEYS},'policy':rev.POLICY,'files':{p.name:rev.file_digest(p) for p in self.home.glob('*.json') if p.name not in {'operation.json','users.json'}},'messages':[{k:v for k,v in m.items() if k!='content'}|{'content_digest':rev.digest(m['content'])} for m in self.messages]}
        gp=self.home/'state'/'target-start-grants'/f'{RID}-{AID}.json';rev.atomic_json(gp,self.grant)
        self.cfg['accounts'][AID]['target_page_replacement']['start_revisions']={RID:{'receipt_path':str(gp),'sha256':rev.file_digest(gp)}}
    def binding(self):return rev.validate_local(self.path,self.cfg,self.approved,self.approval)
    def dryrun(self,p):return CampaignEngine(self.cfg,transport_factory=lambda account:None).dry_run(Manifest.from_dict(p))
    def materialize(self,**kw):
        return rev.materialize(self.binding(),self.cfg,registry=Registry(),dry_run=self.dryrun,start_factory=lambda:(rev.datetime.now(timezone.utc)+timedelta(minutes=5)).replace(microsecond=0).isoformat(),**kw)
    def get(self,path):
        if '/messages/' in path:
            mid=path.rsplit('/',1)[1];m=next(m for m in self.messages if m['id']==mid)
            return {'id':mid,'channel_id':self.q['source_thread_id'],'author':{'id':m['author_id'],'bot':m['bot']},'content':m['content']}
        return {'id':self.q['source_thread_id'],'parent_id':'1539422731727147079','guild_id':'1185714635991679006'}
    def meta(self):
        class Meta:
            def graph_get_credential_metadata(s,aid,token,inspect_token=False):
                return (200,{'data':{'is_valid':True,'user_id':'122147293515218951','app_id':'953171080682697','type':'USER'}} if inspect_token else {'id':'122147293515218951'},{})
        return Meta()
    def test_future_asap_only_start_delta(self):
        out=self.materialize();self.assertTrue(verify_prevalidation(out));rev.only_start_delta(self.payload,out)
        self.assertNotEqual(out['campaigns'][0]['start_time'],self.old);self.assertEqual(self.binding()['original_digest'],self.approved)
    def test_expired_original_supported_without_schema_bypass(self):
        old=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat();self.q['start_time']=old;self.payload['campaigns'][0]['start_time']=old
        from ares_campaign_v3.prevalidation import content_digest
        self.payload['prevalidation']['content_digest']=content_digest(self.payload);self.approved=self.payload['prevalidation']['content_digest'];self.grant['approved_digest']=self.approved
        rev.atomic_json(self.path,self.q);rev.atomic_json(self.home/'manifest.json',self.payload)
        for name in ['request.json','manifest.json']:self.grant['files'][name]=rev.file_digest(self.home/name)
        self.repin();self.assertTrue(verify_prevalidation(self.materialize()))
    def repin(self):
        gp=Path(self.cfg['accounts'][AID]['target_page_replacement']['start_revisions'][RID]['receipt_path']);rev.atomic_json(gp,self.grant);self.cfg['accounts'][AID]['target_page_replacement']['start_revisions'][RID]['sha256']=rev.file_digest(gp)
    def test_retry_keeps_same_future_revision(self):
        first=self.materialize();second=self.materialize();self.assertEqual(first,second);self.assertEqual(len(list((self.home/'start-revisions').glob('[0-9]*'))),1)
    def test_live_human_and_credential_helper(self):rev.live_authority(self.binding(),meta=self.meta(),token='synthetic',get_message=self.get)
    def test_revoked_authority(self):
        self.users['agents']['ares']['authorized_user_discord_ids']=[];rev.atomic_json(self.users_path,self.users)
        with self.assertRaises(ValueError):self.binding()
    def test_absent_grant(self):
        self.cfg['accounts'][AID]['target_page_replacement'].pop('start_revisions')
        with self.assertRaises(ValueError):self.binding()
    def test_forged_grant(self):
        gp=Path(self.cfg['accounts'][AID]['target_page_replacement']['start_revisions'][RID]['receipt_path']);gp.write_text('{}')
        with self.assertRaises(ValueError):self.binding()
    def test_missing_allowlist(self):
        self.cfg['accounts'][AID]['campaign_policy']['immediate_start_request_ids']=[]
        with self.assertRaises(ValueError):self.binding()
    def test_approved_digest_tamper(self):
        with self.assertRaises(ValueError):rev.validate_local(self.path,self.cfg,'a'*64,self.approval)
    def test_receipt_tamper(self):
        rev.atomic_json(self.home/'operator-start-override.json',{'intent':'forged'})
        with self.assertRaises(ValueError):self.binding()
    def test_live_message_deleted(self):
        with self.assertRaises(ValueError):rev.live_authority(self.binding(),meta=self.meta(),token='synthetic',get_message=lambda p:{})
    def test_live_author_forged(self):
        def get(p):
            d=self.get(p)
            if 'author' in d:d['author']['id']='999'
            return d
        with self.assertRaises(ValueError):rev.live_authority(self.binding(),meta=self.meta(),token='synthetic',get_message=get)
    def test_live_instruction_edited(self):
        self.messages[-1]['content']='do not execute'
        with self.assertRaises(ValueError):rev.live_authority(self.binding(),meta=self.meta(),token='synthetic',get_message=self.get)
    def test_wrong_credential_identity(self):
        meta=self.meta();meta.graph_get_credential_metadata=lambda *a,**kw:(200,{'id':'999'},{})
        with self.assertRaises(ValueError):rev.live_authority(self.binding(),meta=meta,token='synthetic',get_message=self.get)
    def test_non_start_delta_denied(self):
        p=copy.deepcopy(self.payload);p['campaigns'][0]['campaign_create']['daily_budget']='3600'
        with self.assertRaises(ValueError):rev.only_start_delta(self.payload,p)
    def test_request_tamper_denied(self):
        q=copy.deepcopy(self.q);q['budget']='new';rev.atomic_json(self.path,q)
        with self.assertRaises(ValueError):self.binding()
    def test_manifest_tamper_denied(self):
        p=copy.deepcopy(self.payload);p['campaigns'][0]['name']='other';rev.atomic_json(self.home/'manifest.json',p)
        with self.assertRaises(ValueError):self.binding()
    def test_summary_tamper_denied_after_revision(self):
        self.materialize();p=json.loads((self.home/'summary.json').read_text());p['name']='other';rev.atomic_json(self.home/'summary.json',p)
        with self.assertRaises(ValueError):self.binding()
    def test_effects_block_and_preserve(self):
        cp=Path(self.cfg['state_root'])/'checkpoints'/f'{RID}-{AID}.json';rev.atomic_json(cp,{'target_clone_ids':{'campaign_id_1':'123'},'start_time':'old'})
        before={p:p.read_bytes() for p in self.home.glob('*.json')}
        with self.assertRaisesRegex(ValueError,'continuation'):self.materialize()
        self.assertEqual(before,{p:p.read_bytes() for p in before});self.assertEqual(json.loads(cp.read_text())['target_clone_ids'],{'campaign_id_1':'123'})
    def test_live_existing_name_blocks_before_revision(self):
        with self.assertRaisesRegex(ValueError,'continuation'):rev.require_no_effects(self.binding(),self.cfg,live_campaigns=[{'id':'123','name':self.payload['campaigns'][0]['name']}])
    def test_uncertain_checkpoint_blocks(self):
        cp=Path(self.cfg['state_root'])/'checkpoints'/f'{RID}-{AID}.json';cp.parent.mkdir(parents=True);cp.write_text('broken')
        with self.assertRaises(ValueError):self.materialize()
    def test_crash_every_cas_boundary_retry(self):
        for boundary in ['transaction','request.json','manifest.json','plan.json','summary.json','commit']:
            with self.subTest(boundary=boundary):
                # A new synthetic sandbox per independent crash.
                other=RevisionTests('test_future_asap_only_start_delta');other.setUp()
                try:
                    def crash(name):
                        if name==boundary:raise KeyboardInterrupt('crash')
                    with self.assertRaises(KeyboardInterrupt):other.materialize(after_write=crash)
                    result=other.materialize();self.assertTrue(verify_prevalidation(result));self.assertEqual(len(list((other.home/'start-revisions').glob('[0-9]*'))),1)
                finally:other.doCleanups()
    def test_cas_conflict_never_overwrites(self):
        def crash(name):
            if name=='request.json':
                (self.home/'manifest.json').write_text('{"foreign":true}');raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):self.materialize(after_write=crash)
        with self.assertRaises(ValueError):self.materialize()
        self.assertEqual(json.loads((self.home/'manifest.json').read_text()),{'foreign':True})
    def test_effects_after_revision_keep_ids_and_start(self):
        p=self.materialize();cp=Path(self.cfg['state_root'])/'checkpoints'/f'{RID}-{AID}.json';rev.atomic_json(cp,{'ids':['123'],'start':p['campaigns'][0]['start_time']})
        self.assertEqual(self.materialize(),p);self.assertEqual(json.loads(cp.read_text())['ids'],['123'])
    def test_wrong_app_denied(self):
        self.cfg['accounts'][AID]['meta_app_id']='other'
        with self.assertRaises(ValueError):self.binding()
    def test_bad_buffer_denied(self):
        with self.assertRaises(ValueError):rev.materialize(self.binding(),self.cfg,registry=Registry(),dry_run=self.dryrun,start_factory=lambda:self.old)

    def advance_clock(self):
        class Future(datetime):
            @classmethod
            def now(cls,tz=None):return datetime.now(tz)+timedelta(days=2)
        return patch.object(rev,'datetime',Future)
    def test_expired_revision_no_effects_gets_successor(self):
        first=self.materialize()
        with self.advance_clock():second=self.materialize()
        self.assertNotEqual(first['campaigns'][0]['start_time'],second['campaigns'][0]['start_time'])
        self.assertEqual(len(list((self.home/'start-revisions').glob('[0-9]*'))),2)
        self.assertEqual((self.home/'start-revisions/original/manifest.json').read_bytes(),self.grant_original_manifest())
    def grant_original_manifest(self):return rev.encoded(self.payload)
    def test_expired_revision_with_effects_no_change(self):
        first=self.materialize();cp=Path(self.cfg['state_root'])/'checkpoints'/f'{RID}-{AID}.json';rev.atomic_json(cp,{'ids':['123']})
        with self.advance_clock(),self.assertRaisesRegex(ValueError,'continuation'):self.materialize()
        self.assertEqual(rev.load(self.home/'manifest.json'),first);self.assertEqual(rev.load(cp)['ids'],['123'])
    def test_pending_revision_effects_block_redo(self):
        def crash(name):
            if name=='request.json':raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):self.materialize(after_write=crash)
        rev.atomic_json(self.home/'engine-result.json',{'ids':['123']})
        before=(self.home/'manifest.json').read_bytes()
        with self.assertRaises(ValueError):self.materialize()
        self.assertEqual((self.home/'manifest.json').read_bytes(),before)
    def test_final_approval_before_engine_not_effect_and_is_archived(self):
        self.materialize();context=self.binding();approval=rev.approval_payload(context['grant'],context['last'][1]);rev.atomic_json(self.home/'final-approval.json',approval)
        with self.advance_clock():self.materialize()
        self.assertEqual(rev.load(self.home/'start-revisions/000001/final-approval.json'),approval)
    def test_temporal_transaction_non_start_tamper_rejected(self):
        self.materialize();p=self.home/'start-revisions/000001/transaction.json';tx=rev.load(p);tx['after']['manifest.json']['campaigns'][0]['status']='PAUSED';rev.atomic_json(p,tx)
        with self.assertRaises(ValueError):self.binding()
    def test_temporal_transaction_new_digest_tamper_rejected(self):
        self.materialize();p=self.home/'start-revisions/000001/transaction.json';tx=rev.load(p);tx['revised_digest']='f'*64;rev.atomic_json(p,tx)
        with self.assertRaises(ValueError):self.binding()
    def test_non_start_request_tamper_in_transaction_rejected(self):
        self.materialize();p=self.home/'start-revisions/000001/transaction.json';tx=rev.load(p);tx['after']['request.json']['budget']='999';rev.atomic_json(p,tx)
        with self.assertRaises(ValueError):self.binding()
    def test_final_approval_mapping_tamper_rejected(self):
        self.materialize();rev.atomic_json(self.home/'final-approval.json',{'approved_digest':self.approved})
        with self.assertRaises(ValueError):self.binding()

    def runner_setup(self):
        from types import SimpleNamespace
        from eggbev_target_fake import TargetFakeMeta
        q=rev.load(self.path);q.update(duplicate_count=1,commercial_ok_message_id='1571342489162489937',media_filenames=['synthetic.mp4'],target_page_token='pg_23186')
        rev.atomic_json(self.path,q)
        for name,value in {'source-live.json':{},'target-page-live.json':{'instagram_user_id':'82002'},'selected-assets.json':[]}.items():rev.atomic_json(self.home/name,value)
        self.grant['files'].update({n:rev.file_digest(self.home/n) for n in ['request.json','source-live.json','target-page-live.json','selected-assets.json']});self.repin()
        config=self.home/'config.json';rev.atomic_json(config,self.cfg)
        inventory=self.home/'inventory.jsonl';inventory.write_text('')
        spec=importlib.util.spec_from_file_location('offline_temporal_target_runner',str(Path(__file__).resolve().parents[1]/'scripts/ares-eggbev-target-clone.py'));runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
        fake=TargetFakeMeta();meta=self.meta()
        context=rev.validate_local(self.path,self.cfg,self.approved,self.approval)
        original_live=rev.live_authority
        stack=__import__('contextlib').ExitStack();self.addCleanup(stack.close)
        stack.enter_context(patch.multiple(runner,CONFIG=config,INVENTORY=inventory,MediaRegistry=lambda p:Registry(),runtime=lambda:(SimpleNamespace(fetch_all_meta=lambda *a,**kw:[]),meta,None,'synthetic'),source_read=lambda *a:{},resolve_page=lambda *a:{'instagram_user_id':'82002'},real_transport_factory=lambda *a:lambda account:fake,module=lambda *a:SimpleNamespace(immediate_execute_start=lambda:(datetime.now(timezone.utc)+timedelta(minutes=5)).replace(microsecond=0).isoformat())))
        stack.enter_context(patch.object(runner.naming,'load_policy',return_value={'account_ids':[AID]}))
        stack.enter_context(patch.object(runner.naming,'collect_history',return_value=[]));stack.enter_context(patch.object(runner.naming,'verify_live_reservation',return_value=True))
        stack.enter_context(patch.object(runner.subprocess,'run',return_value=SimpleNamespace(stdout='{"allowed":true}')))
        stack.enter_context(patch.object(rev,'live_authority',side_effect=lambda ctx,**kw:original_live(ctx,**kw,get_message=self.get)))
        return runner,fake,config
    def test_full_execute_original_digest_and_replay_no_reclock(self):
        runner,fake,_=self.runner_setup()
        result=runner.execute(self.path,True,self.approved,self.approval)
        self.assertEqual(result['phase'],'POSTPROCESS_PENDING')
        active=rev.load(self.home/'manifest.json');self.assertNotEqual(active['prevalidation']['content_digest'],self.approved)
        approval=rev.load(self.home/'final-approval.json');self.assertEqual(approval['original_approved_digest'],self.approved);self.assertEqual(approval['approved_digest'],active['prevalidation']['content_digest'])
        cp=Path(self.cfg['state_root'])/'checkpoints'/f'{RID}-{AID}.json';before=rev.load(cp);count=len(fake.calls)
        runner.execute(self.path,True,self.approved,self.approval)
        self.assertEqual(count,len(fake.calls));self.assertEqual(rev.load(cp)['bundles'][0]['target_clone_ids'],before['bundles'][0]['target_clone_ids']);self.assertEqual(rev.load(self.home/'manifest.json'),active)
    def test_full_execute_bad_digest_before_engine(self):
        runner,fake,_=self.runner_setup()
        with self.assertRaises(ValueError):runner.execute(self.path,True,'f'*64,self.approval)
        self.assertFalse(fake.calls);self.assertFalse((self.home/'start-revisions').exists())
    def test_full_execute_missing_grant_before_engine(self):
        runner,fake,config=self.runner_setup();self.cfg['accounts'][AID]['target_page_replacement']['start_revisions']={};rev.atomic_json(config,self.cfg)
        with self.assertRaises(ValueError):runner.execute(self.path,True,self.approved,self.approval)
        self.assertFalse(fake.calls)
    def test_full_execute_revoked_live_message_before_engine(self):
        runner,fake,_=self.runner_setup();self.messages[-1]['content']='revoked'
        with self.assertRaises(ValueError):runner.execute(self.path,True,self.approved,self.approval)
        self.assertFalse(fake.calls);self.assertFalse((self.home/'start-revisions').exists())
    def test_request_lock_excludes_imported_writer(self):
        import fcntl
        runner,fake,_=self.runner_setup()
        with (self.home/'target-clone.lock').open('a+') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):runner.execute(self.path,True,self.approved,self.approval)
        self.assertFalse(fake.calls)
    def test_other_account_writer_excluded(self):
        from ares_campaign_v3.coordination import AccountWriterLeaseStore,WriterLeaseConflict
        runner,fake,_=self.runner_setup();leases=AccountWriterLeaseStore(self.cfg['state_root']);leases.claim(AID,'other-request')
        with self.assertRaises(WriterLeaseConflict):runner.execute(self.path,True,self.approved,self.approval)
        self.assertFalse(fake.calls)

if __name__=='__main__':unittest.main()
