import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from ares_campaign_v3 import shein_single_clone,shein_general,shein_grouped_media
from ares_campaign_v3.media_registry import MediaNotReady
import test_shein_image_media as original
class RenamedImageHandoffTests(unittest.TestCase):
    fixture=original.ImageTests.fixture
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
                for image in library:image['name'] += '_105'
                shein_grouped_media.prepare(r,base=root,work_dir=media_dir)
                self.assertEqual(uploader.upload.call_count,3)
                # Fresh reservation must not be written when a known renamed hash
                # vanishes or deterministic-name discovery becomes ambiguous.
                before_inventory=inv.read_bytes();before_reservations=ops.atomic_inventory.call_count
                missing=library.pop()
                with self.assertRaises(MediaNotReady):shein_grouped_media.prepare(r,base=root,work_dir=media_dir)
                library.append(missing)
                self.assertEqual(inv.read_bytes(),before_inventory)
                self.assertEqual(ops.atomic_inventory.call_count,before_reservations)
                duplicate_name=library[0]['name'].removesuffix('_105')
                library.extend([{**library[0],'hash':'e'*32,'name':duplicate_name},{**library[0],'hash':'f'*32,'name':duplicate_name}])
                with self.assertRaisesRegex(ValueError,'ambiguous'):shein_grouped_media.prepare(r,base=root,work_dir=media_dir)
                library.pop();library.pop()
                self.assertEqual(inv.read_bytes(),before_inventory)
                self.assertEqual(ops.atomic_inventory.call_count,before_reservations)
                self.assertEqual(uploader.upload.call_count,3)
                self.assertEqual(len(ready['asset_refs']),3)
                def meta(path,token,params):
                    self.assertEqual(path,'act_'+aid+'/adimages');return 200,{'data':library},{}
                common.graph_get.side_effect=meta
                resolved=handoff.load_ready_assets(ready,profile,root,common,'OFFLINE')
                compiled=shein_general.build({**r,'_resolved_assets':resolved},s,114,a)
                _,_,_,_,desired,tree=original.ImageQATests().tree()
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
