"""Offline fixtures: one lease/executor, bounded RPC fanout, durable intents."""
import sys,time,threading,tempfile,unittest,json
from pathlib import Path
from unittest.mock import Mock,patch
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import mgs_archive_owner_transport as t
class BoundedOwnerBatchTests(unittest.TestCase):
 def test_single_engine_fanout_is_bounded_and_result_order_is_preserved(self):
  with tempfile.TemporaryDirectory() as folder:
   engine=t.Engine(Mock(),{},None,None,t.Journal(Path(folder)/'journal.json'));lock=threading.Lock();active=0;maximum=0
   def copy_asset(asset,job):
    nonlocal active,maximum
    with lock:active+=1;maximum=max(maximum,active)
    time.sleep(.03)
    with lock:active-=1
    return {'sourceId':asset['sourceId']}
   job={'assets':[{'sourceId':'OFFLINE_'+str(i)} for i in range(8)]}
   with patch.object(engine,'copy_asset',side_effect=copy_asset):result=engine.copy_assets_bounded(job)
   self.assertEqual([x['sourceId'] for x in result],[x['sourceId'] for x in job['assets']]);self.assertGreater(maximum,1);self.assertLessEqual(maximum,4)
 def test_batch_failure_returns_no_receipt_and_stops_new_submissions(self):
  with tempfile.TemporaryDirectory() as folder:
   engine=t.Engine(Mock(),{},None,None,t.Journal(Path(folder)/'journal.json'));called=[]
   def copy_asset(asset,job):
    called.append(asset['sourceId'])
    if asset['sourceId']=='OFFLINE_0':raise t.TransportError('OFFLINE_REJECTED')
    time.sleep(.04);return {'sourceId':asset['sourceId']}
   with patch.object(engine,'copy_asset',side_effect=copy_asset),self.assertRaises(t.TransportError):engine.copy_assets_bounded({'assets':[{'sourceId':'OFFLINE_'+str(i)} for i in range(8)]})
   self.assertLessEqual(len(called),4)
 def test_concurrent_journal_writes_preserve_all_intents_and_ids(self):
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'journal.json';journal=t.Journal(path)
   def one(i):
    key='copy:OFFLINE_'+str(i);journal.intent(key,{'source':'OFFLINE_'+str(i)});journal.landed(key,'OFFLINE_COPY_'+str(i))
   with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(one,range(40)))
   restored=t.Journal(path)
   self.assertEqual(len(restored.data['intents']),40)
   for i in range(40):self.assertEqual(restored.known_id('copy:OFFLINE_'+str(i)),'OFFLINE_COPY_'+str(i))
if __name__=='__main__':unittest.main()
