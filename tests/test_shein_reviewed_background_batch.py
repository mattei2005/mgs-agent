"""Offline regression for the exact reviewed 3-copy request; no Meta writes."""
import copy
import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from ares_campaign_v3 import shein_reviewed_background_batch as mod
from ares_campaign_v3 import shein_reviewed_background as dispatch
from ares_campaign_v3.shein_continuation import APPROVED_RESUME, content_digest

ROOT=Path('/root/mgs-agent/data/ares/meta-ads/audit/shein/feature-review-1567010220134105191')

class BatchBackgroundTests(unittest.TestCase):
    def setUp(self):
        self.state=json.loads((ROOT/'state.before.json').read_text())
        self.cp=json.loads((ROOT/'checkpoint.before.json').read_text())
        self.bound=json.loads((ROOT/'binding.json').read_text())
        self.messages=json.loads((ROOT/'messages.json').read_text())
        self.desc=mod.make_descriptor(self.state,self.bound)
    def get(self,path):
        if '/messages?' in path:return [self.messages[mod.PROMPT_ID]]
        return self.messages[path.rsplit('/',1)[-1]]
    def context(self):
        return {'descriptor':self.desc,'state':self.state,'checkpoint':self.cp,'verified':{
            'verified':True,'descriptor_digest':content_digest(self.desc),
            'accepted_creative_features':{'binding_digest':mod.BINDING_DIGEST}}}
    def test_valid_partial_future_descriptor(self):
        from ares_campaign_v3.shein_continuation import validate_descriptor
        with patch('ares_campaign_v3.shein_continuation._authorize_late_reviewer',return_value={'live':True}) as a:
            proof=validate_descriptor(self.desc,self.state,self.cp,get_message=self.get)
        a.assert_called_once();self.assertFalse(proof['start_now']);self.assertEqual(proof['campaign_ids'],self.cp['bundles'][0]['campaign_ids'])
        self.assertEqual(proof['original_execution_started_at'],self.state['execution_started_at'])
    def test_requires_exact_review_and_request(self):
        for field,value in [('content','não'),('edited_timestamp','later'),('channel_id','99')]:
            with self.subTest(field=field):
                saved=copy.deepcopy(self.messages[mod.REVIEW_ID]);self.messages[mod.REVIEW_ID][field]=value
                with self.assertRaises(ValueError):mod.validate_descriptor(self.desc,self.state,self.cp,get_message=self.get)
                self.messages[mod.REVIEW_ID]=saved
    def test_ambiguous_intervening_message_rejected(self):
        def get(path):
            if '/messages?' in path:return [self.messages[mod.PROMPT_ID],{'id':str(int(mod.PROMPT_ID)+1),'author':{'id':mod.HUMAN},'content':'other'}]
            return self.get(path)
        with self.assertRaises(ValueError):mod.validate_descriptor(self.desc,self.state,self.cp,get_message=get)
    def test_request_account_budget_clock_and_seals_frozen(self):
        for kind in ['account','budget','clock','source','seal']:
            s=copy.deepcopy(self.state)
            if kind=='account':s['request']['account']='9'
            if kind=='budget':s['request']['budget_usd']='1'
            if kind=='clock':s['execution_started_at']='later'
            if kind=='source':s['source']['ads'][0]['id']='9'
            if kind=='seal':s['manifest']['campaigns'][0]['name']='other'
            with self.subTest(kind=kind),self.assertRaises(ValueError):mod.require_binding(s,self.cp,self.bound)
    def test_shells_and_slots_cannot_be_replaced(self):
        for kind in ['id','key','duplicate']:
            c=copy.deepcopy(self.cp)
            if kind=='id':c['bundles'][0]['campaign_ids'][0]='9'
            if kind=='key':c['bundles'][0]['idempotency_keys'][0]='other'
            if kind=='duplicate':c['bundles'].append(copy.deepcopy(c['bundles'][0]))
            with self.subTest(kind=kind),self.assertRaises(ValueError):mod.require_binding(self.state,c,self.bound)
    def test_undeclared_delta_and_now_rejected(self):
        for field,value in [('start_now',True),('late_activation_authorized',True),('quantity',2),('budget_usd','100'),('review_message_id','1')]:
            d=copy.deepcopy(self.desc);d[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):mod.validate_descriptor(d,self.state,self.cp,get_message=self.get)
    def test_dispatch_and_payload_only_one_feature_changes(self):
        before=copy.deepcopy(self.state);marker=APPROVED_RESUME.set(self.context());cp=self.state['manifest']['campaigns'][0]['ads'][0]['creative_payload']
        try:
            for campaign in self.state['manifest']['campaigns']:
                for ad in campaign['ads']:
                    cp=ad['creative_payload'];out=dispatch.effective(cp)
                    self.assertEqual(out['degrees_of_freedom_spec']['creative_features_spec'][mod.FEATURE],{'enroll_status':'OPT_OUT'})
                    self.assertEqual(dispatch.effective(out),out)
                    out['degrees_of_freedom_spec']['creative_features_spec'][mod.FEATURE]={'enroll_status':'OPT_IN'}
                    self.assertEqual(out,cp)
            bad=copy.deepcopy(cp);bad['name']='bad'
            with self.assertRaises(ValueError):dispatch.effective(bad)
        finally:APPROVED_RESUME.reset(marker)
        self.assertEqual(before,self.state)
    def test_normal_flow_unchanged(self):
        cp=self.state['manifest']['campaigns'][0]['ads'][0]['creative_payload'];self.assertIs(dispatch.effective(cp),cp)
    def test_threadpool_context_propagated_and_lane_checked(self):
        from ares_campaign_v3.schema import Manifest
        m=Manifest.from_dict(self.state['manifest']);marker=APPROVED_RESUME.set(self.context())
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                self.assertTrue(dispatch.submit_lane(pool,lambda *a:mod.active_context() is not None,mod.ACCOUNT,(),mod.REQUEST,m.digest).result())
                with self.assertRaises(ValueError):dispatch.submit_lane(pool,lambda *a:None,'9',(),mod.REQUEST,m.digest)
        finally:APPROVED_RESUME.reset(marker)
    def bundle(self,index):
        from ares_campaign_v3.schema import Manifest
        from ares_campaign_v3.planning import Planner
        return Planner().build(Manifest.from_dict(self.state['manifest'])).lanes[mod.ACCOUNT][index]
    def rows(self,record,ads=None):
        rows=[]
        for i,(cid,sid) in enumerate(zip(record['campaign_ids'],record['adset_ids']),1):
            rows.extend([SimpleNamespace(name='feature_campaign_'+str(i),code=200,body={'id':cid,'account_id':mod.ACCOUNT,'status':'PAUSED'}),
                SimpleNamespace(name='feature_adset_'+str(i),code=200,body={'id':sid,'campaign_id':cid,'account_id':mod.ACCOUNT,'status':'PAUSED'}),
                SimpleNamespace(name='feature_ads_'+str(i),code=200,body={'data':[] if ads is None else ads})])
        return rows
    def test_recovery_two_shells_requires_readback_and_durable_receipt(self):
        from ares_campaign_v3.progress import CURRENT
        bundle=self.bundle(0);r=copy.deepcopy(self.cp['bundles'][0]);events=[]
        engine=SimpleNamespace(_batch=lambda *a:self.rows(r))
        marker=APPROVED_RESUME.set(self.context());journal=CURRENT.set((r,lambda:events.append(copy.deepcopy(r))))
        try:
            out=dispatch.resolve_bundle(engine,bundle,None,r)
            self.assertEqual(len(out.campaigns),2);self.assertEqual(len(events),1)
            self.assertIn('reviewed_creative_feature_resolution',events[0])
            self.assertEqual(dispatch.resolve_bundle(engine,bundle,None,r),out)
        finally:CURRENT.reset(journal);APPROVED_RESUME.reset(marker)
    def test_nonzero_incomplete_or_wrong_parent_blocks_before_receipt(self):
        from ares_campaign_v3.progress import CURRENT
        for kind in ['nonzero','missing','pagination','parent']:
            r=copy.deepcopy(self.cp['bundles'][0]);rows=self.rows(r)
            if kind=='nonzero':rows[2].body['data']=[{'id':'9'}]
            if kind=='missing':rows[2].body={}
            if kind=='pagination':rows[2].body['paging']={'next':'x'}
            if kind=='parent':rows[1].body['campaign_id']='9'
            marker=APPROVED_RESUME.set(self.context());journal=CURRENT.set((r,lambda:self.fail('must not persist')))
            try:
                with self.subTest(kind=kind),self.assertRaises(ValueError):dispatch.resolve_bundle(SimpleNamespace(_batch=lambda *a:rows),self.bundle(0),None,r)
            finally:CURRENT.reset(journal);APPROVED_RESUME.reset(marker)
    def test_third_planned_slot_uses_normal_core_after_receipt_without_copy_replay(self):
        from ares_campaign_v3.progress import CURRENT
        from ares_campaign_v3.schema import Manifest
        b=self.bundle(1);r={'index':b.index,'idempotency_keys':[c.idempotency_key for c in b.campaigns],
                          'sealed_manifest_digest':Manifest.from_dict(self.state['manifest']).digest};events=[]
        engine=SimpleNamespace(_batch=lambda *a:self.fail('uncreated shell must stay in normal core'))
        marker=APPROVED_RESUME.set(self.context());journal=CURRENT.set((r,lambda:events.append(copy.deepcopy(r))))
        try:
            out=dispatch.resolve_bundle(engine,b,None,r)
            self.assertEqual(len(events),1);self.assertEqual(out.campaigns[0].ads[0].creative_payload,dispatch.effective(b.campaigns[0].ads[0].creative_payload))
        finally:CURRENT.reset(journal);APPROVED_RESUME.reset(marker)
    def test_feature_and_other_features_enforced(self):
        cp=self.state['manifest']['campaigns'][0]['ads'][0]['creative_payload'];marker=APPROVED_RESUME.set(self.context())
        try:
            out=dispatch.effective(cp);dispatch.verify_creative(out,cp)
            with self.assertRaises(ValueError):dispatch.verify_creative(cp,cp)
            changed=copy.deepcopy(out);changed['degrees_of_freedom_spec']['creative_features_spec']['arbitrary']={'enroll_status':'OPT_IN'}
            with self.assertRaises(ValueError):dispatch.verify_creative(changed,cp)
        finally:APPROVED_RESUME.reset(marker)

    def test_complex_sourcing_preserved_verbatim_only_in_exact_review_context(self):
        from ares_campaign_v3 import creative_media
        trees=json.loads((ROOT/'trees-paused.json').read_text())
        expected={a['source_ad_id']:a['creative_payload'] for c in self.state['manifest']['campaigns'] for a in c['ads']}
        # Use each campaign's own canonical slot (names and tracking differ).
        source=next(a for a in trees[0]['ads']['data'] if a['source_ad_id']=='120252350213560326')
        cp=next(a['creative_payload'] for a in self.state['manifest']['campaigns'][0]['ads'] if a['source_ad_id']==source['source_ad_id'])
        self.assertFalse(creative_media.matches(source['creative'],mod._opt_out(cp)))
        marker=APPROVED_RESUME.set(self.context())
        try:
            self.assertTrue(creative_media.matches(source['creative'],dispatch.effective(cp)))
            for change in ['crop','uncrop','extra','hash','url','copy']:
                actual=copy.deepcopy(source['creative']);spec=actual['media_sourcing_spec']
                if change=='crop':spec['images'][1]['image_crops'][0]['crop_spec']['100x100'][0][0]=1
                if change=='uncrop':spec['images'][0]['opt_in_status']='opt_in'
                if change=='extra':spec['images'].append(copy.deepcopy(spec['images'][1]))
                if change=='hash':actual['object_story_spec']['link_data']['image_hash']='9'
                if change=='url':spec['images'][0]['url']='https://example.invalid/'
                if change=='copy':spec['bodies'][0]['text']='different'
                with self.subTest(change=change):self.assertFalse(creative_media.matches(actual,dispatch.effective(cp)))
        finally:APPROVED_RESUME.reset(marker)

    def test_all_six_real_creative_definitions_pass_without_rewriting_source_or_manifests(self):
        from ares_campaign_v3.shein_single_clone import verify_readback
        trees=json.loads((ROOT/'trees-paused.json').read_text());before=copy.deepcopy(self.state)
        marker=APPROVED_RESUME.set(self.context())
        try:
            for tree in trees:
                desired=next(c for c in self.state['manifest']['campaigns'] if c['name']==tree['campaign']['name'])
                warnings=verify_readback({**self.state['manifest'],'campaigns':[desired]},self.state['source'],tree)
                self.assertTrue(any('age/gender' in w for w in warnings))
        finally:APPROVED_RESUME.reset(marker)
        self.assertEqual(before,self.state)

    def test_later_missing_source_features_remain_a_material_gate(self):
        trees=json.loads((ROOT/'trees-paused-latest.json').read_text())
        marker=APPROVED_RESUME.set(self.context())
        try:
            for tree in trees:
                desired=next(c for c in self.state['manifest']['campaigns'] if c['name']==tree['campaign']['name'])
                expected={a['source_ad_id']:a['creative_payload'] for a in desired['ads']}
                for ad in tree['ads']['data']:
                    with self.subTest(ad=ad['id']),self.assertRaises(ValueError):dispatch.verify_creative(ad['creative'],expected[ad['source_ad_id']])
        finally:APPROVED_RESUME.reset(marker)

    def final_checkpoint(self):
        from ares_campaign_v3.schema import Manifest
        cp=copy.deepcopy(self.cp);cp['status']='COMPLETE'
        for r in cp['bundles']:
            r['status']='COMPLETE';r['reviewed_creative_feature_resolution']=mod._receipt(self.bound,r['idempotency_keys'])
        b=self.bundle(1);keys=[c.idempotency_key for c in b.campaigns]
        cp['bundles'].append({'index':b.index,'status':'COMPLETE','idempotency_keys':keys,
            'campaign_ids':['900000000000001'],'adset_ids':['900000000000002'],
            'sealed_manifest_digest':Manifest.from_dict(self.state['manifest']).digest,
            'reviewed_creative_feature_resolution':mod._receipt(self.bound,keys)})
        return cp
    def final_tree(self,index,cp):
        campaign=self.state['manifest']['campaigns'][index];r=cp['bundles'][0 if index<2 else 1];slot=index if index<2 else 0
        cid=r['campaign_ids'][slot];sid=r['adset_ids'][slot]
        return {'campaign':{'id':cid,'account_id':mod.ACCOUNT},'adsets':{'data':[{'id':sid}]},
            'ads':{'data':[{'id':'test-ad-'+str(index)+'-'+str(j),'adset_id':sid,
                'source_ad_id':a['source_ad_id'],'creative':mod._opt_out(a['creative_payload'])}
                for j,a in enumerate(campaign['ads'])]}}
    def test_complete_checkpoint_preserves_original_two_and_admits_only_planned_third(self):
        cp=self.final_checkpoint();mod.require_binding(self.state,cp,self.bound)
        cp['bundles'][1]['reviewed_creative_feature_resolution']['review_message_id']='9'
        with self.assertRaises(ValueError):mod.require_binding(self.state,cp,self.bound)
    def test_activation_trees_check_exact_ids_lineage_and_all_feature_states(self):
        cp=self.final_checkpoint();marker=APPROVED_RESUME.set(self.context())
        try:
            with patch.object(mod,'CHECKPOINT',SimpleNamespace(read_text=lambda:json.dumps(cp))):
                for index in range(3):dispatch.validate_activation_tree(self.final_tree(index,cp))
                tree=self.final_tree(0,cp);tree['ads']['data'][0]['adset_id']='9'
                with self.assertRaises(ValueError):dispatch.validate_activation_tree(tree)
                tree=self.final_tree(2,cp);tree['ads']['data'][0]['creative']['degrees_of_freedom_spec']['creative_features_spec'][mod.FEATURE]={'enroll_status':'OPT_IN'}
                with self.assertRaises(ValueError):dispatch.validate_activation_tree(tree)
                tree=self.final_tree(1,cp);tree['ads']['data']=[]
                with self.assertRaises(ValueError):dispatch.validate_activation_tree(tree)
                cp['bundles'][1]['campaign_ids']=cp['bundles'][0]['campaign_ids'][:1]
                with self.assertRaises(ValueError):mod._final_slots(self.context())
        finally:APPROVED_RESUME.reset(marker)
    def test_future_activation_proof_never_grants_now_or_changed_ids(self):
        from ares_campaign_v3.schema import Manifest
        from datetime import datetime,timezone
        class Clock(datetime):
            fake_hour=3
            @classmethod
            def now(cls,tz=None):return datetime(2026,11,3,cls.fake_hour,tzinfo=timezone.utc)
        # Freeze schema admission to this historical fixture's original test time.
        # Production future-schedule validation remains unchanged.
        with patch('ares_campaign_v3.schema.datetime', Clock):
            target=Manifest.from_dict(self.state['target_manifest']);creation=Manifest.from_dict(self.state['manifest'])
        cp=self.final_checkpoint();proof={'trees':[self.final_tree(i,cp) for i in range(3)],'execution_started_at':self.state['execution_started_at']}
        marker=APPROVED_RESUME.set(self.context())
        try:
            with patch.object(mod,'CHECKPOINT',SimpleNamespace(read_text=lambda:json.dumps(cp))),patch.object(mod,'datetime',Clock),patch('ares_campaign_v3.shein_continuation._authorize_late_reviewer',return_value={'live':True}):
                out=mod.activation_authorization(target,creation,proof,get_message=self.get)
                self.assertEqual(len(out['campaign_ids']),3);self.assertFalse(out['start_now'])
                Clock.fake_hour=6
                with self.assertRaises(ValueError):mod.activation_authorization(target,creation,proof,get_message=self.get)
                Clock.fake_hour=3;changed=copy.deepcopy(proof);changed['trees'][2]['campaign']['id']='9'
                with self.assertRaises(ValueError):mod.activation_authorization(target,creation,changed,get_message=self.get)
                changed=copy.deepcopy(proof);changed['execution_started_at']='later'
                with self.assertRaises(ValueError):mod.activation_authorization(target,creation,changed,get_message=self.get)
        finally:APPROVED_RESUME.reset(marker)

if __name__=='__main__':unittest.main()
