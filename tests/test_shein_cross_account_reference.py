"""Explicitly OFFLINE: synthetic media/Graph transport, never live mutations."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_shein_general_runtime import case
from ares_campaign_v3 import shein_reference as ref, shein_general as general, shein_single_clone as driver
from ares_campaign_v3.prevalidation import prevalidate_payload, validate_account_policy
from ares_campaign_v3.media_registry import MediaRegistry
from ares_campaign_v3.schema import Manifest, ManifestError
from ares_campaign_v3.engine import CampaignEngine
from ares_campaign_v3.transport import FakeBatchTransport, BatchResult


def fixture(index=1, count=2):
    r, s, a, assets = case(index, mode='from_zero_prestaged')
    sp = copy.deepcopy(a['shein_profile']); sp['currency'] = 'USD'
    tp = copy.deepcopy(sp)
    tp.update(account_id=str(3000000000000000+index), account_name='Target-'+sp['manager_code'],
              page_id=str(4000000000000000+index), operational_domain='escalatepower.com')
    r.update(account=tp['account_name'], source_account=sp['account_name'], source_campaign_id=s['campaign']['id'],
             quantity=1, website_url='https://escalatepower.com/quiz/us/sh3-'+sp['manager_code'].lower()+'/?utm_source=facebook&utm_medium='+sp['utm_medium']+'&utm_campaign=b01fb02c01&utm_adgroup=b01fb02c01g01',
             primary_text='👚 EXACT\n✔️ NO FEES.', bid_strategy='COCAP', bid_usd='0.90', budget_from_reference=True)
    r.pop('budget_usd')
    if count > len(assets):
        for i in range(len(assets), count):
            asset=copy.deepcopy(assets[0]); asset.update(asset_id=f'asset-extra-{i}', checksum=f'{i+9:064x}', vertical_video_id=f'new-video-{i}', canonical_filename=f'SHEIN_US_EN_VID_FREE_PRODUCT_PV_{i+1:03d}.mp4');assets.append(asset)
    assets=assets[:count];r['_resolved_assets']=assets
    s['campaign'].update(buying_type='AUCTION', special_ad_categories=[], special_ad_category_country=[], status='ACTIVE')
    s['adset'].update(regional_regulated_categories=[], regional_regulation_identities={}, status='ACTIVE')
    tp=ref.target_profile(r,tp,sp,{'enabled':True,'approved_by':ref.RODOLFO})
    tp['page_id']=sp['page_id']
    tp['instagram_user_id']='5000000000000001'
    s['ads'][0]['creative']['object_story_spec']['instagram_user_id']='5000000000000001'
    a.update(alias=tp['account_name'], shein_profile=tp, shein_reference_profile=sp,
             shein_naming={'enabled':True,'route_regex':r'^/quiz/us/sh([123])-g[0-9]{3}/$','layout_version_map':{'1':'v1','2':'v2','3':'v3'}}, token_item='test-corporate-item')
    source_account=copy.deepcopy(a);source_account.update(alias=sp['account_name'],shein_profile=sp);source_account.pop('shein_reference_profile')
    r=driver.resolve_intent(r,s)
    cfg={'enabled':True,'write_enabled':True,'require_account_registration':True,
         'accounts':{tp['account_id']:a,sp['account_id']:source_account},
         'shein_cross_account_reference':{'enabled':True,'approved_by':ref.RODOLFO,'lineage_route':'direct_ad_create_with_source_ad_id','allowed_ad_counts':[1,2,3,4,5]}}
    return r,s,a,assets,cfg


def sealed(root, r, s, a, assets, cfg):
    registry=MediaRegistry(root/'media.json')
    for asset in assets:
        registry.register(account_id=a['shein_profile']['account_id'],asset_id=asset['asset_id'],checksum=asset['checksum'],vertical_video_id=asset['vertical_video_id'],square_video_id=None,ready=True,upload_edge='ad_account_advideos',association_verified=True)
    payload=general.build(r,s,1,a)
    validate_account_policy(Manifest.from_dict(payload),cfg)
    return Manifest.from_dict(prevalidate_payload(payload,registry))


class ReferenceTests(unittest.TestCase):
    def test_two_ads_literals_target_shells_and_source_immutable(self):
        r,s,a,assets,cfg=fixture();before=copy.deepcopy(s)
        payload=general.build(r,s,1,a);shell=payload['campaigns'][0]
        self.assertEqual(s,before);self.assertEqual(shell['account_id'],a['shein_profile']['account_id'])
        self.assertNotIn('source_campaign_id',shell);self.assertNotIn('source_adset_id',shell)
        self.assertTrue(shell['name'].startswith('001 - '));self.assertNotIn('COPY',shell['name'])
        self.assertEqual(shell['campaign_create']['daily_budget'],'4000');self.assertEqual(shell['campaign_create']['bid_strategy'],'COST_CAP')
        self.assertEqual(shell['adset_create']['bid_amount'],'90');self.assertEqual(shell['adset_create']['bid_constraints'],{})
        self.assertEqual(shell['adset_create']['targeting'],s['adset']['targeting'])
        self.assertEqual([x['media']['asset_id'] for x in shell['ads']],[x['asset_id'] for x in assets])
        for slot in shell['ads']:
            cr=slot['creative_payload'];vd=cr['object_story_spec']['video_data']
            self.assertEqual(vd['message'],r['primary_text']);self.assertEqual(vd['call_to_action']['value']['link'],r['website_url']);self.assertEqual(cr['url_tags'],'')
            self.assertEqual(cr['object_story_spec']['page_id'],a['shein_profile']['page_id'])
            self.assertEqual(cr['object_story_spec']['instagram_user_id'],'5000000000000001')
            self.assertEqual(slot['source_ad_id'],s['ads'][0]['id'])
        self.assertEqual(shell['reference']['account_id'],s['campaign']['account_id'])

    def test_all_six_partitions_and_one_through_five_counts_central_core(self):
        for manager in range(6):
            for count in range(1,6):
                with self.subTest(manager=manager,count=count),tempfile.TemporaryDirectory() as raw:
                    root=Path(raw);r,s,a,assets,cfg=fixture(manager,count)
                    cfg.update(state_root=str(root/'state'),audit_root=str(root/'audit'))
                    m=sealed(root,r,s,a,assets,cfg)
                    transport=FakeBatchTransport(a['shein_profile']['account_id'])
                    result=CampaignEngine(cfg,transport_factory=lambda aid:transport).execute(m)
                    self.assertEqual(result['status'],'COMPLETE_PAUSED');self.assertEqual(len(result['campaign_ids']),1)

    def test_request_shape_and_group_order(self):
        r,s,a,assets,_=fixture();r.pop('_resolved_assets');r['budget_from_reference']=False
        r['campaign_groups']=[{'files':[x['canonical_filename'] for x in reversed(assets)],'primary_text':r['primary_text'],'product_label':'EXACT'}]
        driver.validate_request(r)
        r['_resolved_assets']=assets
        out=general.build(r,s,1,a)['campaigns'][0]
        self.assertEqual(out['ads'][0]['media']['asset_id'],assets[-1]['asset_id'])

    def test_binding_language_pixel_tracking_and_authority_fail_closed(self):
        for delta in ['source_id','source_account','partition','language','pixel','number','duplicate_query','authority','native_copy']:
            r,s,a,_,_=fixture()
            if delta=='source_id':r['source_campaign_id']='99999'
            if delta=='source_account':s['campaign']['account_id']='99999'
            if delta=='partition':a['shein_reference_profile']['manager_code']='G006'
            if delta=='language':a['shein_reference_profile']['language']='ES'
            if delta=='pixel':s['adset']['promoted_object']['pixel_id']='wrong'
            if delta=='number':a['shein_profile']['reference_target_token']='b01fb02c02'
            if delta=='duplicate_query':r['website_url']+='&utm_campaign=b01fb02c01'
            if delta=='authority':r['authorized_by']='1055570806945620030'
            if delta=='native_copy':r['mode']='clone_prestaged'
            with self.subTest(delta=delta),self.assertRaises(ValueError):general.build(r,s,1,a)

    def test_capability_and_non_shein_scope_cannot_bypass_schema(self):
        r,s,a,_,cfg=fixture();p=general.build(r,s,1,a)
        cfg['shein_cross_account_reference']['enabled']=False
        with self.assertRaises(ManifestError):validate_account_policy(Manifest.from_dict(p),cfg)
        p['operation']='Eggbev-US-CC-EN-BOT'
        with self.assertRaises(ManifestError):Manifest.from_dict(p)
        p['operation']='SHEIN-US-DIRECT';p['campaigns'][0].pop('reference')
        with self.assertRaises(ManifestError):Manifest.from_dict(p)

    def test_empty_target_number_and_conflicting_literal_not_recycled(self):
        r,_,_,_,_=fixture()
        self.assertEqual(driver.reconcile_number(r,[],None,None),1)
        self.assertEqual(driver.reconcile_number(r,[{'name':'001 - EXISTS','status':'PAUSED'}],None,None),2)
        with self.assertRaises(ValueError):
            r,s,a,_,_=fixture();general.build(r,s,2,a)

    def test_readback_failure_resumes_ids_without_replaying_writes(self):
        class FailOnce(FakeBatchTransport):
            failed=False
            def execute(self, operations, stage):
                if stage=='consolidated_readback' and not self.failed:
                    self.failed=True;raise RuntimeError('offline injected readback failure')
                return super().execute(operations,stage)
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);r,s,a,assets,cfg=fixture();cfg.update(state_root=str(root/'state'),audit_root=str(root/'audit'))
            m=sealed(root,r,s,a,assets,cfg);t=FailOnce(a['shein_profile']['account_id']);e=CampaignEngine(cfg,transport_factory=lambda aid:t)
            with self.assertRaises(RuntimeError):e.execute(m)
            before=list(t.calls); result=e.execute(m)
            self.assertEqual(result['status'],'COMPLETE_PAUSED');self.assertEqual([x['stage'] for x in t.calls[len(before):]],['recovery_consolidated_readback'])
            checkpoint=json.loads(next((root/'state'/'checkpoints').glob('*.json')).read_text())
            self.assertEqual(len(checkpoint['bundles'][0]['ad_ids']),2)

    def test_offline_plan_and_execute_use_only_target_edges_plus_ad_provenance(self):
        class Capture(FakeBatchTransport):
            def __init__(self, aid):super().__init__(aid);self.ops=[]
            def execute(self, operations, stage):self.ops.extend(operations);return super().execute(operations,stage)
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);r,s,a,assets,cfg=fixture();cfg.update(state_root=str(root/'state'),audit_root=str(root/'audit'))
            m=sealed(root,r,s,a,assets,cfg);t=Capture(a['shein_profile']['account_id']);e=CampaignEngine(cfg,transport_factory=lambda aid:t)
            plan=e.planner.build(m)
            planned=[o for b in plan.lanes[a['shein_profile']['account_id']] for stage in b.stages for o in stage.operations]
            self.assertTrue(all(o.body.get('source_ad_id')==s['ads'][0]['id'] for o in planned if o.kind=='ad_create'))
            e.execute(m)
            self.assertFalse(any('/copies' in o.relative_url for o in t.ops))
            self.assertTrue(all(o.relative_url.startswith('act_'+a['shein_profile']['account_id']+'/') for o in t.ops if o.kind in {'campaign_create','adset_create','ad_create','creative_create'}))

    def test_now_and_budget_clock_are_not_reset(self):
        r,s,_,_,_=fixture();r['start_now']=True;r.pop('start_time');r.pop('budget_usd');r['budget_from_reference']=True
        r['source_message_id']='1560010597385506986'
        r.pop('_resolved_assets')
        received,basis=driver.request_clock(r);resolved=driver.resolve_intent(r,s)
        self.assertEqual(resolved['source_message_id'],r['source_message_id']);self.assertLess(received,driver.aware_time(resolved['start_time']))
        self.assertIn('Discord',basis);self.assertEqual(resolved['budget_usd'],'40')

    def test_partial_ad_create_recovers_only_missing_slot(self):
        class Partial(FakeBatchTransport):
            failed=False
            def __init__(self, aid):
                super().__init__(aid);self.ops=[];self.effects={k:[] for k in ['campaign_create','adset_create','creative_create','ad_create']}
            def apply(self, operations, stage):
                results=super().execute(operations,stage)
                for op,result in zip(operations,results):
                    if op.kind in self.effects:
                        effect={**copy.deepcopy(op.body),'id':result.body['id']}
                        if op.kind=='ad_create':effect['creative']={'id':op.body['creative']['creative_id']}
                        self.effects[op.kind].append(effect)
                return results
            def execute(self, operations, stage):
                if stage=='ad_create' and not self.failed:
                    self.failed=True;self.ops.extend(operations[:1]);self.apply(operations[:1],stage)
                    raise RuntimeError('offline crash after first ad effect')
                self.ops.extend(operations)
                kind={'recovery_campaign_inventory':'campaign_create','recovery_adset_inventory':'adset_create','recovery_ad_inventory':'ad_create','recovery_creative_inventory':'creative_create'}.get(stage)
                if kind:
                    self.calls.append({'stage':stage,'operations':len(operations)})
                    return [BatchResult(o.name,200,{'data':copy.deepcopy(self.effects[kind])}) for o in operations]
                return self.apply(operations,stage)
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);r,s,a,assets,cfg=fixture();cfg.update(state_root=str(root/'state'),audit_root=str(root/'audit'))
            m=sealed(root,r,s,a,assets,cfg);t=Partial(a['shein_profile']['account_id']);e=CampaignEngine(cfg,transport_factory=lambda aid:t)
            with self.assertRaises(RuntimeError):e.execute(m)
            before=len(t.ops);result=e.execute(m);new=t.ops[before:]
            self.assertEqual(result['status'],'COMPLETE_PAUSED')
            self.assertEqual(len([o for o in new if o.kind=='ad_create']),1)
            self.assertFalse(any(o.kind in {'campaign_create','adset_create','creative_create'} for o in new))
            self.assertEqual(len([o for o in t.ops if o.kind=='ad_create']),2)

    def test_read_only_reference_preflight_never_loads_or_reserves_media(self):
        r,s,a,assets,cfg=fixture();tp=copy.deepcopy(a['shein_profile']);sp=a['shein_reference_profile'];tp['reference_profile']=sp
        def batch(common, token, queries):
            result={}
            for q in queries:
                name=q['name']
                if name in {'account','reference_account'}:
                    p=tp if name=='account' else sp
                    result[name]={'id':'act_'+p['account_id'],'name':p['account_name'],'currency':'USD','timezone_name':p['timezone'],'account_status':1,'disable_reason':0,'user_tasks':['ADVERTISE','ANALYZE']}
                elif name=='identity':result[name]={'id':driver.SYSTEM_USER_ID,'client_business_id':driver.BUSINESS_ID}
                elif name=='campaigns':result[name]={'data':[]}
                elif name=='campaign':result[name]=copy.deepcopy(s['campaign'])
                elif name=='adsets':result[name]={'data':[copy.deepcopy(s['adset'])]}
                elif name=='ads':result[name]={'data':copy.deepcopy(s['ads'])}
                elif name=='page':result[name]={'id':sp['page_id'],'name':'REFERENCE PAGE','access_token':'offline-test-only-not-real'}
                elif name=='reference_page':result[name]={'id':sp['page_id']}
                elif name in {'assignment','reference_assignment'}:result[name]={'data':[{'id':driver.SYSTEM_USER_ID,'tasks':['ADVERTISE']}]}
                elif name in {'pixels','reference_pixels'}:result[name]={'data':[{'id':sp['pixel_id']}]}
                else:result[name]={'id':name,'status':'ready','title':'offline source'}
            return result
        marker=driver.CURRENT_PROFILE.set(tp)
        try:
            with patch.object(driver,'_batch',side_effect=batch),patch('ares_campaign_v3.shein_media_handoff.load_ready_assets') as load:
                result,_=driver._prepare(r,cfg,None,None,reference_only=True)
                load.assert_not_called();self.assertNotIn('manifest',result)
                self.assertEqual(result['campaign_writes'],0);self.assertEqual(result['number'],1)
                self.assertEqual(result['source']['campaign']['account_id'],sp['account_id'])
        finally:driver.CURRENT_PROFILE.reset(marker)

    def test_disabled_capability_blocks_before_any_preflight_or_media(self):
        r,s,a,_,cfg=fixture();p=copy.deepcopy(a['shein_profile']);p['reference_profile']=a['shein_reference_profile'];cfg['shein_cross_account_reference']['enabled']=False
        marker=driver.CURRENT_PROFILE.set(p)
        try:
            with patch.object(driver,'_batch') as batch,self.assertRaises(ValueError):driver._prepare(r,cfg,None,None,reference_only=True)
            batch.assert_not_called()
        finally:driver.CURRENT_PROFILE.reset(marker)

    def test_reference_event_and_full_config_required_before_upload(self):
        for field in ['targeting','attribution_spec','event']:
            r,s,a,_,_=fixture()
            if field=='event':s['adset']['promoted_object']['custom_event_type']='PURCHASE'
            else:s['adset'].pop(field)
            with self.assertRaises(ValueError):ref.require_binding(r,s,a['shein_profile'],a['shein_reference_profile'])

if __name__=='__main__':unittest.main()
