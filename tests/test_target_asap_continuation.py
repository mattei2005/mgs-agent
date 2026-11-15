"""Offline committed-ASAP partial admission; no production engine/network calls."""
import copy
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
import unittest
import test_target_continuation as legacy
from test_target_continuation import OK, PROMPT, ACTOR, AID, RID
from ares_campaign_v3 import target_continuation as tc
from ares_campaign_v3 import target_start_revision as rev
from ares_campaign_v3.prevalidation import content_digest
from ares_campaign_v3.schema import Manifest

ASAP='1571382777742626848'

class ASAPContinuationTests(legacy.ContinuationTests):
    def setUp(self):
        super().setUp()
        self.q.pop('final_publication_approval')
        self.write(self.path,self.q)
        account=self.config['accounts'][AID]
        self.messages.pop('1570313044771475559')
        self.messages[ASAP]={'id':ASAP,'channel_id':self.q['source_thread_id'],'content':'same approved request ASAP','author':{'id':ACTOR,'bot':False}}
        original=copy.deepcopy(self.payload)
        original['campaigns'][0]['start_time']=(datetime.fromisoformat(self.q['start_time'])-timedelta(hours=2)).isoformat()
        original['prevalidation']['content_digest']=content_digest(original)
        oq={**self.q,'start_time':original['campaigns'][0]['start_time']}
        summary={'start_time':oq['start_time'],'digest':original['prevalidation']['content_digest']}
        originals={'request.json':oq,'manifest.json':original,'summary.json':summary,'plan.json':{'synthetic':'original plan'}}
        for name,value in originals.items():self.write(self.home/'start-revisions/original'/name,value)
        grant={'schema_version':1,'request_path':str(self.path),'request_id':RID,'account_id':AID,'operation':rev.OPERATION,'approved_digest':original['prevalidation']['content_digest'],'approval_message_id':OK,'instruction_message_id':ASAP,'authorized_by':ACTOR,'source_thread_id':self.q['source_thread_id'],'meta_actor_id':'1700526774973769','account_identity':{k:account.get(k) for k in rev.IDENTITY_KEYS},'policy':rev.POLICY,'files':{n:tc.file_digest(self.home/'start-revisions/original'/n) for n in originals},'messages':[{'id':m['id'],'author_id':m['author']['id'],'bot':m['author']['bot'],'content_digest':tc.digest(m['content'])} for m in self.messages.values()]}
        self.grant=grant
        gp=Path(self.config['state_root'])/'target-start-grants'/f'{RID}-{AID}.json';self.write(gp,grant)
        binding={'receipt_path':str(gp),'sha256':tc.file_digest(gp)}
        account['target_page_replacement']['start_revisions']={RID:binding}
        after={'request.json':self.q,'manifest.json':self.payload,'summary.json':dict(summary,start_time=self.q['start_time'],digest=self.payload['prevalidation']['content_digest']),'plan.json':{'synthetic':'revised plan'}}
        tx={'schema_version':1,'request_id':RID,'index':1,'original_approved_digest':grant['approved_digest'],'approval_message_id':OK,'instruction_message_id':ASAP,'grant_digest':rev.digest(grant),'before':grant['files'],'after':after,'start_time':self.q['start_time'],'created_at':(datetime.fromisoformat(self.q['start_time'])-timedelta(minutes=5)).isoformat(),'revised_digest':self.payload['prevalidation']['content_digest']}
        self.tx=tx;self.folder=self.home/'start-revisions/000001'
        self.write(self.folder/'transaction.json',tx);self.write(self.folder/'committed.json',{'transaction_digest':rev.digest(tx)})
        for n,v in after.items():self.write(self.home/n,v)
        self.write(self.home/'final-approval.json',rev.approval_payload(grant,tx))
        self.receipt.update(schema_version=2,kind='committed_asap_partial',original_approved_digest=grant['approved_digest'],instruction_message_id=ASAP,start_grant_binding=binding,temporal_revision_digest=rev.digest(tx),revision_index=1,start_time=self.q['start_time'],request_sha256=tc.file_digest(self.path),messages=grant['messages'],files={n:tc.file_digest(self.home/n) for n in [*after,'final-approval.json']})
        self.pin()
        policy={'discord':{'campaign_ops_channel_id':'1539422731727147079','fixed_threads':{'create':self.q['source_thread_id']},'route_contracts':{'campaign_cloning':{'immediate_start_exception':rev.POLICY}}}}
        users={'agents':{'ares':{'authorized_user_discord_ids':[ACTOR],'_authorized_users_detail':[{'discord_id':ACTOR,'access_level':'full','scope':{'operations':['campaign_management']}}]}},'blocklist':[]}
        self.write(self.home/'policy.json',policy);self.write(self.home/'users.json',users)
        self.clocks.enter_context(patch.multiple(rev,OPERATION_PATH=self.home/'policy.json',USERS_PATH=self.home/'users.json'))
        metadata=self.fake.graph_get_credential_metadata
        def get(aid,token,inspect_token=False):
            code,body,headers=metadata(aid,token,inspect_token=inspect_token)
            if inspect_token:body['data']['type']='USER'
            return code,body,headers
        self.fake.graph_get_credential_metadata=get
    def get_message(self,path):
        if '/messages/' in path:return self.messages[path.split('/')[-1]]
        return {'id':self.q['source_thread_id'],'parent_id':'1539422731727147079','guild_id':'1185714635991679006'}
    def admission(self):return tc.admission(self.path,self.payload,self.config,meta=self.fake,token='synthetic-only',get_message=self.get_message)
    def test_mapping_uses_original_approval_not_new_ok(self):
        with self.admission() as context:
            self.assertEqual(context['temporal']['original_digest'],self.grant['approved_digest'])
            self.assertNotIn('final_publication_approval',context['request'])
            self.assertNotEqual(self.grant['approved_digest'],self.payload['prevalidation']['content_digest'])
            self.assertEqual(context['ids']['creative_id_1_1'],self.initial['bundles'][0]['confirmed_objects']['creative_create_1_1']['id'])
        self.assertIsNone(tc.CURRENT.get())
    def test_v2_receipt_mapping_fields_tamper(self):
        baseline=copy.deepcopy(self.receipt)
        for key,value in [('kind','unknown'),('original_approved_digest','0'*64),('temporal_revision_digest','0'*64),('revision_index',2),('start_time','2026-01-01T00:00:00+00:00'),('instruction_message_id','999999'),('start_grant_binding',{}),('messages',[]),('files',{})]:
            with self.subTest(key=key):
                self.receipt={**baseline,key:value};self.pin()
                with self.assertRaises((ValueError,KeyError)):tc.validate_local(self.path,self.payload,self.config)
        self.receipt=baseline;self.pin()
    def test_unknown_version_or_downgrade_denied(self):
        for version in [3,1]:
            self.receipt['schema_version']=version;self.pin()
            with self.assertRaises(ValueError):tc.validate_local(self.path,self.payload,self.config)
    def test_pending_transaction_rejected(self):
        self.write(self.folder/'committed.json',{'transaction_digest':'0'*64})
        with self.assertRaises(ValueError):tc.validate_local(self.path,self.payload,self.config)
        with patch.object(rev,'_transactions',wraps=rev._transactions) as transactions:
            original=transactions._mock_wraps
            def pending(*a):
                current,last,_=original(*a);return current,last,(self.folder,self.tx,current,current)
            transactions.side_effect=pending
            self.write(self.folder/'committed.json',{'transaction_digest':rev.digest(self.tx)})
            with self.assertRaisesRegex(ValueError,'committed'):tc.validate_local(self.path,self.payload,self.config)
    def test_grant_removed_denied(self):
        self.config['accounts'][AID]['target_page_replacement']['start_revisions']={}
        with self.assertRaises(ValueError):tc.validate_local(self.path,self.payload,self.config)
    def test_final_approval_downgrade_denied(self):
        self.write(self.home/'final-approval.json',{'message_id':OK,'approved_digest':self.payload['prevalidation']['content_digest']})
        with self.assertRaises(ValueError):tc.validate_local(self.path,self.payload,self.config)
    def test_revoked_current_authority_denied(self):
        self.write(self.home/'users.json',{'agents':{'ares':{'authorized_user_discord_ids':[]}}})
        with self.assertRaises(ValueError):tc.validate_local(self.path,self.payload,self.config)
    def test_instruction_edited_or_route_changed_denied(self):
        self.messages[ASAP]['content']='stop'
        with self.assertRaises(ValueError):
            with self.admission():pass
        with self.assertRaises(ValueError):
            with tc.admission(self.path,self.payload,self.config,meta=self.fake,token='synthetic',get_message=lambda p:{}):pass
    def test_elapsed_context_expires_and_clears_after_failure(self):
        with self.admission():
            with patch.object(tc.time,'monotonic',return_value=tc.CURRENT.get()['verified_at']+121):
                with self.assertRaises(ValueError):tc.require_execution(self.manifest)
        self.messages[ASAP]['content']='revoked'
        with self.assertRaises(ValueError):
            with self.admission():pass
        self.assertIsNone(tc.CURRENT.get())
    def test_local_validation_alone_never_admits_schema(self):
        tc.validate_local(self.path,self.payload,self.config)
        with self.assertRaises(ValueError):self.engine.execute(self.manifest)
    def test_no_effects_reclock_still_blocked(self):
        with self.assertRaisesRegex(ValueError,'existing/uncertain'):rev.require_no_effects(rev.validate_local(self.path,self.config,self.grant['approved_digest'],OK),self.config)
    def test_readonly_admission_preserves_all_files_and_quota(self):
        paths=[self.path,self.home/'manifest.json',self.home/'final-approval.json',self.cp,self.folder/'transaction.json',self.folder/'committed.json']
        before={str(p):tc.file_digest(p) for p in paths}
        with self.admission():pass
        self.assertEqual(before,{str(p):tc.file_digest(p) for p in paths})
    def runner(self):
        import importlib.util
        from types import SimpleNamespace
        cfg=self.home/'config.json';self.write(cfg,self.config)
        inventory=self.home/'inventory.jsonl';inventory.write_text('')
        self.write(self.home/'source-live.json',{})
        self.write(self.home/'target-page-live.json',{'instagram_user_id':'82002'})
        self.write(self.home/'selected-assets.json',[])
        spec=importlib.util.spec_from_file_location('asap_partial_runner',str(Path(__file__).resolve().parents[1]/'scripts/ares-eggbev-target-clone.py'))
        runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
        self.clocks.enter_context(patch.multiple(runner,CONFIG=cfg,INVENTORY=inventory,request_load=lambda *a,**kw:dict(self.q,target_page_token='synthetic'),runtime=lambda:(SimpleNamespace(),self.fake,None,'synthetic'),source_read=lambda *a:{},resolve_page=lambda *a:{'instagram_user_id':'82002'},real_transport_factory=lambda *a:lambda account:self.fake))
        for name,value in [('collect_history',[]),('verify_live_reservation',True)]:self.clocks.enter_context(patch.object(runner.naming,name,return_value=value))
        self.clocks.enter_context(patch('ares_campaign_v3.shein_channel_authority._get',side_effect=self.get_message))
        return runner
    def test_runner_check_only_original_arguments_zero_mutation(self):
        runner=self.runner();before=len(self.fake.calls);checkpoint=tc.file_digest(self.cp)
        result=runner.execute(self.path,True,self.grant['approved_digest'],OK,check_only=True)
        self.assertEqual(result['phase'],'CONTINUATION_VERIFIED_READ_ONLY')
        self.assertFalse(any(c[2]=='POST' for c in self.fake.calls[before:]))
        self.assertEqual(checkpoint,tc.file_digest(self.cp))
        self.assertEqual(tc.load(self.path)['start_time'],self.q['start_time'])
    def test_runner_execute_original_arguments_missing_only(self):
        runner=self.runner();before=len(self.fake.calls);manifest=tc.file_digest(self.home/'manifest.json')
        result=runner.execute(self.path,True,self.grant['approved_digest'],OK)
        self.assertEqual(result['phase'],'POSTPROCESS_PENDING')
        self.assertFalse(any(c[2]=='POST' and c[1] in {'campaign_create_1','adset_create_1','creative_create_1_1'} for c in self.fake.calls[before:]))
        self.assertEqual(manifest,tc.file_digest(self.home/'manifest.json'))
    def test_runner_rejects_bad_original_digest_before_any_call(self):
        runner=self.runner();before=len(self.fake.calls)
        with self.assertRaises(ValueError):runner.execute(self.path,True,'0'*64,OK)
        self.assertEqual(before,len(self.fake.calls))
    def test_runner_absent_continuation_blocks_elapsed(self):
        runner=self.runner();self.config['accounts'][AID]['target_page_replacement']['continuations']={}
        self.write(self.home/'config.json',self.config);before=len(self.fake.calls)
        with self.assertRaises(ValueError):runner.execute(self.path,True,self.grant['approved_digest'],OK)
        self.assertFalse(any(c[2]=='POST' for c in self.fake.calls[before:]))
    def test_wrong_type_app_or_actor_denied(self):
        original=self.fake.graph_get_credential_metadata
        for key,value in [('type','SYSTEM_USER'),('app_id','999999'),('user_id','999999')]:
            def wrong(*a,**kw):
                code,body,headers=original(*a,**kw)
                if kw.get('inspect_token'):body['data'][key]=value
                return code,body,headers
            with patch.object(self.fake,'graph_get_credential_metadata',side_effect=wrong):
                with self.assertRaises(ValueError):
                    with self.admission():pass

if __name__=='__main__':unittest.main()
