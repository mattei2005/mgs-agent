"""Source selection/comparison regression. Local receipts or memory only; no API."""
import copy
import importlib.util
import json
import socket
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path('/root/mgs-agent')
sys.path.insert(0,str(ROOT/'scripts'))
SPEC=importlib.util.spec_from_file_location('eggbev_source_selection_runner',ROOT/'scripts/ares-eggbev-target-clone.py')
assert SPEC is not None and SPEC.loader is not None
runner=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(runner)
HOME=ROOT/'data/ares/meta-ads/audit/eggbev/target-clone/eggbev-pg23187-1570285402068091011'


class SourceSelectionTests(unittest.TestCase):
    def setUp(self):
        self.network=patch.object(socket,'socket',side_effect=AssertionError('network forbidden in offline test'));self.network.start();self.addCleanup(self.network.stop)
        self.q=json.loads((HOME/'request.json').read_text())
        self.raw=json.loads((HOME/'read-only-preflight.json').read_text())['source']
        self.campaign={k:self.raw[k] for k in ['id','account_id','name','status']}
        self.sets=copy.deepcopy(self.raw['adsets']);self.ads=copy.deepcopy(self.raw['ads'])
        self.proof=runner.source_seed_proof(self.q)

    def classify(self,ads=None,proof=True,sets=None,count=3):
        return runner.classify_source(self.campaign,self.sets if sets is None else sets,self.ads if ads is None else ads,count,self.proof if proof else None)

    def test_exact_real_receipt_three_plus_three(self):
        result=self.classify();self.assertEqual([len(result[k]) for k in ['ads','all_ads','technical_seed_ads']],[3,6,3])
        self.assertEqual([x['id'] for x in result['ads']],[a for a,_ in self.proof['pairs']])
        self.assertEqual([x['id'] for x in result['technical_seed_ads']],[b for _,b in self.proof['pairs']])
        self.assertTrue(all(x['status']=='PAUSED' for x in result['technical_seed_ads']))
        self.assertEqual(result['all_ads'],self.ads)

    def test_no_in_place_mutation(self):
        old=copy.deepcopy((self.campaign,self.sets,self.ads,self.proof));result=self.classify()
        result['ads'][0]['name']='changed in returned copy'
        self.assertEqual((self.campaign,self.sets,self.ads,self.proof),old)

    def test_proof_survives_json_roundtrip(self):
        source=self.classify();self.assertEqual(runner.source_comparison(source),runner.source_comparison(json.loads(json.dumps(source))))

    def test_no_status_name_heuristic(self):
        with self.assertRaises(ValueError):self.classify(proof=False)

    def test_names_not_used_to_select(self):
        for ad in self.ads:ad['name']='arbitrary identical name'
        self.assertEqual([a['id'] for a in self.classify()['ads']],[a for a,_ in self.proof['pairs']])

    def test_unknown_extra_rejected(self):
        self.ads.append(dict(self.ads[0],id='9999999999999999'))
        with self.assertRaises(ValueError):self.classify()

    def test_missing_seed_rejected_even_when_count_matches(self):
        self.ads=[a for a in self.ads if a['id'] in {x for x,_ in self.proof['pairs']}]
        with self.assertRaises(ValueError):self.classify()

    def test_missing_final_rejected(self):
        self.ads=[a for a in self.ads if a['id']!=self.proof['pairs'][0][0]]
        with self.assertRaises(ValueError):self.classify()

    def test_duplicate_id_rejected(self):
        self.ads[-1]['id']=self.ads[0]['id']
        with self.assertRaises(ValueError):self.classify()

    def test_wrong_set_rejected(self):
        self.ads[0]['adset_id']='9999999'
        with self.assertRaises(ValueError):self.classify()

    def test_multiple_sets_rejected(self):
        with self.assertRaises(ValueError):self.classify(sets=self.sets+self.sets)

    def test_empty_sets_rejected(self):
        with self.assertRaises(ValueError):self.classify(sets=[])

    def test_activated_seed_rejected(self):
        next(a for a in self.ads if a['id']==self.proof['pairs'][0][1])['status']='ACTIVE'
        with self.assertRaises(ValueError):self.classify()

    def test_paused_final_rejected(self):
        next(a for a in self.ads if a['id']==self.proof['pairs'][0][0])['status']='PAUSED'
        with self.assertRaises(ValueError):self.classify()

    def test_deleted_seed_rejected(self):
        next(a for a in self.ads if a['id']==self.proof['pairs'][0][1])['status']='DELETED'
        with self.assertRaises(ValueError):self.classify()

    def test_wrong_lineage_rejected(self):
        self.ads[0]['source_ad_id']=self.proof['pairs'][0][0]
        with self.assertRaises(ValueError):self.classify()

    def test_crossed_lineage_rejected(self):
        next(a for a in self.ads if a['id']==self.proof['pairs'][0][0])['source_ad_id']=self.proof['pairs'][1][1]
        with self.assertRaises(ValueError):self.classify()

    def test_seed_with_nonzero_lineage_rejected(self):
        next(a for a in self.ads if a['id']==self.proof['pairs'][0][1])['source_ad_id']='9999'
        with self.assertRaises(ValueError):self.classify()

    def test_request_cardinality_rejected(self):
        with self.assertRaises(ValueError):self.classify(count=2)

    def test_plain_source_exact_count_preserved(self):
        selected=[a for a in self.ads if a['status']=='ACTIVE'];result=self.classify(ads=selected,proof=False)
        self.assertEqual(result['ads'],selected);self.assertEqual(result['all_ads'],selected);self.assertFalse(result['technical_seed_ads'])

    def test_source_read_requests_lineage_and_preserves_all_rows(self):
        case=self
        class Meta:
            def graph_get(self,path,token,params):
                case.assertEqual(path,case.q['source_campaign_id_candidate']);return 200,copy.deepcopy(case.campaign),{}
        class Common:
            def fetch_all_meta(self,meta,token,path,params):
                if path.endswith('/ads'):
                    case.assertIn('source_ad_id',params['fields']);return copy.deepcopy(case.ads)
                return copy.deepcopy(case.sets)
        result=runner.source_read(self.q,Common(),Meta(),'offline-only')
        self.assertEqual(result,self.classify())

    def test_wrong_source_identity_rejected(self):
        class Meta:
            def graph_get(self,*args):return 200,dict(self_campaign,id='999'),{}
        self_campaign=self.campaign
        with self.assertRaises(ValueError):runner.source_read(self.q,None,Meta(),'offline-only')

    def test_build_only_final_ids_never_seeds(self):
        source=self.classify();source['campaign'].update(objective='OUTCOME_SALES',buying_type='AUCTION',bid_strategy='LOWEST_COST_WITHOUT_CAP',special_ad_categories=[],special_ad_category_country=[])
        for ad in source['ads']:ad['creative']={'asset_feed_spec':{'call_to_action_types':['APPLY_NOW']},'url_tags':'utm_campaign=pg_23186'}
        class Registry:
            def require_ready(self,account,asset,checksum):
                return dict(asset_id=asset,checksum=checksum,vertical_video_id='91',square_video_id='92',ready=True,upload_edge='ad_account_advideos',association_verified=True)
        assets=[dict(asset_id=str(i),clean_checksum='a'*64,canonical_filename=f'CC_US_EN_VID_AVAILABLE_LIMIT_PV_{i:03d}.mp4') for i in range(1,4)]
        before=copy.deepcopy(source)
        with patch.object(runner,'_creative_payload',return_value={'url_tags':'placeholder'}):
            manifest=runner.build(self.q,source,dict(id='123',instagram_user_id='124',page_token='pg_23187'),assets,Registry(),{'names':['approved target']})
        self.assertEqual(len(manifest['campaigns'][0]['ads']),3)
        self.assertEqual([a['source_ad_id'] for a in manifest['campaigns'][0]['ads']],[a for a,_ in self.proof['pairs']])
        self.assertEqual(manifest['campaigns'][0]['mode'],'clone_target_prestaged');self.assertEqual(source,before)

    def proof_with_mutation(self,change):
        actual=runner.load
        def modified(path):
            value=copy.deepcopy(actual(path));change(str(path),value);return value
        with patch.object(runner,'load',side_effect=modified):return runner.source_seed_proof(self.q)

    def test_ambiguous_allocation_rejected(self):
        def change(path,value):
            if 'allocations' in value:value['allocations']['duplicate']=copy.deepcopy(next(v for v in value['allocations'].values() if self.campaign['id'] in v.get('campaign_ids',[])))
        with self.assertRaises(ValueError):self.proof_with_mutation(change)

    def test_uncommitted_allocation_rejected(self):
        def change(path,value):
            for v in value.get('allocations',{}).values():
                if self.campaign['id'] in v.get('campaign_ids',[]):v['status']='RESERVED'
        with self.assertRaises(ValueError):self.proof_with_mutation(change)

    def test_checkpoint_incomplete_rejected(self):
        def change(path,value):
            if 'checkpoints/' in path:value['status']='RECOVERY_PENDING'
        with self.assertRaises(ValueError):self.proof_with_mutation(change)

    def test_extra_checkpoint_slot_rejected(self):
        def change(path,value):
            if 'checkpoints/' in path:value['bundles'][0]['target_clone_ids']['seed_ad_id_1_4']='99999'
        with self.assertRaises(ValueError):self.proof_with_mutation(change)

    def test_duplicate_checkpoint_pairs_rejected(self):
        def change(path,value):
            if 'checkpoints/' in path:
                ids=value['bundles'][0]['target_clone_ids'];ids['seed_ad_id_1_2']=ids['seed_ad_id_1_1']
        with self.assertRaises(ValueError):self.proof_with_mutation(change)

    def test_wrong_completion_rejected(self):
        def change(path,value):
            if path.endswith('/final.json'):value['phase']='POSTPROCESS_PENDING'
        with self.assertRaises(ValueError):self.proof_with_mutation(change)

    def test_wrong_completion_assignments_rejected(self):
        def change(path,value):
            if path.endswith('/final.json'):value['assignments'][0]['ad_id']='999999'
        with self.assertRaises(ValueError):self.proof_with_mutation(change)

    def test_broken_manifest_seal_rejected(self):
        def change(path,value):
            if path.endswith('/manifest.json'):value['campaigns'][0]['mode']='from_zero_prestaged'
        with self.assertRaises(ValueError):self.proof_with_mutation(change)

    def test_no_allocation_never_allows_extra_rows(self):
        def change(path,value):
            if 'allocations' in value:value['allocations']={}
        self.assertIsNone(self.proof_with_mutation(change))
        with self.assertRaises(ValueError):self.classify(proof=False)


