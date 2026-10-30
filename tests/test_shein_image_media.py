"""IMG/VID capability tests; synthetic API objects are never live inputs."""
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_shein_general_runtime import case
from ares_campaign_v3 import shein_general, shein_grouped_media, shein_single_clone, shein_qa
from ares_campaign_v3.media_registry import MediaRegistry, MediaNotReady
from ares_campaign_v3.schema import Manifest, ManifestError
from ares_campaign_v3.prevalidation import prevalidate_payload
from ares_campaign_v3.engine import CampaignEngine
from ares_campaign_v3.transport import FakeBatchTransport

class ImageTests(unittest.TestCase):
    def fixture(self):
        r,s,a,assets=case(5,'ES','clone_prestaged')
        r['quantity']=1
        for i,x in enumerate(assets):
            x.pop('vertical_video_id'); x.pop('thumbnail_url')
            x.update(media_type='image',image_hash=f'{i+1:032x}',upload_edge='ad_account_adimages',canonical_filename=f'SHEIN_US_ES_IMG_TEST_NV_{i+1:03d}.png')
        r['campaign_groups']=[{'files':[x['canonical_filename'] for x in assets], 'product_label':'LITERAL', 'primary_text':'👜 EXACTO\n✅ SIN COSTOS.'}]
        return r,s,a,assets

    def test_real_request_intake_accepts_exact_16_images(self):
        r=json.loads(Path('/root/mgs-agent/data/ares/meta-ads/audit/shein/campaigns/intake/shein-1565747351543480374/request.json').read_text())
        before=copy.deepcopy(r)
        self.assertEqual(len(shein_grouped_media.validate_groups(r)),16)
        shein_single_clone.validate_request(r)
        self.assertEqual(r,before)

    def test_images_compile_schema_registry_and_core_plan_without_network(self):
        r,s,a,assets=self.fixture(); before=copy.deepcopy(s)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); registry=MediaRegistry(root/'registry.json')
            for x in assets:registry.register_image(account_id=a['shein_profile']['account_id'],asset_id=x['asset_id'],checksum=x['checksum'],image_hash=x['image_hash'],ready=True,association_verified=True)
            payload=shein_general.build(r,s,114,a)
            for ad in payload['campaigns'][0]['ads']:
                cp=ad['creative_payload'];ld=cp['object_story_spec']['link_data']
                self.assertEqual(ld['message'],r['campaign_groups'][0]['primary_text'])
                self.assertNotIn('video_data',cp['object_story_spec']);self.assertNotIn('media_sourcing_spec',cp)
                self.assertEqual(ld['link'],ld['call_to_action']['value']['link'])
            sealed=prevalidate_payload(payload,registry)
            cfg={'enabled':True,'write_enabled':True,'accounts':{a['shein_profile']['account_id']:a},'state_root':str(root/'state'),'audit_root':str(root/'audit')}
            eng=CampaignEngine(cfg,transport_factory=lambda _: self.fail('plan invoked transport'))
            plan=eng.dry_run(Manifest.from_dict(sealed))
            self.assertEqual(plan['network_calls'],0);self.assertEqual(plan['writes'],0)
            eng=CampaignEngine(cfg,transport_factory=FakeBatchTransport)
            self.assertEqual(eng.execute(Manifest.from_dict(sealed))['status'],'COMPLETE_PAUSED')
        self.assertEqual(s,before)

    def test_mixed_image_video_groups_preserve_order_and_types(self):
        r,s,a,images=self.fixture();_,_,_,videos=case(5,'ES','clone_prestaged')
        for x in videos:x['asset_id']='vid-'+x['asset_id']
        r['quantity']=2;r['campaign_groups'].append({'files':[x['canonical_filename'] for x in videos],'product_label':'VIDEO','primary_text':'VIDEO LITERAL'})
        r['_resolved_assets']=images+videos
        payload=shein_general.build(r,s,114,a)
        self.assertEqual([len(c['ads']) for c in payload['campaigns']],[3,3])
        self.assertTrue(all('link_data' in ad['creative_payload']['object_story_spec'] for ad in payload['campaigns'][0]['ads']))
        self.assertTrue(all('video_data' in ad['creative_payload']['object_story_spec'] for ad in payload['campaigns'][1]['ads']))
        self.assertEqual(len(Manifest.from_dict(payload).campaigns),2)

    def test_filename_negatives(self):
        r,*_=self.fixture()
        for bad in ['../SHEIN_US_ES_IMG_TEST_NV_001.png','SHEIN_US_ES_IMG_TEST_NV_001.mp4','SHEIN_US_ES_VID_TEST_NV_001.jpg','SHEIN_US_ES_IMG_TEST_NS_001.jpg','SHEIN_US_ES_IMG_TEST_NV_000.jpg','SHEIN_US_ES_IMG_TEST_NV_001.webp']:
            t=copy.deepcopy(r);t['campaign_groups'][0]['files'][0]=bad
            with self.subTest(filename=bad),self.assertRaises(ValueError):shein_grouped_media.validate_groups(t)

    def test_schema_rejects_media_disguise_and_mixed_ids(self):
        r,s,a,assets=self.fixture(); payload=shein_general.build(r,s,114,a)
        for change in ['edge','mixed','missing','type']:
            t=copy.deepcopy(payload);m=t['campaigns'][0]['ads'][0]['media']
            if change=='edge':m['upload_edge']='ad_account_advideos'
            if change=='mixed':m['vertical_video_id']='fake-video'
            if change=='missing':m['image_hash']=''
            if change=='type':m['media_type']='unknown'
            with self.subTest(change=change),self.assertRaises(ManifestError):Manifest.from_dict(t)

    def test_registry_type_isolation_and_drift(self):
        r,s,a,assets=self.fixture();x=assets[0];aid=a['shein_profile']['account_id']
        with tempfile.TemporaryDirectory() as d:
            reg=MediaRegistry(Path(d)/'registry.json')
            reg.register_image(account_id=aid,asset_id=x['asset_id'],checksum=x['checksum'],image_hash=x['image_hash'],ready=True,association_verified=True)
            with self.assertRaises(MediaNotReady):reg.require_ready(aid,x['asset_id'],x['checksum'])
            self.assertEqual(reg.require_ready(aid,x['asset_id'],x['checksum'],media_type='image')['image_hash'],x['image_hash'])
            payload=shein_general.build(r,s,114,a)
            payload['campaigns'][0]['ads']=payload['campaigns'][0]['ads'][:1]
            payload['campaigns'][0]['ads'][0]['media']['image_hash']='f'*32
            with self.assertRaises(ManifestError):prevalidate_payload(payload,reg)

