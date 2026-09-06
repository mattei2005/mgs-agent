import unittest,json,pathlib,calendar
from decimal import Decimal as D
import worker
class PeriodTests(unittest.TestCase):
 def test_september_has_no_august_movements(self):
  r=worker.run({'period':'2026-09','as_of':'2026-09-16'});d=r['domain']
  self.assertEqual({f['date'][:7] for f in d['facts']},{'2026-09'})
  self.assertEqual(max(f['date'] for f in d['facts']),'2026-09-30')
  self.assertEqual(D(d['cash']['gross']),0);self.assertEqual(D(d['cash']['spend']),0);self.assertEqual(D(d['cash']['company_expenses']),0)
 def test_february_rejects_nonexistent_day_and_projects_28(self):
  r=worker.run({'period':'2027-02','as_of':'2027-02-15','overrides':{'principal|Agosto 2026|KU5':'100','principal|Agosto 2026|H1':'1.38405'}})
  d=r['domain'];self.assertEqual(max(f['date'] for f in d['facts']),'2027-02-28');self.assertEqual(D(d['cash']['gross']),100)
  with self.assertRaises(ValueError):worker.run({'period':'2027-02','overrides':{'principal|Agosto 2026|KT35':'10'}})
 def test_month_rejects_outside_registered_range(self):
  with self.assertRaises(ValueError):worker.run({'period':'2028-01'})
if __name__=='__main__':unittest.main()
