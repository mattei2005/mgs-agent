"""Offline direct-backup slot binding; no private grant or provider response."""
import sys,copy,unittest,tempfile,json
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import mgs_private_backup_upload as x
class DirectSlots(unittest.TestCase):
 def setUp(self):
  self.p={'archiveRootId':'OFFLINE_ARCHIVE','tiers':{'hourly':{'archiveId':'OFFLINE_TIER'}}};self.c={'approval_message_id':x.APPROVAL,'archive_root_id':'OFFLINE_ARCHIVE','owner':x.b.ACCOUNT};self.j={'schema':'mgs.backup.direct.slot.v1','tier':'hourly','mode':'quick','parent_id':'OFFLINE_TIER','name':'mgs-dr-hourly-20261022T120000Z.zip.gpg','sha256':'a'*64,'md5':'b'*32,'size':100}
 def test_exact_encrypted_generation(self):self.assertTrue(x.validate_slot(self.j,self.p,self.c))
 def test_scope_name_hash_and_mode_rejected(self):
  for k,v in [('parent_id','OTHER'),('name','plain.zip'),('mode','full'),('sha256','x'),('size',0)]:
   j=copy.deepcopy(self.j);j[k]=v
   with self.subTest(k=k),self.assertRaises(x.b.ArchiveError):x.validate_slot(j,self.p,self.c)
 def test_invalid_rollout_does_not_fall_back(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(x,'BINDING',Path(tmp)/'binding.json'):
   x.BINDING.write_text(json.dumps({'production_enabled':True,'approval_message_id':'foreign'}))
   with self.assertRaises(x.b.ArchiveError):x.contract()
if __name__=='__main__':unittest.main()