class SourceComparisonTests(unittest.TestCase):
    def setUp(self):
        self.snapshot={'campaign':{'daily_budget':'3500'},'adset':{'targeting':{'age_min':18}},'ads':[{'id':'1','status':'ACTIVE','source_ad_id':'2','creative':{'id':'3','url_tags':'utm_campaign=pg_23186','asset_feed_spec':{'bodies':[{'text':'literal copy'}],'videos':[{'video_id':'91','thumbnail_url':'https://scontent-lga3-2.xx.fbcdn.net/v/t15/example.jpg?oh=old&oe=old&_nc_sid=one&stp=size'}]}}}],'all_ads':[],'technical_seed_ads':[]}
    def test_signed_thumbnail_rotation_only(self):
        current=copy.deepcopy(self.snapshot);current['ads'][0]['creative']['asset_feed_spec']['videos'][0]['thumbnail_url']='https://scontent-lga3-1.xx.fbcdn.net/v/t15/example.jpg?_nc_sid=two&oe=new&oh=new&stp=size'
        self.assertNotEqual(current,self.snapshot);self.assertEqual(runner.source_comparison(current),runner.source_comparison(self.snapshot))
        self.assertIn('oh=old',self.snapshot['ads'][0]['creative']['asset_feed_spec']['videos'][0]['thumbnail_url'])
    def test_thumbnail_path_change_is_drift(self):
        current=copy.deepcopy(self.snapshot);current['ads'][0]['creative']['asset_feed_spec']['videos'][0]['thumbnail_url']='https://scontent-lga3-1.xx.fbcdn.net/v/t15/DIFFERENT.jpg?oh=new&stp=size'
        self.assertNotEqual(runner.source_comparison(current),runner.source_comparison(self.snapshot))
    def test_thumbnail_transform_change_is_drift(self):
        current=copy.deepcopy(self.snapshot);current['ads'][0]['creative']['asset_feed_spec']['videos'][0]['thumbnail_url']=current['ads'][0]['creative']['asset_feed_spec']['videos'][0]['thumbnail_url'].replace('stp=size','stp=DIFFERENT')
        self.assertNotEqual(runner.source_comparison(current),runner.source_comparison(self.snapshot))
    def test_other_host_not_normalized(self):
        before=copy.deepcopy(self.snapshot);before['ads'][0]['creative']['asset_feed_spec']['videos'][0]['thumbnail_url']='https://example.org/file.jpg?oh=old'
        after=copy.deepcopy(before);after['ads'][0]['creative']['asset_feed_spec']['videos'][0]['thumbnail_url']='https://example.org/file.jpg?oh=new'
        self.assertNotEqual(runner.source_comparison(before),runner.source_comparison(after))
    def test_all_commercial_drift_preserved(self):
        paths=[(['campaign','daily_budget'],'4500'),(['adset','targeting','age_min'],21),(['ads',0,'status'],'PAUSED'),(['ads',0,'source_ad_id'],'4'),(['ads',0,'creative','id'],'5'),(['ads',0,'creative','url_tags'],'utm_campaign=pg_999'),(['ads',0,'creative','asset_feed_spec','bodies',0,'text'],'changed copy'),(['ads',0,'creative','asset_feed_spec','videos',0,'video_id'],'92')]
        for path,value in paths:
            with self.subTest(path=path):
                current=copy.deepcopy(self.snapshot);node=current
                for part in path[:-1]:node=node[part]
                node[path[-1]]=value
                self.assertNotEqual(runner.source_comparison(current),runner.source_comparison(self.snapshot))
    def test_seed_drift_is_not_hidden(self):
        before=copy.deepcopy(self.snapshot);before['technical_seed_ads']=[{'id':'2','status':'PAUSED'}];after=copy.deepcopy(before);after['technical_seed_ads'][0]['status']='ACTIVE'
        self.assertNotEqual(runner.source_comparison(before),runner.source_comparison(after))
    def test_raw_edge_order_not_drift(self):
        before=copy.deepcopy(self.snapshot);before['all_ads']=[{'id':'2'},{'id':'1'}];after=copy.deepcopy(before);after['all_ads'].reverse()
        self.assertEqual(runner.source_comparison(before),runner.source_comparison(after))


if __name__=='__main__':unittest.main()
