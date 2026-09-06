import unittest
from decimal import Decimal as D
from domain import daily,project_month,fx_convert,portfolio
class DomainTests(unittest.TestCase):
 def test_net_order(self):
  x=daily('100','-60','.02','.1','.05');self.assertEqual(x['net'],D('88.2'));self.assertEqual(x['profit'],D('23.79'))
 def test_new_site_and_country_dynamic(self):
  rows=[daily('100','-60','.02','.1','.05')];a=portfolio(rows,0,0,5)
  rows.append(daily('100','-60','.02','.1','.05'));b=portfolio(rows,0,0,5)
  self.assertEqual(b['profit'],a['profit']*2)
 def test_blank_zero_distinct(self):
  self.assertEqual(daily('',0,0,0,0)['net'],'');self.assertEqual(daily(0,0,0,0,0)['net'],0)
 def test_currency_direction(self):
  self.assertEqual(fx_convert('140','CAD',{'USDCAD':'1.4'}),100)
 def test_no_future_projection(self):
  self.assertEqual(project_month('100','2026-08-01','2026-09-05'),100)
  self.assertEqual(project_month('100','2026-08-01','2026-08-01'),'')
 def test_month_lengths(self):
  for start,asof,days in [('2024-02-01','2024-02-02',29),('2025-02-01','2025-02-02',28),('2026-04-01','2026-04-02',30),('2026-08-01','2026-08-02',31)]:self.assertEqual(project_month('10',start,asof),D(10)*days)
if __name__=='__main__':unittest.main()
