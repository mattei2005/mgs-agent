import datetime as dt
import importlib.util
import pathlib
import unittest
from zoneinfo import ZoneInfo

PATH=pathlib.Path(__file__).resolve().parents[1]/'deploy'/'cron_stdlib.py'
SPEC=importlib.util.spec_from_file_location('cron_stdlib_under_test',PATH)
assert SPEC and SPEC.loader
cron=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(cron)

class CronStdlibTest(unittest.TestCase):
 def setUp(self): self.tz=ZoneInfo('America/New_York')
 def test_dense_and_weekly_expansion(self):
  start=dt.datetime(2026,9,13,tzinfo=self.tz);end=dt.datetime(2026,9,21,tzinfo=self.tz)
  self.assertEqual(len(cron.cron_dates_between('*/15 * * * *',start,end,self.tz)),768)
  self.assertEqual([x.day for x in cron.cron_dates_between('30 3 * * 0',start,end,self.tz)],[13,20])
 def test_fall_back_hour_is_expanded_twice(self):
  start=dt.datetime(2026,10,31,tzinfo=self.tz);end=dt.datetime(2026,11,3,tzinfo=self.tz)
  rows=cron.cron_dates_between('30 1 * * *',start,end,self.tz)
  self.assertEqual(len(rows),4)
  self.assertEqual([x.utcoffset() for x in rows if x.date()==dt.date(2026,11,1)],[dt.timedelta(hours=-4),dt.timedelta(hours=-5)])
 def test_invalid_expressions_fail_closed(self):
  now=dt.datetime(2026,9,13,tzinfo=self.tz)
  for expr in ('* * * *','60 * * * *','*/0 * * * *','@daily','MON * * * *'):
   with self.assertRaises(ValueError): cron.cron_dates_between(expr,now,now+dt.timedelta(days=1),self.tz)

if __name__=='__main__': unittest.main()
