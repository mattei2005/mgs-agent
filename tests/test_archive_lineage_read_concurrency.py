"""Synthetic IO fixtures: bounded reads, all checks retained, no worker writes."""
import sys,time,threading,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import mgs_archive_read_admission as reads

class ReadMapTests(unittest.TestCase):
 def test_bounded_parallel_order_and_caller_waits(self):
  guard=threading.Lock();active=0;peak=0
  def read(value):
   nonlocal active,peak
   with guard:active+=1;peak=max(peak,active)
   time.sleep(.01*(4-value%4))
   with guard:active-=1
   return value*2
  self.assertEqual(reads.readonly_map(read,range(8)),[i*2 for i in range(8)])
  self.assertGreater(peak,1);self.assertLessEqual(peak,4);self.assertEqual(active,0)
 def test_failure_stops_new_submissions_and_drains(self):
  visited=[];done=[]
  def read(i):
   visited.append(i)
   if i==0:raise RuntimeError('bad native byte')
   time.sleep(.03);done.append(i);return i
  with self.assertRaisesRegex(RuntimeError,'bad native byte'):reads.readonly_map(read,range(8))
  self.assertLessEqual(len(visited),4);self.assertEqual(set(done),set(visited)-{0})
 def test_serial_compatibility_and_empty(self):
  self.assertEqual(reads.readonly_map(lambda i:i,[2,1],parallel=False),[2,1])
  self.assertEqual(reads.readonly_map(lambda i:i,[]),[])
 def test_pool_limit_cannot_be_widened_by_caller(self):
  import inspect
  self.assertNotIn('max_workers',inspect.signature(reads.readonly_map).parameters)

class LineageChecksTests(unittest.TestCase):
 def fixture(self):
  import ares_archive_bridge as b
  import hashlib,json
  from unittest.mock import Mock
  assets=[];metadata={};hashes={}
  for role in ['original','clean']:
   sid='offline-'+role;pid='provider-'+role;blob=('offline fixture '+role).encode()
   h={'size':str(len(blob)),'md5':hashlib.md5(blob).hexdigest(),'sha256':hashlib.sha256(blob).hexdigest()}
   asset={'sourceId':sid,'role':role,'name':role+'.png','relativeParent':['SHEIN_US_ES','IMG','01_READY'],**h}
   assets.append(asset);hashes[sid]=h;hashes[pid]=h
   metadata[pid]={'id':pid,'owners':[{'emailAddress':b.ACCOUNT}],'trashed':False,'size':h['size'],'md5Checksum':h['md5'],'name':asset['name'],'parents':['offline-parent'],'permissions':[]}
   metadata[sid]={'id':sid}
  job={'jobId':'offline-job','lineageId':'offline-lineage','kind':'lineage','assets':assets}
  receipt={'schema':'mgs.archive.receipt.v1','jobId':job['jobId'],'status':'copied','deleteSource':False,'assets':[{'sourceId':a['sourceId'],'role':a['role'],'archiveId':'provider-'+a['role']} for a in assets]}
  d=Mock();d.one.side_effect=lambda parent,key:{'id':'offline-receipt' if key.startswith('receipt:') else 'offline-request'}
  metadata['offline-receipt']={'lastModifyingUser':{'permissionId':b.PUBLISHER_PERMISSION_IDS[b.ACCOUNT]}}
  metadata['offline-request']={'lastModifyingUser':{'permissionId':b.PUBLISHER_PERMISSION_IDS[b.CANONICAL_SA]},'properties':{'mgsArchiveState':'verified'}}
  d.meta.side_effect=lambda fid:metadata[fid];d.raw.return_value=json.dumps(receipt).encode()
  d.relative_parent.return_value=assets[0]['relativeParent'];d.hashes.side_effect=lambda fid:hashes[fid]
  return b,d,job,metadata,hashes
 def run_case(self,mutate=None,apply=False):
  import ares_archive_retirement as retire
  b,d,job,metadata,hashes=self.fixture()
  if mutate:mutate(metadata,hashes)
  cfg={'owner_executor_mode':'vps','receipts_folder_id':'offline-receipts','requests_folder_id':'offline-requests'}
  caller=threading.get_ident();writes=[]
  def write(*args,**kwargs):
   self.assertEqual(threading.get_ident(),caller);writes.append(args)
  d.upload_once.side_effect=write;d.api.side_effect=write
  def read(path,default=None):
   return {'mappings':{},'verified_jobs':{}} if path.name=='archive-index.json' else job
  with patch.object(b,'read_json',side_effect=read),patch.object(b,'atomic_json',side_effect=write),patch.object(retire,'source_state',side_effect=lambda d,c,j,a:metadata[a['sourceId']]),patch.object(b,'validate_reconciliation_source',return_value=True):
   try:return b.reconcile(d,cfg,job['jobId'],apply),d,writes
   except Exception:
    self.assertFalse(writes,'No ACK/index or provider mutation after a failed reader');raise
 def test_every_stream_preserved_and_ack_only_on_caller(self):
  result,d,writes=self.run_case(apply=True)
  self.assertEqual([a['role'] for a in result['assets']],['original','clean'])
  self.assertEqual(sorted(c.args[0] for c in d.hashes.call_args_list),['offline-clean','offline-original','provider-clean','provider-original'])
  self.assertTrue(writes)
 def test_corrupt_source_or_provider_never_publishes(self):
  import ares_archive_bridge as b
  for fid in ['offline-original','provider-clean']:
   with self.subTest(fid=fid),self.assertRaisesRegex(b.ArchiveError,'BINARY_INTEGRITY'):
    self.run_case(lambda m,h:h.__setitem__(fid,{'size':'0','md5':'bad','sha256':'bad'}),True)
 def test_owner_path_metadata_and_public_guards_remain(self):
  import ares_archive_bridge as b
  for field,value,error in [('owners',[],'COPIED_OWNER_OR_STATE'),('parents',[],'COPIED_PATH'),('name','wrong','COPIED_METADATA'),('permissions',[{'type':'anyone'}],'COPIED_PUBLIC')]:
   with self.subTest(field=field),self.assertRaisesRegex(b.ArchiveError,error):
    self.run_case(lambda m,h:m['provider-clean'].__setitem__(field,value),True)

class NestedReadTests(unittest.TestCase):
 def test_nested_maps_do_not_multiply_readers(self):
  guard=threading.Lock();active=0;peak=0
  def leaf(x):
   nonlocal active,peak
   with guard:active+=1;peak=max(peak,active)
   time.sleep(.01)
   with guard:active-=1
   return x
  result=reads.readonly_map(lambda i:reads.readonly_map(leaf,[i,i]),range(8))
  self.assertEqual(result,[[i,i] for i in range(8)]);self.assertLessEqual(peak,4);self.assertGreater(peak,1)

if __name__=='__main__':unittest.main()
