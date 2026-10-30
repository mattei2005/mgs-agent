"""Offline contract and same-manifest sourcing recovery; never Meta probes."""
import copy
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace as S
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_shein_image_media as image_fixtures
from ares_campaign_v3 import shein_general

class SourcingCompilerTests(unittest.TestCase):
    def test_image_compiler_explicit_exact_primary_sourcing(self):
        r,s,a,_=image_fixtures.ImageTests().fixture()
        before=copy.deepcopy(s)
        payload=shein_general.build(r,s,114,a)
        for slot in payload['campaigns'][0]['ads']:
            cp=slot['creative_payload']; ld=cp['object_story_spec']['link_data']
            self.assertEqual(cp['media_sourcing_spec'], {
                'images':[{'hash':ld['image_hash'],'source':'multi_media','opt_in_status':'opt_in'}],
                'titles':[{'text':ld['name']}], 'bodies':[{'text':ld['message']}]})
        self.assertEqual(s,before)

class SourcingRecoveryTests(unittest.TestCase):
    def fixture(self):
        from ares_campaign_v3.schema import Manifest
        from ares_campaign_v3.planning import Planner
        from ares_campaign_v3.transport import BatchOperation
        r,s,a,_=image_fixtures.ImageTests().fixture()
        p=shein_general.build(r,s,114,a)
        for slot in p['campaigns'][0]['ads']:slot['creative_payload'].pop('media_sourcing_spec')
        manifest=Manifest.from_dict(p);aid=manifest.campaigns[0].account_id
        bundle=Planner().build(manifest).lanes[aid][0]
        record={'campaign_ids':['1001'],'adset_ids':['2001'],'sealed_manifest_digest':manifest.digest,
                'idempotency_keys':[c.idempotency_key for c in bundle.campaigns]}
        ops=[BatchOperation(f'recovery_ad_copy_1_{i}','POST',f'{ad.source_ad_id}/copies',
            body={'adset_id':'2001','creative_parameters':copy.deepcopy(ad.creative_payload),'status_option':'PAUSED'},kind='ad_copy_with_creative') for i,ad in enumerate(bundle.campaigns[0].ads,1)]
        class Engine:
            config={'accounts':{aid:{'operation':'SHEIN-US-DIRECT'}}}
            def __init__(self):self.calls=[];self.bad=None
            def _batch(self,b,t,operations,stage):
                self.calls.append((stage,operations));result=[]
                for op in operations:
                    if 'campaign_' in op.name:body={'id':'1001','account_id':aid,'status':'PAUSED'}
                    elif 'adset_' in op.name:body={'id':'2001','campaign_id':'1001','account_id':aid,'status':'PAUSED'}
                    else:body={'data':[]}
                    if self.bad:self.bad(op,body)
                    result.append(S(name=op.name,code=200,body=body))
                return result
        return manifest,bundle,record,ops,Engine()
    def resolve(self,e,b,r,ops,save=None):
        from ares_campaign_v3 import progress,image_sourcing
        marker=progress.CURRENT.set((r,save or Mock()))
        try:return image_sourcing.resolve_operations(e,b,None,r,ops)
        finally:progress.CURRENT.reset(marker)
    def test_effective_recovery_same_digest_ids_slots_and_durable_receipts(self):
        from ares_campaign_v3.image_sourcing import digest
        m,b,r,ops,e=self.fixture();before=copy.deepcopy(m.raw);saved=[]
        out=self.resolve(e,b,r,ops,lambda:saved.append(copy.deepcopy(r)))
        self.assertEqual(m.raw,before);self.assertEqual(len(saved),1)
        self.assertEqual(len(r['image_sourcing_resolutions']),len(ops))
        for i,op in enumerate(out,1):
            original=ops[i-1].body['creative_parameters'];cp=op.body['creative_parameters']
            self.assertNotIn('media_sourcing_spec',original)
            self.assertEqual(cp['media_sourcing_spec']['images'][0]['hash'],original['object_story_spec']['link_data']['image_hash'])
            stripped=copy.deepcopy(cp);stripped.pop('media_sourcing_spec');self.assertEqual(stripped,original)
            receipt=r['image_sourcing_resolutions'][f'1.{i}']
            self.assertEqual(receipt['sealed_creative_digest'],digest(original));self.assertEqual(receipt['effective_creative_digest'],digest(cp))
            self.assertEqual(op.relative_url,ops[i-1].relative_url);self.assertEqual(op.body['adset_id'],'2001')
        old=copy.deepcopy(r['image_sourcing_resolutions']);self.resolve(e,b,r,ops);self.assertEqual(old,r['image_sourcing_resolutions'])
    def test_already_compiled_payload_does_not_change_or_read(self):
        from ares_campaign_v3.image_sourcing import effective
        _,b,r,ops,e=self.fixture()
        # Use new matching immutable slots as compiler would.
        for ad,op in zip(b.campaigns[0].ads,ops):
            ad.creative_payload.update(effective(ad.creative_payload));op.body['creative_parameters']=copy.deepcopy(ad.creative_payload)
        self.assertEqual(self.resolve(e,b,r,ops),ops);self.assertEqual(e.calls,[])
    def test_no_durable_journal_blocks_before_get_or_write(self):
        from ares_campaign_v3 import image_sourcing
        _,b,r,ops,e=self.fixture()
        with self.assertRaisesRegex(ValueError,'durable'):image_sourcing.resolve_operations(e,b,None,r,ops)
        self.assertEqual(e.calls,[])
    def test_any_existing_ad_or_pagination_or_parent_drift_blocks_all_receipts(self):
        for bad in ['ads','paging','account','campaign','adset','active_campaign','active_adset','missing_data']:
            with self.subTest(bad=bad):
                _,b,r,ops,e=self.fixture()
                def mutate(op,body):
                    if bad=='ads' and '_ads_' in op.name:body['data']=[{'id':'existing'}]
                    if bad=='paging' and '_ads_' in op.name:body['paging']={'next':'opaque'}
                    if bad=='missing_data' and '_ads_' in op.name:body.pop('data')
                    if bad=='account' and '_campaign_' in op.name:body['account_id']='wrong'
                    if bad=='campaign' and '_adset_' in op.name:body['campaign_id']='wrong'
                    if bad=='adset' and '_adset_' in op.name:body['id']='wrong'
                    if bad=='active_campaign' and '_campaign_' in op.name:body['status']='ACTIVE'
                    if bad=='active_adset' and '_adset_' in op.name:body['status']='ACTIVE'
                e.bad=mutate
                with self.assertRaises(ValueError):self.resolve(e,b,r,ops)
                self.assertNotIn('image_sourcing_resolutions',r)
                self.assertTrue(all(op.method=='GET' for _,calls in e.calls for op in calls))
    def test_wrong_scope_slot_payload_source_and_hash_fail_closed(self):
        from dataclasses import replace
        for bad in ['slot','name','path','method','payload','hash','status','mode','media_type']:
            with self.subTest(bad=bad):
                _,b,r,ops,e=self.fixture();first=ops[0]
                if bad=='slot':ops[0]=replace(first,name='recovery_ad_copy_8_1')
                if bad=='name':ops[0]=replace(first,name='unbound')
                if bad=='path':ops[0]=replace(first,relative_url='foreign/copies')
                if bad=='method':ops[0]=replace(first,method='GET')
                if bad=='payload':first.body['creative_parameters']['url_tags']='changed'
                if bad=='hash':first.body['creative_parameters']['object_story_spec']['link_data']['image_hash']='wrong'
                if bad in {'status','mode'}:
                    c=replace(b.campaigns[0],**{bad:'ACTIVE' if bad=='status' else 'pure_clone'});b=replace(b,campaigns=(c,))
                if bad=='media_type':
                    ad=replace(b.campaigns[0].ads[0],media=replace(b.campaigns[0].ads[0].media,media_type='video'))
                    b=replace(b,campaigns=(replace(b.campaigns[0],ads=(ad,*b.campaigns[0].ads[1:])),))
                with self.assertRaises(ValueError):self.resolve(e,b,r,ops)
                self.assertEqual(e.calls,[])
    def test_other_operation_untouched_and_incomplete_shells_blocked(self):
        _,b,r,ops,e=self.fixture();e.config={'accounts':{b.account_id:{'operation':'OTHER'}}}
        self.assertEqual(self.resolve(e,b,r,ops),ops);self.assertEqual(e.calls,[])
        _,b,r,ops,e=self.fixture();r['adset_ids']=[]
        with self.assertRaises(ValueError):self.resolve(e,b,r,ops)
    def test_resolution_receipt_cannot_be_rebound_or_changed(self):
        _,b,r,ops,e=self.fixture();self.resolve(e,b,r,ops)
        original=copy.deepcopy(r['image_sourcing_resolutions']);r['image_sourcing_resolutions']['1.1']['effective_creative_digest']='forged'
        with self.assertRaisesRegex(ValueError,'immutable'):self.resolve(e,b,r,ops)
        self.assertEqual(r['image_sourcing_resolutions']['1.2'],original['1.2'])
    def test_missing_sourcing_adds_exact_get_quota_reserve_and_dryrun_disclosure(self):
        import tempfile
        from ares_campaign_v3.engine import CampaignEngine
        m,b,_,_,e=self.fixture()
        with tempfile.TemporaryDirectory() as d:
            config={**e.config,'state_root':d+'/state','audit_root':d+'/audit'}
            eng=CampaignEngine(config,transport_factory=lambda _:self.fail('dryrun network'))
            self.assertEqual(eng._points(b),45+3)
            with patch('ares_campaign_v3.engine.validate_account_policy'):
                result=eng.dry_run(m)
            self.assertEqual(result['effective_payload_recovery']['legacy_image_slots'],3)
            self.assertEqual(result['writes'],0);self.assertFalse(result['effective_payload_recovery']['meta_acceptance_verified'])

