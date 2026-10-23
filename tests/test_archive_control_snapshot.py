"""Offline regression for real My Drive controls; no production I/O."""
import sys,json,hashlib,copy,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import ares_archive_bridge as b
import ares_archive_automation as a
class SnapshotControlStore(unittest.TestCase):
 def setUp(self):
  self.c={'requests_folder_id':'NEW_REQUESTS','receipts_folder_id':'NEW_RECEIPTS','source_drive_id':b.SOURCE_DRIVE,'owner_executor_mode':'vps'}
  self.binding={'production_enabled':True,'parent_ids':['NEW_REQUESTS','NEW_RECEIPTS'],'folder_map':{},'migration_pending':False}
  self.job={'jobId':'offline','kind':'lineage','assets':[]};self.raw=b.canonical(self.job)
  self.receipt={'schema':'mgs.archive.receipt.v1','jobId':'offline','kind':'lineage','status':'copied','assets':[],'deleteSource':False}
  self.ack={'schema':'mgs.archive.ack.v1','jobId':'offline','kind':'lineage','status':'verified','deleteSource':False}
  def meta(parent,kind,author):return {'parents':[parent],'trashed':False,'owners':[{'emailAddress':b.ACCOUNT}],'permissions':[],'properties':{'mgsArchiveType':kind},'lastModifyingUser':{'permissionId':b.PUBLISHER_PERMISSION_IDS[author]}}
  self.ms={'REQ':meta('NEW_REQUESTS','vps_request',b.CANONICAL_SA),'REC':meta('NEW_RECEIPTS','receipt',b.ACCOUNT),'ACK':meta('NEW_REQUESTS','ack',b.CANONICAL_SA)}
  self.ms['REQ']['properties'].update(mgsArchiveKey='request:offline',sha256=hashlib.sha256(self.raw).hexdigest(),mgsArchiveState='verified')
 def run_snapshot(self):
  obj=self
  class D:
   def one(self,parent,key):return {'id':{'request:offline':'REQ','receipt:offline':'REC','ack:offline':'ACK'}[key]}
   def meta(self,fid):return obj.ms[fid]
   def raw(self,fid):return {'REQ':obj.raw,'REC':b.canonical(obj.receipt),'ACK':b.canonical(obj.ack)}[fid]
  with patch.object(b,'read_json',return_value=self.binding):return a.verification_snapshot(D(),self.c,self.job)
 def test_my_drive_request_receipt_ack_accepted(self):self.assertTrue(self.run_snapshot()['acked'])
 def test_foreign_owner_rejected_at_each_surface(self):
  for fid in ['REQ','REC','ACK']:
   old=copy.deepcopy(self.ms[fid]);self.ms[fid]['owners']=[{'emailAddress':'foreign@example.invalid'}]
   with self.subTest(fid=fid),self.assertRaises(b.ArchiveError):self.run_snapshot()
   self.ms[fid]=old
 def test_unknown_parent_still_rejected(self):
  self.ms['REQ']['parents']=['FOREIGN']
  with self.assertRaises(b.ArchiveError):self.run_snapshot()
 def test_disabled_binding_still_rejected(self):
  self.binding['production_enabled']=False
  with self.assertRaises(b.ArchiveError):self.run_snapshot()
 def test_raw_request_change_still_rejected(self):
  self.raw=b.canonical({**self.job,'injected':True})
  with self.assertRaises(b.ArchiveError):self.run_snapshot()
if __name__=='__main__':unittest.main()
