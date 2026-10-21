import sys,json,copy,contextlib,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import mgs_whole_drive_migration as m
b=m.b

class OwnerAcceptanceTests(unittest.TestCase):
 def fixture(self,kind='ok'):
  stage=m.read(m.DATA/'stage.json');manifest=m.read(m.DATA/'probe-manifest.json');c=b.config_load();hs=m.read(m.historical.location()/'stage.json');hp=m.historical.location()/'stage.json'
  store={m.DATA/'stage.json':copy.deepcopy(stage),m.DATA/'probe-manifest.json':manifest,b.CONFIG:copy.deepcopy(c),hp:copy.deepcopy(hs)};writes=[]
  worker=(b.BASE/stage['worker_source_path']).read_bytes()
  # Offline fixture follows the candidate being tested, not an older live pin.
  import hashlib
  stage['worker_sha256']=hashlib.sha256(worker).hexdigest();store[m.DATA/'stage.json']=copy.deepcopy(stage)
  receipt={'schema':'mgs.whole.drive.probe.receipt.v1','authorizationMessageId':m.AUTH,'manifestSha256':stage['manifest_sha256'],'status':'completed','productionMutation':False,'deleteSource':False,'canary':{'restored':kind!='unrestored'},'targets':[{'metadata':{'id':x['id']}} for x in manifest['targets']]}
  hb={'workerSha256':stage['worker_sha256'],'triggerUid':'2456112746912022528' if kind!='manual' else None,'status':'ok','blocked':[],'canaryAcknowledged':True,'deleteSource':False,'executedAt':b.now_iso() if kind!='stale' else '2020-01-01T00:00:00Z'}
  owner={'permissionId':'03783617840924670288','emailAddress':b.ACCOUNT};sa={'permissionId':'07414359829876449782','emailAddress':b.CANONICAL_SA}
  class Drive:
   def __init__(self,*args):pass
   def one(self,parent,key):
    if key==m.PROBE_KEY:return None if kind=='missing' else {'id':'RECEIPT'}
    if key=='heartbeat:worker-v1':return {'id':'HEARTBEAT'}
    raise AssertionError(key)
   def meta(self,fid):
    if fid=='RECEIPT':return {'parents':[c['receipts_folder_id']],'properties':{'mgsArchiveType':'whole_drive_probe_receipt'},'lastModifyingUser':owner}
    if fid=='HEARTBEAT':return {'lastModifyingUser':owner}
    if fid==stage['worker_file_id']:return {'id':fid,'lastModifyingUser':sa}
    if fid==stage['canary_id']:return {'driveId':b.SOURCE_DRIVE,'parents':[b.SOURCE_DRIVE] if kind!='wrong_parent' else ['OTHER'],'properties':{'validationOnly':'true'}}
    raise AssertionError(fid)
   def raw(self,fid):
    if fid=='RECEIPT':return b.canonical(receipt)
    if fid=='HEARTBEAT':return b.canonical(hb)
    if fid==stage['worker_file_id']:return worker if kind!='wrong_code' else b'wrong-code'
    raise AssertionError(fid)
  def atomic(path,value):
   writes.append(str(path))
   if kind=='write_failure' and len(writes)==2:raise OSError('controlled second-write failure')
   store[path]=copy.deepcopy(value)
  def read(path,default=None):return copy.deepcopy(store.get(path,default))
  return stage,c,store,writes,Drive,atomic,read,hp
 def execute(self,kind):
  stage,c,store,writes,Drive,atomic,read,hp=self.fixture(kind)
  with patch.object(b,'Drive',Drive),patch.object(b,'queue_lock',contextlib.nullcontext),patch.object(b,'config_load',side_effect=lambda:copy.deepcopy(store[b.CONFIG])),patch.object(m,'read',side_effect=read),patch.object(b,'atomic_json',side_effect=atomic):
   if kind=='ok':
    out=m.accept_owner();self.assertEqual(out['status'],'owner_probe_verified');self.assertFalse(out['production_migrated']);self.assertEqual(store[b.CONFIG]['worker_sha256'],stage['worker_sha256']);self.assertEqual(store[hp]['worker_sha256'],stage['worker_sha256']);self.assertTrue(store[hp]['copy_enabled']);self.assertFalse(store[hp]['historical_cleanup_enabled'])
   elif kind=='write_failure':
    with self.assertRaises(OSError):m.accept_owner()
    self.assertEqual(store[b.CONFIG],c);self.assertEqual(store[hp]['worker_sha256'],c['worker_sha256'])
   else:
    with self.assertRaises(b.ArchiveError):m.accept_owner()
    self.assertEqual(writes,[])
 def test_valid_receipt_scheduled_heartbeat_promotes_both_pins_only(self):self.execute('ok')
 def test_missing_receipt_no_write(self):self.execute('missing')
 def test_unrestored_canary_no_write(self):self.execute('unrestored')
 def test_manual_heartbeat_no_write(self):self.execute('manual')
 def test_stale_heartbeat_no_write(self):self.execute('stale')
 def test_wrong_canary_parent_no_write(self):self.execute('wrong_parent')
 def test_wrong_code_no_write(self):self.execute('wrong_code')
 def test_second_pin_write_failure_rolls_back_first(self):self.execute('write_failure')

if __name__=='__main__':unittest.main()