class ImagePrestageTests(unittest.TestCase):
    def setUp(self):
        from PIL import Image
        from ares_campaign_v3 import image_prestage as ip
        self.ip=ip;self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);p=self.root/'SHEIN_US_ES_IMG_TEST_NV_001.png'
        Image.new('RGB',(200,300),'red').save(p)
        self.a={'asset_id':'offline-image','checksum':hashlib.sha256(p.read_bytes()).hexdigest(),'canonical_filename':p.name,'vertical_file':str(p)}
        self.reg=MediaRegistry(self.root/'registry.json');self.u=Mock();self.rows=[]
        def inventory(hashes=None):return [dict(x) for x in self.rows if hashes is None or x['hash'] in hashes]
        def upload(path,name):
            h='a'*32;self.rows.append({'hash':h,'name':name,'original_width':200,'original_height':300,'status':'ACTIVE'});return h
        self.u.inventory.side_effect=inventory;self.u.upload.side_effect=upload
    def run_prestage(self):
        return self.ip.prestage_images([self.a],account_id='123456789',registry=self.reg,uploader=self.u,proof_dir=self.root/'proof',atomic_json=shein_single_clone.atomic_json)
    def test_upload_readback_registry_and_idempotent_replay(self):
        self.assertEqual(self.run_prestage()['assets'][0]['registry']['image_hash'],'a'*32)
        self.assertEqual(self.run_prestage()['registry_hits'],1);self.u.upload.assert_called_once()
    def test_existing_name_recovery_has_zero_upload(self):
        self.rows.append({'hash':'b'*32,'name':self.ip.image_title(self.a['asset_id'],self.a['checksum'],self.a['canonical_filename']),'original_width':200,'original_height':300})
        self.assertEqual(self.run_prestage()['assets'][0]['registry']['image_hash'],'b'*32);self.u.upload.assert_not_called()
    def test_ambiguous_write_never_replayed(self):
        self.u.upload.side_effect=self.ip.MediaUploadError('synthetic timeout')
        with self.assertRaises(self.ip.MediaUploadError):self.run_prestage()
        with self.assertRaisesRegex(MediaNotReady,'no blind replay'):self.run_prestage()
        self.u.upload.assert_called_once()
    def test_upload_response_lost_reconciles_name(self):
        upload=self.u.upload.side_effect
        def lost(path,name):upload(path,name);raise self.ip.MediaUploadError('synthetic lost response')
        self.u.upload.side_effect=lost
        with self.assertRaises(self.ip.MediaUploadError):self.run_prestage()
        self.assertTrue(self.run_prestage()['assets'][0]['registry']['ready']);self.u.upload.assert_called_once()
    def test_bad_bytes_rejected_before_any_api(self):
        Path(self.a['vertical_file']).write_bytes(b'not an image')
        with self.assertRaises(MediaNotReady):self.run_prestage()
        self.u.inventory.assert_not_called();self.u.upload.assert_not_called()
    def test_wrong_hash_name_dimensions_status_fail_closed(self):
        for delta in [{'hash':'bad'},{'name':'wrong'},{'original_width':0},{'status':'DELETED'}]:
            row={'hash':'a'*32,'name':'correct','original_width':200,'original_height':300,'status':'ACTIVE',**delta}
            with self.subTest(delta=delta),self.assertRaises(MediaNotReady):self.ip.require_image([row],'a'*32,name='correct')
    def test_pagination_complete_and_loop_rejected(self):
        c=Mock();c.graph_get.side_effect=[(200,{'data':[],'paging':{'next':'not-persisted','cursors':{'after':'a'}}},{}),(200,{'data':[{'hash':'a'*32}]},{})]
        self.assertEqual(len(self.ip.read_account_images(c,'OFFLINE','123456789')),1)
        c.graph_get.side_effect=None;c.graph_get.return_value=(200,{'data':[],'paging':{'next':'not-persisted','cursors':{'after':'a'}}},{})
        with self.assertRaisesRegex(MediaNotReady,'pagination'):self.ip.read_account_images(c,'OFFLINE','123456789')
    def test_upload_transport_enforces_exact_account_and_no_retry(self):
        c=Mock();u=self.ip.AdAccountImageUploader(common=c,user_token='OFFLINE',account_id='123456789')
        response=Mock(status_code=200,headers={});response.json.return_value={'images':{'file.png':{'hash':'a'*32}}}
        with patch.object(self.ip.requests,'post',return_value=response) as post:
            self.assertEqual(u.upload(self.a['vertical_file'],'offline.png'),'a'*32)
            self.assertEqual(post.call_count,1)
            self.assertTrue(post.call_args.args[0].endswith('/act_123456789/adimages'))
            self.assertEqual(post.call_args.kwargs['files']['filename'][0],'offline.png')
        c._enforce_operational_account_scope.assert_called_once_with('act_123456789/adimages',{},'POST')
        response.status_code=500;response.json.return_value={'error':{'code':2}}
        with patch.object(self.ip.requests,'post',return_value=response) as post,self.assertRaises(self.ip.MediaUploadError):u.upload(self.a['vertical_file'],'offline.png')
        self.assertEqual(post.call_count,1)

