import sys,unittest,copy
from pathlib import Path
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import mgs_archive_backup_retention as r
import ares_archive_bridge as b
class Retention(unittest.TestCase):
 def setUp(self):
  self.p={'archiveRootId':'archive-root','pilotId':'pilot','retentionCount':r.COUNTS}
  self.policy={'schema':'mgs.archive.backup.retention.v1','confirmation_message_id':r.AUTH,'confirmation_user_id':'344196393512075265','confirmation_thread_id':'1562078493498540042','archive_root_id':'archive-root','account':b.ACCOUNT,'retention_count':r.COUNTS,'action':'trash_only','permanent_delete':False,'protect_latest_pass_restore':True,'protect_pilot':True,'active':False}
 def test_exact_policy(self):self.assertIs(r.validate_policy(self.policy,self.p),self.policy)
 def test_bad_policy_fields_fail(self):
  for key,value in [('confirmation_message_id','wrong'),('permanent_delete',True),('account','wrong'),('action','delete'),('archive_root_id','source'),('active',1),('protect_latest_pass_restore',False),('retention_count',{'hourly':1})]:
   with self.subTest(key=key),self.assertRaises(b.ArchiveError):r.validate_policy({**self.policy,key:value},self.p)
 def rows(self,n=53):return [{'id':str(i),'tier':'hourly','createdTime':f'2026-10-{(i//24)+1:02}T{i%24:02}:00:00Z','location':'archive','verified':True} for i in range(n)]
 def test_exact_count(self):self.assertEqual(r.select(self.rows(),self.p,set()),['4','3','2','1','0'])
 def test_restore_protected(self):self.assertNotIn('1',r.select(self.rows(),self.p,{'1'}))
 def test_unverified_protected(self):
  rows=self.rows();rows[0]['verified']=False;self.assertNotIn('0',r.select(rows,self.p,set()))
 def test_source_protected(self):
  rows=self.rows();rows[0]['location']='source';self.assertNotIn('0',r.select(rows,self.p,set()))
 def test_duplicates_fail_closed(self):
  with self.assertRaises(b.ArchiveError):r.select(self.rows()+self.rows()[:1],self.p,set())
 def test_no_restore_fails_closed(self):
  with patch.object(b,'read_json',return_value={}),self.assertRaises(b.ArchiveError):r.protected(self.p)
 def test_failed_restore_fails_closed(self):
  with patch.object(b,'read_json',return_value={'last_restore_test':{'status':'FAIL','remote_file_id':'x'}}),self.assertRaises(b.ArchiveError):r.protected(self.p)
 def test_real_restore_selection(self):
  with patch.object(b,'read_json',return_value={'last_restore_test':{'status':'PASS','remote_file_id':'last','download_sha256':'a'*64,'isolated_only':True}}):self.assertEqual(r.protected(self.p)[0],{'pilot','last'})
 def test_cas_before_mutation(self):
  owner=Mock();expected={'id':'x','parents':['dest'],'version':'1'}
  with patch.object(r.backup,'native_meta',return_value={**expected,'version':'2'}),patch.object(r.urllib.request,'urlopen') as rpc:
   with self.assertRaises(b.ArchiveError):r.trash_once(owner,'x','dest',expected)
   rpc.assert_not_called()
 def test_shared_drive_never_trashed(self):
  meta={'id':'x','parents':['dest'],'version':'1','driveId':b.SOURCE_DRIVE,'trashed':False,'mimeType':'application/pgp-encrypted','capabilities':{'canTrash':True},'owners':[{'emailAddress':b.ACCOUNT}]}
  with patch.object(r.backup,'native_meta',return_value=meta),patch.object(r.urllib.request,'urlopen') as rpc:
   with self.assertRaises(b.ArchiveError):r.trash_once(Mock(),'x','dest',meta)
   rpc.assert_not_called()
if __name__=='__main__':unittest.main()
