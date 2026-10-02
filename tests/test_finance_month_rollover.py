import importlib.util,unittest,datetime,pathlib,sys
from zoneinfo import ZoneInfo
p=pathlib.Path('/root/mgs-agent/scripts/finance-month-rollover.py');spec=importlib.util.spec_from_file_location('rollover',p);assert spec and spec.loader;m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class CalendarTests(unittest.TestCase):
 def test_last_day_leap_and_year(self):
  for day,want in [('2026-10-31','2026-11'),('2026-11-30','2026-12'),('2026-12-31','2027-01'),('2028-02-29','2028-03')]:
   now=datetime.datetime.fromisoformat(day+'T23:04:00').replace(tzinfo=ZoneInfo('America/New_York'));self.assertEqual(m.selection(now,scheduled=True),(day[:7],want))
 def test_other_days_noop(self):
  for day in ['2026-10-02','2026-10-30','2026-11-29','2028-02-28']:
   now=datetime.datetime.fromisoformat(day+'T23:04:00').replace(tzinfo=m.TZ);self.assertIsNone(m.selection(now,scheduled=True))
 def test_first_import_can_finish_prior_month_on_day_one(self):
  now=datetime.datetime(2026,11,1,8,3,tzinfo=m.TZ);self.assertEqual(m.selection(now,ensure='2026-10'),('2026-09','2026-10'));self.assertEqual(m.selection(now,ensure='2026-11'),('2026-10','2026-11'))
if __name__=='__main__':unittest.main()