class ImageQATests(unittest.TestCase):
    fixture=ImageTests.fixture
    def tree(self):
        r,s,a,assets=self.fixture();payload=shein_general.build(r,s,114,a);desired=payload['campaigns'][0]
        ads=[]
        for i,slot in enumerate(desired['ads']):
            ads.append({'id':f'ad-{i}','name':slot['name'],'status':'PAUSED','source_ad_id':slot['source_ad_id'],'adset_id':'target-set','creative':{'id':f'cr-{i}','effective_object_story_id':a['shein_profile']['page_id']+f'_new-{i}',**copy.deepcopy(slot['creative_payload'])}})
        return r,s,a,assets,desired,{'campaign':{'id':'target'},'adsets':{'data':[{'id':'target-set'}]},'ads':{'data':ads}}
    def test_image_preview_does_not_inherit_source_video_requirement(self):
        _,s,_,_,d,live=self.tree();c=Mock()
        def batch(token,queries):
            return 200,[{'name':q['name'],'code':200,'body':{'data':[{'body':'<iframe src="https://business.facebook.com/ads/api/preview_iframe.php?offline=1"></iframe>'}]}} for q in queries],{}
        c.graph_batch_get.side_effect=batch
        with patch.object(shein_qa,'render_previews',return_value=[{'images':[{'width':200,'height':300}]} for _ in d['ads']]) as render:
            proof=shein_qa.verify_media(c,'OFFLINE',live,d,s,{'enabled':True,'chrome_path':'offline'})
        self.assertTrue(proof['verified']);self.assertEqual(render.call_args.kwargs['expect_video'],[False]*3)
        self.assertEqual(shein_single_clone.verify_media_ads(d,s,live,[]),[])
    def test_wrong_image_hash_blocks_semantic_and_preview_qa_before_network(self):
        _,s,_,_,d,live=self.tree();live['ads']['data'][0]['creative']['object_story_spec']['link_data']['image_hash']='f'*32;c=Mock()
        from ares_campaign_v3.creative_media import matches
        self.assertFalse(matches(live['ads']['data'][0]['creative'],d['ads'][0]['creative_payload']))
        with self.assertRaises(ValueError):shein_single_clone.verify_media_ads(d,s,live,[])
        with self.assertRaises(ValueError):shein_qa.verify_media(c,'OFFLINE',live,d,s,{'enabled':True})
        c.graph_batch_get.assert_not_called()
    def test_empty_preview_rejects_activation(self):
        with self.assertRaises(ValueError):shein_qa.validate_rendered({'images':[],'videos':[]},False)
    def test_image_manifest_not_allowed_for_other_operation(self):
        r,s,a,_=self.fixture();p=shein_general.build(r,s,114,a);p['operation']='OTHER'
        with self.assertRaises(ManifestError):Manifest.from_dict(p)