class SourcingQATests(unittest.TestCase):
    def test_wrong_sourcing_blocks_schema_and_semantic_qa(self):
        from ares_campaign_v3.image_sourcing import effective
        from ares_campaign_v3.creative_media import matches
        from ares_campaign_v3.schema import Manifest,ManifestError
        r,s,a,_=image_fixtures.ImageTests().fixture();p=shein_general.build(r,s,114,a)
        cp=p['campaigns'][0]['ads'][0]['creative_payload'];self.assertTrue(matches(cp,cp))
        for bad in ['hash','extra','video','related','copy','destination','opt','missing']:
            with self.subTest(bad=bad):
                actual=copy.deepcopy(cp);spec=actual['media_sourcing_spec']
                if bad=='hash':spec['images'][0]['hash']='wrong'
                if bad=='extra':spec['images'].append(copy.deepcopy(spec['images'][0]))
                if bad=='video':spec['videos']=[{'video_id':'source'}]
                if bad=='related':spec['related_media']={}
                if bad=='copy':spec['bodies']=[{'text':'changed'}]
                if bad=='destination':spec['images'][0]['destination_customizations']=[{'url':'https://wrong.example'}]
                if bad=='opt':spec['images'][0]['opt_in_status']='opt_out'
                if bad=='missing':actual.pop('media_sourcing_spec')
                self.assertFalse(matches(actual,cp))
                if bad!='missing':
                    changed=copy.deepcopy(p);changed['campaigns'][0]['ads'][0]['creative_payload']=actual
                    with self.assertRaises(ManifestError):Manifest.from_dict(changed)
    def test_video_branch_not_rewritten_and_source_remains_unchanged(self):
        from test_shein_general_runtime import case
        r,s,a,assets=case(5,'ES','clone_prestaged');before=copy.deepcopy(s)
        p=shein_general.build(r,s,114,a)
        for slot,asset in zip(p['campaigns'][0]['ads'],assets):
            cp=slot['creative_payload'];self.assertNotIn('images',cp['media_sourcing_spec'])
            self.assertEqual(cp['media_sourcing_spec']['videos'][0]['video_id'],asset['vertical_video_id'])
        self.assertEqual(s,before)

