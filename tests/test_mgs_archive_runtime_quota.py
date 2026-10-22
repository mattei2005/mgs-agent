"""Offline publication/rollback/idempotency tests. No live Google calls."""
import contextlib,copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,'/root/mgs-agent/scripts')
import mgs_archive_runtime_quota as q

class QuotaRevision(unittest.TestCase):
 def test_base_digest_drift_rejected(self):
  with self.assertRaisesRegex(q.b.ArchiveError,'BASE_CHANGED'):q.build(b'untrusted',q.POLICY.read_bytes())
 def test_only_two_existing_expressions_change(self):
  base=q.SOURCE.read_text();policy=q.POLICY.read_text();out=q.build(base.encode(),policy.encode()).decode()
  original=out.removesuffix('\n'+policy).replace('>=mgsArchiveBulkRuntimeLimit())','>=3600000)').replace('Date.now(),mgsArchiveBulkRuntimeLimit(),350)','Date.now(),3600000,350)')
  self.assertEqual(original,base)
 def fixture(self,root):
  stage=root/'backup-automation-stage.json';whole=root/'stage.json';target=root/'new.js';rollback=root/'rollback.json'
  source=q.SOURCE;policy=q.POLICY
  initial={'worker_file_id':'prior-staged','worker_sha256':q.BASE_SHA,'previous_active_worker_sha256':'active-before','owner_accepted':False,'automatic_archive_enabled':False,'heartbeat_samples':[{'old':True}],'archive_trash_enabled':False,'plan_sha256':'same-plan'}
  stage.write_text(json.dumps(initial));whole.write_text(json.dumps({'worker_sha256':q.BASE_SHA,'canary_id':'unchanged-canary','previous_active_worker_sha256':'active-before'}));config={'worker_sha256':'active-before','control_folder_id':'control123'};remote={};writes=[]
  class Drive:
   def meta(self,fid):return {'id':fid,'lastModifyingUser':{'permissionId':'07414359829876449782'}}
   def raw(self,fid):return remote[fid]
  def publish(d,s,parent,key,kind,raw,name,mime):
   fid='new-worker-id';remote[fid]=raw;writes.append(fid);return fid
  load=lambda:({},json.loads(stage.read_text()))
  patches=[patch.object(q.b,'BASE',root),patch.object(q,'TARGET',target),patch.object(q,'ROLLBACK',rollback),patch.object(q.a,'STAGE',stage),patch.object(q.a.m,'DATA',root),patch.object(q.a,'load',side_effect=load),patch.object(q.b,'queue_lock',contextlib.nullcontext),patch.object(q.b,'config_load',return_value=config),patch.object(q.b,'preflight',return_value={}),patch.object(q.b,'Drive',return_value=Drive()),patch.object(q.a,'staged_blob',side_effect=publish)]
  return patches,stage,whole,target,rollback,config,writes,remote
 def case(self,action):
  with tempfile.TemporaryDirectory() as tmp:
   values=self.fixture(Path(tmp));patches=values[0]
   with contextlib.ExitStack() as stack:
    for p in patches:stack.enter_context(p)
    action(*values[1:])
 def test_publication_preserves_active_pin_and_full_rollback(self):
  def check(stage,whole,target,rollback,config,writes,remote):
   out=q.publish();self.assertEqual(config['worker_sha256'],'active-before');self.assertEqual(len(writes),1);self.assertEqual(out['heartbeat_samples'],[]);self.assertFalse(out['automatic_archive_enabled']);self.assertEqual(json.loads(rollback.read_text())['backup_stage']['worker_sha256'],q.BASE_SHA);self.assertEqual(json.loads(whole.read_text())['worker_sha256'],out['worker_sha256']);self.assertEqual(remote[out['worker_file_id']],target.read_bytes())
  self.case(check)
 def test_repeated_publication_does_not_create_again(self):
  def check(stage,whole,target,rollback,config,writes,remote):
   one=q.publish();two=q.publish();self.assertEqual(one,two);self.assertEqual(len(writes),1)
  self.case(check)
 def test_partial_stage_promotion_repairs_only_whole_stage(self):
  def check(stage,whole,target,rollback,config,writes,remote):
   out=q.publish();v=json.loads(whole.read_text());v['worker_sha256']=q.BASE_SHA;whole.write_text(json.dumps(v));q.publish();self.assertEqual(json.loads(whole.read_text())['worker_sha256'],out['worker_sha256']);self.assertEqual(len(writes),1)
  self.case(check)
 def test_changed_remote_code_blocks_replay(self):
  def check(stage,whole,target,rollback,config,writes,remote):
   out=q.publish();remote[out['worker_file_id']]=b'changed'
   with self.assertRaisesRegex(q.b.ArchiveError,'REMOTE_DRIFT'):q.publish()
   self.assertEqual(len(writes),1)
  self.case(check)
 def test_active_cutover_race_blocks_before_new_upload(self):
  def check(stage,whole,target,rollback,config,writes,remote):
   config['worker_sha256']='unexpected-active'
   with self.assertRaisesRegex(q.b.ArchiveError,'ACTIVE_PIN_CHANGED'):q.publish()
   self.assertEqual(writes,[])
  self.case(check)

if __name__=='__main__':unittest.main()
