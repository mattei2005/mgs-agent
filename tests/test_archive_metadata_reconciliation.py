"""Offline tests: byte-frozen membership cannot change through metadata overlay."""
import sys,unittest,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import ares_archive_backfill as h
class MetadataOverlayTests(unittest.TestCase):
 def setUp(self):
  self.asset={'role':'historical','sourceId':'OFFLINE_SOURCE01','sourceParentId':'OFFLINE_PARENT01','relativeParent':['SHEIN_US_EN','VID','01_READY'],'name':'frozen.mp4','size':'5','md5':'a'*32,'sha256':'b'*64,'mimeType':'video/mp4','version':'12','sourceCreatedTime':'2026-10-20T00:00:00Z'}
  self.base={'assets':[self.asset]};self.overlay={'schema':'mgs.archive.metadata.reconciliation.v1','migration_id':h.MIGRATION,'copy_authority_message_id':'1562256530454220851','unchanged_binary_membership':True,'source_and_archive_roots_unchanged':True,'changes':[{'source_id':'OFFLINE_SOURCE01','frozen_asset':self.asset,'effective_asset':{**self.asset,'name':'01 - used','sourceParentId':'OFFLINE_PARENT02','relativeParent':['SHEIN_US_EN','VID','JOE - USADOS'],'version':'14'},'source_hashes':{k:self.asset[k] for k in ['size','md5','sha256']},'native_actor_email':'joewillams2009@gmail.com','native_actor_role':'fileOrganizer','native_actor_permission_id':'13925914125691610133'}]}
 def test_legitimate_metadata_overlay_preserves_byte_scope_and_base(self):
  before=copy.deepcopy(self.base);view=h.apply_metadata_reconciliation(self.base,self.overlay);self.assertEqual(self.base,before);self.assertEqual(view['assets'][0]['name'],'01 - used');self.assertEqual(view['assets'][0]['sourceId'],self.asset['sourceId']);self.assertEqual(view['assets'][0]['sha256'],self.asset['sha256'])
 def test_content_or_membership_change_is_rejected(self):
  for key,value in [('sourceId','OTHER_ID'),('size','6'),('md5','c'*32),('sha256','d'*64),('mimeType','image/jpeg'),('sourceCreatedTime','2026-10-21T00:00:00Z')]:
   x=copy.deepcopy(self.overlay);x['changes'][0]['effective_asset'][key]=value
   with self.subTest(key=key),self.assertRaises(h.BackfillError):h.apply_metadata_reconciliation(self.base,x)
 def test_unknown_actor_or_cross_operation_path_is_rejected(self):
  x=copy.deepcopy(self.overlay);x['changes'][0]['native_actor_email']='outside@example.invalid'
  with self.assertRaises(h.BackfillError):h.apply_metadata_reconciliation(self.base,x)
  x=copy.deepcopy(self.overlay);x['changes'][0]['effective_asset']['relativeParent']=['CAR_BR_BR','VID','01_READY']
  with self.assertRaises(h.BackfillError):h.apply_metadata_reconciliation(self.base,x)
 def test_wrong_base_or_failed_full_hash_is_rejected(self):
  for mutation in ['base','hash']:
   x=copy.deepcopy(self.overlay)
   if mutation=='base':x['changes'][0]['frozen_asset']['name']='unexpected'
   else:x['changes'][0]['source_hashes']['sha256']='e'*64
   with self.subTest(mutation=mutation),self.assertRaises(h.BackfillError):h.apply_metadata_reconciliation(self.base,x)
if __name__=='__main__':unittest.main()
