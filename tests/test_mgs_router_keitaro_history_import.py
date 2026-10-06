import importlib.util,json,sqlite3,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('imp',Path(__file__).parents[1]/'scripts/mgs-router-keitaro-history-import.py');assert spec and spec.loader;m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class TestImport(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.path=Path(self.tmp.name)/'clicks.sqlite';d=sqlite3.connect(self.path);d.executescript("PRAGMA journal_mode=WAL;CREATE TABLE click_totals(day TEXT NOT NULL,route_key TEXT NOT NULL,total INTEGER NOT NULL,PRIMARY KEY(day,route_key)) WITHOUT ROWID;CREATE TABLE click_meta(name TEXT PRIMARY KEY,value TEXT NOT NULL) WITHOUT ROWID;INSERT INTO click_meta VALUES('since','2026-10-06T05:37:49Z');INSERT INTO click_totals VALUES('2026-10-06','go.example.com'+char(10)+'/a',6);");d.commit();d.close()
  self.rows=[{'day':'2026-01-22','route_key':'go.example.com\n/a','clicks':3},{'day':'2026-01-23','route_key':'go.example.com\n/a','clicks':7}];self.h={'source':'Keitaro','timezone':'America/New_York','from':'2026-01-22','to':'2026-01-23','daily_rows':2,'imported_clicks':10,'campaigns_with_history':1,'routes_matched':1}
 def totals(self):
  d=sqlite3.connect(self.path);r=list(d.execute('SELECT * FROM click_totals ORDER BY day,route_key'));d.close();return r
 def test_exact_native_preservation_and_idempotency(self):
  r=m.import_history(self.path,self.rows,self.h,'a'*64);self.assertEqual(r['status'],'applied_exact_readback');self.assertEqual(self.totals()[-1][2],6);before=self.totals();r=m.import_history(self.path,self.rows,self.h,'a'*64);self.assertEqual(r['status'],'already_applied');self.assertEqual(before,self.totals())
 def test_hash_change_blocked_without_sideeffects(self):
  m.import_history(self.path,self.rows,self.h,'a'*64);before=self.totals()
  with self.assertRaisesRegex(AssertionError,'replay_source_changed'):m.import_history(self.path,self.rows,self.h,'b'*64)
  self.assertEqual(before,self.totals())
 def test_failure_before_commit_rolls_back_all(self):
  def fail(d):raise RuntimeError('injected')
  before=self.totals()
  with self.assertRaisesRegex(RuntimeError,'injected'):m.import_history(self.path,self.rows,self.h,'a'*64,fail)
  self.assertEqual(before,self.totals());self.assertEqual(m.import_history(self.path,self.rows,self.h,'a'*64)['status'],'applied_exact_readback')
 def test_duplicate_zero_overlap_rejected(self):
  for rows in [self.rows+self.rows,[{**self.rows[0],'clicks':0}],[{**self.rows[0],'day':'2026-10-06'}]]:
   with self.assertRaises((AssertionError,ValueError)):m.import_history(self.path,rows,self.h,'a'*64)
  self.assertEqual(len(self.totals()),1)
if __name__=='__main__':unittest.main()