class SourcingEngineIntegrationTests(unittest.TestCase):
    def test_exact_failed_bundle_recovers_once_without_recreating_shells_or_manifest(self):
        import tempfile,json
        from ares_campaign_v3 import image_sourcing
        from ares_campaign_v3.engine import CampaignEngine
        from ares_campaign_v3.transport import FakeBatchTransport,BatchResult,BatchTransportError
        m,b,_,_,e=SourcingRecoveryTests().fixture();original=copy.deepcopy(m.raw)
        class Transport(FakeBatchTransport):
            def __init__(self,aid):super().__init__(aid);self.fail_once=True;self.payloads=[]
            def execute(self,ops,stage):
                if stage=='ad_copy_with_creative' and self.fail_once:
                    self.fail_once=False
                    raise BatchTransportError(stage,{'children':[{'name':o.name,'code':400,'error':{'code':100,'error_subcode':4931013}} for o in ops],'successful_children':[]})
                if stage=='recovery_existing_ads_readback':
                    self.calls.append({'stage':stage,'operations':len(ops)})
                    return [BatchResult(o.name,200,{'data':[]}) for o in ops]
                if stage=='image_sourcing_zero_ads_readback':
                    self.calls.append({'stage':stage,'operations':len(ops)});rows=[]
                    for o in ops:
                        path=o.relative_url.split('?')[0]
                        body={'data':[]} if '_ads_' in o.name else {'id':path,'account_id':self.account_id,'status':'PAUSED'}
                        if '_adset_' in o.name:body['campaign_id']=self.account_id+'-campaign-1'
                        rows.append(BatchResult(o.name,200,body))
                    return rows
                if stage=='recovery_missing_ad_copies':
                    from ares_campaign_v3 import progress
                    record,_=progress.CURRENT.get()
                    assert len(record['image_sourcing_resolutions'])==len(ops)
                    self.payloads.extend(copy.deepcopy(o.body) for o in ops)
                return super().execute(ops,stage)
        with tempfile.TemporaryDirectory() as d:
            cfg={**e.config,'enabled':True,'write_enabled':True,'state_root':d+'/state','audit_root':d+'/audit'}
            t=Transport(b.account_id);eng=CampaignEngine(cfg,transport_factory=lambda _:t)
            with patch('ares_campaign_v3.engine.validate_account_policy'):
                # Reproduce the old deployed omission without a live payload probe.
                with patch.object(image_sourcing,'resolve_operations',side_effect=lambda _e,_b,_t,_r,ops:ops):
                    with self.assertRaises(BatchTransportError):eng.execute(m)
                checkpoint=next(Path(d+'/state/checkpoints').glob('*.json'));old=json.loads(checkpoint.read_text())
                shells=copy.deepcopy(old['bundles'][0]['campaign_ids']);adsets=copy.deepcopy(old['bundles'][0]['adset_ids'])
                before=len(t.calls);result=eng.execute(m)
                self.assertEqual(result['campaign_ids'],shells);self.assertEqual(result['status'],'COMPLETE_PAUSED')
                self.assertFalse(any(c['stage'] in {'campaign_copy','adset_copy'} for c in t.calls[before:]))
                state=json.loads(checkpoint.read_text());rec=state['bundles'][0]
                self.assertEqual(rec['adset_ids'],adsets);self.assertEqual(len(rec['image_sourcing_resolutions']),3)
                self.assertEqual(rec['sealed_manifest_digest'],m.digest)
                self.assertTrue(all(p['creative_parameters']['media_sourcing_spec']['images'] for p in t.payloads))
                self.assertTrue(all(p['status_option']=='PAUSED' for p in t.payloads))
                before=len(t.calls);self.assertTrue(eng.execute(m)['idempotent_replay']);self.assertEqual(len(t.calls),before)
            self.assertEqual(m.raw,original)

if __name__=='__main__': unittest.main()
