"""Explicitly offline media-gate, renderer, recovery and snapshot regressions."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_shein_pipeline_hardening import flexible
from test_shein_general_runtime import case
from ares_campaign_v3 import shein_general as compiler
from ares_campaign_v3 import shein_single_clone as driver
from ares_campaign_v3 import shein_qa
from ares_campaign_v3.creative_media import matches
from ares_campaign_v3.engine import CampaignEngine
from ares_campaign_v3.prevalidation import prevalidate_payload
from ares_campaign_v3.media_registry import MediaRegistry
from ares_campaign_v3.schema import Manifest
from ares_campaign_v3.transport import FakeBatchTransport,BatchResult,BatchTransportError

CHROME='/root/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome'
PLAYABLE={'videos':[{'readyState':4,'duration':18,'width':720,'height':720,'error':None}],'images':[]}


class MediaQATests(unittest.TestCase):
    def fixture(self):
        r,s,a=flexible();desired=compiler.build(r,s,114,a)['campaigns'][0]
        cp=desired['ads'][0]['creative_payload'];cr=copy.deepcopy(cp);cr.update(id='created-creative',instagram_user_id='ig-source',effective_object_story_id=a['shein_profile']['page_id']+'_new')
        cr['asset_feed_spec']['videos'][0]['video_id']='derived-video'
        live={'ads':{'data':[{'id':'new-ad','source_ad_id':s['ads'][0]['id'],'creative':cr}]}}
        return s,desired,live

    def common(self,wrong_title=False):
        class Common:
            def __init__(self):self.reads=[]
            def graph_batch_get(self,token,requests):
                self.reads.extend(requests);rows=[]
                for q in requests:
                    if q['path'].endswith('/previews'):
                        body={'data':[{'body':'<iframe src="https://business.facebook.com/ads/api/preview_iframe.php?d=OFFLINE"></iframe>'}]}
                    else:body={'id':q['path'],'title':'wrong' if wrong_title and q['path']=='derived-video' else 'VIDEO','length':18,'status':{'video_status':'ready'}}
                    rows.append({'name':q['name'],'code':200,'body':body})
                return 200,rows,{}
        return Common()

    def test_legacy_link_only_target_is_rejected(self):
        s,d,l=self.fixture();l['ads']['data'][0]['creative'].pop('asset_feed_spec')
        with self.assertRaisesRegex(ValueError,'media/copy'):shein_qa.verify_media(self.common(),'OFFLINE',l,d,s,{'enabled':True,'chrome_path':CHROME})

    def test_full_media_passes_and_signed_preview_is_not_persisted(self):
        s,d,l=self.fixture();common=self.common()
        with patch.object(shein_qa,'render_previews',return_value=[PLAYABLE]):proof=shein_qa.verify_media(common,'OFFLINE',l,d,s,{'enabled':True,'chrome_path':CHROME})
        self.assertTrue(proof['verified']);self.assertNotIn('iframe',json.dumps(proof));self.assertNotIn('?d=',json.dumps(proof))
        self.assertEqual(len([q for q in common.reads if q['path']=='derived-video']),1)

    def test_source_metadata_snapshot_avoids_repeated_source_get(self):
        s,d,l=self.fixture();s['video_metadata']={'video-source':{'id':'video-source','title':'VIDEO','length':18,'status':{'video_status':'ready'}}};common=self.common()
        with patch.object(shein_qa,'render_previews',return_value=[PLAYABLE]):shein_qa.verify_media(common,'OFFLINE',l,d,s,{'enabled':True,'chrome_path':CHROME})
        self.assertNotIn('video-source',[q['path'] for q in common.reads])

    def test_video_thumbnail_without_loaded_video_fails(self):
        for row in [{'videos':[],'images':[{'width':720,'height':720}]},{'videos':[{'readyState':0,'duration':18,'width':720,'height':720}]}]:
            with self.subTest(row=row),self.assertRaises(ValueError):shein_qa.validate_rendered(row,True)

    def test_changed_video_identity_fails_before_rendering(self):
        s,d,l=self.fixture()
        with patch.object(shein_qa,'render_previews') as renderer,self.assertRaisesRegex(ValueError,'lineage'):
            shein_qa.verify_media(self.common(True),'OFFLINE',l,d,s,{'enabled':True,'chrome_path':CHROME})
        renderer.assert_not_called()

    def test_package_drift_and_instagram_drift_fail(self):
        s,d,l=self.fixture();expected=d['ads'][0]['creative_payload']
        for change in ['title','rules','tracking','ig']:
            actual=copy.deepcopy(l['ads']['data'][0]['creative'])
            if change=='title':actual['asset_feed_spec']['titles'][0]['text']='WRONG'
            if change=='rules':actual['asset_feed_spec']['asset_customization_rules']=[]
            if change=='tracking':actual['url_tags']='utm_campaign=wrong'
            if change=='ig':actual['instagram_user_id']='other'
            self.assertFalse(matches(actual,expected))

    def test_full_media_supports_all_manager_profiles(self):
        for index in range(6):
            r,s,a=flexible();_,_,account,_=case(index)
            original=a['shein_profile'];target=account['shein_profile']
            r.update(account=target['account_name'],authorized_by=target['manager_discord_id'],source_channel_id=target['channel_id'])
            s['campaign']['account_id']=target['account_id'];s['campaign']['name']=s['campaign']['name'].replace(original['tracking_prefix'],target['tracking_prefix'])
            s['adset']['name']=s['adset']['name'].replace(original['tracking_prefix'],target['tracking_prefix'])
            cr=s['ads'][0]['creative'];cr['effective_object_story_id']=target['page_id']+'_111';cr['object_story_spec']['page_id']=target['page_id']
            cr['asset_feed_spec']['link_urls'][0]['website_url']=target['destination_base']+'?utm_source=facebook&utm_medium='+target['utm_medium']+'&utm_campaign='+target['tracking_prefix']+'c110&utm_adgroup='+target['tracking_prefix']+'c110g01'
            self.assertEqual(compiler.build(r,s,114,account)['campaigns'][0]['creative_materialization_route'],'full_media_two_phase')


class FlexibleCoreRecoveryTests(unittest.TestCase):
    def test_abrupt_stop_preserves_ids_and_resumes_without_duplicate_creatives(self):
        r,s,a=flexible();payload=compiler.build(r,s,114,a);aid=a['shein_profile']['account_id']
        class Stateful(FakeBatchTransport):
            def __init__(self):super().__init__(aid);self.creatives={};self.ads={};self.ops=[];self.crash=True
            def execute(self,operations,stage):
                self.ops.extend(operations)
                if stage=='existing_post_ad_attach' and self.crash:
                    self.crash=False;raise KeyboardInterrupt('offline stopped after materialization')
                if stage.startswith('existing_post_recovery_inventory'):
                    out=[]
                    for o in operations:
                        path=o.relative_url.split('?')[0]
                        if '/ads' in path:body={'data':list(self.ads.values())}
                        elif path in self.creatives:body=copy.deepcopy(self.creatives[path])
                        elif path.endswith('/adcreatives'):body={'data':list(self.creatives.values())}
                        else:raise AssertionError(path)
                        out.append(BatchResult(o.name,200,body))
                    return out
                out=super().execute(operations,stage)
                for o,result in zip(operations,out):
                    if o.kind=='creative_create':self.creatives[result.body['id']]={**copy.deepcopy(o.body),'id':result.body['id'],'account_id':aid,'instagram_user_id':'ig-source','effective_object_story_id':a['shein_profile']['page_id']+'_new'}
                    if o.kind=='existing_post_ad_copy':self.ads[result.body['copied_ad_id']]={'id':result.body['copied_ad_id'],'adset_id':o.body['adset_id'],'source_ad_id':o.relative_url.split('/')[0],'name':'unattached','status':'PAUSED','creative':{}}
                    if o.kind=='existing_post_ad_attach':
                        ad=self.ads[o.relative_url];ad.update(name=o.body['name'],status=o.body['status'],creative=self.creatives[o.body['creative']['creative_id']])
                return out
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);config={'enabled':True,'write_enabled':True,'accounts':{aid:a},'state_root':str(root/'state'),'audit_root':str(root/'audit')}
            sealed=Manifest.from_dict(prevalidate_payload(payload,MediaRegistry(root/'registry.json')));transport=Stateful()
            with self.assertRaises(KeyboardInterrupt):CampaignEngine(config,transport_factory=lambda _:transport).execute(sealed)
            checkpoint=json.loads(next((root/'state/checkpoints').glob('*.json')).read_text());record=checkpoint['bundles'][0]
            self.assertEqual(len(record['creative_ids']),1);self.assertTrue(record['existing_post_creative_ids'])
            result=CampaignEngine(config,transport_factory=lambda _:transport).execute(sealed)
            self.assertEqual(result['status'],'COMPLETE_PAUSED')
            self.assertEqual(len([o for o in transport.ops if o.kind=='campaign_copy']),1)
            self.assertEqual(len([o for o in transport.ops if o.kind=='adset_copy']),1)
            self.assertEqual(len([o for o in transport.ops if o.kind=='creative_create']),1)
            self.assertEqual(len([o for o in transport.ops if o.kind=='existing_post_ad_copy']),1)
            self.assertTrue(any(o.body.get('asset_feed_spec') for o in transport.ops if o.kind=='creative_create'))
            tree=driver._engine_tree(config,r['request_id'],result['campaign_ids'][0]);self.assertIsNotNone(tree)


class RendererIntegrationTests(unittest.TestCase):
    def test_real_isolated_chromium_loads_local_video_and_rejects_link_only(self):
        import http.server,threading,subprocess
        from functools import partial
        from ares_campaign_v3.preview_renderer import render_previews
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            subprocess.run(['/usr/bin/ffmpeg','-loglevel','error','-f','lavfi','-i','color=c=red:s=160x160:r=10','-t','1','-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart','-y',str(root/'video.mp4')],check=True,timeout=20)
            (root/'video.html').write_text('<video src="/video.mp4" preload="auto" controls></video>')
            (root/'empty.html').write_text('<p>TEXT AND LINK ONLY</p><img width="40" height="40">')
            class Quiet(http.server.SimpleHTTPRequestHandler):
                def log_message(self,*args):pass
            server=http.server.ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(root)));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                base='http://127.0.0.1:'+str(server.server_port)
                rows=render_previews([base+'/video.html'],chrome_path=CHROME,timeout=8,allow_local=True,expect_video=[True]);shein_qa.validate_rendered(rows[0],True)
                self.assertEqual(rows[0]['videos'][0]['width'],160)
                rows=render_previews([base+'/empty.html'],chrome_path=CHROME,timeout=3,allow_local=True,expect_video=[True])
                with self.assertRaises(ValueError):shein_qa.validate_rendered(rows[0],True)
            finally:server.shutdown();server.server_close();thread.join(timeout=5)

class DriveCacheTests(unittest.TestCase):
    def test_same_ready_folder_queried_once_without_skipping_asset_checks(self):
        from unittest.mock import Mock
        from ares_campaign_v3 import shein_media_handoff as handoff
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);inv=root/'data/ares/creative-ops/inventory/assets.jsonl';inv.parent.mkdir(parents=True)
            refs=[{'asset_id':'asset-'+str(i),'checksum':str(i+1)*64} for i in range(2)]
            rows=[{'asset_id':r['asset_id'],'reservation_request_id':'request','language':'EN','vertical':'SHEIN','metadata_clean':True,'status':'01_READY','asset_path':'SHEIN/VID/01_READY','clean_checksum':r['checksum'],'asset_drive_id':'file-'+str(i),'canonical_filename':'video-'+str(i)+'.mp4'} for i,r in enumerate(refs)]
            inv.write_text('\n'.join(json.dumps(r) for r in rows))
            registry=MediaRegistry(root/'data/ares/meta-ads/engine-v3/media-registry.json')
            for i,r in enumerate(refs):registry.register(account_id='100',asset_id=r['asset_id'],checksum=r['checksum'],vertical_video_id='v'+str(i),square_video_id=None,ready=True,upload_edge='ad_account_advideos',association_verified=True)
            ops=Mock();ops.drive_runtime_token.return_value=('OFFLINE_DRIVE',None)
            def file_read(token,identifier):
                if identifier=='ready':return {'id':'ready','name':'01_READY','parents':['operation']}
                i=int(identifier[-1]);return {'id':identifier,'driveId':'0AEwt4Ye690ocUk9PVA','name':rows[i]['canonical_filename'],'parents':['ready'],'trashed':False,'md5Checksum':'verified'}
            ops.drive_file_readback.side_effect=file_read
            common=Mock()
            def meta_read(path,token,params):
                if path=='act_100/advideos':return 200,{'data':[{'id':'v0'},{'id':'v1'}]},{}
                i=int(path[-1]);return 200,{'id':path,'title':refs[i]['asset_id']+' '+refs[i]['checksum'][:10],'status':{'video_status':'ready'},'thumbnails':{'data':[{'uri':'https://example.test/thumb'}]}},{}
            common.graph_get.side_effect=meta_read
            with patch.object(handoff,'_ops',return_value=ops),patch.object(handoff,'_get',return_value={'files':[{'id':'testing','name':'02_TESTING','driveId':'0AEwt4Ye690ocUk9PVA'}]}) as siblings:
                out=handoff.load_ready_assets({'request_id':'request','asset_refs':refs},{'account_id':'100','language':'EN'},root,common,'OFFLINE_META')
            self.assertEqual(len(out),2);self.assertEqual(siblings.call_count,1)
            self.assertEqual(sum(c.args[1]=='ready' for c in ops.drive_file_readback.call_args_list),1)
            self.assertEqual(sum(c.args[1].startswith('file-') for c in ops.drive_file_readback.call_args_list),2)

if __name__=='__main__':unittest.main()
