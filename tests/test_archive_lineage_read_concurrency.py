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

if __name__=='__main__':unittest.main()