class ImageHandoffTests(unittest.TestCase):
    fixture=ImageTests.fixture
    def test_prepare_handoff_finalize_preserves_folder_and_lineage(self):
        from PIL import Image
        from ares_campaign_v3 import image_prestage as ip, shein_media_handoff as handoff
        import ares_archive_locations as locations
        import ares_archive_storage as storage
        r,s,a,assets=self.fixture();r.pop('_resolved_assets');r['manager_media_folder_id']='offline-manager-123'
        aid=a['shein_profile']['account_id'];profile=a['shein_profile'];manager={'id':r['manager_media_folder_id'],'name':'Nicolas','parents':['stock-root']}
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);media_dir=root/'media';media_dir.mkdir();inv=root/'data/ares/creative-ops/inventory/assets.jsonl';inv.parent.mkdir(parents=True)
            rows=[];files={};library=[]
            for i,x in enumerate(assets):
                p=media_dir/x['canonical_filename'];Image.new('RGB',(200,300),(i*60,20,30)).save(p);raw=p.read_bytes();sha=hashlib.sha256(raw).hexdigest();md5=hashlib.md5(raw).hexdigest()
                row={'asset_id':x['asset_id'],'canonical_filename':p.name,'language':'ES','vertical':'SHEIN','format':'IMG','metadata_clean':True,'clean_checksum':sha,'clean_md5':md5,'asset_drive_id':'file-'+str(i),'status':'01_READY','used_by':'preserved-history' if i==0 else None}
                rows.append(row);files[row['asset_drive_id']]={'id':row['asset_drive_id'],'name':p.name,'parents':[manager['id']],'size':len(raw),'md5Checksum':md5}
            inv.write_text(''.join(json.dumps(row)+'\n' for row in rows))
            cfg=root/'data/ares/meta-ads/engine-v3/config.json';cfg.parent.mkdir(parents=True);cfg.write_text(json.dumps({'media_upload_enabled':True,'accounts':{aid:{**a,'token_item':'OFFLINE'}}}))
            op=root/'data/ares/meta-ads/operations/SHEIN-US-DIRECT.json';op.parent.mkdir(parents=True);op.write_text(json.dumps({'channel_authorization_policy':{}}))
            ops=Mock();ops.drive_runtime_token.return_value=('OFFLINE',None);ops.drive_file_readback.side_effect=lambda token,fid:manager if fid==manager['id'] else files[fid]
            def save_rows(current):inv.write_text(''.join(json.dumps(row)+'\n' for row in current))
            ops.atomic_inventory.side_effect=save_rows
            common=Mock();common.get_token_from_1password.return_value=('OFFLINE',None);common.graph_get.return_value=(200,{'name':profile['account_name'],'currency':'USD','timezone_name':profile['timezone'],'account_status':1,'disable_reason':0,'user_tasks':['ADVERTISE']},{})
            uploader=Mock();uploader.inventory.side_effect=lambda hashes=None:[dict(x) for x in library if hashes is None or x['hash'] in hashes]
            def upload(path,name):
                h=f'{len(library)+1:032x}';library.append({'hash':h,'name':name,'original_width':200,'original_height':300,'status':'ACTIVE'});return h
            uploader.upload.side_effect=upload
            with patch.object(shein_single_clone,'lookup_account',return_value={'account_id':aid}),patch.object(shein_single_clone,'_load_common',return_value=common),patch.object(shein_general,'authorize'),patch.object(shein_grouped_media,'manager_folder',return_value=manager),patch.object(handoff,'_ops',return_value=ops),patch.object(locations,'stock_scope_for_token',return_value=True),patch.object(storage,'require_lineage_available',return_value=True),patch.object(shein_grouped_media.subprocess,'run',return_value=Mock(returncode=0,stdout='clean: true\n')),patch.object(ip,'AdAccountImageUploader',return_value=uploader):
                ready=shein_grouped_media.prepare(r,base=root,work_dir=media_dir)
                shein_grouped_media.prepare(r,base=root,work_dir=media_dir)
                self.assertEqual(uploader.upload.call_count,3)
                self.assertEqual(len(ready['asset_refs']),3)
                def meta(path,token,params):
                    self.assertEqual(path,'act_'+aid+'/adimages');return 200,{'data':library},{}
                common.graph_get.side_effect=meta
                resolved=handoff.load_ready_assets(ready,profile,root,common,'OFFLINE')
                compiled=shein_general.build({**r,'_resolved_assets':resolved},s,114,a)
                _,_,_,_,desired,tree=ImageQATests().tree()
                # Rebind synthetic live creatives to the freshly resolved registry identities.
                for ad,slot in zip(tree['ads']['data'],compiled['campaigns'][0]['ads']):ad['creative'].update(copy.deepcopy(slot['creative_payload']))
                state={'request':r,'manifest':compiled,'new_media_assets':resolved}
                assigned=handoff.finalize_ready_assets(state,tree,root,common,'OFFLINE')
                handoff.finalize_ready_assets(state,tree,root,common,'OFFLINE')
                after=[json.loads(line) for line in inv.read_text().splitlines()]
                self.assertEqual({row['asset_id'] for row in after},set(assigned))
                self.assertTrue(all(row['status']=='02_TESTING' and len(row['test_history'])==1 and row['meta_image_hash'] for row in after))
                self.assertEqual(after[0]['reservation_history'][0]['previous_used_by'],'preserved-history')
                ops.move_asset_to_testing.assert_not_called()
                # A later binary change cannot pass handoff merely because the filename survived.
                files['file-0']['md5Checksum']='changed'
                with self.assertRaisesRegex(ValueError,'checksum changed'):handoff.load_ready_assets(ready,profile,root,common,'OFFLINE')

