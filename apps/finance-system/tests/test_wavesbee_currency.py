"""Real graph, synthetic inputs ONLY in isolated worker; source stays immutable."""
import unittest,json,pathlib,copy
from decimal import Decimal as D
from worker import run
ROOT=pathlib.Path(__file__).resolve().parents[1]
ROW={'kind':'site','id':'site-wavesbee-principal','name':'WavesBee','new':False,'status':'INATIVO','network':'SB Rede1','input_currency':'CAD','currency_policy':'wavesbee-cad-1546607083468623912'}
class WavesbeeTests(unittest.TestCase):
 def test_authorized_months_real_conversion_and_downstream(self):
  source=(ROOT/'private/source.json').read_bytes()
  for period in ['2026-08','2026-09']:
   with self.subTest(period=period):
    r=run({'period':period,'as_of':'2026-10-01','additions':[ROW], 'overrides':{'principal|Agosto 2026|GP5':'140','principal|Agosto 2026|H1':'1.4','principal|Agosto 2026|I1':'1.3395'}})
    self.assertEqual(D(r['results']['principal|Agosto 2026|GQ5']['actual']),D('100'))
    f=next(f for f in r['domain']['facts'] if f['site']=='WavesBee' and f['date']==period+'-01')
    self.assertEqual(D(f['gross']),D('100'));self.assertEqual(D(f['invalid']),-D('100')*D(f['invalid_rate']))
    self.assertEqual(r['summary']['counts'].get('error',0),0)
  self.assertEqual((ROOT/'private/source.json').read_bytes(),source)
 def test_without_authorized_month_record_retains_gbp(self):
  r=run({'period':'2026-10','overrides':{'principal|Agosto 2026|GP5':'100','principal|Agosto 2026|I1':'1.3'}})
  self.assertEqual(D(r['results']['principal|Agosto 2026|GQ5']['actual']),D('130'))
if __name__=='__main__':unittest.main()
