"""Offline controlled clock: queue admission cannot consume work budget."""
import sys,unittest,tempfile,contextlib
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import mgs_archive_owner_transport as t
class LeaseBudget(unittest.TestCase):
 def test_wait_is_reported_but_execution_keeps_its_whole_bound(self):
  digest=t.code_hash();cfg={'owner_executor_mode':'vps','owner_executor_sha256':digest,'requests_folder_id':'OFFLINE_REQUESTS'};contract={'production_enabled':True,'engine_sha256':digest,'approval_message_id':t.auth.APPROVAL};owner=Mock();owner.listing.return_value=[];engine=Mock()
  def objects(p):return {'phase':'exclusive'} if p.name=='exclusive-handoff.json' else contract
  with tempfile.TemporaryDirectory() as tmp,patch.object(t,'HOME',Path(tmp)),patch.object(t.b,'queue_lock',return_value=contextlib.nullcontext()),patch.object(t.b,'config_load',return_value=cfg),patch.object(t,'object_file',side_effect=objects),patch.object(t,'OwnerDrive',return_value=owner),patch.object(t.b,'Drive',return_value=Mock()),patch.object(t.h,'manifest_load',return_value=({},{})),patch.object(t,'Engine',return_value=engine),patch.object(t,'heartbeat'),patch.object(t.b,'atomic_json'),patch.object(t.time,'monotonic',side_effect=[0,100,120,120]):
   result=t.run_tick(max_jobs=1,max_seconds=30,produce=False)
  self.assertEqual(engine.deadline,130);self.assertEqual(result['queue_wait_seconds'],100);self.assertEqual(result['execution_seconds'],20);self.assertEqual(result['elapsed_seconds'],120)
if __name__=='__main__':unittest.main()
