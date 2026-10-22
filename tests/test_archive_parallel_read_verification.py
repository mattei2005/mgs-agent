"""Offline concurrency fixture: parallel reads, never parallel archive writers."""
import sys,time,threading,unittest
from pathlib import Path
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import ares_archive_backfill as h
class ParallelReadTests(unittest.TestCase):
 def test_ordered_parallel_reads_are_bounded(self):
  lock=threading.Lock();active=0;maximum=0
  def verify(d,c,j,a,r):
   nonlocal active,maximum
   with lock:active+=1;maximum=max(maximum,active)
   time.sleep(.025)
   with lock:active-=1
   return a['sourceId']
  assets=[{'sourceId':str(i)} for i in range(8)];job={'assets':assets}
  with patch.object(h,'verify_asset',side_effect=verify):result=h.verify_assets_readonly(None,{'owner_executor_mode':'vps'},job,{})
  self.assertEqual(result,[str(i) for i in range(8)]);self.assertGreater(maximum,1);self.assertLessEqual(maximum,4)
 def test_non_vps_remains_serial(self):
  job={'assets':[{'sourceId':'one'},{'sourceId':'two'}]}
  with patch.object(h,'verify_asset',side_effect=lambda d,c,j,a,r:a['sourceId']):self.assertEqual(h.verify_assets_readonly(None,{},job,{}),['one','two'])
 def test_one_failed_asset_prevents_result(self):
  def fail(d,c,j,a,r):
   if a['sourceId']=='bad':raise h.BackfillError('OFFLINE_BAD_BYTES')
   return a['sourceId']
  with patch.object(h,'verify_asset',side_effect=fail),self.assertRaises(h.BackfillError):h.verify_assets_readonly(None,{'owner_executor_mode':'vps'},{'assets':[{'sourceId':'good'},{'sourceId':'bad'}]},{})
 def test_source_preflight_is_readonly_bounded_parallel(self):
  lock=threading.Lock();active=0;maximum=0
  def check(d,a,c):
   nonlocal active,maximum
   with lock:active+=1;maximum=max(maximum,active)
   time.sleep(.025)
   with lock:active-=1
   return a['sourceId']
  with patch.object(h,'source_access',side_effect=check):self.assertEqual(h.check_sources_readonly(None,{'owner_executor_mode':'vps'},[{'sourceId':str(i)} for i in range(8)]),[str(i) for i in range(8)])
  self.assertGreater(maximum,1);self.assertLessEqual(maximum,4)
if __name__=='__main__':unittest.main()