class ImageRendererActivationTests(unittest.TestCase):
    fixture=ImageTests.fixture
    def test_real_chromium_renders_static_image_and_rejects_wrong_kind(self):
        import functools,threading
        from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
        from PIL import Image
        from ares_campaign_v3.preview_renderer import render_previews
        chrome='/root/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome'
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);Image.new('RGB',(200,300),'blue').save(root/'image.png');(root/'index.html').write_text('<img src="/image.png" width="200" height="300">')
            class Silent(SimpleHTTPRequestHandler):
                def log_message(self,*args):pass
            server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Silent,directory=d));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                row=render_previews([f'http://127.0.0.1:{server.server_port}/index.html'],chrome_path=chrome,timeout=8,allow_local=True,expect_video=[False])[0]
                shein_qa.validate_rendered(row,False,expect_image=True)
                self.assertEqual(row['images'][0],{'width':200,'height':300})
                with self.assertRaises(ValueError):shein_qa.validate_rendered({'videos':[{'readyState':4,'duration':3,'width':200,'height':300}],'images':[{'width':200,'height':300}]},False,expect_image=True)
            finally:server.shutdown();server.server_close();thread.join(timeout=5)
    def test_image_activation_uses_existing_status_only_barrier_and_rejects_hash_drift(self):
        from test_shein_batch_barrier_activation import OfflineActivationTransport
        r,s,a,assets=self.fixture();r['status']='ACTIVE';aid=a['shein_profile']['account_id']
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);reg=MediaRegistry(root/'media.json')
            for x in assets:reg.register_image(account_id=aid,asset_id=x['asset_id'],checksum=x['checksum'],image_hash=x['image_hash'],ready=True,association_verified=True)
            raw=shein_general.build(r,s,114,a);target=Manifest.from_dict(prevalidate_payload(raw,reg));paused=copy.deepcopy(raw);paused['campaigns'][0]['status']='PAUSED';creation=Manifest.from_dict(prevalidate_payload(paused,reg))
            cfg={'enabled':True,'write_enabled':True,'require_prevalidated_manifest':True,'accounts':{aid:a},'state_root':str(root/'state'),'audit_root':str(root/'audit'),'shein_media_qa':{'enabled':True}}
            made=CampaignEngine(cfg,transport_factory=FakeBatchTransport).execute(creation);spec=creation.campaigns[0];cid=made['campaign_ids'][0]
            _,_,_,_,_,tree=ImageQATests().tree();tree['campaign'].update(id=cid,account_id=aid,name=spec.name,status='PAUSED',configured_status='PAUSED',daily_budget='3000',bid_strategy='LOWEST_COST_WITHOUT_CAP',start_time=spec.start_time)
            tree['adsets']['data'][0].update(name=spec.adset_name,status='PAUSED',configured_status='PAUSED',start_time=spec.start_time)
            proof={'verified':True,'request_id':target.request_id,'creation_digest':creation.digest,'target_digest':target.digest,'trees':[copy.deepcopy(tree)],'media_qa':{cid:{'verified':True,'ad_ids':[x['id'] for x in tree['ads']['data']],'creative_ids':[x['creative']['id'] for x in tree['ads']['data']]}}}
            transport=OfflineActivationTransport([tree]);engine=CampaignEngine(cfg,transport_factory=lambda _:transport)
            tree['ads']['data'][0]['creative']['object_story_spec']['link_data']['image_hash']='f'*32
            with self.assertRaises(ValueError):engine.activate_verified(target,creation,proof)
            self.assertEqual(transport.posts,[])
            tree['ads']['data'][0]['creative']['object_story_spec']['link_data']['image_hash']=assets[0]['image_hash']
            self.assertEqual(engine.activate_verified(target,creation,proof)['status'],'COMPLETE_FUTURE_ACTIVE')
            self.assertTrue(all(body=={'status':'ACTIVE'} for _,body in transport.posts));self.assertEqual(len(transport.posts),5)

if __name__=='__main__':unittest.main()
