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
 def disposition(self,*,valid=True,actual_change=None,ack_change=None):
  asset={'sourceId':'file','destinationParentId':'dest','name':'backup','mimeType':'application/pgp-encrypted','sourceCreatedTime':'time','size':'10','md5':'a'*32,'sha256':'b'*64,'managedProperties':{'mgs_dr':'true'}}
  job={'jobId':'job','verified':True,'ack_file_id':'ack','body':{'asset':asset}}
  actual={'id':'file','parents':['dest'],'trashed':True,'name':'backup','createdTime':'time','size':'10','md5Checksum':'a'*32,'sha256Checksum':'b'*64,'appProperties':asset['managedProperties']}
  if actual_change:actual.update(actual_change)
  intent={'status':'verified','confirmation_message_id':r.AUTH if valid else 'wrong','job_id':'job','ack_id':'ack','metadata_after':actual}
  ack={'status':'verified','archiveId':'file','sha256':'b'*64,'requestSha256':r.a.sha(job['body'])}
  if ack_change:ack.update(ack_change)
  def read(path,default=None):return self.policy if path==r.POLICY else {'intents':{'file':intent}}
  with patch.object(b,'read_json',side_effect=read),patch.object(r.a,'queue_object',return_value=(ack,{})),patch.object(r.a.corp,'load_plan',return_value=({},{})),patch.object(r.a.corp,'check_acl'),patch.object(r.a.corp,'desired',return_value={}),patch.object(r.a.corp.h,'permissions',return_value=[]):
   return r.verify_recorded_trash(Mock(),{},self.p,job,actual)
 def test_confirmed_trashed_migration_is_reconciled(self):self.assertTrue(self.disposition())
 def test_unconfirmed_trash_is_not_accepted(self):
  with self.assertRaises(b.ArchiveError):self.disposition(valid=False)
 def test_trash_byte_drift_is_not_excused(self):
  with self.assertRaises(b.ArchiveError):self.disposition(actual_change={'md5Checksum':'c'*32})
 def test_trash_native_ack_must_match(self):
  with self.assertRaises(b.ArchiveError):self.disposition(ack_change={'archiveId':'other'})
if __name__=='__main__':unittest.main()
